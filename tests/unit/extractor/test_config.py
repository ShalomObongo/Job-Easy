"""Tests for extractor configuration."""

import pytest


class TestExtractorConfig:
    """Test ExtractorConfig settings."""

    def test_extractor_config_has_defaults(self):
        """ExtractorConfig should load with sensible defaults."""
        from src.extractor.config import ExtractorConfig

        config = ExtractorConfig(_env_file=None)

        assert config.headless is True
        assert config.step_timeout == 60
        assert config.max_failures == 3
        assert config.use_vision == "auto"
        assert config.keep_browser_use_temp_dirs is False

    def test_extractor_config_reads_from_environment_variables(self, monkeypatch):
        """ExtractorConfig should read from environment variables."""
        from src.extractor.config import ExtractorConfig

        monkeypatch.setenv("EXTRACTOR_HEADLESS", "false")
        monkeypatch.setenv("EXTRACTOR_STEP_TIMEOUT", "120")
        monkeypatch.setenv("EXTRACTOR_MAX_FAILURES", "5")
        monkeypatch.setenv("EXTRACTOR_USE_VISION", "true")

        config = ExtractorConfig(_env_file=None)

        assert config.headless is False
        assert config.step_timeout == 120
        assert config.max_failures == 5
        assert config.use_vision == "true"

    def test_extractor_config_validates_timeout_positive(self):
        """ExtractorConfig should validate timeout > 0."""
        from pydantic import ValidationError

        from src.extractor.config import ExtractorConfig

        with pytest.raises(ValidationError):
            ExtractorConfig(_env_file=None, step_timeout=0)

        with pytest.raises(ValidationError):
            ExtractorConfig(_env_file=None, step_timeout=-10)

    def test_extractor_config_validates_max_failures_positive(self):
        """ExtractorConfig should validate max_failures > 0."""
        from pydantic import ValidationError

        from src.extractor.config import ExtractorConfig

        with pytest.raises(ValidationError):
            ExtractorConfig(_env_file=None, max_failures=0)

        with pytest.raises(ValidationError):
            ExtractorConfig(_env_file=None, max_failures=-1)

    def test_extractor_config_has_output_dir(self, tmp_path):
        """ExtractorConfig should have output_dir field."""
        from src.extractor.config import ExtractorConfig

        config = ExtractorConfig(_env_file=None, output_dir=tmp_path)

        assert config.output_dir == tmp_path

    def test_extractor_config_has_allowed_domains(self):
        """ExtractorConfig should have allowed_domains list."""
        from src.extractor.config import ExtractorConfig

        domains = ["lever.co", "greenhouse.io", "workday.com"]
        config = ExtractorConfig(_env_file=None, allowed_domains=domains)

        assert config.allowed_domains == domains

    def test_extractor_config_allowed_domains_defaults_to_empty(self):
        """ExtractorConfig allowed_domains should default to empty list."""
        from src.extractor.config import ExtractorConfig

        config = ExtractorConfig(_env_file=None)

        assert config.allowed_domains == []

    def test_extractor_config_validates_use_vision_values(self):
        """ExtractorConfig should accept valid use_vision values."""
        from src.extractor.config import ExtractorConfig

        # Valid values
        config_auto = ExtractorConfig(_env_file=None, use_vision="auto")
        assert config_auto.use_vision == "auto"

        config_true = ExtractorConfig(_env_file=None, use_vision="true")
        assert config_true.use_vision == "true"

        config_false = ExtractorConfig(_env_file=None, use_vision="false")
        assert config_false.use_vision == "false"

    def test_extractor_config_has_window_size(self):
        """ExtractorConfig should have window_size with defaults."""
        from src.extractor.config import ExtractorConfig

        config = ExtractorConfig(_env_file=None)

        assert config.window_width == 1280
        assert config.window_height == 720

    def test_extractor_config_has_llm_settings_with_defaults(self, monkeypatch):
        """ExtractorConfig should have LLM settings with sensible defaults."""
        from src.extractor.config import ExtractorConfig

        monkeypatch.delenv("EXTRACTOR_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("EXTRACTOR_LLM_BASE_URL", raising=False)
        monkeypatch.delenv("EXTRACTOR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("EXTRACTOR_LLM_MODEL", raising=False)
        monkeypatch.delenv("EXTRACTOR_LLM_REASONING_EFFORT", raising=False)

        config = ExtractorConfig(_env_file=None)

        assert config.llm_provider == "auto"
        assert config.llm_base_url is None
        assert config.llm_api_key is None
        assert config.llm_model is None
        assert config.llm_reasoning_effort is None

    def test_extractor_config_reads_llm_settings_from_env(self, monkeypatch):
        """ExtractorConfig should read LLM settings from environment."""
        from src.extractor.config import ExtractorConfig

        monkeypatch.setenv("EXTRACTOR_LLM_PROVIDER", "openai")
        monkeypatch.setenv("EXTRACTOR_LLM_BASE_URL", "https://custom.endpoint.com/v1")
        monkeypatch.setenv("EXTRACTOR_LLM_API_KEY", "my-secret-key")
        monkeypatch.setenv("EXTRACTOR_LLM_MODEL", "gpt-4o-mini")
        monkeypatch.setenv("EXTRACTOR_LLM_REASONING_EFFORT", "high")

        config = ExtractorConfig(_env_file=None)

        assert config.llm_provider == "openai"
        assert config.llm_base_url == "https://custom.endpoint.com/v1"
        assert config.llm_api_key == "my-secret-key"
        assert config.llm_model == "gpt-4o-mini"
        assert config.llm_reasoning_effort == "high"


class TestGetExtractorConfig:
    """Test get_extractor_config function."""

    def test_get_extractor_config_returns_config(self):
        """get_extractor_config should return an ExtractorConfig instance."""
        from src.extractor.config import ExtractorConfig, get_extractor_config

        config = get_extractor_config()

        assert isinstance(config, ExtractorConfig)

    def test_get_extractor_config_is_singleton(self):
        """get_extractor_config should return the same instance."""
        from src.extractor.config import get_extractor_config, reset_extractor_config

        reset_extractor_config()
        config1 = get_extractor_config()
        config2 = get_extractor_config()

        assert config1 is config2

    def test_reset_extractor_config_clears_singleton(self):
        """reset_extractor_config should clear the singleton."""
        from src.extractor.config import get_extractor_config, reset_extractor_config

        config1 = get_extractor_config()
        reset_extractor_config()
        config2 = get_extractor_config()

        assert config1 is not config2
