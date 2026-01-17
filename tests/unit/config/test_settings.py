"""Tests for Settings configuration class."""

import os
from pathlib import Path

import pytest


class TestSettingsDefaults:
    """Test that Settings loads sensible defaults."""

    def test_settings_loads_with_defaults(self):
        """Settings should load with default values when no env vars are set."""
        # Clear relevant env vars
        env_vars_to_clear = [
            "MODE",
            "AUTO_SUBMIT",
            "MAX_APPLICATIONS_PER_DAY",
            "TRACKER_DB_PATH",
            "OUTPUT_DIR",
            "PROHIBITED_DOMAINS",
            "ALLOWLIST_LOG_PATH",
            "QA_BANK_PATH",
            "RUNNER_HEADLESS",
            "RUNNER_WINDOW_WIDTH",
            "RUNNER_WINDOW_HEIGHT",
            "RUNNER_MAX_FAILURES",
            "RUNNER_MAX_ACTIONS_PER_STEP",
            "RUNNER_STEP_TIMEOUT",
            "RUNNER_USE_VISION",
            "RUNNER_LLM_PROVIDER",
            "RUNNER_LLM_API_KEY",
            "RUNNER_LLM_BASE_URL",
            "RUNNER_LLM_MODEL",
        ]
        original_values = {}
        for var in env_vars_to_clear:
            original_values[var] = os.environ.pop(var, None)

        try:
            from src.config.settings import Settings

            settings = Settings(_env_file=None)

            # Check defaults
            assert settings.mode == "single"
            assert settings.auto_submit is False
            assert settings.max_applications_per_day == 10
            assert settings.tracker_db_path == Path("./data/tracker.db")
            assert settings.output_dir == Path("./artifacts")
            assert settings.prohibited_domains == []
            assert settings.allowlist_log_path == Path("./data/allowlist.log")
            assert settings.qa_bank_path == Path("./data/qa_bank.json")
            assert settings.runner_headless is False
            assert settings.runner_window_width == 1280
            assert settings.runner_window_height == 720
            assert settings.runner_max_failures == 3
            assert settings.runner_max_actions_per_step == 4
            assert settings.runner_step_timeout == 120
            assert settings.runner_use_vision == "auto"
            assert settings.runner_llm_provider is None
            assert settings.runner_llm_api_key is None
            assert settings.runner_llm_base_url is None
            assert settings.runner_llm_model is None
        finally:
            # Restore env vars
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value


class TestSettingsFromEnvironment:
    """Test that Settings reads from environment variables."""

    def test_settings_reads_mode_from_env(self, monkeypatch):
        """Settings should read MODE from environment."""
        monkeypatch.setenv("MODE", "autonomous")

        from src.config.settings import Settings

        settings = Settings(_env_file=None)
        assert settings.mode == "autonomous"

    def test_settings_reads_auto_submit_from_env(self, monkeypatch):
        """Settings should read AUTO_SUBMIT from environment."""
        monkeypatch.setenv("AUTO_SUBMIT", "true")

        from src.config.settings import Settings

        settings = Settings(_env_file=None)
        assert settings.auto_submit is True

    def test_settings_reads_max_applications_from_env(self, monkeypatch):
        """Settings should read MAX_APPLICATIONS_PER_DAY from environment."""
        monkeypatch.setenv("MAX_APPLICATIONS_PER_DAY", "25")

        from src.config.settings import Settings

        settings = Settings(_env_file=None)
        assert settings.max_applications_per_day == 25

    def test_settings_reads_paths_from_env(self, monkeypatch):
        """Settings should read path configurations from environment."""
        monkeypatch.setenv("TRACKER_DB_PATH", "/custom/tracker.db")
        monkeypatch.setenv("OUTPUT_DIR", "/custom/output")
        monkeypatch.setenv("ALLOWLIST_LOG_PATH", "/custom/allowlist.log")
        monkeypatch.setenv("QA_BANK_PATH", "/custom/qa_bank.json")

        from src.config.settings import Settings

        settings = Settings(_env_file=None)
        assert settings.tracker_db_path == Path("/custom/tracker.db")
        assert settings.output_dir == Path("/custom/output")
        assert settings.allowlist_log_path == Path("/custom/allowlist.log")
        assert settings.qa_bank_path == Path("/custom/qa_bank.json")

    def test_settings_parses_prohibited_domains_from_env(self, monkeypatch):
        """Settings should parse comma-separated PROHIBITED_DOMAINS."""
        monkeypatch.setenv("PROHIBITED_DOMAINS", "example.com, *.evil.com")

        from src.config.settings import Settings

        settings = Settings(_env_file=None)
        assert settings.prohibited_domains == ["example.com", "*.evil.com"]

    def test_settings_parses_prohibited_domains_from_json_env(self, monkeypatch):
        """Settings should parse JSON-list PROHIBITED_DOMAINS."""
        monkeypatch.setenv("PROHIBITED_DOMAINS", '["example.com", "*.evil.com"]')

        from src.config.settings import Settings

        settings = Settings(_env_file=None)
        assert settings.prohibited_domains == ["example.com", "*.evil.com"]


class TestSettingsValidation:
    """Test that Settings validates values correctly."""

    def test_settings_validates_mode_values(self, monkeypatch):
        """Settings should only accept valid mode values."""
        monkeypatch.setenv("MODE", "invalid_mode")

        from src.config.settings import Settings

        with pytest.raises(ValueError):
            Settings(_env_file=None)

    def test_settings_validates_max_applications_positive(self, monkeypatch):
        """Settings should require max_applications_per_day to be positive."""
        monkeypatch.setenv("MAX_APPLICATIONS_PER_DAY", "-5")

        from src.config.settings import Settings

        with pytest.raises(ValueError):
            Settings(_env_file=None)


class TestSettingsOptionalFields:
    """Test optional configuration fields."""

    def test_settings_chrome_profile_optional(self, monkeypatch):
        """Chrome profile settings should be optional."""
        # Ensure a clean environment even if the developer has Chrome profile
        # env vars set locally (e.g., via shell profile/direnv).
        for var in [
            "USE_EXISTING_CHROME_PROFILE",
            "CHROME_USER_DATA_DIR",
            "CHROME_PROFILE_DIR",
            "CHROME_PROFILE_MODE",
        ]:
            monkeypatch.delenv(var, raising=False)

        from src.config.settings import Settings

        settings = Settings(_env_file=None)
        assert settings.use_existing_chrome_profile is False
        assert settings.chrome_user_data_dir is None
        assert settings.chrome_profile_dir == "Default"
        assert settings.chrome_profile_mode == "auto"

    def test_settings_llm_api_key_optional(self):
        """LLM API key should be optional (can be loaded later)."""
        from src.config.settings import Settings

        settings = Settings(_env_file=None)
        # Should not raise, even without API key
        assert settings.llm_api_key is None or isinstance(settings.llm_api_key, str)
