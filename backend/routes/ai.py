"""AI research assistant endpoint (local development; not for public deployment yet).

POST /ai/chat follows the existing route convention (no /api prefix).

This module imports only Pydantic-based configuration and schemas. LangChain
and the agent are imported lazily inside the default runner, so the
application starts and serves every existing route without AI packages, and
a disabled or unconfigured assistant returns 503 without contacting OpenAI.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from backend.ai.agent.config import AgentConfig, AgentConfigError, load_agent_config
from backend.ai.agent.schemas import ChatRequest, ChatResponse, ErrorInfo

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


def _unavailable(request_id: str, config: AgentConfig, message: str) -> JSONResponse:
    body = ChatResponse(request_id=request_id, status="unavailable", model=config.model,
                        error=ErrorInfo(type="unavailable", message=message))
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=body.model_dump(mode="json"))


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask the Nobel Explorer AI research assistant",
    responses={
        422: {"description": "Invalid question"},
        502: {"description": "Language model provider error"},
        503: {"description": "Assistant disabled, unconfigured or AI packages missing"},
    },
)
async def chat(
    payload: ChatRequest,
    config: AgentConfig = Depends(get_agent_config),
    runner: AgentRunner = Depends(get_agent_runner),
):
    request_id = uuid.uuid4().hex
    if len(payload.question) > config.max_question_chars:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail=f"question must be at most {config.max_question_chars} characters")
    available, reason = config.availability()
    if not available:
        return _unavailable(request_id, config, reason)
    try:
        result = await runner(payload.question, config, request_id)
    except ImportError:
        return _unavailable(request_id, config, "AI packages are not installed on this server.")
    except ValueError as exc:  # AgentInputError
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)[:300]) from None

    if result.status == "error":
        code = (status.HTTP_502_BAD_GATEWAY if result.error and result.error.type.startswith("provider_")
                else status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        code = STATUS_CODES.get(result.status, status.HTTP_200_OK)
    return JSONResponse(status_code=code, content=result.model_dump(mode="json"))
