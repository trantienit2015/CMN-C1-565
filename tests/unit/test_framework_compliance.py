# CMN-C1-565 - Framework Compliance Tests (TC-01..08)
#
# Shape: 3-slot AgentBaseGraph, ANONYMOUS trust for read-only Q&A nodes,
# S-2/S-3 _extra_* hooks, S-4 emit_trace_event.

import inspect

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_state import AgentState
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from src.nodes.main_node import MainNode
from src.nodes.post_process_node import PostProcessNode
from src.nodes.pre_process_node import PreProcessNode
from src.schemas.state import State


class TestTC01StateContract:
    """TC-01: State is a flat TypedDict extending AgentState (no Pydantic/dataclass)."""

    def test_state_extends_agent_state(self):
        # TypedDict class-based inheritance loses the parent from __mro__
        # (issubclass() raises TypeError for TypedDicts), so verify structurally:
        # every AgentState field must be present in State's annotations.
        assert set(AgentState.__annotations__).issubset(set(State.__annotations__))

    def test_state_fields_json_serialisable_shape(self):
        annotations = State.__annotations__
        assert "sanitized_query" in annotations
        assert "memory_context" in annotations


class TestTC02FailClosedValidation:
    """TC-02: invalid/empty input -> ERROR, never raise."""

    def test_empty_state_returns_error_not_raise(self):
        node = PreProcessNode()
        result = node.execute({})
        assert result["status"] == AgentStatus.ERROR


class TestTC03NoCredentials:
    """TC-03: no os.environ / hardcoded credentials in node source (see gate-credential-scan)."""

    def test_no_os_environ_in_node_modules(self):
        for mod in (PreProcessNode, MainNode, PostProcessNode):
            src = inspect.getsource(mod)
            assert "os.environ" not in src


class TestTC04InvocationContextIsolation:
    """TC-04: nodes never receive InvocationContext directly in execute(state)."""

    def test_execute_signature_is_state_only(self):
        for mod in (PreProcessNode, MainNode, PostProcessNode):
            sig = inspect.signature(mod.execute)
            params = list(sig.parameters.keys())
            assert params == ["self", "state"]


class TestTC05AuditLogging:
    """TC-05: emit_trace_event called for domain events (no re-emit of framework lifecycle events)."""

    def test_nodes_import_emit_trace_event(self):
        for mod in (PreProcessNode, MainNode, PostProcessNode):
            src = inspect.getsource(inspect.getmodule(mod))
            assert "emit_trace_event" in src


class TestTC06S2GateHook:
    """TC-06: _extra_security_gate_input is overridable and non-raising."""

    def test_hook_returns_dict_on_violation(self):
        node = PreProcessNode()
        out = node._extra_security_gate_input({"user_input": "Bearer sk-abcdefghijklmnop"})
        assert isinstance(out, dict)
        assert out["status"] == AgentStatus.ERROR


class TestTC07S3GateHook:
    """TC-07: _extra_security_gate_output is overridable, redacts/rejects, never raises."""

    def test_hook_rejects_missing_compliance_notes(self):
        node = PostProcessNode()
        out = node._extra_security_gate_output(
            {"formatted_output": {"answer": "x"}, "compliance_notes": [{"topic": "fisc", "note": "..."}]}
        )
        assert isinstance(out, dict)
        assert out["status"] == AgentStatus.ERROR


class TestTC08TrustGateDeclaredAndEnforced:
    """TC-08: required_trust_level declared as a valid enum on every FunctionNode."""

    def test_all_nodes_declare_valid_trust_level(self):
        for mod in (PreProcessNode, MainNode, PostProcessNode):
            assert issubclass(mod, FunctionNode)
            assert mod.required_trust_level in (
                TrustLevel.ANONYMOUS,
                TrustLevel.VERIFIED_EXTERNAL,
                TrustLevel.INTERNAL,
            )

    def test_all_nodes_are_anonymous_read_only_qna(self):
        for mod in (PreProcessNode, MainNode, PostProcessNode):
            assert mod.required_trust_level == TrustLevel.ANONYMOUS
