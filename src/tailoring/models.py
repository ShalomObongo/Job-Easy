"""Data models for the Tailoring module.

Contains Pydantic models for:
- TailoringPlan: Keyword maps, evidence mappings, section ordering
- TailoredResume: Fully tailored resume structure
- CoverLetter: Generated cover letter content
- DocReviewPacket: Summary for HITL review
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class KeywordMatch(BaseModel):
    """Maps a job keyword to a matching user skill."""

    job_keyword: str = Field(..., description="Keyword from job requirements")
    user_skill: str = Field(..., description="Matching skill from user profile")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Match confidence score (0-1)"
    )


class EvidenceMapping(BaseModel):
    """Maps a job requirement to user evidence."""

    requirement: str = Field(..., description="Job requirement text")
    evidence: str = Field(
        ..., description="User evidence that supports this requirement"
    )
    source_company: str = Field(..., description="Company where evidence comes from")
    source_role: str = Field(..., description="Role where evidence comes from")
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Relevance score (0-1)"
    )


class BulletRewrite(BaseModel):
    """Suggestion for rewriting a resume bullet point."""

    original: str = Field(..., description="Original bullet text")
    suggested: str = Field(..., description="Suggested rewritten text")
    keywords_added: list[str] = Field(
        default_factory=list, description="Keywords added in rewrite"
    )
    emphasis_reason: str = Field(..., description="Reason for emphasis/rewrite")


class UnsupportedClaim(BaseModel):
    """Warning about a job requirement without user evidence."""

    requirement: str = Field(..., description="Requirement that cannot be supported")
    reason: str = Field(..., description="Why this requirement cannot be supported")
    severity: Literal["warning", "critical"] = Field(..., description="Severity level")


class TailoringPlan(BaseModel):
    """Complete tailoring plan for a job application.

    Contains keyword maps, evidence mappings, section ordering,
    and warnings about unsupported requirements.
    """

    job_url: str = Field(..., description="URL of the job posting")
    company: str = Field(..., description="Company name")
    role_title: str = Field(..., description="Job title")
    keyword_matches: list[KeywordMatch] = Field(
        default_factory=list, description="Keyword matches between job and profile"
    )
    evidence_mappings: list[EvidenceMapping] = Field(
        default_factory=list, description="Evidence mapped to requirements"
    )
    section_order: list[str] = Field(
        default_factory=list, description="Recommended section order for resume"
    )
    bullet_rewrites: list[BulletRewrite] = Field(
        default_factory=list, description="Suggested bullet rewrites"
    )
    unsupported_claims: list[UnsupportedClaim] = Field(
        default_factory=list, description="Requirements without supporting evidence"
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TailoringPlan:
        """Deserialize from dictionary."""
        return cls.model_validate(data)


class TailoredBullet(BaseModel):
    """A single tailored bullet point."""

    text: str = Field(..., description="Bullet point text")
    keywords_used: list[str] = Field(
        default_factory=list, description="Keywords integrated in this bullet"
    )


class TailoredSection(BaseModel):
    """A section of the tailored resume."""

    name: str = Field(..., description="Section identifier (e.g., 'experience')")
    title: str = Field(..., description="Display title for the section")
    content: str = Field(
        default="", description="Section content (if not bullet-based)"
    )
    bullets: list[TailoredBullet] = Field(
        default_factory=list, description="Bullet points in this section"
    )


class TailoredResume(BaseModel):
    """Complete tailored resume ready for rendering."""

    # Contact info
    name: str = Field(..., description="Candidate name")
    email: str = Field(..., description="Contact email")
    phone: str | None = Field(default=None, description="Contact phone")
    location: str = Field(..., description="Location")
    linkedin_url: str | None = Field(default=None, description="LinkedIn profile URL")
    github_url: str | None = Field(default=None, description="GitHub profile URL")

    # Content
    summary: str = Field(..., description="Professional summary tailored for this job")
    sections: list[TailoredSection] = Field(
        default_factory=list, description="Resume sections in order"
    )
    keywords_used: list[str] = Field(
        default_factory=list, description="All keywords integrated throughout resume"
    )

    # Target job info
    target_job_url: str = Field(..., description="URL of target job")
    target_company: str = Field(..., description="Target company name")
    target_role: str = Field(..., description="Target job title")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TailoredResume:
        """Deserialize from dictionary."""
        return cls.model_validate(data)


class CoverLetter(BaseModel):
    """Generated cover letter content."""

    opening: str = Field(..., description="Opening paragraph with hook")
    body: str = Field(..., description="Body with qualifications and evidence")
    closing: str = Field(..., description="Closing with call to action")
    full_text: str = Field(..., description="Complete cover letter text")
    word_count: int = Field(..., ge=0, description="Total word count")

    # Target job info
    target_job_url: str = Field(..., description="URL of target job")
    target_company: str = Field(..., description="Target company name")
    target_role: str = Field(..., description="Target job title")
    key_qualifications: list[str] = Field(
        default_factory=list, description="Key qualifications highlighted"
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CoverLetter:
        """Deserialize from dictionary."""
        return cls.model_validate(data)


class DocReviewPacket(BaseModel):
    """Summary packet for human-in-the-loop review before upload."""

    job_url: str = Field(..., description="Job posting URL")
    company: str = Field(..., description="Company name")
    role_title: str = Field(..., description="Job title")

    changes_summary: list[str] = Field(
        default_factory=list, description="Summary of key changes made"
    )
    keywords_highlighted: list[str] = Field(
        default_factory=list, description="Keywords emphasized in documents"
    )
    requirements_vs_evidence: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Mapping of requirements to user evidence (with matched status)",
    )

    resume_path: str = Field(..., description="Path to generated resume PDF")
    cover_letter_path: str | None = Field(
        default=None, description="Path to generated cover letter PDF"
    )
    generated_at: datetime = Field(
        default_factory=datetime.now, description="Generation timestamp"
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocReviewPacket:
        """Deserialize from dictionary."""
        return cls.model_validate(data)
