# CMN-C1-565 — Unit Tests: PostProcessNode (OutputValidate, S-3)

from framework.schemas.agent_status import AgentStatus
from src.nodes.post_process_node import PostProcessNode


class TestPostProcessNode:
    def setup_method(self):
        self.node = PostProcessNode()

    def test_success_path(self):
        state = {
            "draft_answer": "Local-first OpenMemory guidance: deploy on-prem, no cloud API.",
            "memory_context": [{"id": "m1", "content": "user prefers local-first deployments"}],
            "compliance_notes": [{"topic": "fisc", "note": "FISC FY2026 data-residency guidance..."}],
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["pii_leak_detected"] is False
        assert result["validated_answer"]["compliance_notes"]

    def test_pii_leak_detected_when_memory_content_echoed_verbatim(self):
        state = {
            "draft_answer": "We found this in memory: contact jane.doe@example.com for details.",
            "memory_context": [{"id": "m1", "content": "contact jane.doe@example.com for details."}],
            "compliance_notes": [],
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR
        assert result["pii_leak_detected"] is True

    def test_pii_leak_detected_for_partial_email_not_matching_full_entry(self):
        # CR-1430-01: answer discloses the email in isolation, reworded around it —
        # entry_text is not echoed verbatim, so only a direct scan of draft_answer
        # catches this.
        state = {
            "draft_answer": "You can reach the requester at jane.doe@example.com for follow-up.",
            "memory_context": [{"id": "m1", "content": "requester: jane.doe@example.com, prefers async"}],
            "compliance_notes": [],
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR
        assert result["pii_leak_detected"] is True

    def test_pii_leak_detected_for_partial_phone_not_matching_full_entry(self):
        state = {
            "draft_answer": "Escalate via phone at 090-1234-5678 if urgent.",
            "memory_context": [{"id": "m1", "content": "on-call contact: 090-1234-5678, weekdays only"}],
            "compliance_notes": [],
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR
        assert result["pii_leak_detected"] is True

    def test_pii_leak_detected_for_partial_my_number_not_matching_full_entry(self):
        state = {
            "draft_answer": "The record references My Number 123456789012 for verification.",
            "memory_context": [{"id": "m1", "content": "My Number on file: 123456789012 (verified 2026)"}],
            "compliance_notes": [],
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR
        assert result["pii_leak_detected"] is True

    def test_no_leak_when_memory_content_not_pii_shaped(self):
        state = {
            "draft_answer": "We found this in memory: user prefers local-first deployments.",
            "memory_context": [{"id": "m1", "content": "user prefers local-first deployments"}],
            "compliance_notes": [],
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["pii_leak_detected"] is False

    def test_extra_security_gate_output_rejects_missing_compliance_notes(self):
        state = {
            "formatted_output": {"answer": "x"},
            "compliance_notes": [{"topic": "fisc", "note": "..."}],
            "error_log": [],
        }
        out = self.node._extra_security_gate_output(state)
        assert out["status"] == AgentStatus.ERROR

    def test_extra_security_gate_output_passthrough(self):
        state = {
            "formatted_output": {"answer": "x", "compliance_notes": []},
            "compliance_notes": [],
            "error_log": [],
        }
        out = self.node._extra_security_gate_output(state)
        assert out is state
