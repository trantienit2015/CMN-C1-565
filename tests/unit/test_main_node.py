# CMN-C1-565 — Unit Tests: MainNode
# Orchestrates MemoryContextRetrieve -> ComplianceContextEnrich -> GuidanceGenerate
# (docs/02_design.md).

from framework.schemas.agent_status import AgentStatus
from src.nodes.main_node import MainNode


class FakeMemoryClient:
    def search(self, query: str, top_k: int) -> list[dict]:
        return [{"id": "m1", "content": "user prefers local-first deployments"}]


class FakeLLM:
    """Backward-compat fake — returns a bare string (canonical is a dict)."""

    def complete(self, messages: list[dict]) -> str:
        first_line = messages[0]["content"].splitlines()[0]
        return f"Local-first OpenMemory guidance for: {first_line}"


class RaisingLLM:
    def complete(self, messages: list[dict]) -> dict:
        raise RuntimeError("provider unavailable")


class TestMainNode:
    def test_success_path_fisc(self):
        node = MainNode(llm=FakeLLM(), memory_client=FakeMemoryClient())
        state = {
            "sanitized_query": "what is the FISC data residency guidance",
            "compliance_topic": "fisc",
            "node_history": [],
            "error_log": [],
        }
        result = node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["memory_context"]
        assert result["compliance_notes"]
        assert result["compliance_notes"][0]["topic"] == "fisc"
        assert result["draft_answer"]

    def test_no_memory_client_configured_returns_empty(self):
        node = MainNode()  # no memory_client configured
        state = {
            "sanitized_query": "a query with no configured memory client",
            "compliance_topic": "general",
            "node_history": [],
            "error_log": [],
        }
        result = node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["memory_context"] == []
        assert result["compliance_notes"] == []
        assert result["draft_answer"] == ""

    def test_llm_failure_is_error_not_silent_success(self):
        # 3m half-fix trap: a configured-but-failing LLM must yield ERROR, never
        # a deterministic-fallback SUCCESS (that degrade is reserved for llm=None).
        node = MainNode(llm=RaisingLLM(), memory_client=FakeMemoryClient())
        state = {
            "sanitized_query": "what is the FISC data residency guidance",
            "compliance_topic": "fisc",
            "node_history": [],
            "error_log": [],
        }
        result = node.execute(state)
        assert result["status"] == AgentStatus.ERROR.value
        assert result["error_log"]

    def test_short_circuits_on_upstream_error(self):
        node = MainNode()
        state = {"status": AgentStatus.ERROR, "error_log": ["upstream failure"]}
        result = node.execute(state)
        assert result == {}
