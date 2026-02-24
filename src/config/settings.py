"""Configuration settings for Job-Easy."""

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Mode(StrEnum):
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
    runner_assume_yes: bool = Field(
        default=False,
        description=(
            "Assume 'yes' for non-submit prompts (fit skip/review and document approval). "
            "Does NOT bypass duplicate checks, OTP/CAPTCHA prompts, or the final submit gate."
        ),
    )
    runner_yolo_mode: bool = Field(
        default=False,
        description=(
            "Enable runner YOLO mode (best-effort auto-answering for application questions)."
        ),
    )
    runner_auto_submit: bool = Field(
        default=False,
        description=(
            "Automatically confirm submit without human prompt. "
            "Requires both runner_yolo_mode and runner_assume_yes to be enabled."
        ),
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
    runner_backend: str = Field(
        default="skyvern_local",
        description="Runner backend implementation. Currently only 'skyvern_local'.",
    )
    runner_skyvern_base_url: str = Field(
        default="http://localhost:8000",
        description="Local Skyvern API base URL for runner execution.",
    )
    runner_skyvern_api_key: str | None = Field(
        default=None,
        description="Optional Skyvern API key for local runner execution.",
    )
    runner_skyvern_timeout_seconds: Annotated[int, Field(gt=0)] = Field(
        default=15,
        description="HTTP timeout in seconds for Skyvern health and artifact requests.",
    )
    runner_skyvern_poll_interval_seconds: Annotated[float, Field(gt=0)] = Field(
        default=1.5,
        description="Polling interval in seconds for async Skyvern run checks.",
    )
    runner_skyvern_max_wait_seconds: Annotated[int, Field(gt=0)] = Field(
        default=1800,
        description="Maximum wait in seconds for Skyvern run completion.",
    )
    runner_skyvern_enforce_local: bool = Field(
        default=True,
        description="Reject non-local Skyvern base URLs for runner execution.",
    )
    runner_skyvern_verify_health: bool = Field(
        default=True,
        description="Probe Skyvern health endpoint before execution.",
    )
    runner_skyvern_env_overrides: str | None = Field(
        default=None,
        description=(
            "Optional JSON object of Skyvern env overrides. "
            "Applied before mapped RUNNER_LLM_* compatibility values."
        ),
    )
    runner_skyvern_workflow_id: str | None = Field(
        default=None,
        description=(
            "Optional workflow ID for runner execution. If unset, runner uses run_task."
        ),
    )
    runner_skyvern_browser_profile_id: str | None = Field(
        default=None,
        description="Optional browser profile ID for persistent authenticated sessions.",
    )
    runner_skyvern_browser_session_id: str | None = Field(
        default=None,
        description="Optional browser session ID for session reuse.",
    )
    runner_skyvern_browser_address: str | None = Field(
        default=None,
        description="Optional remote-debugging browser address (e.g. 127.0.0.1:9222).",
    )
    runner_skyvern_browser_path: str | None = Field(
        default=None,
        description="Optional Chrome executable path for Skyvern CDP connect mode.",
    )
    runner_skyvern_persist_browser_session: bool = Field(
        default=False,
        description="Request browser session persistence for profile bootstrap/rotation.",
    )
    runner_skyvern_profile_bootstrap_workflow_id: str | None = Field(
        default=None,
        description=(
            "Optional workflow ID used to bootstrap and persist a browser session profile."
        ),
    )
    runner_skyvern_profile_name: str = Field(
        default="job-easy-profile",
        description="Name used when creating a Skyvern browser profile.",
    )
    runner_skyvern_profile_create_retries: Annotated[int, Field(gt=0)] = Field(
        default=10,
        description="Retries for async browser profile archive availability.",
    )
    runner_skyvern_profile_create_retry_delay_seconds: Annotated[float, Field(gt=0)] = (
        Field(
            default=1.0,
            description="Retry delay in seconds for browser profile creation.",
        )
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

    @field_validator("runner_backend", mode="before")
    @classmethod
    def validate_runner_backend(cls, v: str) -> str:
        """Validate runner backend selection."""
        if not isinstance(v, str):
            raise ValueError("runner_backend must be a string")
        value = v.lower().strip()
        if value != "skyvern_local":
            raise ValueError("runner_backend must be 'skyvern_local'")
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
