"""Production safeguards for POST /ai/chat: rate limits, daily caps, spending guard,
concurrency, outer timeout and request-body size. All model calls are mocked."""

import asyncio

import pytest

httpx = pytest.importorskip("httpx")  # TestClient needs it; absent from the base (non-AI) environment

from fastapi.testclient import TestClient  # noqa: E402

from backend.ai import guard as guard_module  # noqa: E402
from backend.ai.agent.config import AgentConfig  # noqa: E402
from backend.ai.agent.schemas import ChatResponse, Usage  # noqa: E402
from backend.ai.guard import AIGuard, GuardConfig, Rejection, Ticket, client_ip  # noqa: E402
from backend.main import app  # noqa: E402
from backend.routes import ai as ai_route  # noqa: E402

QUESTION = {"question": "Who won the 2022 Nobel Prize in Chemistry?"}
LIMITS = dict(per_ip_per_minute=5, per_ip_per_day=50, global_per_day=100, max_concurrent=2,
              daily_spend_limit_usd=1.0, monthly_spend_limit_usd=10.0)


class Clock:
    def __init__(self, now=1_798_761_600.0):  # 2027-01-01T00:00:00Z
        self.now = now

    def __call__(self):
        return self.now


def _usage(input_tokens=6000, cached=4500, output=80):
    return Usage(input_tokens=input_tokens, cached_input_tokens=cached, output_tokens=output,
                 total_tokens=input_tokens + output)


def _completed(request_id, usage=None, model_calls=2):
    return ChatResponse(request_id=request_id, status="completed", model="gpt-6-luna", answer="ok",
                        grounding="no_evidence", model_calls=model_calls, usage=usage)


@pytest.fixture()
def setup():
    """Returns a function installing a guard and a runner on the real app."""
    def install(runner=None, guard=None, config=None):
        guard = guard or AIGuard(GuardConfig(**LIMITS), clock=Clock())
        app.dependency_overrides[ai_route.get_ai_guard] = lambda: guard
        app.dependency_overrides[ai_route.get_agent_config] = lambda: config or AgentConfig(
            enabled=True, openai_api_key="sk-test-not-real")

        async def default(question, cfg, request_id):
            return _completed(request_id, usage=_usage())

        app.dependency_overrides[ai_route.get_agent_runner] = lambda: runner or default
        return guard

    yield install
    app.dependency_overrides.clear()


def _post(client, ip=None, **kwargs):
    headers = {"X-Real-IP": ip} if ip else {}
    return client.post("/ai/chat", json=QUESTION, headers=headers, **kwargs)


# ---------------------------------------------------------------- per-client and global limits

def test_per_ip_minute_limit_then_window_slides(setup):
    clock = Clock()
    guard = setup(guard=AIGuard(GuardConfig(**LIMITS, client_ip_header="x-real-ip"), clock=clock))
    client = TestClient(app)
    assert [_post(client, "203.0.113.7").status_code for _ in range(5)] == [200] * 5
    blocked = _post(client, "203.0.113.7")
    assert blocked.status_code == 429 and 1 <= int(blocked.headers["retry-after"]) <= 60
    body = blocked.json()  # a ChatResponse the existing page can render
    assert body["status"] == "unavailable" and body["error"]["type"] == "ip_minute_limit"
    assert _post(client, "203.0.113.8").status_code == 200  # other clients unaffected
    clock.now += 61
    assert _post(client, "203.0.113.7").status_code == 200
    assert guard.snapshot()["global_today"] == 7


def test_per_ip_daily_limit():
    clock = Clock()
    guard = AIGuard(GuardConfig(**{**LIMITS, "per_ip_per_minute": 1000}), clock=clock)
    for _ in range(50):
        guard.admit("198.51.100.1", 0.0).finish(0.0)
    rejected = guard.admit("198.51.100.1", 0.0)
    assert isinstance(rejected, Rejection) and rejected.reason == "ip_daily_limit"
    assert isinstance(guard.admit("198.51.100.2", 0.0), Ticket)


