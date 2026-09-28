"""AgentCore Platform v1.0"""

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.services.compliance_enrich_service import ComplianceEnrichService
from src.services.guidance_generate_service import GuidanceGenerateService, GuidanceGenerationError
from src.services.memory_retrieve_service import MemoryRetrieveService


class MainNode(FunctionNode):
    """Orchestrates MemoryContextRetrieve -> ComplianceContextEnrich -> GuidanceGenerate
    (docs/02_design.md canonical node flow, steps 2-4)."""

    # S-1: read-only local-memory Q&A — matches agent.yaml default.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def __init__(
        self,
        llm: Any = None,
        memory_client: Any = None,
        top_k: int = 5,
        snapshot_kb: Any = None,
    ) -> None:
        self._memory_retrieve = MemoryRetrieveService(memory_client, top_k)
        self._compliance_enrich = ComplianceEnrichService(snapshot_kb)
        self._guidance_generate = GuidanceGenerateService(llm)

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        # pre_process -> main is a fixed (non-conditional) edge — main always runs even
        # when pre_process already rejected the input. Pass the error through unchanged
        # rather than overwriting it with SUCCESS below.
        if state.get("status") == AgentStatus.ERROR.value:
            emit_trace_event(
                "main_short_circuited_on_upstream_error",
                {"correlation_id": state.get("correlation_id")},
                state,
            )
            return {}

        query = state.get("sanitized_query", "")
        compliance_topic = state.get("compliance_topic", "general")

        memory_context = self._memory_retrieve.retrieve(query)
        emit_trace_event(
            "memory_context_retrieved",
            {"correlation_id": state.get("correlation_id"), "entry_count": len(memory_context)},
            state,
        )

        compliance_notes = self._compliance_enrich.enrich(compliance_topic)
        emit_trace_event(
            "compliance_context_enriched",
            {"correlation_id": state.get("correlation_id"), "note_count": len(compliance_notes)},
            state,
        )

        try:
            draft_answer = self._guidance_generate.generate(query, memory_context, compliance_notes)
        except GuidanceGenerationError as exc:
            emit_trace_event(
                "guidance_generate_llm_failed",
                {"correlation_id": state.get("correlation_id"), "error": str(exc)},
                state,
            )
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [f"GuidanceGenerate: LLM synthesis failed — {exc}"],
            }

        emit_trace_event(
            "guidance_generated",
            {"correlation_id": state.get("correlation_id"), "answer_length": len(draft_answer)},
            state,
        )

        return {
            "memory_context": memory_context,
            "compliance_notes": compliance_notes,
            "draft_answer": draft_answer,
            "status": AgentStatus.SUCCESS.value,
        }
