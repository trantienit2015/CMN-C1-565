# CMN-C1-565 — Integration Test: full graph (compile + invoke)

from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel
from src.graph.graph import Graph


class FakeMemoryClient:
    def search(self, query: str, top_k: int) -> list[dict]:
        return [{"id": "m1", "content": "user prefers local-first deployments"}]


class FakeLLM:
    """Canonical shape: complete() returns a dict with a 'content' string field."""

    def complete(self, messages: list[dict]) -> dict:
        return {"content": "Local-first OpenMemory guidance: deploy on-prem, no cloud API."}


class TestOpenMemoryQAGraph:
    def setup_method(self):
        self.agent = Graph(
            config={
                "llm": FakeLLM(),
                "memory_client": FakeMemoryClient(),
                "max_retry": 1,
            }
        )
        self.agent.compile()

    def _invoke(self, text: str):
        ctx = InvocationContext(
            session_id="test-session",
            caller_trust_level=TrustLevel.ANONYMOUS,
            caller_id="test-caller",
        )
        return self.agent.invoke(text, ctx=ctx)

    def test_full_pipeline_success(self):
        result = self._invoke("What is the FISC data residency guidance for local memory?")
        assert result["status"] in ("success", "SUCCESS")
        assert result.get("output") or result.get("formatted_output")

    def test_empty_input_errors(self):
        result = self._invoke("")
        assert result["status"] in ("error", "ERROR", "cancelled", "CANCELLED")
