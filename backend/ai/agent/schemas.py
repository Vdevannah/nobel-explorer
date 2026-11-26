"""Request/response models for the research agent (Pydantic only)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AgentStatus = Literal["completed", "budget_exhausted", "timeout", "error", "unavailable"]
# cited:           every citation refers to evidence returned in this request
# partially_cited: valid citations exist, but invalid citations or links were removed
#                  (affected statements are marked [unverified] / [link removed])
# uncited:         evidence was retrieved but the answer cites none of it
# no_evidence:     no tool returned citable evidence
Grounding = Literal["cited", "partially_cited", "uncited", "no_evidence"]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    # Static upper bound; the configured AI_AGENT_MAX_QUESTION_CHARS is checked too.
    question: str = Field(min_length=1, max_length=4000, description="The user's question.")


class SourceRef(BaseModel):
    name: str
    url: str


class Citation(BaseModel):
    evidence_id: str
    tool: str
    kind: str
    title: str
    citation_status: str
    source: SourceRef | None = Field(default=None, description="Direct source; only for source_linked evidence.")
    source_name: str | None = Field(default=None, description="Provenance name for structured records.")
    related_source: SourceRef | None = Field(
        default=None, description="Context only (parent contribution source); NOT a citation for this text."
    )
    reference: dict[str, Any] = Field(default_factory=dict)


class ToolCallSummary(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    ok: bool
    error_type: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    latency_ms: float | None = None


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_input_tokens: int = 0  # subset of input_tokens served from the provider's prompt cache


class ErrorInfo(BaseModel):
    type: str
    message: str


class ChatResponse(BaseModel):
    request_id: str
    status: AgentStatus
    answer: str | None = None
    grounding: Grounding | None = None
    citations: list[Citation] = Field(default_factory=list)
    tool_calls: list[ToolCallSummary] = Field(default_factory=list)
    evidence_limitations: list[str] = Field(default_factory=list)
    model: str | None = None
    model_calls: int = 0
    usage: Usage | None = None
    latency_ms: float = 0.0
    error: ErrorInfo | None = None
