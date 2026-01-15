"""Configuration settings for the Fit Scoring system."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScoringConfig(BaseSettings):
    """Fit scoring configuration settings.

    All settings have sensible defaults and can be overridden via
    environment variables with `SCORING_` prefix or a .env file.
    """

    model_config = SettingsConfigDict(
        env_prefix="SCORING_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Profile settings
    profile_path: Path = Field(
        default=Path("profiles/profile.yaml"),
        description="Path to user profile file (YAML/JSON)",
    )

    # Threshold settings
    fit_score_threshold: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.75,
        description="Minimum score for 'apply' recommendation",
    )
    review_margin: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.05,
        description="Margin around threshold for 'review' recommendation",
    )

    # Scoring weights (must sum to 1.0)
    weight_must_have: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.40,
        description="Weight for required skills match",
    )
    weight_preferred: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.20,
        description="Weight for preferred skills match",
    )
    weight_experience: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.25,
        description="Weight for experience match",
    )
    weight_education: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.15,
        description="Weight for education match",
    )

    # Matching settings
    skill_fuzzy_match: bool = Field(
        default=True,
        description="Enable fuzzy skill matching",
    )
    skill_fuzzy_threshold: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.85,
        description="Similarity threshold for fuzzy matching",
    )
    experience_tolerance_years: Annotated[int, Field(ge=0)] = Field(
        default=2,
        description="Tolerance for experience mismatch in years",
    )

    # Constraint modes (True = hard constraint causing skip, False = soft warning)
    location_strict: bool = Field(
        default=False,
        description="Strict location matching (hard constraint)",
    )
    visa_strict: bool = Field(
        default=True,
        description="Strict visa requirement (hard constraint)",
    )
    salary_strict: bool = Field(
        default=False,
        description="Strict salary filtering (hard constraint)",
    )

    @model_validator(mode="after")
    def validate_weights_sum_to_one(self) -> ScoringConfig:
        """Ensure scoring weights sum to 1.0 (within tolerance)."""
        weight_sum = (
            self.weight_must_have
            + self.weight_preferred
            + self.weight_experience
            + self.weight_education
        )
        if abs(weight_sum - 1.0) > 1e-6:
            raise ValueError(
                "Scoring weights must sum to 1.0. "
                f"Got {weight_sum:.6f} "
                f"(must_have={self.weight_must_have}, preferred={self.weight_preferred}, "
                f"experience={self.weight_experience}, education={self.weight_education})."
            )
        return self


# Singleton instance for easy import
_scoring_config: ScoringConfig | None = None


def get_scoring_config() -> ScoringConfig:
    """Get the scoring configuration singleton."""
    global _scoring_config
    if _scoring_config is None:
        _scoring_config = ScoringConfig()
    return _scoring_config


def reset_scoring_config() -> None:
    """Reset the scoring configuration singleton (useful for testing)."""
    global _scoring_config
    _scoring_config = None
