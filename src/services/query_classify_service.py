"""AgentCore Platform v1.0"""

# Service layer: deterministic query normalization + compliance-topic
# classification. No LLM call — must not hold credentials.

from __future__ import annotations


class QueryClassifyService:
    """Normalizes the caller's question and tags it with a compliance topic."""

    _FISC_MARKERS = ("fisc", "data residency", "data-residency", "financial sector")
    _APPI_MARKERS = ("appi", "cross-border", "erasure", "personal information protection")

    def classify(self, query: str) -> str:
        if not query:
            return "general"
        lowered = query.lower()
        if any(marker in lowered for marker in self._FISC_MARKERS):
            return "fisc"
        if any(marker in lowered for marker in self._APPI_MARKERS):
            return "appi"
        return "general"

    def normalize(self, raw_query: str) -> str:
        return " ".join(raw_query.split()).strip()
