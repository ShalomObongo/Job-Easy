"""Business logic service for the Application Tracker.

This module provides the TrackerService class which handles:
- Duplicate detection using fingerprinting
- Record creation with automatic fingerprint computation
- Override recording for duplicate handling
"""

from datetime import datetime

from src.tracker.fingerprint import compute_fingerprint, extract_job_id, normalize_url
from src.tracker.models import ApplicationStatus, SourceMode, TrackerRecord
from src.tracker.repository import TrackerRepository


class TrackerService:
    """Business logic service for tracking job applications.

    This class coordinates between the fingerprint module and the
    repository to provide high-level operations for duplicate
    detection and record management.
    """

    def __init__(self, repository: TrackerRepository):
        """Initialize the service.

        Args:
            repository: The TrackerRepository instance for database access.
        """
        self.repository = repository

    async def check_duplicate(
        self,
        url: str | None,
        company: str,
        role: str,
        location: str | None,
    ) -> TrackerRecord | None:
        """Check if a job application already exists.

        Uses the cascading fingerprint strategy:
        1. If URL provided, extract job_id and compute fingerprint
        2. Look up by fingerprint in database
        3. Return existing record if found

        Args:
            url: The job posting URL (optional).
            company: The company name.
            role: The job role/title.
            location: The job location (optional).

        Returns:
            The existing TrackerRecord if duplicate found, None otherwise.
        """
        # Extract job ID if URL provided
        job_id = extract_job_id(url) if url else None

        # Compute fingerprint using cascading strategy
        fingerprint = compute_fingerprint(
            url=url,
            job_id=job_id,
            company=company,
            role=role,
            location=location,
        )

        # Look up existing record
        return await self.repository.get_by_fingerprint(fingerprint)

    async def create_record(
        self,
        url: str | None,
        company: str,
        role: str,
        location: str | None,
        source_mode: SourceMode,
    ) -> str:
        """Create a new tracker record.

        Computes the fingerprint and creates a new record in the database.

        Args:
            url: The job posting URL (optional).
            company: The company name.
            role: The job role/title.
            location: The job location (optional).
            source_mode: How the job was sourced (SINGLE or AUTONOMOUS).

        Returns:
            The fingerprint of the created record.
        """
        # Extract job ID if URL provided
        job_id = extract_job_id(url) if url else None

        # Compute fingerprint
        fingerprint = compute_fingerprint(
            url=url,
            job_id=job_id,
            company=company,
            role=role,
            location=location,
        )

        # Normalize URL if provided
        canonical_url = normalize_url(url) if url else ""

        # Create record
        record = TrackerRecord(
            fingerprint=fingerprint,
            canonical_url=canonical_url,
            source_mode=source_mode,
            company=company,
            role_title=role,
            status=ApplicationStatus.NEW,
            first_seen_at=datetime.now(),
            location=location,
        )

        await self.repository.insert_record(record)
        return fingerprint

    async def record_override(
        self,
        fingerprint: str,
        reason: str | None = None,
    ) -> None:
        """Record that a duplicate was overridden by the user.

        This marks a record as having been reviewed by the user who
        confirmed it should be processed despite being flagged as
        a potential duplicate.

        Args:
            fingerprint: The fingerprint of the record to update.
            reason: Optional reason for the override.
        """
        await self.repository.update_override(
            fingerprint=fingerprint,
            override=True,
            reason=reason,
        )

    async def update_status(
        self,
        fingerprint: str,
        status: ApplicationStatus,
    ) -> None:
        """Update the status of a job application.

        Args:
            fingerprint: The fingerprint of the record to update.
            status: The new status.
        """
        await self.repository.update_status(fingerprint, status)

    async def get_record(self, fingerprint: str) -> TrackerRecord | None:
        """Get a record by fingerprint.

        Args:
            fingerprint: The fingerprint to look up.

        Returns:
            The TrackerRecord if found, None otherwise.
        """
        return await self.repository.get_by_fingerprint(fingerprint)
