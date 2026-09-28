"""AgentCore Platform v1.0"""

# ADR-005: State must be a flat TypedDict — never Pydantic BaseModel.
# LangGraph checkpoints use msgpack serialization; Pydantic objects
# cause silent corruption. Extend AgentState with agent-specific
# fields only. Do NOT add credentials, secrets, or Pydantic models.

from typing import NotRequired

from framework.schemas.agent_state import AgentState


# Type-check note: the wheel ships no py.typed, so mypy resolves AgentState to Any
# and reports every NotRequired below as valid-type. The fields are correct (the state
# contract requires NotRequired) -- the report is a packaging artifact, suppressed per field.
# Drop these ignores once the wheel ships py.typed.
class State(AgentState):
    """OpenMemory local-first memory Q&A / FISC-APPI compliance agent state.

    All agent-specific fields are NotRequired: they are absent from the
    initial invocation input and only appear once the corresponding
    pipeline node has run (state-safety — checkpoint/resume safe).
    """

    sanitized_query: NotRequired[str]  # type: ignore[valid-type]
    compliance_topic: NotRequired[str]  # type: ignore[valid-type]
    memory_context: NotRequired[list[dict]]  # type: ignore[valid-type]
    compliance_notes: NotRequired[list[dict]]  # type: ignore[valid-type]
    draft_answer: NotRequired[str]  # type: ignore[valid-type]
    pii_leak_detected: NotRequired[bool]  # type: ignore[valid-type]
    validated_answer: NotRequired[dict]  # type: ignore[valid-type]
