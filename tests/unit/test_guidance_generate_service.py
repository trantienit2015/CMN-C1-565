# CMN-C1-565 — Unit Tests: GuidanceGenerateService LLM contract (recipe 3m)
#
# Canonical BaseLLM.complete(messages: list) -> dict {"content": str, ...}. A node
# that treats the raw result as a string crashes with a real client (only a
# string-fake hides it). These tests pin: (1) canonical dict is normalized to
# text, (2) empty/unusable content raises (not a silent SUCCESS fallback), (3) a
# raising provider raises (not swallowed), (4) llm is None still degrades safely.

import pytest

from src.services.guidance_generate_service import GuidanceGenerateService, GuidanceGenerationError


class CanonicalDictLLM:
    """Canonical shape: complete() returns a dict with a 'content' string field."""

    def complete(self, messages: list[dict]) -> dict:
        return {"content": "Local-first OpenMemory guidance based on retrieved context.", "model": "fake"}


class EmptyContentLLM:
    def complete(self, messages: list[dict]) -> dict:
        return {"content": ""}


class RaisingLLM:
    def complete(self, messages: list[dict]) -> dict:
        raise RuntimeError("provider unavailable")


class TestGuidanceGenerateServiceLLMContract:
    def test_canonical_dict_response_is_normalized_to_text(self):
        service = GuidanceGenerateService(llm=CanonicalDictLLM())
        answer = service.generate("what is FISC data residency guidance", [], [])
        assert isinstance(answer, str)
        assert answer == "Local-first OpenMemory guidance based on retrieved context."

    def test_empty_content_raises_not_silent_success(self):
        service = GuidanceGenerateService(llm=EmptyContentLLM())
        with pytest.raises(GuidanceGenerationError):
            service.generate("a question", [], [])

    def test_raising_provider_raises_not_swallowed(self):
        service = GuidanceGenerateService(llm=RaisingLLM())
        with pytest.raises(GuidanceGenerationError):
            service.generate("a question", [], [])

    def test_no_llm_configured_returns_deterministic_empty(self):
        # llm is None is the ONLY valid case for a silent empty-string degrade.
        service = GuidanceGenerateService(llm=None)
        assert service.generate("a question", [], []) == ""

    def test_complete_called_with_messages_list_not_bare_string(self):
        captured = {}

        class SpyLLM:
            def complete(self, messages):
                captured["messages"] = messages
                return {"content": "ok"}

        GuidanceGenerateService(llm=SpyLLM()).generate("q", [], [])
        assert isinstance(captured["messages"], list)
        assert captured["messages"][0]["role"] == "user"
        assert isinstance(captured["messages"][0]["content"], str)
