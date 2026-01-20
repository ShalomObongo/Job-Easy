"""Unit tests for tailoring configuration."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.tailoring.config import (
    TailoringConfig,
    get_tailoring_config,
    reset_tailoring_config,
)

# Keys to remove for isolated tests (prevents fallback to EXTRACTOR_* settings)
ENV_KEYS_TO_REMOVE = [
    "TAILORING_LLM_PROVIDER",
    "TAILORING_LLM_MODEL",
    "TAILORING_LLM_API_KEY",
    "TAILORING_LLM_BASE_URL",
    "TAILORING_LLM_REASONING_EFFORT",
    "EXTRACTOR_LLM_PROVIDER",
    "EXTRACTOR_LLM_MODEL",
    "EXTRACTOR_LLM_API_KEY",
    "EXTRACTOR_LLM_BASE_URL",
    "EXTRACTOR_LLM_REASONING_EFFORT",
]


@pytest.fixture
def isolated_env():
    """Remove LLM env vars for isolated testing."""
    # Save original values
    saved = {k: os.environ.pop(k, None) for k in ENV_KEYS_TO_REMOVE}
    reset_tailoring_config()
    yield
    # Restore original values
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]
    reset_tailoring_config()


class TestTailoringConfig:
    """Tests for TailoringConfig settings."""

    def teardown_method(self):
        """Reset config singleton after each test."""
        reset_tailoring_config()

    def test_default_values(self, isolated_env):
        """Test default configuration values."""
        assert isolated_env is None
        config = TailoringConfig(_env_file=None)

        # LLM settings
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4o"
        assert config.llm_api_key is None
        assert config.llm_reasoning_effort is None

        # Template paths
        assert config.template_dir == Path("src/tailoring/templates")
        assert config.resume_template == "resume.html"
        assert config.cover_letter_template == "cover_letter.html"

        # Output settings
        assert config.output_dir == Path("artifacts/docs")

        # Generation settings
        assert config.cover_letter_min_words == 300
        assert config.cover_letter_max_words == 400

    def test_llm_provider_validation(self, isolated_env):
        """Test LLM provider must be valid."""
        assert isolated_env is None
        config = TailoringConfig(_env_file=None, llm_provider="anthropic")
        assert config.llm_provider == "anthropic"

        config = TailoringConfig(_env_file=None, llm_provider="openai")
        assert config.llm_provider == "openai"

        # LiteLLM supports many providers, so we allow any string
        config = TailoringConfig(_env_file=None, llm_provider="azure")
        assert config.llm_provider == "azure"

    def test_llm_model_customization(self, isolated_env):
        """Test custom LLM model selection."""
        assert isolated_env is None
        config = TailoringConfig(_env_file=None, llm_model="claude-3-opus-20240229")
        assert config.llm_model == "claude-3-opus-20240229"

    def test_template_dir_path(self):
        """Test template directory as Path."""
        config = TailoringConfig(_env_file=None, template_dir=Path("/custom/templates"))
        assert config.template_dir == Path("/custom/templates")

    def test_output_dir_customization(self):
        """Test custom output directory."""
        config = TailoringConfig(_env_file=None, output_dir=Path("/custom/output"))
        assert config.output_dir == Path("/custom/output")

    def test_cover_letter_word_limits(self):
        """Test cover letter word count settings."""
        config = TailoringConfig(
            _env_file=None, cover_letter_min_words=250, cover_letter_max_words=500
        )
        assert config.cover_letter_min_words == 250
        assert config.cover_letter_max_words == 500

    def test_cover_letter_min_words_validation(self):
        """Test minimum words must be positive."""
        with pytest.raises(ValidationError):
            TailoringConfig(_env_file=None, cover_letter_min_words=0)

        with pytest.raises(ValidationError):
            TailoringConfig(_env_file=None, cover_letter_min_words=-10)

    def test_cover_letter_max_words_validation(self):
        """Test maximum words must be positive."""
        with pytest.raises(ValidationError):
            TailoringConfig(_env_file=None, cover_letter_max_words=0)

    def test_max_retries_setting(self):
        """Test LLM retry configuration."""
        config = TailoringConfig(_env_file=None, llm_max_retries=5)
        assert config.llm_max_retries == 5

    def test_max_retries_must_be_positive(self):
        """Test retries must be >= 0."""
        with pytest.raises(ValidationError):
            TailoringConfig(_env_file=None, llm_max_retries=-1)

    def test_timeout_setting(self):
        """Test LLM timeout configuration."""
        config = TailoringConfig(_env_file=None, llm_timeout=120.0)
        assert config.llm_timeout == 120.0

    def test_timeout_must_be_positive(self):
        """Test timeout must be positive."""
        with pytest.raises(ValidationError):
            TailoringConfig(_env_file=None, llm_timeout=0)

        with pytest.raises(ValidationError):
            TailoringConfig(_env_file=None, llm_timeout=-30)

    @patch.dict(
        "os.environ",
        {
            "TAILORING_LLM_PROVIDER": "anthropic",
            "TAILORING_LLM_MODEL": "claude-3-sonnet",
            "TAILORING_LLM_API_KEY": "test-api-key",
        },
    )
    def test_environment_variable_override(self):
        """Test settings can be overridden via environment variables."""
        reset_tailoring_config()
        config = TailoringConfig(_env_file=None)
        assert config.llm_provider == "anthropic"
        assert config.llm_model == "claude-3-sonnet"
        assert config.llm_api_key == "test-api-key"


class TestGetTailoringConfig:
    """Tests for config singleton accessor."""

    def teardown_method(self):
        """Reset config singleton after each test."""
        reset_tailoring_config()

    def test_get_tailoring_config_returns_singleton(self):
        """Test that get_tailoring_config returns the same instance."""
        config1 = get_tailoring_config()
        config2 = get_tailoring_config()
        assert config1 is config2

    def test_reset_tailoring_config_clears_singleton(self):
        """Test that reset clears the singleton."""
        config1 = get_tailoring_config()
        reset_tailoring_config()
        config2 = get_tailoring_config()
        assert config1 is not config2


class TestConfigPaths:
    """Tests for path-related configuration."""

    def teardown_method(self):
        """Reset config singleton after each test."""
        reset_tailoring_config()

    def test_template_paths_as_strings(self):
        """Test template paths can be provided as strings."""
        config = TailoringConfig(
            _env_file=None,
            template_dir="custom/path",
            resume_template="my_resume.html",
            cover_letter_template="my_cover.html",
        )
        assert config.template_dir == Path("custom/path")
        assert config.resume_template == "my_resume.html"
        assert config.cover_letter_template == "my_cover.html"

    def test_output_dir_as_string(self):
        """Test output directory can be provided as string."""
        config = TailoringConfig(_env_file=None, output_dir="output/pdfs")
        assert config.output_dir == Path("output/pdfs")

    def test_get_resume_template_path(self):
        """Test getting full resume template path."""
        config = TailoringConfig(
            _env_file=None,
            template_dir=Path("/templates"),
            resume_template="resume.html",
        )
        assert config.get_resume_template_path() == Path("/templates/resume.html")

    def test_get_cover_letter_template_path(self):
        """Test getting full cover letter template path."""
        config = TailoringConfig(
            _env_file=None,
            template_dir=Path("/templates"),
            cover_letter_template="cover.html",
        )
        assert config.get_cover_letter_template_path() == Path("/templates/cover.html")

    def test_get_styles_path(self):
        """Test getting styles CSS path."""
        config = TailoringConfig(_env_file=None, template_dir=Path("/templates"))
        assert config.get_styles_path() == Path("/templates/styles.css")


class TestExtractorFallback:
    """Tests for falling back to EXTRACTOR_LLM_* settings."""

    def teardown_method(self):
        """Reset config singleton after each test."""
        reset_tailoring_config()

    def test_falls_back_to_extractor_settings(self, isolated_env):
        """Test that config falls back to EXTRACTOR_LLM_* when TAILORING_* not set."""
        assert isolated_env is None
        # Set only EXTRACTOR_* env vars
        os.environ["EXTRACTOR_LLM_PROVIDER"] = "anthropic"
        os.environ["EXTRACTOR_LLM_MODEL"] = "claude-sonnet-4-20250514"
        os.environ["EXTRACTOR_LLM_API_KEY"] = "extractor-key"
        os.environ["EXTRACTOR_LLM_BASE_URL"] = "http://localhost:8000/v1"
        os.environ["EXTRACTOR_LLM_REASONING_EFFORT"] = "high"

        reset_tailoring_config()
        config = TailoringConfig(_env_file=None)

        assert config.llm_provider == "anthropic"
        assert config.llm_model == "claude-sonnet-4-20250514"
        assert config.llm_api_key == "extractor-key"
        assert config.llm_base_url == "http://localhost:8000/v1"
        assert config.llm_reasoning_effort == "high"

    def test_tailoring_settings_override_extractor(self, isolated_env):
        """Test that TAILORING_* settings take precedence over EXTRACTOR_*."""
        assert isolated_env is None
        # Set both TAILORING_* and EXTRACTOR_* env vars
        os.environ["TAILORING_LLM_PROVIDER"] = "openai"
        os.environ["TAILORING_LLM_MODEL"] = "gpt-4o"
        os.environ["TAILORING_LLM_REASONING_EFFORT"] = "low"
        os.environ["EXTRACTOR_LLM_PROVIDER"] = "anthropic"
        os.environ["EXTRACTOR_LLM_MODEL"] = "claude-sonnet-4-20250514"
        os.environ["EXTRACTOR_LLM_REASONING_EFFORT"] = "high"

        reset_tailoring_config()
        config = TailoringConfig(_env_file=None)

        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4o"
        assert config.llm_reasoning_effort == "low"
