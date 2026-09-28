"""AgentCore Platform v1.0"""

# Service layer: LLM-driven synthesis of implementation/compliance guidance from
# retrieved memory context + compliance notes. Must never echo raw memory_context
# verbatim without going through the S-3 output gate (nodes/post_process_node.py).

from __future__ import annotations

from typing import Any


class GuidanceGenerationError(Exception):
    """Raised when a configured LLM fails or returns unusable content.

    Callers must translate this to an error status — never swallowed into a
    deterministic fallback (that degrade path is reserved for llm is None only)."""


def _extract_text(raw: Any) -> str:
    """Normalize a BaseLLM.complete() result. Canonical shape is a dict with a
    'content' string field; a bare string is accepted for backward-compat fakes."""
    if isinstance(raw, dict):
        content = raw.get("content", "")
        return content if isinstance(content, str) else ""
    if isinstance(raw, str):
        return raw
    return ""


class GuidanceGenerateService:
    """Synthesizes local-first OpenMemory implementation + compliance guidance."""

    def __init__(self, llm: Any = None) -> None:
        self._llm = llm

    def generate(
        self, sanitized_query: str, memory_context: list[dict[str, Any]], compliance_notes: list[dict[str, Any]]
    ) -> str:
        if self._llm is None:
            # No LLM configured — deterministic placeholder, never a fabricated answer.
            return ""

        context_summary = f"{len(memory_context)} memory entr{'y' if len(memory_context) == 1 else 'ies'}"
        notes_summary = "; ".join(n["note"] for n in compliance_notes) if compliance_notes else "no compliance overlay"
        prompt = (
            f"Question: {sanitized_query}\n"
            f"Retrieved memory context: {context_summary}\n"
            f"Compliance notes: {notes_summary}\n"
            "Provide local-first OpenMemory implementation guidance, referencing the "
            "compliance notes where relevant. Do not repeat raw memory content verbatim."
        )
        try:
            raw = self._llm.complete([{"role": "user", "content": prompt}])
        except Exception as exc:  # noqa: BLE001 - narrow domain error re-raised below
            raise GuidanceGenerationError(f"LLM complete() call failed: {exc}") from exc

        text = _extract_text(raw)
        if not text.strip():
            # LLM IS configured but returned unusable content — this is a failure,
            # not "no answer available"; must not be swallowed into SUCCESS.
            raise GuidanceGenerationError("LLM complete() returned empty/unusable content")
        return text.strip()
