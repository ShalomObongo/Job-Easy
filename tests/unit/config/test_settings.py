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

        from src.config.settings import Settings

        settings = Settings(_env_file=None)
        assert settings.tracker_db_path == Path("/custom/tracker.db")
        assert settings.output_dir == Path("/custom/output")


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

    def test_settings_chrome_profile_optional(self):
        """Chrome profile settings should be optional."""
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
