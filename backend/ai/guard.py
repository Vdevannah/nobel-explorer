"""Production safeguards for POST /ai/chat (standard library only).

Admission happens before any model call and checks, atomically:

* per-client limits: questions per minute (sliding 60 s window) and per UTC day;
* a global limit of questions per UTC day;
* a conservative spending guard (daily and monthly USD caps);
* a concurrency limit (requests in flight). A full server is rejected at once
  with 429 instead of queueing, so held connections cannot pile up.

Only admitted requests are counted, and per-client state is kept only for
admitted clients, so memory is bounded by the global daily limit.

Spending guard. Each admitted request first reserves its WORST-CASE cost
(max model calls x (reserved input tokens + max output tokens) at the configured
prices). When it finishes, the reservation is replaced by ``request_cost``: the
cost of the reported token usage (worst case per call for completed calls that
reported none), plus one worst-case call when the request ended in a timeout or
an error the provider may still bill. Errors the provider rejects before
billing (authentication, connection, rate limit, bad request) add nothing. If
the agent crashes or hangs, the full reservation is kept. A request is admitted
only if spent + reserved + its own reservation stays within both caps, so
concurrent requests can never overshoot them.

Counters live in process memory. They RESET when the process restarts or is
redeployed, and each replica keeps its own. Deploy a single replica, and treat
the OpenAI project budget as the backstop that survives restarts.

Concurrency. The slot is released only in ``finally`` after the agent task has
finished or been cancelled. The route also wraps the agent in an outer time
limit, so a hung or timed-out request always frees its slot, and a client that
disconnects and retries cannot obtain a second slot while its first request is
still running.
"""

from __future__ import annotations

import ipaddress
import math
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    value = int(raw)
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    value = float(raw)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a non-negative number")
    return value


@dataclass(frozen=True)
class GuardConfig:
    per_ip_per_minute: int = 5
    per_ip_per_day: int = 50
    global_per_day: int = 100
    max_concurrent: int = 2
    max_body_bytes: int = 16_384
    # Empty: use the TCP peer address. On Railway set to "x-real-ip" (the edge
    # overwrites it on every public request); never trust a header you have not verified.
    client_ip_header: str = ""
    # Spending guard (USD). Prices are per 1M tokens (gpt-6-luna, Standard tier).
    daily_spend_limit_usd: float = 0.05
    monthly_spend_limit_usd: float = 0.90
    price_input_per_mtok: float = 0.10
    price_cached_input_per_mtok: float = 0.01
    price_output_per_mtok: float = 0.50
    reserve_input_tokens_per_call: int = 20_000

    @classmethod
    def from_env(cls) -> "GuardConfig":
        return cls(
            per_ip_per_minute=_env_int("AI_RATE_PER_IP_PER_MINUTE", cls.per_ip_per_minute, 1),
            per_ip_per_day=_env_int("AI_RATE_PER_IP_PER_DAY", cls.per_ip_per_day, 1),
            global_per_day=_env_int("AI_GLOBAL_DAILY_LIMIT", cls.global_per_day, 1),
            max_concurrent=_env_int("AI_MAX_CONCURRENT_REQUESTS", cls.max_concurrent, 1),
            max_body_bytes=_env_int("AI_MAX_BODY_BYTES", cls.max_body_bytes, 256),
            client_ip_header=os.getenv("AI_CLIENT_IP_HEADER", "").strip().lower(),
            daily_spend_limit_usd=_env_float("AI_DAILY_SPEND_LIMIT_USD", cls.daily_spend_limit_usd),
            monthly_spend_limit_usd=_env_float("AI_MONTHLY_SPEND_LIMIT_USD", cls.monthly_spend_limit_usd),
            price_input_per_mtok=_env_float("AI_PRICE_INPUT_PER_MTOK", cls.price_input_per_mtok),
            price_cached_input_per_mtok=_env_float("AI_PRICE_CACHED_INPUT_PER_MTOK", cls.price_cached_input_per_mtok),
            price_output_per_mtok=_env_float("AI_PRICE_OUTPUT_PER_MTOK", cls.price_output_per_mtok),
            reserve_input_tokens_per_call=_env_int("AI_RESERVE_INPUT_TOKENS_PER_CALL",
                                                   cls.reserve_input_tokens_per_call, 1),
        )

    def worst_case_cost(self, max_model_calls: int, max_output_tokens: int) -> float:
        per_call = (self.reserve_input_tokens_per_call * self.price_input_per_mtok
                    + max_output_tokens * self.price_output_per_mtok) / 1_000_000
        return max_model_calls * per_call

    def usage_cost(self, usage) -> float:
        cached = min(usage.cached_input_tokens, usage.input_tokens)
        return ((usage.input_tokens - cached) * self.price_input_per_mtok
                + cached * self.price_cached_input_per_mtok
                + usage.output_tokens * self.price_output_per_mtok) / 1_000_000


