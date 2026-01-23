"""Tests for LLM scoring models."""

from __future__ import annotations

import pytest


class TestLLMFitEvaluation:
    def test_llm_fit_evaluation_valid_values_succeeds(self) -> None:
        from src.scoring.models import LLMFitEvaluation

        result = LLMFitEvaluation(
            total_score=0.8,
            recommendation="apply",
            reasoning="Strong match on required skills.",
        )

        assert result.total_score == 0.8
        assert result.recommendation == "apply"
        assert result.must_have_matched == []
        assert result.must_have_missing == []
        assert result.preferred_matched == []
        assert result.risk_flags == []

    def test_llm_fit_evaluation_total_score_out_of_range_raises(self) -> None:
        from pydantic import ValidationError

        from src.scoring.models import LLMFitEvaluation

        with pytest.raises(ValidationError):
            LLMFitEvaluation(
                total_score=1.5,
                recommendation="apply",
                reasoning="",
            )

        with pytest.raises(ValidationError):
            LLMFitEvaluation(
                total_score=-0.1,
                recommendation="apply",
                reasoning="",
            )

    def test_llm_fit_evaluation_invalid_recommendation_raises(self) -> None:
        from pydantic import ValidationError

        from src.scoring.models import LLMFitEvaluation

        with pytest.raises(ValidationError):
            LLMFitEvaluation(
                total_score=0.5,
                recommendation="maybe",
                reasoning="",
            )
