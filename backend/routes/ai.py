"""AI research assistant endpoint (Nobel Intelligence).

POST /ai/chat follows the existing route convention (no /api prefix).
Production safeguards (rate limits, daily caps, spending guard, concurrency
limit) are applied by ``backend.ai.guard`` after validation and availability
checks and before any model call; see that module for the reset semantics.

This module imports only Pydantic-based configuration and schemas. LangChain
and the agent are imported lazily inside the default runner, so the
application starts and serves every existing route without AI packages, and
a disabled or unconfigured assistant returns 503 without contacting OpenAI.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from backend.ai.agent.config import AgentConfig, AgentConfigError, load_agent_config
from backend.ai.agent.schemas import ChatRequest, ChatResponse, ErrorInfo
from backend.ai.guard import AIGuard, Rejection, client_ip, get_guard, request_cost

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Research Assistant"])

AgentRunner = Callable[[str, AgentConfig, str], Awaitable[ChatResponse]]

STATUS_CODES = {
    "completed": status.HTTP_200_OK,
    "budget_exhausted": status.HTTP_200_OK,   # controlled outcome with partial details
    "timeout": status.HTTP_200_OK,            # controlled outcome with partial details
    "unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
}


def get_agent_config() -> AgentConfig:
    try:
        return load_agent_config()
    except AgentConfigError as exc:
        logger.warning("AI agent configuration invalid")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from None


async def _default_runner(question: str, config: AgentConfig, request_id: str) -> ChatResponse:
    from backend.ai.agent.service import run_agent  # lazy: needs LangChain

    return await run_agent(question, config=config, request_id=request_id)


def get_agent_runner() -> AgentRunner:
    return _default_runner


def get_ai_guard() -> AIGuard:
    try:
        return get_guard()
    except ValueError as exc:  # invalid AI_* limit variable: fail closed for AI only
        logger.warning("AI guard configuration invalid")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from None


# Extra time allowed beyond the agent's own deadline before the route gives up,
# so a hung request can never hold a concurrency slot indefinitely.
OUTER_TIMEOUT_GRACE_SECONDS = 15.0


def _unavailable(request_id: str, config: AgentConfig, message: str) -> JSONResponse:
    body = ChatResponse(request_id=request_id, status="unavailable", model=config.model,
                        error=ErrorInfo(type="unavailable", message=message))
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=body.model_dump(mode="json"))


def _rejected(request_id: str, config: AgentConfig, rejection: Rejection) -> JSONResponse:
    # A ChatResponse body (status "unavailable") so the existing page renders it.
    body = ChatResponse(request_id=request_id, status="unavailable", model=config.model,
                        error=ErrorInfo(type=rejection.reason, message=rejection.message))
    return JSONResponse(status_code=rejection.status_code, content=body.model_dump(mode="json"),
                        headers={"Retry-After": str(rejection.retry_after)})


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask the Nobel Explorer AI research assistant",
    responses={
        413: {"description": "Request body too large"},
        422: {"description": "Invalid question"},
        429: {"description": "Rate limit, daily limit or concurrency limit reached"},
        502: {"description": "Language model provider error"},
        503: {"description": "Assistant disabled, unconfigured or AI packages missing"},
    },
)
async def chat(
    payload: ChatRequest,
    request: Request,
    config: AgentConfig = Depends(get_agent_config),
    runner: AgentRunner = Depends(get_agent_runner),
    guard: AIGuard = Depends(get_ai_guard),
):
    request_id = uuid.uuid4().hex
    if len(payload.question) > config.max_question_chars:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail=f"question must be at most {config.max_question_chars} characters")
    available, reason = config.availability()
    if not available:
        return _unavailable(request_id, config, reason)

    ip = client_ip(request.client.host if request.client else None, request.headers,
                   guard.config.client_ip_header)
    ticket = guard.admit(ip, guard.config.worst_case_cost(config.max_model_calls, config.max_output_tokens))
    if isinstance(ticket, Rejection):
        logger.info("ai request %s rejected: %s", request_id, ticket.reason)
        return _rejected(request_id, config, ticket)

    cost: float | None = None  # None keeps the full worst-case reservation
    try:
        result = await asyncio.wait_for(runner(payload.question, config, request_id),
                                        timeout=config.max_duration_seconds + OUTER_TIMEOUT_GRACE_SECONDS)
        cost = request_cost(guard.config, result, config.max_output_tokens)
    except ImportError:
        cost = 0.0
        return _unavailable(request_id, config, "AI packages are not installed on this server.")
    except ValueError as exc:  # AgentInputError
        cost = 0.0
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)[:300]) from None
    except asyncio.TimeoutError:
        logger.warning("ai request %s exceeded the outer time limit", request_id)
        body = ChatResponse(request_id=request_id, status="timeout", model=config.model,
                            answer="I could not finish within the time limit. Please try a narrower question.",
                            error=ErrorInfo(type="timeout", message="The request exceeded the configured time limit."))
        return JSONResponse(status_code=status.HTTP_200_OK, content=body.model_dump(mode="json"))
    finally:
        ticket.finish(cost)

    if result.status == "error":
        code = (status.HTTP_502_BAD_GATEWAY if result.error and result.error.type.startswith("provider_")
                else status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        code = STATUS_CODES.get(result.status, status.HTTP_200_OK)
    return JSONResponse(status_code=code, content=result.model_dump(mode="json"))