def test_global_daily_limit_and_utc_midnight_reset():
    clock = Clock()
    guard = AIGuard(GuardConfig(**LIMITS), clock=clock)
    for n in range(100):
        guard.admit(f"10.0.{n // 5}.{n % 5}", 0.0).finish(0.0)
    rejected = guard.admit("10.9.9.9", 0.0)
    assert isinstance(rejected, Rejection) and rejected.reason == "global_daily_limit"
    clock.now += 86_400
    assert isinstance(guard.admit("10.9.9.9", 0.0), Ticket)
    assert guard.snapshot()["global_today"] == 1


def test_rejected_requests_are_not_counted_or_stored():
    guard = AIGuard(GuardConfig(**{**LIMITS, "max_concurrent": 1}), clock=Clock())
    held = guard.admit("1.1.1.1", 0.0)
    for n in range(20):
        assert guard.admit(f"2.2.2.{n}", 0.0).reason == "busy"
    snap = guard.snapshot()
    assert snap["global_today"] == 1 and snap["clients_today"] == 1
    held.finish(0.0)


def test_disabled_assistant_consumes_no_quota(setup, monkeypatch):
    guard = setup()
    app.dependency_overrides[ai_route.get_agent_config] = lambda: AgentConfig(enabled=False)
    client = TestClient(app)
    assert all(_post(client).status_code == 503 for _ in range(8))
    assert guard.snapshot()["global_today"] == 0


def test_invalid_question_consumes_no_quota(setup):
    guard = setup()
    client = TestClient(app)
    assert client.post("/ai/chat", json={"question": ""}).status_code == 422
    assert guard.snapshot()["global_today"] == 0


# ---------------------------------------------------------------- client address

def test_forwarded_headers_ignored_unless_configured():
    headers = {"x-real-ip": "203.0.113.9", "x-forwarded-for": "6.6.6.6"}
    assert client_ip("100.64.0.2", headers, "") == "100.64.0.2"
    assert client_ip("100.64.0.2", headers, "x-real-ip") == "203.0.113.9"
    # Invalid or missing header falls back to the peer (fail safe: one shared bucket).
    assert client_ip("100.64.0.2", {"x-real-ip": "1.2.3.4, 5.6.7.8"}, "x-real-ip") == "100.64.0.2"
    assert client_ip("100.64.0.2", {}, "x-real-ip") == "100.64.0.2"
    assert client_ip("100.64.0.2", {"x-real-ip": "2001:DB8::1"}, "x-real-ip") == "2001:db8::1"


def test_spoofed_header_cannot_evade_limit_when_not_trusted(setup):
    setup()  # default: no trusted header, so every request is the TestClient peer
    client = TestClient(app)
    codes = [_post(client, f"203.0.113.{n}").status_code for n in range(6)]
    assert codes == [200] * 5 + [429]


# ---------------------------------------------------------------- spending guard

def test_worst_case_matches_the_documented_gate():
    assert GuardConfig().worst_case_cost(6, 800) == pytest.approx(0.0144)


def test_usage_cost_uses_cached_rate():
    cost = GuardConfig().usage_cost(_usage(input_tokens=35888, cached=27443, output=454))
    assert cost == pytest.approx(0.00134593, rel=1e-6)  # the measured Phase 4E.2 total


def test_reservations_prevent_overshooting_the_daily_cap():
    guard = AIGuard(GuardConfig(**{**LIMITS, "daily_spend_limit_usd": 0.03, "max_concurrent": 10}), clock=Clock())
    first, second = guard.admit("a", 0.0144), guard.admit("b", 0.0144)
    assert isinstance(first, Ticket) and isinstance(second, Ticket)
    third = guard.admit("c", 0.0144)
    assert isinstance(third, Rejection) and third.reason == "spend_limit" and third.status_code == 503
    first.finish(0.0002)  # actual cost replaces the reservation
    assert isinstance(guard.admit("c", 0.0144), Ticket)


