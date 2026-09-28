"""AgentCore Platform v1.0"""

import re
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

# Deterministic PII-shaped patterns (email / phone / JP My Number). Used to detect
# whether a raw memory_context entry that looks like PII has leaked verbatim into
# the generated answer (docs/02_design.md step 5 — S-3 gate).
_PII_PATTERNS = (
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    re.compile(r"\b\d{3}[-.\s]?\d{3,4}[-.\s]?\d{4}\b"),
    re.compile(r"\b\d{12}\b"),  # JP My Number (12 digits)
)


def _looks_like_pii(text: str) -> bool:
    return any(p.search(text) for p in _PII_PATTERNS)


class PostProcessNode(FunctionNode):
    """OutputValidate: S-3 deterministic gate — reject raw PII echoed from the
    retrieved memory context into the answer (docs/02_design.md step 5). Returns
    FAIL + audit log, never an LLM self-check.
    """

    # S-1: explicit by design, not inherited implicitly.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        draft_answer = state.get("draft_answer", "")
        memory_context = state.get("memory_context", [])
        compliance_notes = state.get("compliance_notes", [])

        # Primary check: scan the final answer itself for
        # PII-shaped content, not only whole-entry-echoed-verbatim. A generated answer
        # can disclose an email/phone/My-Number in isolation or reworded around it.
        pii_leak_detected = _looks_like_pii(draft_answer)
        if not pii_leak_detected:
            # Provenance-aware safeguard, retained: verbatim-entry echo across
            # sentence boundaries that _looks_like_pii(draft_answer) alone might miss
            # (e.g. entry content that isn't itself PII-shaped but must never leak raw).
            for entry in memory_context:
                entry_text = str(entry.get("content", entry) if isinstance(entry, dict) else entry)
                if _looks_like_pii(entry_text) and entry_text and entry_text in draft_answer:
                    pii_leak_detected = True
                    break

        if pii_leak_detected:
            emit_trace_event(
                "output_validation_failed",
                {"correlation_id": state.get("correlation_id")},
                state,
            )
            return {
                "pii_leak_detected": True,
                "status": AgentStatus.ERROR.value,
                "error_log": [
                    "OutputValidate: raw PII from memory context echoed in answer — output withheld (S-3 gate)"
                ],
            }

        formatted_output = {
            "answer": draft_answer,
            "compliance_notes": compliance_notes,
        }

        emit_trace_event(
            "output_validated",
            {"correlation_id": state.get("correlation_id"), "note_count": len(compliance_notes)},
            state,
        )

        return {
            "pii_leak_detected": False,
            "validated_answer": formatted_output,
            "formatted_output": formatted_output,
            "status": AgentStatus.SUCCESS.value,
        }

    def _extra_security_gate_output(self, state: dict[str, Any]) -> dict[str, Any]:
        # S-3 own-dict self-consistency: re-check the exact key execute() produced
        # (formatted_output), not a separately re-derived field. If compliance_notes
        # were enriched upstream, formatted_output must preserve them (preservation
        # variant) — silently dropping them would present guidance without the
        # FISC/APPI compliance overlay that makes this an Agent-level capability.
        formatted = state.get("formatted_output")
        compliance_notes = state.get("compliance_notes") or []
        if isinstance(formatted, dict) and compliance_notes and "compliance_notes" not in formatted:
            return {
                **state,
                "status": AgentStatus.ERROR.value,
                "error_log": [
                    *(state.get("error_log") or []),
                    "OutputValidate: compliance_notes missing from formatted_output",
                ],
            }
        return state
