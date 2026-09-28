"""AgentCore Platform v1.0"""

# Cat 1 — Single technical capability (local-first OpenMemory query Q&A +
# FISC/APPI compliance overlay, use-case-agnostic within that scope).
# Parent: AgentBaseGraph (L1 direct). The vector-RAG agent shape is a pattern
# reference only, not an inheritance target.
# Pipeline: START -> initialize -> pre_process -> main -> {route} -> post_process -> finalize -> END
#
# Canonical node flow (docs/02_design.md), mapped to the fixed 3-slot backbone:
#   pre_process  -> QueryNormalize
#   main         -> MemoryContextRetrieve -> ComplianceContextEnrich -> GuidanceGenerate (src/services/*)
#   post_process -> OutputValidate (S-3 PII-leak gate)

from framework.graph.agent_base_graph import AgentBaseGraph

from src.nodes.main_node import MainNode
from src.nodes.post_process_node import PostProcessNode
from src.nodes.pre_process_node import PreProcessNode
from src.schemas.state import State


class Graph(AgentBaseGraph):
    """Enterprise AI Agent Local Memory & Context Persistence Q&A (OpenMemory pattern)."""

    @property
    def name(self) -> str:
        return "cmn-c1-565"

    @property
    def state_schema(self) -> type:
        return State

    def register_nodes(self) -> None:
        super().register_nodes()  # injects InitializeNode + FinalizeNode

        llm = self.config.get("llm")
        memory_client = self.config.get("memory_client")
        top_k = self.config.get("top_k", 5)
        snapshot_kb = self.config.get("snapshot_kb")

        self._nodes["pre_process"] = PreProcessNode()
        self._nodes["main"] = MainNode(llm, memory_client, top_k, snapshot_kb)
        self._nodes["post_process"] = PostProcessNode()