def test_unknown_usage_keeps_the_full_reservation():
    guard = AIGuard(GuardConfig(**LIMITS), clock=Clock())
    guard.admit("a", 0.0144).finish(None)
    assert guard.snapshot()["spent_day_usd"] == pytest.approx(0.0144)


def test_monthly_cap_survives_day_rollover_but_not_month_rollover():
    clock = Clock()
    guard = AIGuard(GuardConfig(**{**LIMITS, "monthly_spend_limit_usd": 0.02}), clock=clock)
    guard.admit("a", 0.0).finish(0.015)
    clock.now += 86_400
    assert guard.admit("a", 0.01).reason == "spend_limit"
    clock.now += 31 * 86_400
    assert isinstance(guard.admit("a", 0.01), Ticket)


PER_CALL = GuardConfig().worst_case_cost(1, 800)  # 0.0024


def test_route_charges_actual_usage(setup):
    guard = setup()
    assert _post(TestClient(app)).status_code == 200
    assert guard.snapshot()["spent_day_usd"] == pytest.approx(GuardConfig().usage_cost(_usage()), abs=1e-6)
    assert guard.snapshot()["reserved_usd"] == 0


@pytest.mark.parametrize("status,error_type,usage,model_calls,expected", [
    ("completed", None, None, 3, 3 * PER_CALL),               # calls without reported usage: worst case each
    ("timeout", "timeout", None, 0, PER_CALL),                  # the call in flight may be billed
    ("timeout", "deadline_exceeded", _usage(), 2, GuardConfig().usage_cost(_usage()) + PER_CALL),
    ("error", "provider_timeout", None, 0, PER_CALL),
    ("error", "provider_error", None, 1, 2 * PER_CALL),
    ("error", "internal_error", None, 0, PER_CALL),
    ("error", "provider_unavailable", None, 0, 0.0),            # never reached the provider
    ("error", "provider_auth", None, 0, 0.0),
    ("error", "provider_rate_limited", None, 0, 0.0),
    ("budget_exhausted", "model_call_limit", _usage(), 6, GuardConfig().usage_cost(_usage())),
])
def test_conservative_request_cost(status, error_type, usage, model_calls, expected):
    from backend.ai.agent.schemas import ErrorInfo
    from backend.ai.guard import request_cost

    response = ChatResponse(request_id="r", status=status, model="gpt-6-luna", usage=usage, model_calls=model_calls,
                            error=ErrorInfo(type=error_type, message="x") if error_type else None)
    assert request_cost(GuardConfig(), response, 800) == pytest.approx(expected)


def test_provider_outage_does_not_exhaust_the_daily_budget(setup):
    from backend.ai.agent.schemas import ErrorInfo

    async def unreachable(question, cfg, request_id):
        return ChatResponse(request_id=request_id, status="error", model="gpt-6-luna",
                            error=ErrorInfo(type="provider_unavailable", message="x"))

    guard = setup(runner=unreachable, guard=AIGuard(GuardConfig(**{**LIMITS, "daily_spend_limit_usd": 0.03,
                                                                    "client_ip_header": "x-real-ip"})))
    client = TestClient(app)
    assert [_post(client, f"203.0.113.{n}").status_code for n in range(10)] == [502] * 10
    assert guard.snapshot()["spent_day_usd"] == 0


def test_runner_crash_releases_slot_and_keeps_reservation(setup):
    async def crash(question, cfg, request_id):
        raise RuntimeError("boom")

    guard = setup(runner=crash)
    with pytest.raises(RuntimeError):
        _post(TestClient(app))
    snap = guard.snapshot()
    assert snap["in_flight"] == 0 and snap["spent_day_usd"] == pytest.approx(0.0144)


# ---------------------------------------------------------------- concurrency and timeouts

async def _async_post(client, ip="203.0.113.1"):
    return await client.post("/ai/chat", json=QUESTION, headers={"X-Real-IP": ip})