# Provider errors raised before a request is processed; OpenAI does not bill them.
UNBILLED_ERROR_TYPES = frozenset({"provider_unavailable", "provider_auth", "provider_rate_limited",
                                  "provider_model_not_found", "provider_bad_request", "unavailable"})


def request_cost(config: GuardConfig, response, max_output_tokens: int) -> float:
    """Conservative cost of a finished agent run (see the module docstring)."""
    per_call = config.worst_case_cost(1, max_output_tokens)
    if response.usage is not None:
        cost = config.usage_cost(response.usage)
    else:
        cost = per_call * response.model_calls
    error_type = response.error.type if response.error else None
    if response.status == "timeout" or (response.status == "error" and error_type not in UNBILLED_ERROR_TYPES):
        cost += per_call  # a call in flight when the request ended may still be billed
    return cost


def client_ip(peer: str | None, headers, header_name: str) -> str:
    """Client address for rate limiting. A configured header is used only if it
    holds one valid IP; otherwise the TCP peer is used (fails safe: behind a
    proxy every client then shares one bucket)."""
    if header_name:
        raw = (headers.get(header_name) or "").strip()
        try:
            return str(ipaddress.ip_address(raw))
        except ValueError:
            pass
    return peer or "unknown"


@dataclass
class Rejection:
    status_code: int
    reason: str
    message: str
    retry_after: int


@dataclass
class _Client:
    minute: deque = field(default_factory=deque)
    day_count: int = 0


class Ticket:
    """Proof of admission; ``finish`` must be called exactly once (idempotent)."""

    def __init__(self, guard: "AIGuard", reservation: float, day: str, month: str):
        self._guard = guard
        self.reservation = reservation
        self._day, self._month = day, month
        self._done = False

    def finish(self, actual_cost: float | None) -> None:
        if self._done:
            return
        self._done = True
        self._guard._release(self, self.reservation if actual_cost is None else actual_cost)


