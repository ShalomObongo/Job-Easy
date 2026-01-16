"""Data models for the Fit Scoring system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class WorkExperience(BaseModel):
    """Work experience entry for a user's profile."""

    company: str = Field(..., description="Company name")
    title: str = Field(..., description="Job title")
    start_date: date = Field(..., description="Start date")
    end_date: date | None = Field(default=None, description="End date (if applicable)")
    description: str = Field(..., description="Role description")
    skills_used: list[str] = Field(
        default_factory=list, description="Skills used in this role"
    )

    def to_dict(self) -> dict:
        """Serialize to a dictionary."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> WorkExperience:
        """Deserialize from a dictionary."""
        return cls.model_validate(data)


class Education(BaseModel):
    """Education entry for a user's profile."""

    institution: str = Field(..., description="Institution name")
    degree: str = Field(..., description="Degree level")
    field: str = Field(..., description="Field of study")
    graduation_year: int | None = Field(default=None, description="Graduation year")

    def to_dict(self) -> dict:
        """Serialize to a dictionary."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Education:
        """Deserialize from a dictionary."""
        return cls.model_validate(data)


class Certification(BaseModel):
    """Certification / training entry for a user's profile."""

    name: str = Field(..., description="Certification or training name")
    issuer: str | None = Field(
        default=None, description="Issuing organization/provider"
    )
    date_awarded: date | None = Field(
        default=None, description="Date awarded/completed"
    )
    expires: date | None = Field(default=None, description="Expiration date")
    url: str | None = Field(default=None, description="Verification URL")

    def to_dict(self) -> dict:
        """Serialize to a dictionary."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Certification:
        """Deserialize from a dictionary."""
        return cls.model_validate(data)


class UserProfile(BaseModel):
    """User profile used for fit scoring."""

    # Basic info
    name: str = Field(..., description="Candidate full name")
    email: str = Field(..., description="Contact email")
    phone: str | None = Field(default=None, description="Contact phone")
    location: str = Field(..., description="Current location")
    linkedin_url: str | None = Field(default=None, description="LinkedIn profile URL")

    # Skills & experience
    skills: list[str] = Field(..., description="List of skills/technologies")
    years_of_experience: int = Field(..., ge=0, description="Total years of experience")
    current_title: str = Field(default="", description="Current job title")
    summary: str = Field(default="", description="Brief professional summary")

    # History
    work_history: list[WorkExperience] = Field(
        default_factory=list, description="Past positions"
    )
    education: list[Education] = Field(
        default_factory=list, description="Education history"
    )
    certifications: list[Certification] = Field(
        default_factory=list,
        description="Certifications and trainings (optional)",
    )

    # Constraints and preferences
    work_type_preferences: list[Literal["remote", "hybrid", "onsite"]] = Field(
        default_factory=lambda: ["remote", "hybrid", "onsite"],
        description="Acceptable work types",
    )
    target_locations: list[str] | None = Field(
        default=None, description="Acceptable cities/regions (None = any)"
    )
    visa_sponsorship_needed: bool = Field(
        default=False, description="Whether sponsorship is required"
    )
    min_salary: int | None = Field(
        default=None, description="Minimum acceptable salary"
    )
    preferred_salary: int | None = Field(default=None, description="Target salary")
    salary_currency: str = Field(default="USD", description="Currency code")
    experience_level: Literal["entry", "mid", "senior", "lead", "executive"] = Field(
        default="mid", description="Experience level"
    )

    def to_dict(self) -> dict:
        """Serialize to a dictionary."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> UserProfile:
        """Deserialize from a dictionary."""
        return cls.model_validate(data)


@dataclass
class FitScore:
    """Detailed scoring breakdown for a job evaluation."""

    total_score: float
    must_have_score: float
    must_have_matched: list[str] = field(default_factory=list)
    must_have_missing: list[str] = field(default_factory=list)
    preferred_score: float = 1.0
    preferred_matched: list[str] = field(default_factory=list)
    experience_score: float = 1.0
    experience_reasoning: str = ""
    education_score: float = 1.0
    education_reasoning: str = ""

    def __post_init__(self) -> None:
        for name in (
            "total_score",
            "must_have_score",
            "preferred_score",
            "experience_score",
            "education_score",
        ):
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be between 0.0 and 1.0 (got {value})")


@dataclass
class ConstraintResult:
    """Result of evaluating hard/soft constraints against a job."""

    passed: bool
    hard_violations: list[str] = field(default_factory=list)
    soft_warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.passed and self.hard_violations:
            raise ValueError(
                "ConstraintResult.passed=True is incompatible with hard_violations"
            )
        if not self.passed and not self.hard_violations:
            raise ValueError(
                "ConstraintResult.passed=False requires at least one hard violation"
            )


@dataclass
class FitResult:
    """Full evaluation result for a job."""

    job_url: str
    job_title: str
    company: str
    fit_score: FitScore
    constraints: ConstraintResult
    recommendation: Literal["apply", "skip", "review"]
    reasoning: str
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.recommendation not in {"apply", "skip", "review"}:
            raise ValueError(
                "recommendation must be one of: apply, skip, review "
                f"(got {self.recommendation})"
            )


# Placeholder for remaining models (implemented in subsequent tasks).
