"""Integration tests for the Application Tracker system."""

import asyncio

import pytest

from src.tracker.models import ApplicationStatus, SourceMode
from src.tracker.repository import TrackerRepository
from src.tracker.service import TrackerService


class TestFullWorkflow:
    """Test the full tracker workflow end-to-end."""

    @pytest.fixture
    async def service(self, tmp_path):
        """Create a test service with an initialized repository."""
        db_path = tmp_path / "test_tracker.db"
        repo = TrackerRepository(db_path)
        await repo.initialize()
        svc = TrackerService(repo)
        yield svc
        await repo.close()

    @pytest.mark.asyncio
    async def test_full_workflow_create_check_update(self, service):
        """Test full workflow: create record, check duplicate, update status."""
        # Step 1: Create a new application record
        fingerprint = await service.create_record(
            url="https://boards.greenhouse.io/company/jobs/12345",
            company="TechCorp",
            role="Senior Developer",
            location="NYC",
            source_mode=SourceMode.SINGLE,
        )
        assert fingerprint is not None

        # Step 2: Verify record exists
        record = await service.get_record(fingerprint)
        assert record is not None
        assert record.company == "TechCorp"
        assert record.status == ApplicationStatus.NEW

        # Step 3: Check for duplicate with same URL
        duplicate = await service.check_duplicate(
            url="https://boards.greenhouse.io/company/jobs/12345",
            company="TechCorp",
            role="Senior Developer",
            location="NYC",
        )
        assert duplicate is not None
        assert duplicate.fingerprint == fingerprint

        # Step 4: Update status to in_progress
        await service.update_status(fingerprint, ApplicationStatus.IN_PROGRESS)
        record = await service.get_record(fingerprint)
        assert record.status == ApplicationStatus.IN_PROGRESS

        # Step 5: Update status to submitted
        await service.update_status(fingerprint, ApplicationStatus.SUBMITTED)
        record = await service.get_record(fingerprint)
        assert record.status == ApplicationStatus.SUBMITTED
        assert record.submitted_at is not None


class TestDatabasePersistence:
    """Test that database persists between sessions."""

    @pytest.mark.asyncio
    async def test_database_persists_between_sessions(self, tmp_path):
        """Test that records persist when reopening the database."""
        db_path = tmp_path / "persistent_tracker.db"

        # Session 1: Create a record
        repo1 = TrackerRepository(db_path)
        await repo1.initialize()
        service1 = TrackerService(repo1)

        fingerprint = await service1.create_record(
            url="https://example.com/job/999",
            company="PersistCo",
            role="Test Role",
            location="Remote",
            source_mode=SourceMode.AUTONOMOUS,
        )
        await repo1.close()

        # Session 2: Verify record still exists
        repo2 = TrackerRepository(db_path)
        await repo2.initialize()
        service2 = TrackerService(repo2)

        record = await service2.get_record(fingerprint)
        assert record is not None
        assert record.company == "PersistCo"
        assert record.source_mode == SourceMode.AUTONOMOUS

        await repo2.close()


class TestConcurrentAccess:
    """Test concurrent access handling."""

    @pytest.mark.asyncio
    async def test_concurrent_reads_succeed(self, tmp_path):
        """Test that concurrent reads work correctly."""
        db_path = tmp_path / "concurrent_tracker.db"

        repo = TrackerRepository(db_path)
        await repo.initialize()
        service = TrackerService(repo)

        # Create a record
        fingerprint = await service.create_record(
            url="https://example.com/job/concurrent",
            company="ConcurrentCo",
            role="Test Role",
            location="Remote",
            source_mode=SourceMode.SINGLE,
        )

        # Perform multiple concurrent reads
        async def read_record():
            return await service.get_record(fingerprint)

        results = await asyncio.gather(
            read_record(),
            read_record(),
            read_record(),
            read_record(),
            read_record(),
        )

        # All reads should succeed
        assert all(r is not None for r in results)
        assert all(r.company == "ConcurrentCo" for r in results)

        await repo.close()

    @pytest.mark.asyncio
    async def test_concurrent_duplicate_checks_succeed(self, tmp_path):
        """Test that concurrent duplicate checks work correctly."""
        db_path = tmp_path / "concurrent_dup_tracker.db"

        repo = TrackerRepository(db_path)
        await repo.initialize()
        service = TrackerService(repo)

        # Create a record
        await service.create_record(
            url="https://example.com/job/dup-check",
            company="DupCheckCo",
            role="Engineer",
            location="NYC",
            source_mode=SourceMode.SINGLE,
        )

        # Perform multiple concurrent duplicate checks
        async def check_dup():
            return await service.check_duplicate(
                url="https://example.com/job/dup-check",
                company="DupCheckCo",
                role="Engineer",
                location="NYC",
            )

        results = await asyncio.gather(
            check_dup(),
            check_dup(),
            check_dup(),
        )

        # All checks should find the duplicate
        assert all(r is not None for r in results)
        assert all(r.company == "DupCheckCo" for r in results)

        await repo.close()
