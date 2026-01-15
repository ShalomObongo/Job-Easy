"""Tests for the TrackerService business logic."""

import pytest

from src.tracker.models import ApplicationStatus, SourceMode


class TestDuplicateDetection:
    """Test duplicate detection functionality."""

    @pytest.fixture
    async def service(self, tmp_path):
        """Create a test service with an initialized repository."""
        from src.tracker.repository import TrackerRepository
        from src.tracker.service import TrackerService

        db_path = tmp_path / "test_tracker.db"
        repo = TrackerRepository(db_path)
        await repo.initialize()
        svc = TrackerService(repo)
        yield svc
        await repo.close()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_duplicate_exists(self, service):
        """check_duplicate should return None when no duplicate exists."""
        result = await service.check_duplicate(
            url="https://example.com/jobs/new",
            company="NewCo",
            role="Engineer",
            location="Remote",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_record_when_duplicate_found_by_fingerprint(self, service):
        """check_duplicate should return TrackerRecord when duplicate found."""
        # Create a record using create_record (computes proper fingerprint)
        fingerprint = await service.create_record(
            url="https://example.com/jobs/123",
            company="ExampleCo",
            role="Software Engineer",
            location="Remote",
            source_mode=SourceMode.SINGLE,
        )

        # Check for duplicate with same URL (will generate same fingerprint)
        result = await service.check_duplicate(
            url="https://example.com/jobs/123",
            company="ExampleCo",
            role="Software Engineer",
            location="Remote",
        )
        assert result is not None
        assert result.fingerprint == fingerprint

    @pytest.mark.asyncio
    async def test_detects_duplicates_by_url(self, service):
        """check_duplicate should detect duplicates by URL."""
        # Create a record
        await service.create_record(
            url="https://example.com/jobs/123",
            company="ExampleCo",
            role="Software Engineer",
            location="Remote",
            source_mode=SourceMode.SINGLE,
        )

        # Same URL, different company/role should still match (URL takes precedence)
        result = await service.check_duplicate(
            url="https://example.com/jobs/123",
            company="DifferentCo",
            role="Different Role",
            location="Different Location",
        )
        assert result is not None
        assert result.company == "ExampleCo"  # Original company

    @pytest.mark.asyncio
    async def test_detects_duplicates_by_company_role_location(self, service):
        """check_duplicate should detect duplicates by company+role+location."""
        # Create a record without a URL (uses company|role|location fingerprint)
        await service.create_record(
            url=None,
            company="ManualCo",
            role="Manual Role",
            location="NYC",
            source_mode=SourceMode.SINGLE,
        )

        # Check with same company+role+location but no URL
        result = await service.check_duplicate(
            url=None,
            company="ManualCo",
            role="Manual Role",
            location="NYC",
        )
        # This should find the duplicate by fingerprint match
        assert result is not None
        assert result.company == "ManualCo"


class TestRecordCreation:
    """Test record creation functionality."""

    @pytest.fixture
    async def service(self, tmp_path):
        """Create a test service with an initialized repository."""
        from src.tracker.repository import TrackerRepository
        from src.tracker.service import TrackerService

        db_path = tmp_path / "test_tracker.db"
        repo = TrackerRepository(db_path)
        await repo.initialize()
        svc = TrackerService(repo)
        yield svc
        await repo.close()

    @pytest.mark.asyncio
    async def test_create_record_stores_in_database(self, service):
        """create_record should store a new record in the database."""
        fingerprint = await service.create_record(
            url="https://example.com/jobs/456",
            company="TestCo",
            role="Test Engineer",
            location="Remote",
            source_mode=SourceMode.SINGLE,
        )

        # Verify it's stored
        record = await service.repository.get_by_fingerprint(fingerprint)
        assert record is not None
        assert record.company == "TestCo"
        assert record.status == ApplicationStatus.NEW


class TestOverrideRecording:
    """Test override recording functionality."""

    @pytest.fixture
    async def service(self, tmp_path):
        """Create a test service with an initialized repository."""
        from src.tracker.repository import TrackerRepository
        from src.tracker.service import TrackerService

        db_path = tmp_path / "test_tracker.db"
        repo = TrackerRepository(db_path)
        await repo.initialize()
        svc = TrackerService(repo)
        yield svc
        await repo.close()

    @pytest.mark.asyncio
    async def test_records_override_decision_correctly(self, service):
        """record_override should record override decision correctly."""
        # Create a record and get its fingerprint
        fingerprint = await service.create_record(
            url="https://example.com/jobs/override",
            company="OverrideCo",
            role="Test Role",
            location="Remote",
            source_mode=SourceMode.SINGLE,
        )

        await service.record_override(
            fingerprint=fingerprint,
            reason="User confirmed this is a different position",
        )

        record = await service.repository.get_by_fingerprint(fingerprint)
        assert record.override_duplicate is True

    @pytest.mark.asyncio
    async def test_stores_override_reason(self, service):
        """record_override should store the override reason."""
        # Create a record and get its fingerprint
        fingerprint = await service.create_record(
            url="https://example.com/jobs/override2",
            company="OverrideCo2",
            role="Test Role 2",
            location="Remote",
            source_mode=SourceMode.SINGLE,
        )

        reason = "Different team, same company"
        await service.record_override(
            fingerprint=fingerprint,
            reason=reason,
        )

        record = await service.repository.get_by_fingerprint(fingerprint)
        assert record.override_reason == reason