class AIGuard:
    def __init__(self, config: GuardConfig, clock: Callable[[], float] = time.time):
        self.config = config
        self._clock = clock
        self._lock = threading.Lock()
        self._day = self._month = ""
        self._clients: dict[str, _Client] = {}
        self._global_today = 0
        self._spent_day = self._spent_month = 0.0
        self._reserved = 0.0
        self._in_flight = 0

    # -- periods ------------------------------------------------------------
    def _roll(self, now: float) -> tuple[str, str]:
        moment = datetime.fromtimestamp(now, tz=timezone.utc)
        day, month = moment.strftime("%Y-%m-%d"), moment.strftime("%Y-%m")
        if day != self._day:
            self._day, self._clients, self._global_today, self._spent_day = day, {}, 0, 0.0
        if month != self._month:
            self._month, self._spent_month = month, 0.0
        return day, month

    def _seconds_to_midnight(self, now: float) -> int:
        return max(1, int(86_400 - now % 86_400))

    # -- admission ----------------------------------------------------------
    def admit(self, ip: str, reservation: float) -> Ticket | Rejection:
        cfg = self.config
        with self._lock:
            now = self._clock()
            day, month = self._roll(now)
            client = self._clients.get(ip)
            if client is not None:
                while client.minute and now - client.minute[0] >= 60:
                    client.minute.popleft()
                if client.day_count >= cfg.per_ip_per_day:
                    return Rejection(429, "ip_daily_limit", "You have reached today's question limit. "
                                     "Please try again tomorrow.", self._seconds_to_midnight(now))
                if len(client.minute) >= cfg.per_ip_per_minute:
                    wait = max(1, math.ceil(60 - (now - client.minute[0])))
                    return Rejection(429, "ip_minute_limit", "You are asking questions too quickly. "
                                     "Please wait a moment and try again.", wait)
            if self._global_today >= cfg.global_per_day:
                return Rejection(429, "global_daily_limit", "Nobel Intelligence has reached its daily question "
                                 "limit. Please try again tomorrow.", self._seconds_to_midnight(now))
            if self._in_flight >= cfg.max_concurrent:
                return Rejection(429, "busy", "Nobel Intelligence is busy answering other questions. "
                                 "Please try again in a few seconds.", 5)
            if (self._spent_day + self._reserved + reservation > cfg.daily_spend_limit_usd
                    or self._spent_month + self._reserved + reservation > cfg.monthly_spend_limit_usd):
                # Retry-After is advisory: in-flight reservations may free budget sooner.
                return Rejection(503, "spend_limit", "Nobel Intelligence is temporarily unavailable. "
                                 "Please try again later.", self._seconds_to_midnight(now))

            client = self._clients.setdefault(ip, _Client())
            client.minute.append(now)
            client.day_count += 1
            self._global_today += 1
            self._in_flight += 1
            self._reserved += reservation
            return Ticket(self, reservation, day, month)

    def _release(self, ticket: Ticket, cost: float) -> None:
        with self._lock:
            self._in_flight -= 1
            self._reserved = max(0.0, self._reserved - ticket.reservation)
            self._roll(self._clock())
            # Charge the period the request was admitted in, if it is still current.
            if ticket._day == self._day:
                self._spent_day += cost
            if ticket._month == self._month:
                self._spent_month += cost

    def snapshot(self) -> dict:
        with self._lock:
            return {"in_flight": self._in_flight, "global_today": self._global_today,
                    "reserved_usd": round(self._reserved, 6), "spent_day_usd": round(self._spent_day, 6),
                    "spent_month_usd": round(self._spent_month, 6), "clients_today": len(self._clients)}


_guard: AIGuard | None = None
_guard_lock = threading.Lock()


def get_guard() -> AIGuard:
    global _guard
    with _guard_lock:
        if _guard is None:
            _guard = AIGuard(GuardConfig.from_env())
        return _guard


class BodySizeLimitMiddleware:
    """Pure ASGI middleware rejecting request bodies above ``max_bytes`` with 413
    for paths under ``prefix``. Checks Content-Length and also counts streamed
    (chunked) bodies, so a missing or false Content-Length cannot bypass it."""

    def __init__(self, app, max_bytes: int, prefix: str = "/ai/"):
        self.app, self.max_bytes, self.prefix = app, max_bytes, prefix

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith(self.prefix):
            await self.app(scope, receive, send)
            return
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    too_big = int(value) > self.max_bytes
                except ValueError:
                    too_big = True
                if too_big:
                    await _send_413(send)
                    return

        received = 0
        rejected = False
        started = False

        async def limited_receive():
            nonlocal received, rejected
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    rejected = True
                    raise _BodyTooLarge()
            return message

        async def guarded_send(message):
            # Once the limit is hit, the framework's own error response (for
            # example Starlette's 400 for an unreadable body) is replaced by 413.
            nonlocal started
            if rejected:
                return
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except Exception:
            # Frameworks may wrap the exception raised inside receive().
            if not rejected:
                raise
        if rejected and not started:
            await _send_413(send)


class _BodyTooLarge(Exception):
    pass


async def _send_413(send):
    body = b'{"detail":"Request body too large."}'
    await send({"type": "http.response.start", "status": 413,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})
