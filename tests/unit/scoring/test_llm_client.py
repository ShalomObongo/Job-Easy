"""Unit tests for ScoringLLM."""

from __future__ import annotations

import pytest


class _DummyFunction:
    def __init__(self, arguments: str):
        self.arguments = arguments


class _DummyToolCall:
    def __init__(self, arguments: str):
        self.function = _DummyFunction(arguments)


class _DummyMessage:
    def __init__(self, content: str | None, tool_calls: list[object] | None = None):
        self.content = content
        self.tool_calls = tool_calls


class _DummyChoice:
    def __init__(self, message: _DummyMessage):
        self.message = message


class _DummyResponse:
    def __init__(self, message: _DummyMessage):
        self.choices = [_DummyChoice(message)]


class TestScoringLLM:
    def test_generate_structured_parses_json_content(self, monkeypatch) -> None:
        from src.scoring.config import ScoringConfig
        from src.scoring.llm import ScoringLLM
        from src.scoring.models import LLMFitEvaluation

        llm = ScoringLLM(config=ScoringConfig(_env_file=None, llm_max_retries=0))  # type: ignore[call-arg]

        def _fake_call_completion(*, messages, response_format):  # noqa: ARG001
            return _DummyResponse(
                _DummyMessage(
                    '{"total_score": 0.8, "recommendation": "apply", "reasoning": "ok"}'
                )
            )

        monkeypatch.setattr(llm, "_call_completion", _fake_call_completion)

        result = llm.generate_structured(
            prompt="x",
            output_model=LLMFitEvaluation,
            system_prompt=None,
        )

        assert result.total_score == 0.8
        assert result.recommendation == "apply"

    def test_generate_structured_strips_code_fences(self, monkeypatch) -> None:
        from src.scoring.config import ScoringConfig
        from src.scoring.llm import ScoringLLM
        from src.scoring.models import LLMFitEvaluation

        llm = ScoringLLM(config=ScoringConfig(_env_file=None, llm_max_retries=0))  # type: ignore[call-arg]

        fenced = """```json
        {"total_score": 0.5, "recommendation": "review", "reasoning": "ok"}
        ```"""

        monkeypatch.setattr(
            llm,
            "_call_completion",
            lambda *, messages, response_format: _DummyResponse(_DummyMessage(fenced)),  # noqa: ARG005
        )

        result = llm.generate_structured(
            prompt="x",
            output_model=LLMFitEvaluation,
        )

        assert result.total_score == 0.5
        assert result.recommendation == "review"

    def test_generate_structured_reads_tool_call_arguments(self, monkeypatch) -> None:
        from src.scoring.config import ScoringConfig
        from src.scoring.llm import ScoringLLM
        from src.scoring.models import LLMFitEvaluation

        llm = ScoringLLM(config=ScoringConfig(_env_file=None, llm_max_retries=0))  # type: ignore[call-arg]

        tool_calls: list[object] = [
            _DummyToolCall(
                '{"total_score": 0.2, "recommendation": "skip", "reasoning": "no"}'
            )
        ]
        monkeypatch.setattr(
            llm,
            "_call_completion",
            lambda **_kwargs: _DummyResponse(
                _DummyMessage(None, tool_calls=tool_calls)
            ),
        )

        result = llm.generate_structured(prompt="x", output_model=LLMFitEvaluation)

        assert result.total_score == 0.2
        assert result.recommendation == "skip"

    def test_generate_structured_invalid_json_raises(self, monkeypatch) -> None:
        from src.scoring.config import ScoringConfig
        from src.scoring.llm import ScoringLLM, ScoringLLMError
        from src.scoring.models import LLMFitEvaluation

        llm = ScoringLLM(config=ScoringConfig(_env_file=None, llm_max_retries=0))  # type: ignore[call-arg]

        monkeypatch.setattr(
            llm,
            "_call_completion",
            lambda **_kwargs: _DummyResponse(_DummyMessage("not-json")),
        )

        with pytest.raises(ScoringLLMError):
            llm.generate_structured(prompt="x", output_model=LLMFitEvaluation)
