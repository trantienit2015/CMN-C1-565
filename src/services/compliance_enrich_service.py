"""AgentCore Platform v1.0"""

# Service layer: overlays FISC/APPI compliance notes from a curated snapshot KB
# (never the live memory store). Scope: FISC FY2026 data-residency guidance +
# APPI cross-border-transfer guidance for local-first memory deployments.
# APPI erasure-workflow execution is out of scope (separate template).

from __future__ import annotations

from typing import Any

_FISC_NOTE = {
    "topic": "fisc",
    "note": (
        "FISC FY2026 data-residency guidance: financial-sector AI agents must not "
        "persist memory/context to cloud-hosted stores. A local-first OpenMemory "
        "deployment satisfies this residency constraint."
    ),
}
_APPI_NOTE = {
    "topic": "appi",
    "note": (
        "APPI cross-border-transfer guidance: AI-inferred personal data held in "
        "conversational memory is subject to APPI disclosure/erasure rights. "
        "Local-first storage avoids cross-border transfer exposure; erasure-request "
        "execution itself is out of scope for this agent."
    ),
}


class ComplianceEnrichService:
    """Overlays curated FISC/APPI compliance notes onto a compliance-tagged query."""

    def __init__(self, snapshot_kb: Any = None) -> None:
        # snapshot_kb reserved for a future externally-curated notes source;
        # the built-in notes below are the deterministic default.
        self._snapshot_kb = snapshot_kb

    def enrich(self, compliance_topic: str) -> list[dict[str, Any]]:
        if compliance_topic == "fisc":
            return [_FISC_NOTE]
        if compliance_topic == "appi":
            return [_APPI_NOTE]
        if compliance_topic == "general":
            return []
        return []
