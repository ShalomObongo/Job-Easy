"""Database repository for the Application Tracker.

This module provides async SQLite database operations for storing
and retrieving job application records.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import aiosqlite

from src.tracker.models import ApplicationStatus, SourceMode, TrackerRecord

# SQL schema for the tracker table
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tracker (
    fingerprint TEXT PRIMARY KEY,
    canonical_url TEXT NOT NULL,
    source_mode TEXT NOT NULL,
    company TEXT NOT NULL,
    role_title TEXT NOT NULL,
    status TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    location TEXT,
    last_attempt_at TEXT,
    submitted_at TEXT,
    resume_artifact_path TEXT,
    cover_letter_artifact_path TEXT,
    proof_text TEXT,
    proof_screenshot_path TEXT,
    override_duplicate INTEGER DEFAULT 0,
    override_reason TEXT
)
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_tracker_status ON tracker(status);
CREATE INDEX IF NOT EXISTS idx_tracker_first_seen ON tracker(first_seen_at);
"""


class TrackerRepository:
    """Async SQLite repository for tracker records.

    This class provides CRUD operations for job application records
    using aiosqlite for async database access.
    """

    def __init__(self, db_path: Path | str):
        """Initialize the repository.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self._connection: aiosqlite.Connection | None = None

    @asynccontextmanager
    async def _get_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Get a database connection.

        Yields:
            An aiosqlite connection.
        """
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
        yield self._connection

    async def initialize(self) -> None:
        """Initialize the database, creating tables if needed."""
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        async with self._get_connection() as conn:
            await conn.execute(CREATE_TABLE_SQL)
            await conn.executescript(CREATE_INDEX_SQL)
            await conn.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def insert_record(self, record: TrackerRecord) -> None:
        """Insert a new tracker record.

        Args:
            record: The tracker record to insert.

        Raises:
            sqlite3.IntegrityError: If a record with the same fingerprint exists.
        """
        async with self._get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO tracker (
                    fingerprint, canonical_url, source_mode, company, role_title,
                    status, first_seen_at, location, last_attempt_at, submitted_at,
                    resume_artifact_path, cover_letter_artifact_path, proof_text,
                    proof_screenshot_path, override_duplicate, override_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.fingerprint,
                    record.canonical_url,
                    record.source_mode.value,
                    record.company,
                    record.role_title,
                    record.status.value,
                    record.first_seen_at.isoformat() if record.first_seen_at else None,
                    record.location,
                    record.last_attempt_at.isoformat()
                    if record.last_attempt_at
                    else None,
                    record.submitted_at.isoformat() if record.submitted_at else None,
                    record.resume_artifact_path,
                    record.cover_letter_artifact_path,
                    record.proof_text,
                    record.proof_screenshot_path,
                    1 if record.override_duplicate else 0,
                    record.override_reason,
                ),
            )
            await conn.commit()

    async def get_by_fingerprint(self, fingerprint: str) -> TrackerRecord | None:
        """Get a record by its fingerprint.

        Args:
            fingerprint: The fingerprint to look up.

        Returns:
            The tracker record if found, None otherwise.
        """
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM tracker WHERE fingerprint = ?",
                (fingerprint,),
            )
            row = await cursor.fetchone()

        if row is None:
            return None

        return self._row_to_record(row)

    async def get_by_url(self, url: str) -> TrackerRecord | None:
        """Get a record by its canonical URL.

        Args:
            url: The canonical URL to look up.

        Returns:
            The tracker record if found, None otherwise.
        """
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM tracker WHERE canonical_url = ?",
                (url,),
            )
            row = await cursor.fetchone()

        if row is None:
            return None

        return self._row_to_record(row)

    async def update_status(self, fingerprint: str, status: ApplicationStatus) -> None:
        """Update the status of a record.

        Also updates the last_attempt_at timestamp.

        Args:
            fingerprint: The fingerprint of the record to update.
            status: The new status.
        """
        now = datetime.now().isoformat()

        async with self._get_connection() as conn:
            # Also update submitted_at if status is SUBMITTED
            if status == ApplicationStatus.SUBMITTED:
                await conn.execute(
                    """
                    UPDATE tracker
                    SET status = ?, last_attempt_at = ?, submitted_at = ?
                    WHERE fingerprint = ?
                    """,
                    (status.value, now, now, fingerprint),
                )
            else:
                await conn.execute(
                    """
                    UPDATE tracker
                    SET status = ?, last_attempt_at = ?
                    WHERE fingerprint = ?
                    """,
                    (status.value, now, fingerprint),
                )
            await conn.commit()

    async def update_proof(
        self,
        fingerprint: str,
        proof_text: str | None = None,
        screenshot_path: str | None = None,
    ) -> None:
        """Update the proof fields for a record.

        Args:
            fingerprint: The fingerprint of the record to update.
            proof_text: The proof text to set.
            screenshot_path: The screenshot path to set.
        """
        async with self._get_connection() as conn:
            await conn.execute(
                """
                UPDATE tracker
                SET proof_text = ?, proof_screenshot_path = ?
                WHERE fingerprint = ?
                """,
                (proof_text, screenshot_path, fingerprint),
            )
            await conn.commit()

    async def update_artifacts(
        self,
        fingerprint: str,
        resume_artifact_path: str | None = None,
        cover_letter_artifact_path: str | None = None,
    ) -> None:
        """Update resume/cover letter artifact paths for a record."""
        async with self._get_connection() as conn:
            await conn.execute(
                """
                UPDATE tracker
                SET resume_artifact_path = ?, cover_letter_artifact_path = ?
                WHERE fingerprint = ?
                """,
                (resume_artifact_path, cover_letter_artifact_path, fingerprint),
            )
            await conn.commit()

    async def get_status_counts(self) -> dict[ApplicationStatus, int]:
        """Return record counts grouped by status."""
        async with self._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT status, COUNT(*) AS count FROM tracker GROUP BY status"
            )
            rows = await cursor.fetchall()

        counts: dict[ApplicationStatus, int] = {}
        for row in rows:
            try:
                status = ApplicationStatus(row["status"])
            except Exception:
                continue
            counts[status] = int(row["count"]) if row["count"] is not None else 0
        return counts

    async def list_recent(
        self,
        limit: int = 10,
        status_filter: ApplicationStatus | None = None,
    ) -> list[TrackerRecord]:
        """List recent tracker records.

        Args:
            limit: Maximum number of records to return.
            status_filter: Optional status to filter by.

        Returns:
            List of tracker records, ordered by first_seen_at descending.
        """
        async with self._get_connection() as conn:
            if status_filter is not None:
                cursor = await conn.execute(
                    """
                    SELECT * FROM tracker
                    WHERE status = ?
                    ORDER BY first_seen_at DESC
                    LIMIT ?
                    """,
                    (status_filter.value, limit),
                )
            else:
                cursor = await conn.execute(
                    """
                    SELECT * FROM tracker
                    ORDER BY first_seen_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            rows = await cursor.fetchall()

        return [self._row_to_record(row) for row in rows]

    async def update_override(
        self, fingerprint: str, override: bool, reason: str | None = None
    ) -> None:
        """Update the override fields for a record.

        Args:
            fingerprint: The fingerprint of the record to update.
            override: Whether the duplicate was overridden.
            reason: The reason for overriding (optional).
        """
        async with self._get_connection() as conn:
            await conn.execute(
                """
                UPDATE tracker
                SET override_duplicate = ?, override_reason = ?
                WHERE fingerprint = ?
                """,
                (1 if override else 0, reason, fingerprint),
            )
            await conn.commit()

    def _row_to_record(self, row: aiosqlite.Row) -> TrackerRecord:
        """Convert a database row to a TrackerRecord.

        Args:
            row: The database row.

        Returns:
            A TrackerRecord instance.
        """

        def parse_datetime(value: str | None) -> datetime | None:
            if value is None:
                return None
            return datetime.fromisoformat(value)

        return TrackerRecord(
            fingerprint=row["fingerprint"],
            canonical_url=row["canonical_url"],
            source_mode=SourceMode(row["source_mode"]),
            company=row["company"],
            role_title=row["role_title"],
            status=ApplicationStatus(row["status"]),
            first_seen_at=parse_datetime(row["first_seen_at"]) or datetime.now(),
            location=row["location"],
            last_attempt_at=parse_datetime(row["last_attempt_at"]),
            submitted_at=parse_datetime(row["submitted_at"]),
            resume_artifact_path=row["resume_artifact_path"],
            cover_letter_artifact_path=row["cover_letter_artifact_path"],
            proof_text=row["proof_text"],
            proof_screenshot_path=row["proof_screenshot_path"],
            override_duplicate=bool(row["override_duplicate"]),
            override_reason=row["override_reason"],
        )