def test_third_concurrent_request_is_rejected_immediately(setup):
    async def scenario():
        release = asyncio.Event()
        started = 0

        async def slow(question, cfg, request_id):
            nonlocal started
            started += 1
            await release.wait()
            return _completed(request_id, usage=_usage())

        guard = setup(runner=slow, guard=AIGuard(GuardConfig(**LIMITS, client_ip_header="x-real-ip")))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first = asyncio.create_task(_async_post(client, "203.0.113.1"))
            second = asyncio.create_task(_async_post(client, "203.0.113.2"))
            while started < 2:
                await asyncio.sleep(0.01)
            third = await _async_post(client, "203.0.113.3")
            assert third.status_code == 429 and third.json()["error"]["type"] == "busy"
            assert guard.snapshot()["in_flight"] == 2
            release.set()
            assert [r.status_code for r in await asyncio.gather(first, second)] == [200, 200]
            assert guard.snapshot()["in_flight"] == 0
            assert (await _async_post(client, "203.0.113.3")).status_code == 200
        assert started == 3

    asyncio.run(scenario())


def test_hung_request_is_timed_out_and_frees_its_slot(setup, monkeypatch):
    monkeypatch.setattr(ai_route, "OUTER_TIMEOUT_GRACE_SECONDS", -4.8)  # 5 s agent limit -> 0.2 s
    cancelled = []

    async def hang(question, cfg, request_id):
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            cancelled.append(request_id)
            raise

    guard = setup(runner=hang, config=AgentConfig(enabled=True, openai_api_key="sk-test-not-real",
                                                  max_duration_seconds=5, provider_timeout_seconds=1))
    response = _post(TestClient(app))
    assert response.status_code == 200 and response.json()["status"] == "timeout"
    assert len(cancelled) == 1  # the agent task was cancelled, not left running
    snap = guard.snapshot()
    assert snap["in_flight"] == 0 and snap["spent_day_usd"] == pytest.approx(0.0144)


def test_client_disconnect_keeps_slot_until_the_agent_stops(setup):
    """Real uvicorn server: a client that gives up cannot free its slot early and
    retry into a second one; the slot is freed when the agent itself finishes."""
    import socket
    import threading
    import time

    import uvicorn

    running, release = threading.Event(), threading.Event()

    async def slow(question, cfg, request_id):
        running.set()
        while not release.is_set():
            await asyncio.sleep(0.01)
        return _completed(request_id, usage=_usage())

    guard = setup(runner=slow, guard=AIGuard(GuardConfig(**{**LIMITS, "max_concurrent": 1})))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="off"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        while not server.started:
            time.sleep(0.01)
        url = f"http://127.0.0.1:{port}/ai/chat"
        with pytest.raises(httpx.TimeoutException):
            httpx.post(url, json=QUESTION, timeout=0.3)  # client gives up and disconnects
        assert running.is_set()
        retry = httpx.post(url, json=QUESTION, timeout=5)
        assert retry.status_code == 429 and retry.json()["error"]["type"] == "busy"
        release.set()
        for _ in range(200):
            if guard.snapshot()["in_flight"] == 0:
                break
            time.sleep(0.01)
        assert guard.snapshot()["in_flight"] == 0
        assert httpx.post(url, json=QUESTION, timeout=5).status_code == 200
    finally:
        release.set()
        server.should_exit = True
        thread.join(timeout=5)


def test_ticket_finish_is_idempotent():
    guard = AIGuard(GuardConfig(**LIMITS), clock=Clock())
    ticket = guard.admit("a", 0.01)
    ticket.finish(0.001)
    ticket.finish(0.001)
    snap = guard.snapshot()
    assert snap["in_flight"] == 0 and snap["spent_day_usd"] == pytest.approx(0.001)


# ---------------------------------------------------------------- request body size

