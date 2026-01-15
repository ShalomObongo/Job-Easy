"""Data models for the Job Extractor."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class JobDescription(BaseModel):
    """Pydantic model representing extracted job posting data.

    This model is used with Browser Use's `output_model_schema` parameter
    to get structured output from the extraction agent.

    Attributes:
        company: Company name.
        role_title: Job title/position.
        job_url: Canonical URL of the job posting.
        location: Job location (city, state, country, or "Remote").
        apply_url: Direct application URL (if different from job_url).
        job_id: Platform-specific job identifier.
        description: Full job description text.
        responsibilities: List of key responsibilities.
        qualifications: List of required/preferred qualifications.
        required_skills: Must-have skills/technologies.
        preferred_skills: Nice-to-have skills/technologies.
        experience_years_min: Minimum required years of experience.
        experience_years_max: Maximum years of experience.
        education: Required education level.
        salary_min: Minimum salary (if disclosed).
        salary_max: Maximum salary (if disclosed).
        salary_currency: Currency code (USD, EUR, etc.).
        work_type: Remote, hybrid, or onsite.
        employment_type: Full-time, part-time, or contract.
        extracted_at: Timestamp of extraction.
        extraction_source: Detected job board (greenhouse, lever, workday, etc.).
    """

    # Required fields
    company: str = Field(..., description="Company name")
    role_title: str = Field(..., description="Job title/position")
    job_url: str = Field(..., description="Canonical URL of the job posting")

    # Basic metadata (optional)
    location: str | None = Field(
        default=None, description="Job location (city, state, country, or 'Remote')"
    )
    apply_url: str | None = Field(
        default=None, description="Direct application URL (if different from job_url)"
    )
    job_id: str | None = Field(
        default=None,
        description="Platform-specific job identifier (Greenhouse, Lever, Workday patterns)",
    )

    # Job description content
    description: str | None = Field(
        default=None, description="Full job description text"
    )
    responsibilities: list[str] = Field(
        default_factory=list, description="List of key responsibilities"
    )
    qualifications: list[str] = Field(
        default_factory=list, description="List of required/preferred qualifications"
    )

    # Requirements breakdown
    required_skills: list[str] = Field(
        default_factory=list, description="Must-have skills/technologies"
    )
    preferred_skills: list[str] = Field(
        default_factory=list, description="Nice-to-have skills/technologies"
    )
    experience_years_min: int | None = Field(
        default=None, description="Minimum required years of experience"
    )
    experience_years_max: int | None = Field(
        default=None, description="Maximum years of experience"
    )
    education: str | None = Field(default=None, description="Required education level")

    # Compensation & work type
    salary_min: int | None = Field(
        default=None, description="Minimum salary (if disclosed)"
    )
    salary_max: int | None = Field(
        default=None, description="Maximum salary (if disclosed)"
    )
    salary_currency: str | None = Field(
        default=None, description="Currency code (USD, EUR, etc.)"
    )
    work_type: Literal["remote", "hybrid", "onsite"] | None = Field(
        default=None, description="Work arrangement type"
    )
    employment_type: Literal["full-time", "part-time", "contract"] | None = Field(
        default=None, description="Employment type"
    )

    # Extraction metadata
    extracted_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp of extraction"
    )
    extraction_source: str | None = Field(
        default=None,
        description="Detected job board (greenhouse, lever, workday, linkedin, etc.)",
    )

    def to_dict(self) -> dict:
        """Serialize the job description to a dictionary.

        Returns:
            Dictionary representation of the job description.
        """
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> JobDescription:
        """Deserialize a job description from a dictionary.

        Args:
            data: Dictionary containing job description data.

        Returns:
            JobDescription instance.
        """
        return cls.model_validate(data)

    def save_json(self, path: Path | str) -> None:
        """Save the job description to a JSON file.

        Args:
            path: Path to the output JSON file.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
