"""Data models for the Application Tracker."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ApplicationStatus(str, Enum):
    """Status of a job application."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    SKIPPED = "skipped"
    DUPLICATE_SKIPPED = "duplicate_skipped"
    SUBMITTED = "submitted"
    FAILED = "failed"


class SourceMode(str, Enum):
    """Mode in which the application was initiated."""

    SINGLE = "single"
    AUTONOMOUS = "autonomous"


@dataclass
class TrackerRecord:
    """A record of a job application attempt.

    Attributes:
        fingerprint: Unique identifier for the job (hash-based).
        canonical_url: Normalized URL of the job posting.
        source_mode: How the application was initiated (single/autonomous).
        company: Name of the company.
        role_title: Title of the job role.
        status: Current status of the application.
        first_seen_at: When the job was first encountered.
        location: Job location (optional).
        last_attempt_at: When the last application attempt was made.
        submitted_at: When the application was successfully submitted.
        resume_artifact_path: Path to the tailored resume file.
        cover_letter_artifact_path: Path to the tailored cover letter file.
        proof_text: Text confirmation of submission.
        proof_screenshot_path: Path to screenshot proof.
        override_duplicate: Whether user chose to proceed despite duplicate.
        override_reason: User's reason for overriding duplicate detection.
    """

    fingerprint: str
    canonical_url: str
    source_mode: SourceMode
    company: str
    role_title: str
    status: ApplicationStatus
    first_seen_at: datetime
    location: str | None = None
    last_attempt_at: datetime | None = None
    submitted_at: datetime | None = None
    resume_artifact_path: str | None = None
    cover_letter_artifact_path: str | None = None
    proof_text: str | None = None
    proof_screenshot_path: str | None = None
    override_duplicate: bool = field(default=False)
    override_reason: str | None = None

    def to_dict(self) -> dict:
        """Serialize the record to a dictionary.

        Returns:
            Dictionary representation of the record.
        """
        return {
            "fingerprint": self.fingerprint,
            "canonical_url": self.canonical_url,
            "source_mode": self.source_mode.value,
            "company": self.company,
            "role_title": self.role_title,
            "status": self.status.value,
            "first_seen_at": self.first_seen_at.isoformat()
            if self.first_seen_at
            else None,
            "location": self.location,
            "last_attempt_at": self.last_attempt_at.isoformat()
            if self.last_attempt_at
            else None,
            "submitted_at": self.submitted_at.isoformat()
            if self.submitted_at
            else None,
            "resume_artifact_path": self.resume_artifact_path,
            "cover_letter_artifact_path": self.cover_letter_artifact_path,
            "proof_text": self.proof_text,
            "proof_screenshot_path": self.proof_screenshot_path,
            "override_duplicate": self.override_duplicate,
            "override_reason": self.override_reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TrackerRecord":
        """Deserialize a record from a dictionary.

        Args:
            data: Dictionary containing record data.

        Returns:
            TrackerRecord instance.
        """

        def parse_datetime(value: str | datetime | None) -> datetime | None:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            return datetime.fromisoformat(value)

        return cls(
            fingerprint=data["fingerprint"],
            canonical_url=data["canonical_url"],
            source_mode=SourceMode(data["source_mode"]),
            company=data["company"],
            role_title=data["role_title"],
            status=ApplicationStatus(data["status"]),
            first_seen_at=parse_datetime(data["first_seen_at"]),
            location=data.get("location"),
            last_attempt_at=parse_datetime(data.get("last_attempt_at")),
            submitted_at=parse_datetime(data.get("submitted_at")),
            resume_artifact_path=data.get("resume_artifact_path"),
            cover_letter_artifact_path=data.get("cover_letter_artifact_path"),
            proof_text=data.get("proof_text"),
            proof_screenshot_path=data.get("proof_screenshot_path"),
            override_duplicate=data.get("override_duplicate", False),
            override_reason=data.get("override_reason"),
        )
