# CMN-C1-565 — Unit Tests: PreProcessNode (QueryNormalize)

from framework.schemas.agent_status import AgentStatus
from src.nodes.pre_process_node import PreProcessNode


class TestPreProcessNode:
    def setup_method(self):
        self.node = PreProcessNode()

    def test_success_path_fisc(self):
        state = {
            "user_input": "  What is the FISC data residency guidance for local memory?  ",
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["sanitized_query"] == " ".join(state["user_input"].split())
        assert result["compliance_topic"] == "fisc"

    def test_success_path_appi(self):
        state = {
            "user_input": "How does APPI cross-border transfer apply to memory context?",
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["compliance_topic"] == "appi"

    def test_success_path_general(self):
        state = {
            "user_input": "How do I configure OpenMemory locally?",
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["compliance_topic"] == "general"

    def test_empty_input_rejected(self):
        state = {"user_input": "   ", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR
        assert result["error_log"]

    def test_extra_security_gate_input_rejects_credential(self):
        state = {"user_input": "here is my token Bearer sk-abcdefghijklmnop", "error_log": []}
        out = self.node._extra_security_gate_input(state)
        assert out["status"] == AgentStatus.ERROR

    def test_extra_security_gate_input_passthrough(self):
        state = {"user_input": "what is the FISC guidance?", "error_log": []}
        out = self.node._extra_security_gate_input(state)
        assert out is state
