"""Environment-driven, validated configuration for the research agent.

Importing this module needs only Pydantic, so the FastAPI app can read the
configuration (and report "unavailable") without LangChain installed.

Defaults (conservative MVP):
* AI_AGENT_ENABLED=false            the feature is off unless explicitly enabled
* OPENAI_MODEL=gpt-6-luna           OpenAI's named replacement for the deprecated
                                    gpt-4.1-mini (shutdown 2027-01-14)
* reasoning effort "none"           required by gpt-6-luna for function calling on
                                    Chat Completions (AI_AGENT_REASONING_EFFORT=unset
                                    omits it, for non-reasoning models)
* temperature unset                 gpt-6-luna documentation does not state whether
                                    temperature is accepted, so it is not sent
* max_question_chars=1000           long enough for multi-part questions
* max_model_calls=6                 1 planning call + up to 4 tool rounds + 1 answer
* max_tool_calls=8                  per request, counting every requested call,
                                    including parallel calls in one model response
* max_duration_seconds=45           hard wall-clock limit for the whole request
* max_output_tokens=800             per model call; keeps answers concise
* provider_timeout_seconds=20       per HTTP request to the provider
* provider_max_retries=1            one retry for transient provider failures
"""

from __future__ import annotations

import os
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, model_validator

_MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")

ENV_VARS = {
    "enabled": "AI_AGENT_ENABLED",
    "openai_api_key": "OPENAI_API_KEY",
    "model": "OPENAI_MODEL",
    "max_question_chars": "AI_AGENT_MAX_QUESTION_CHARS",
    "max_model_calls": "AI_AGENT_MAX_MODEL_CALLS",
    "max_tool_calls": "AI_AGENT_MAX_TOOL_CALLS",
    "max_duration_seconds": "AI_AGENT_MAX_DURATION_SECONDS",
    "max_output_tokens": "AI_AGENT_MAX_OUTPUT_TOKENS",
    "provider_timeout_seconds": "AI_AGENT_PROVIDER_TIMEOUT_SECONDS",
    "provider_max_retries": "AI_AGENT_PROVIDER_MAX_RETRIES",
    "reasoning_effort": "AI_AGENT_REASONING_EFFORT",
    "temperature": "AI_AGENT_TEMPERATURE",
}


class AgentConfigError(ValueError):
    """Invalid agent configuration. Messages name variables, never secret values."""


class AgentConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = False
    openai_api_key: SecretStr | None = None
    model: str = "gpt-6-luna"
    max_question_chars: int = Field(default=1000, ge=20, le=4000)
    max_model_calls: int = Field(default=6, ge=2, le=12)
    max_tool_calls: int = Field(default=8, ge=1, le=20)
    max_duration_seconds: float = Field(default=45.0, ge=5, le=120)
    max_output_tokens: int = Field(default=800, ge=100, le=4000)
    provider_timeout_seconds: float = Field(default=20.0, ge=1, le=60)
    provider_max_retries: int = Field(default=1, ge=0, le=3)
    # Chat Completions with function calling: gpt-6-luna requires "none".
    # None ("unset") omits the parameter for models that do not accept it.
    reasoning_effort: Literal["none"] | None = "none"
    # Not sent unless configured: support for gpt-6-luna is undocumented.
    temperature: float | None = Field(default=None, ge=0, le=2)

    @model_validator(mode="after")
    def _check(self) -> "AgentConfig":
        if not _MODEL_NAME.match(self.model):
            raise ValueError("model name contains unsupported characters")
        if self.provider_timeout_seconds >= self.max_duration_seconds:
            raise ValueError("provider timeout must be shorter than the total request duration")
        return self

    @property
    def recursion_limit(self) -> int:
        """LangGraph backstop only; real budgets are enforced by middleware.

        Each agent iteration takes about 6 graph steps with this middleware
        stack (measured: 6 * model_calls + 2), so the backstop must exceed that
        or it would fire before the model-call budget.
        """
        return 8 * self.max_model_calls + 10

    def availability(self) -> tuple[bool, str | None]:
        if not self.enabled:
            return False, "The AI research assistant is disabled (AI_AGENT_ENABLED is not true)."
        if self.openai_api_key is None or not self.openai_api_key.get_secret_value().strip():
            return False, "The AI research assistant is not configured (OPENAI_API_KEY is missing)."
        return True, None


def _parse_bool(raw: str, name: str) -> bool:
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off", ""}:
        return False
    raise AgentConfigError(f"{name} must be true or false")


def load_agent_config(environ: dict[str, str] | None = None) -> AgentConfig:
    env = os.environ if environ is None else environ
    values: dict[str, object] = {}
    for field_name, var in ENV_VARS.items():
        raw = env.get(var)
        if raw is None or (raw.strip() == "" and field_name != "enabled"):
            continue
        if field_name == "enabled":
            values[field_name] = _parse_bool(raw, var)
        elif field_name == "reasoning_effort" and raw.strip().lower() == "unset":
            values[field_name] = None
        else:
            values[field_name] = raw.strip()
    try:
        return AgentConfig(**values)
    except ValidationError as exc:
        names = sorted({ENV_VARS.get(str(err["loc"][0]), str(err["loc"][0])) if err["loc"] else "configuration"
                        for err in exc.errors()})
        reasons = "; ".join(err["msg"] for err in exc.errors(include_input=False, include_url=False))
        raise AgentConfigError(f"Invalid AI agent configuration ({', '.join(names)}): {reasons}") from None
