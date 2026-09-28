"""AgentCore Platform v1.0"""

# Node contract:
#  - Extend FunctionNode; implement execute(state) -> dict
#  - Return ONLY the fields this node changes (never full state)
#  - Set status with AgentStatus.<X>.value (the string)
#  - Read input_context via state.get("input_context", {}) — read-only
#  - Never import from mediator/, api/, or other agents
#
# Canonical node flow (docs/02_design.md), mapped to the pre_process slot:
#   Step 1 QueryNormalize -> classify compliance topic (src/services/query_classify_service.py)

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.services.query_classify_service import QueryClassifyService


class PreProcessNode(FunctionNode):
    """QueryNormalize: strip/normalize the question, tag it with a compliance topic."""

    # S-1: explicit by design, not inherited implicitly. This is the
    # outer boundary node — matches agent.yaml default (ANONYMOUS, read-only Q&A).
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def __init__(self) -> None:
        self._classify = QueryClassifyService()

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        user_input = state.get("user_input", "")

        if not user_input or not user_input.strip():
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["QueryNormalize: user_input is empty or missing"],
            }

        sanitized_query = self._classify.normalize(user_input)
        compliance_topic = self._classify.classify(sanitized_query)

        emit_trace_event(
            "query_normalized",
            {"correlation_id": state.get("correlation_id"), "compliance_topic": compliance_topic},
            state,
        )

        return {
            "validated_input": sanitized_query,
            "sanitized_query": sanitized_query,
            "compliance_topic": compliance_topic,
            "status": AgentStatus.SUCCESS.value,
        }

    def _extra_security_gate_input(self, state: dict[str, Any]) -> dict[str, Any]:
        # S-2 domain check: runs BEFORE execute() (framework @final _security_gate_input
        # calls this hook prior to dispatching to execute()), so it must inspect the raw
        # user_input — sanitized_query does not exist in state yet at this point. The
        # generic framework S-2 PII scan already masks standard fields; this hook adds a
        # deterministic reject for credential-shaped tokens in the raw query.
        query = state.get("user_input", "") or ""
        lowered = query.lower()
        if "bearer " in lowered or "sk-" in lowered:
            return {
                **state,
                "status": AgentStatus.ERROR.value,
                "error_log": [
                    *(state.get("error_log") or []),
                    "QueryNormalize: credential-shaped token detected in query",
                ],
            }
        return state
