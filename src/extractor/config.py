"""Configuration settings for the Job Extractor."""

from pathlib import Path
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExtractorConfig(BaseSettings):
    """Extractor configuration settings.

    All settings have sensible defaults and can be overridden via
    environment variables with EXTRACTOR_ prefix or a .env file.

    Attributes:
        headless: Run browser in headless mode.
        step_timeout: Timeout per step in seconds.
        max_failures: Maximum retry attempts for failed steps.
        use_vision: Vision mode ("auto", "true", "false").
        output_dir: Directory for output artifacts.
        allowed_domains: List of allowed domains for navigation.
        window_width: Browser window width.
        window_height: Browser window height.
        llm_provider: LLM provider to use ("openai", "anthropic", "browser_use", "auto").
        llm_base_url: Base URL for the LLM API (for custom endpoints).
        llm_api_key: API key for the LLM provider.
        llm_model: Model ID to use for extraction.
        keep_browser_use_temp_dirs: If True, do not delete Browser Use temp
            `user_data_dir` directories created under the system temp folder.
    """

    model_config = SettingsConfigDict(
        env_prefix="EXTRACTOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Browser settings
    headless: bool = Field(
        default=True,
        description="Run browser in headless mode",
    )
    window_width: int = Field(
        default=1280,
        description="Browser window width",
    )
    window_height: int = Field(
        default=720,
        description="Browser window height",
    )

    # Agent settings
    step_timeout: Annotated[int, Field(gt=0)] = Field(
        default=60,
        description="Timeout per step in seconds",
    )
    max_failures: Annotated[int, Field(gt=0)] = Field(
        default=3,
        description="Maximum retry attempts for failed steps",
    )
    use_vision: str = Field(
        default="auto",
        description="Vision mode: 'auto', 'true', or 'false'",
    )

    # Output settings
    output_dir: Path = Field(
        default=Path("./artifacts"),
        description="Directory for output artifacts (jd.json, etc.)",
    )

    # Domain restrictions
    allowed_domains: list[str] = Field(
        default_factory=list,
        description="List of allowed domains for browser navigation",
    )

    # LLM settings
    llm_provider: str = Field(
        default="auto",
        description="LLM provider: 'openai', 'anthropic', 'browser_use', or 'auto'",
    )
    llm_base_url: str | None = Field(
        default=None,
        description="Base URL for the LLM API (for OpenAI-compatible endpoints)",
    )
    llm_api_key: str | None = Field(
        default=None,
        description="API key for the LLM provider",
    )
    llm_model: str | None = Field(
        default=None,
        description="Model ID to use for extraction (e.g., 'gpt-4o', 'claude-sonnet-4-20250514')",
    )
    llm_reasoning_effort: str | None = Field(
        default=None,
        description=(
            "Reasoning effort for supported models (e.g. 'none', 'minimal', 'low', "
            "'medium', 'high', 'xhigh')."
        ),
    )

    keep_browser_use_temp_dirs: bool = Field(
        default=False,
        description="Keep Browser Use temp user_data_dir directories (not recommended)",
    )


# Singleton instance for easy import
_extractor_config: ExtractorConfig | None = None


def get_extractor_config() -> ExtractorConfig:
    """Get the extractor configuration singleton."""
    global _extractor_config
    if _extractor_config is None:
        _extractor_config = ExtractorConfig()
    return _extractor_config


def reset_extractor_config() -> None:
    """Reset the extractor configuration singleton (useful for testing)."""
    global _extractor_config
    _extractor_config = None
