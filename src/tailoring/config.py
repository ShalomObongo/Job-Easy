"""Configuration settings for the Tailoring module.

Provides settings for LLM provider, templates, and output paths.
Falls back to EXTRACTOR_LLM_* settings when TAILORING_* settings are not set.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_env_with_fallback(tailoring_key: str, extractor_key: str, default: str) -> str:
    """Get env var with fallback from TAILORING_ to EXTRACTOR_ prefix."""
    return os.getenv(f"TAILORING_{tailoring_key}") or os.getenv(extractor_key) or default


class TailoringConfig(BaseSettings):
    """Configuration for the tailoring system.

    Settings can be overridden via environment variables prefixed with TAILORING_.
    Falls back to EXTRACTOR_LLM_* settings for LLM configuration.

    Example: TAILORING_LLM_PROVIDER=anthropic
    Or reuse extractor settings: EXTRACTOR_LLM_PROVIDER=openai
    """

    model_config = SettingsConfigDict(
        env_prefix="TAILORING_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM settings (with fallback to EXTRACTOR_LLM_* settings)
    llm_provider: str = Field(
        default="openai",
        description="LLM provider (openai, anthropic, azure, etc.)",
    )
    llm_model: str = Field(
        default="gpt-4o",
        description="LLM model name",
    )
    llm_api_key: str | None = Field(
        default=None,
        description="API key for LLM provider",
    )
    llm_base_url: str | None = Field(
        default=None,
        description="Base URL for OpenAI-compatible endpoints",
    )
    llm_max_retries: Annotated[int, Field(ge=0)] = Field(
        default=1,
        description="Maximum retry attempts for LLM calls",
    )
    llm_timeout: Annotated[float, Field(gt=0)] = Field(
        default=180.0,
        description="Timeout in seconds for LLM calls",
    )

    @model_validator(mode="after")
    def apply_extractor_fallbacks(self) -> TailoringConfig:
        """Fall back to EXTRACTOR_LLM_* settings if TAILORING_* not set.

        Only applies fallback when:
        1. No TAILORING_* env var is set for the field
        2. The value is still the default (wasn't explicitly passed to constructor)
        """
        # Only fallback provider if env not set AND value is default
        if not os.getenv("TAILORING_LLM_PROVIDER") and self.llm_provider == "openai":
            extractor_provider = os.getenv("EXTRACTOR_LLM_PROVIDER")
            if extractor_provider:
                self.llm_provider = extractor_provider

        # Only fallback model if env not set AND value is default
        if not os.getenv("TAILORING_LLM_MODEL") and self.llm_model == "gpt-4o":
            extractor_model = os.getenv("EXTRACTOR_LLM_MODEL")
            if extractor_model:
                self.llm_model = extractor_model

        # Only fallback api_key if env not set AND value is default (None)
        if not os.getenv("TAILORING_LLM_API_KEY") and self.llm_api_key is None:
            extractor_key = os.getenv("EXTRACTOR_LLM_API_KEY")
            if extractor_key:
                self.llm_api_key = extractor_key

        # Only fallback base_url if env not set AND value is default (None)
        if not os.getenv("TAILORING_LLM_BASE_URL") and self.llm_base_url is None:
            extractor_base_url = os.getenv("EXTRACTOR_LLM_BASE_URL")
            if extractor_base_url:
                self.llm_base_url = extractor_base_url

        return self

    # Template settings
    template_dir: Path = Field(
        default=Path("src/tailoring/templates"),
        description="Directory containing HTML/CSS templates",
    )
    resume_template: str = Field(
        default="resume.html",
        description="Resume template filename",
    )
    cover_letter_template: str = Field(
        default="cover_letter.html",
        description="Cover letter template filename",
    )

    # Output settings
    output_dir: Path = Field(
        default=Path("artifacts/docs"),
        description="Directory for generated PDF documents",
    )

    # Cover letter generation settings
    cover_letter_min_words: Annotated[int, Field(gt=0)] = Field(
        default=300,
        description="Minimum word count for cover letters",
    )
    cover_letter_max_words: Annotated[int, Field(gt=0)] = Field(
        default=400,
        description="Maximum word count for cover letters",
    )

    @field_validator("template_dir", "output_dir", mode="before")
    @classmethod
    def convert_to_path(cls, v: str | Path) -> Path:
        """Convert string paths to Path objects."""
        if isinstance(v, str):
            return Path(v)
        return v

    def get_resume_template_path(self) -> Path:
        """Get full path to resume template."""
        return self.template_dir / self.resume_template

    def get_cover_letter_template_path(self) -> Path:
        """Get full path to cover letter template."""
        return self.template_dir / self.cover_letter_template

    def get_styles_path(self) -> Path:
        """Get full path to styles CSS file."""
        return self.template_dir / "styles.css"


# Singleton instance
_tailoring_config: TailoringConfig | None = None


def get_tailoring_config() -> TailoringConfig:
    """Get the tailoring configuration singleton."""
    global _tailoring_config
    if _tailoring_config is None:
        _tailoring_config = TailoringConfig()
    return _tailoring_config


def reset_tailoring_config() -> None:
    """Reset the configuration singleton (useful for testing)."""
    global _tailoring_config
    _tailoring_config = None
