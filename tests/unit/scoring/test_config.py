"""Tests for scoring configuration."""

import pytest


class TestScoringConfig:
    """Test ScoringConfig settings."""

    def test_scoring_config_has_defaults(self):
        """ScoringConfig should load with sensible defaults."""
        from src.scoring.config import ScoringConfig

        config = ScoringConfig(_env_file=None)

        assert str(config.profile_path) == "profiles/profile.yaml"
        assert config.fit_score_threshold == 0.75
        assert config.review_margin == 0.05

        assert config.weight_must_have == 0.40
        assert config.weight_preferred == 0.20
        assert config.weight_experience == 0.25
        assert config.weight_education == 0.15

        assert config.skill_fuzzy_match is True
        assert config.skill_fuzzy_threshold == 0.85
        assert config.experience_tolerance_years == 2

        assert config.location_strict is False
        assert config.visa_strict is True
        assert config.salary_strict is False

    def test_scoring_config_reads_from_environment_variables(self, monkeypatch):
        """ScoringConfig should read from environment variables."""
        from src.scoring.config import ScoringConfig

        monkeypatch.setenv("SCORING_PROFILE_PATH", "profiles/custom.yaml")
        monkeypatch.setenv("SCORING_FIT_SCORE_THRESHOLD", "0.80")
        monkeypatch.setenv("SCORING_REVIEW_MARGIN", "0.10")
        monkeypatch.setenv("SCORING_SKILL_FUZZY_MATCH", "false")
        monkeypatch.setenv("SCORING_LOCATION_STRICT", "true")

        config = ScoringConfig(_env_file=None)

        assert str(config.profile_path) == "profiles/custom.yaml"
        assert config.fit_score_threshold == 0.80
        assert config.review_margin == 0.10
        assert config.skill_fuzzy_match is False
        assert config.location_strict is True

    def test_scoring_config_validates_weights_sum_to_one(self):
        """ScoringConfig should validate weight sum is ~1.0."""
        from pydantic import ValidationError

        from src.scoring.config import ScoringConfig

        with pytest.raises(ValidationError):
            ScoringConfig(
                _env_file=None,
                weight_must_have=0.50,
                weight_preferred=0.20,
                weight_experience=0.20,
                weight_education=0.20,
            )


class TestGetScoringConfig:
    """Test get_scoring_config function."""

    def test_get_scoring_config_returns_config(self):
        """get_scoring_config should return a ScoringConfig instance."""
        from src.scoring.config import ScoringConfig, get_scoring_config

        config = get_scoring_config()

        assert isinstance(config, ScoringConfig)

    def test_get_scoring_config_is_singleton(self):
        """get_scoring_config should return the same instance."""
        from src.scoring.config import get_scoring_config, reset_scoring_config

        reset_scoring_config()
        config1 = get_scoring_config()
        config2 = get_scoring_config()

        assert config1 is config2

    def test_reset_scoring_config_clears_singleton(self):
        """reset_scoring_config should clear the singleton."""
        from src.scoring.config import get_scoring_config, reset_scoring_config

        config1 = get_scoring_config()
        reset_scoring_config()
        config2 = get_scoring_config()

        assert config1 is not config2
