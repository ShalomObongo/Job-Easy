"""Configuration settings for Job-Easy."""

import json
from enum import Enum
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Mode(str, Enum):
    """Application operating mode."""

    SINGLE = "single"
    AUTONOMOUS = "autonomous"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings have sensible defaults and can be overridden via
    environment variables or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        enable_decoding=False,
        extra="ignore",
    )

    # Operating mode
    mode: Mode = Field(
        default=Mode.SINGLE,
        description="Operating mode: 'single' for one job, 'autonomous' for batch",
    )

    # Safety settings
    auto_submit: bool = Field(
        default=False,
        description="If True, submit applications automatically (NOT RECOMMENDED)",
    )

    # Application limits
    max_applications_per_day: Annotated[int, Field(gt=0)] = Field(
        default=10,
        description="Maximum applications to process per day in autonomous mode",
    )

    # Paths
    tracker_db_path: Path = Field(
        default=Path("./data/tracker.db"),
        description="Path to the SQLite tracker database",
    )
    output_dir: Path = Field(
        default=Path("./artifacts"),
        description="Directory for generated artifacts",
    )

    # Runner settings
    prohibited_domains: list[str] = Field(
        default_factory=list,
        description=(
            "Domain patterns the runner must NOT navigate to (blocklist-first policy). "
            "Examples: example.com, *.example.com, http*://example.com"
        ),
    )
    allowlist_log_path: Path = Field(
        default=Path("./data/allowlist.log"),
        description="Append-only log of encountered non-prohibited domains",
    )
    qa_bank_path: Path = Field(
        default=Path("./data/qa_bank.json"),
        description="Path to the persistent Q&A bank used for application questions",
    )
    runner_headless: bool = Field(
        default=False,
        description="Run application browser headless (not recommended for debugging)",
    )
    runner_window_width: int = Field(
        default=1280,
        description="Browser window width for application runs",
    )
    runner_window_height: int = Field(
        default=720,
        description="Browser window height for application runs",
    )
    runner_max_failures: Annotated[int, Field(gt=0)] = Field(
        default=3,
        description="Maximum retry attempts for failed runner steps",
    )
    runner_max_actions_per_step: Annotated[int, Field(gt=0)] = Field(
        default=4,
        description="Max actions per agent step (form fill batching)",
    )
    runner_step_timeout: Annotated[int, Field(gt=0)] = Field(
        default=120,
        description="Timeout per runner step in seconds",
    )
    runner_use_vision: str = Field(
        default="auto",
        description="Runner vision mode: 'auto', 'true', or 'false'",
    )
    runner_llm_provider: str | None = Field(
        default=None,
        description="Runner LLM provider: 'openai', 'anthropic', 'browser_use', or 'auto'",
    )
    runner_llm_base_url: str | None = Field(
        default=None,
        description="Runner LLM base URL for OpenAI-compatible endpoints",
    )
    runner_llm_api_key: str | None = Field(
        default=None,
        description="Runner LLM API key (overrides extractor provider keys for runner only)",
    )
    runner_llm_model: str | None = Field(
        default=None,
        description="Runner LLM model ID (e.g., 'gpt-4o', 'claude-sonnet-4-20250514')",
    )
    runner_llm_reasoning_effort: str | None = Field(
        default=None,
        description=(
            "Reasoning effort for supported models (e.g. 'none', 'minimal', 'low', "
            "'medium', 'high', 'xhigh')."
        ),
    )

    # Chrome profile settings
    use_existing_chrome_profile: bool = Field(
        default=False,
        description="Use an existing Chrome profile for sessions",
    )
    chrome_user_data_dir: Path | None = Field(
        default=None,
        description="Chrome user data directory path",
    )
    chrome_profile_dir: str = Field(
        default="Default",
        description="Chrome profile directory name",
    )
    chrome_profile_mode: str = Field(
        default="auto",
        description="Chrome profile mode: 'copy' (safe), 'direct' (use in place), or 'auto'",
    )

    # API settings
    llm_api_key: str | None = Field(
        default=None,
        description="API key for LLM provider (OpenAI, Anthropic, etc.)",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR",
    )

    @field_validator("mode", mode="before")
    @classmethod
    def validate_mode(cls, v: str | Mode) -> Mode:
        """Convert string mode to Mode enum."""
        if isinstance(v, Mode):
            return v
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower == "single":
                return Mode.SINGLE
            elif v_lower == "autonomous":
                return Mode.AUTONOMOUS
            else:
                raise ValueError(f"Invalid mode: {v}. Must be 'single' or 'autonomous'")
        raise ValueError(f"Invalid mode type: {type(v)}")

    @field_validator("prohibited_domains", mode="before")
    @classmethod
    def parse_prohibited_domains(cls, v: object) -> list[str]:
        """Parse PROHIBITED_DOMAINS from env-friendly formats.

        Supports:
        - JSON list: ["example.com", "*.example.com"]
        - Comma-separated: example.com, *.example.com
        - Newline-separated entries
        """
        if v is None:
            return []

        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]

        if not isinstance(v, str):
            return [str(v).strip()] if str(v).strip() else []

        raw = v.strip()
        if not raw:
            return []

        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None
            else:
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]

        parts: list[str] = []
        for chunk in raw.replace("\n", ",").split(","):
            item = chunk.strip()
            if item:
                parts.append(item)
        return parts

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a known level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

    @field_validator("chrome_profile_mode", mode="before")
    @classmethod
    def validate_chrome_profile_mode(cls, v: str) -> str:
        """Validate chrome_profile_mode."""
        if not isinstance(v, str):
            raise ValueError("chrome_profile_mode must be a string")
        value = v.lower().strip()
        if value not in {"auto", "copy", "direct"}:
            raise ValueError("chrome_profile_mode must be one of: auto, copy, direct")
        return value

    @field_validator("runner_use_vision", mode="before")
    @classmethod
    def validate_runner_use_vision(cls, v: str) -> str:
        """Validate runner_use_vision."""
        if not isinstance(v, str):
            raise ValueError("runner_use_vision must be a string")
        value = v.lower().strip()
        if value not in {"auto", "true", "false"}:
            raise ValueError("runner_use_vision must be one of: auto, true, false")
        return value

    @field_validator("runner_llm_provider", mode="before")
    @classmethod
    def validate_runner_llm_provider(cls, v: str | None) -> str | None:
        """Validate runner_llm_provider."""
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("runner_llm_provider must be a string")
        value = v.lower().strip()
        if value not in {"auto", "openai", "anthropic", "browser_use"}:
            raise ValueError(
                "runner_llm_provider must be one of: auto, openai, anthropic, browser_use"
            )
        return value


# Singleton instance for easy import
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset the settings singleton (useful for testing)."""
    global _settings
    _settings = None
