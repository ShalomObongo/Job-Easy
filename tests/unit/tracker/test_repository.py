"""Tests for the TrackerRepository database layer."""

import sqlite3
from datetime import datetime

import pytest

from src.tracker.models import ApplicationStatus, SourceMode, TrackerRecord


class TestDatabaseInitialization:
    """Test database initialization."""

    @pytest.mark.asyncio
    async def test_creates_database_file_if_not_exists(self, tmp_path):
        """Should create database file if it doesn't exist."""
        from src.tracker.repository import TrackerRepository

        db_path = tmp_path / "test_tracker.db"
        assert not db_path.exists()

        repo = TrackerRepository(db_path)
        await repo.initialize()

        assert db_path.exists()
        await repo.close()

    @pytest.mark.asyncio
    async def test_creates_tracker_table_with_correct_schema(self, tmp_path):
        """Should create tracker table with all required columns."""
        from src.tracker.repository import TrackerRepository

        db_path = tmp_path / "test_tracker.db"
        repo = TrackerRepository(db_path)
        await repo.initialize()

        # Query table info
        async with repo._get_connection() as conn:
            cursor = await conn.execute("PRAGMA table_info(tracker)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

        expected_columns = [
            "fingerprint",
            "canonical_url",
            "source_mode",
            "company",
            "role_title",
            "status",
            "first_seen_at",
            "location",
            "last_attempt_at",
            "submitted_at",
            "resume_artifact_path",
            "cover_letter_artifact_path",
            "proof_text",
            "proof_screenshot_path",
            "override_duplicate",
            "override_reason",
        ]
        for col in expected_columns:
            assert col in column_names

        await repo.close()

    @pytest.mark.asyncio
    async def test_handles_existing_database_gracefully(self, tmp_path):
        """Should not error when database already exists."""
        from src.tracker.repository import TrackerRepository

        db_path = tmp_path / "test_tracker.db"

        # Create and initialize first time
        repo1 = TrackerRepository(db_path)
        await repo1.initialize()
        await repo1.close()

        # Initialize again
        repo2 = TrackerRepository(db_path)
        await repo2.initialize()  # Should not raise
        await repo2.close()


class TestCRUDOperations:
    """Test CRUD operations."""

    @pytest.fixture
    async def repo(self, tmp_path):
        """Create a test repository."""
        from src.tracker.repository import TrackerRepository

        db_path = tmp_path / "test_tracker.db"
        repo = TrackerRepository(db_path)
        await repo.initialize()
        yield repo
        await repo.close()

    @pytest.fixture
    def sample_record(self):
        """Create a sample tracker record."""
        return TrackerRecord(
            fingerprint="abc123",
            canonical_url="https://example.com/jobs/123",
            source_mode=SourceMode.SINGLE,
            company="ExampleCo",
            role_title="Software Engineer",
            status=ApplicationStatus.NEW,
            first_seen_at=datetime.now(),
            location="Remote",
        )

    @pytest.mark.asyncio
    async def test_insert_record_creates_new_record(self, repo, sample_record):
        """insert_record should create a new record."""
        await repo.insert_record(sample_record)

        result = await repo.get_by_fingerprint("abc123")
        assert result is not None
        assert result.company == "ExampleCo"

    @pytest.mark.asyncio
    async def test_insert_record_fails_on_duplicate_fingerprint(
        self, repo, sample_record
    ):
        """insert_record should fail on duplicate fingerprint."""
        await repo.insert_record(sample_record)

        with pytest.raises(sqlite3.IntegrityError):
            await repo.insert_record(sample_record)

    @pytest.mark.asyncio
    async def test_get_by_fingerprint_returns_correct_record(self, repo, sample_record):
        """get_by_fingerprint should return the correct record."""
        await repo.insert_record(sample_record)

        result = await repo.get_by_fingerprint("abc123")
        assert result is not None
        assert result.fingerprint == "abc123"
        assert result.company == "ExampleCo"
        assert result.status == ApplicationStatus.NEW

    @pytest.mark.asyncio
    async def test_get_by_fingerprint_returns_none_if_not_found(self, repo):
        """get_by_fingerprint should return None if record not found."""
        result = await repo.get_by_fingerprint("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_status_changes_status_and_timestamp(
        self, repo, sample_record
    ):
        """update_status should change status and update last_attempt_at."""
        await repo.insert_record(sample_record)

        await repo.update_status("abc123", ApplicationStatus.SUBMITTED)

        result = await repo.get_by_fingerprint("abc123")
        assert result.status == ApplicationStatus.SUBMITTED
        assert result.last_attempt_at is not None

    @pytest.mark.asyncio
    async def test_update_proof_sets_proof_fields(self, repo, sample_record):
        """update_proof should set proof_text and proof_screenshot_path."""
        await repo.insert_record(sample_record)

        await repo.update_proof(
            "abc123",
            proof_text="Application received. Confirmation #ABC123",
            screenshot_path="/path/to/proof.png",
        )

        result = await repo.get_by_fingerprint("abc123")
        assert result.proof_text == "Application received. Confirmation #ABC123"
        assert result.proof_screenshot_path == "/path/to/proof.png"

    @pytest.mark.asyncio
    async def test_update_artifacts_sets_artifact_paths(self, repo, sample_record):
        """update_artifacts should set resume and cover letter artifact paths."""
        await repo.insert_record(sample_record)

        await repo.update_artifacts(
            "abc123",
            resume_artifact_path="/path/to/resume.pdf",
            cover_letter_artifact_path="/path/to/cover.pdf",
        )

        result = await repo.get_by_fingerprint("abc123")
        assert result.resume_artifact_path == "/path/to/resume.pdf"
        assert result.cover_letter_artifact_path == "/path/to/cover.pdf"

    @pytest.mark.asyncio
    async def test_list_recent_returns_records(self, repo, sample_record):
        """list_recent should return recent records."""
        await repo.insert_record(sample_record)

        result = await repo.list_recent(limit=10)
        assert len(result) == 1
        assert result[0].fingerprint == "abc123"

    @pytest.mark.asyncio
    async def test_list_recent_filters_by_status(self, repo, sample_record):
        """list_recent should filter by status when provided."""
        await repo.insert_record(sample_record)

        # Should find with matching status
        result = await repo.list_recent(limit=10, status_filter=ApplicationStatus.NEW)
        assert len(result) == 1

        # Should not find with different status
        result = await repo.list_recent(
            limit=10, status_filter=ApplicationStatus.SUBMITTED
        )
        assert len(result) == 0