def test_oversized_body_rejected_before_parsing(setup):
    guard = setup()
    client = TestClient(app)
    big = '{"question": "' + "x" * 20_000 + '"}'
    response = client.post("/ai/chat", content=big, headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    assert guard.snapshot()["global_today"] == 0


def test_streamed_body_without_length_is_counted(setup):
    setup()
    client = TestClient(app)

    def chunks():
        yield b'{"question": "'
        for _ in range(40):
            yield b"x" * 1000
        yield b'"}'

    response = client.post("/ai/chat", content=chunks(), headers={"Content-Type": "application/json"})
    assert response.status_code == 413


def test_normal_body_and_other_routes_unaffected(setup):
    setup()
    client = TestClient(app)
    assert _post(client).status_code == 200
    assert client.get("/health").json() == {"status": "healthy"}


# ---------------------------------------------------------------- configuration

def test_limits_configurable_through_environment(monkeypatch):
    for name, value in {"AI_RATE_PER_IP_PER_MINUTE": "3", "AI_RATE_PER_IP_PER_DAY": "20",
                        "AI_GLOBAL_DAILY_LIMIT": "40", "AI_MAX_CONCURRENT_REQUESTS": "1",
                        "AI_MAX_BODY_BYTES": "4096", "AI_CLIENT_IP_HEADER": " X-Real-IP ",
                        "AI_DAILY_SPEND_LIMIT_USD": "0.05", "AI_MONTHLY_SPEND_LIMIT_USD": "0.5"}.items():
        monkeypatch.setenv(name, value)
    cfg = GuardConfig.from_env()
    assert (cfg.per_ip_per_minute, cfg.per_ip_per_day, cfg.global_per_day, cfg.max_concurrent,
            cfg.max_body_bytes, cfg.client_ip_header) == (3, 20, 40, 1, 4096, "x-real-ip")
    assert (cfg.daily_spend_limit_usd, cfg.monthly_spend_limit_usd) == (0.05, 0.5)


def test_defaults_match_the_approved_limits(monkeypatch):
    for name in ("AI_RATE_PER_IP_PER_MINUTE", "AI_RATE_PER_IP_PER_DAY", "AI_GLOBAL_DAILY_LIMIT",
                 "AI_MAX_CONCURRENT_REQUESTS", "AI_CLIENT_IP_HEADER", "AI_DAILY_SPEND_LIMIT_USD",
                 "AI_MONTHLY_SPEND_LIMIT_USD", "AI_RESERVE_INPUT_TOKENS_PER_CALL", "AI_PRICE_INPUT_PER_MTOK",
                 "AI_PRICE_OUTPUT_PER_MTOK"):
        monkeypatch.delenv(name, raising=False)
    cfg = GuardConfig.from_env()
    assert (cfg.per_ip_per_minute, cfg.per_ip_per_day, cfg.global_per_day, cfg.max_concurrent,
            cfg.client_ip_header) == (5, 50, 100, 2, "")
    # Two concurrent worst-case reservations fit within the daily cap, and 30 days stay under $1.
    assert 2 * cfg.worst_case_cost(6, 800) < cfg.daily_spend_limit_usd
    assert cfg.monthly_spend_limit_usd < 1.0


@pytest.mark.parametrize("name,value", [("AI_MAX_CONCURRENT_REQUESTS", "0"), ("AI_GLOBAL_DAILY_LIMIT", "-1"),
                                        ("AI_DAILY_SPEND_LIMIT_USD", "nan"), ("AI_RATE_PER_IP_PER_DAY", "lots")])
def test_invalid_limit_fails_closed_for_ai_only(name, value, monkeypatch):
    monkeypatch.setenv(name, value)
    monkeypatch.setattr(guard_module, "_guard", None)
    client = TestClient(app)
    app.dependency_overrides[ai_route.get_agent_config] = lambda: AgentConfig(
        enabled=True, openai_api_key="sk-test-not-real")
    try:
        assert client.post("/ai/chat", json=QUESTION).status_code == 503
        assert client.get("/health").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_full_server_reports_busy_before_spend_limit():
    guard = AIGuard(GuardConfig(**{**LIMITS, "daily_spend_limit_usd": 0.03}), clock=Clock())
    guard.admit("a", 0.0144), guard.admit("b", 0.0144)
    assert guard.admit("c", 0.0144).reason == "busy"
