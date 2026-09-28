"""AgentCore Platform v1.0"""

# Service layer: Tool call to the OpenMemory LOCAL API (live local memory store,
# no cloud API — docs/02_design.md scope boundary). Never fetches a cloud memory
# endpoint; `memory_client` must point at a local-first OpenMemory deployment.

from __future__ import annotations

from typing import Any, cast


class MemoryRetrieveService:
    """Queries a live local-first OpenMemory instance for relevant memory entries."""

    def __init__(self, memory_client: Any = None, top_k: int = 5) -> None:
        self._memory_client = memory_client
        self._top_k = top_k

    def retrieve(self, sanitized_query: str) -> list[dict[str, Any]]:
        if not sanitized_query:
            return []
        if self._memory_client is None:
            # No local OpenMemory client configured — deterministic empty result,
            # never a fabricated stub answer.
            return []
        return cast(list[dict[str, Any]], self._memory_client.search(sanitized_query, top_k=self._top_k))
