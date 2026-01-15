"""Tests for tracker data models."""

from datetime import datetime


class TestApplicationStatus:
    """Test ApplicationStatus enum."""

    def test_application_status_has_all_values(self):
        """ApplicationStatus should have all required status values."""
        from src.tracker.models import ApplicationStatus

        assert hasattr(ApplicationStatus, "NEW")
        assert hasattr(ApplicationStatus, "IN_PROGRESS")
        assert hasattr(ApplicationStatus, "SKIPPED")
        assert hasattr(ApplicationStatus, "DUPLICATE_SKIPPED")
        assert hasattr(ApplicationStatus, "SUBMITTED")
        assert hasattr(ApplicationStatus, "FAILED")

    def test_application_status_values_are_strings(self):
        """ApplicationStatus values should be lowercase strings."""
        from src.tracker.models import ApplicationStatus

        assert ApplicationStatus.NEW.value == "new"
        assert ApplicationStatus.IN_PROGRESS.value == "in_progress"
        assert ApplicationStatus.SUBMITTED.value == "submitted"


class TestSourceMode:
    """Test SourceMode enum."""

    def test_source_mode_has_all_values(self):
        """SourceMode should have single and autonomous modes."""
        from src.tracker.models import SourceMode

        assert hasattr(SourceMode, "SINGLE")
        assert hasattr(SourceMode, "AUTONOMOUS")

    def test_source_mode_values_are_strings(self):
        """SourceMode values should be lowercase strings."""
        from src.tracker.models import SourceMode

        assert SourceMode.SINGLE.value == "single"
        assert SourceMode.AUTONOMOUS.value == "autonomous"


class TestTrackerRecord:
    """Test TrackerRecord dataclass."""

    def test_tracker_record_has_required_fields(self):
        """TrackerRecord should have all required fields."""
        from src.tracker.models import ApplicationStatus, SourceMode, TrackerRecord

        now = datetime.now()
        record = TrackerRecord(
            fingerprint="abc123",
            canonical_url="https://example.com/jobs/123",
            source_mode=SourceMode.SINGLE,
            company="ExampleCo",
            role_title="Software Engineer",
            status=ApplicationStatus.NEW,
            first_seen_at=now,
        )

        assert record.fingerprint == "abc123"
        assert record.canonical_url == "https://example.com/jobs/123"
        assert record.source_mode == SourceMode.SINGLE
        assert record.company == "ExampleCo"
        assert record.role_title == "Software Engineer"
        assert record.status == ApplicationStatus.NEW
        assert record.first_seen_at == now

    def test_tracker_record_optional_fields_default_to_none(self):
        """Optional fields should default to None."""
        from src.tracker.models import ApplicationStatus, SourceMode, TrackerRecord

        record = TrackerRecord(
            fingerprint="abc123",
            canonical_url="https://example.com/jobs/123",
            source_mode=SourceMode.SINGLE,
            company="ExampleCo",
            role_title="Software Engineer",
            status=ApplicationStatus.NEW,
            first_seen_at=datetime.now(),
        )

        assert record.location is None
        assert record.last_attempt_at is None
        assert record.submitted_at is None
        assert record.resume_artifact_path is None
        assert record.cover_letter_artifact_path is None
        assert record.proof_text is None
        assert record.proof_screenshot_path is None
        assert record.override_duplicate is False
        assert record.override_reason is None

    def test_tracker_record_serializes_to_dict(self):
        """TrackerRecord should serialize to dict correctly."""
        from src.tracker.models import ApplicationStatus, SourceMode, TrackerRecord

        now = datetime.now()
        record = TrackerRecord(
            fingerprint="abc123",
            canonical_url="https://example.com/jobs/123",
            source_mode=SourceMode.SINGLE,
            company="ExampleCo",
            role_title="Software Engineer",
            status=ApplicationStatus.NEW,
            first_seen_at=now,
            location="Remote",
        )

        result = record.to_dict()

        assert isinstance(result, dict)
        assert result["fingerprint"] == "abc123"
        assert result["canonical_url"] == "https://example.com/jobs/123"
        assert result["source_mode"] == "single"
        assert result["company"] == "ExampleCo"
        assert result["role_title"] == "Software Engineer"
        assert result["status"] == "new"
        assert result["location"] == "Remote"

    def test_tracker_record_deserializes_from_dict(self):
        """TrackerRecord should deserialize from dict correctly."""
        from src.tracker.models import ApplicationStatus, SourceMode, TrackerRecord

        data = {
            "fingerprint": "abc123",
            "canonical_url": "https://example.com/jobs/123",
            "source_mode": "single",
            "company": "ExampleCo",
            "role_title": "Software Engineer",
            "status": "new",
            "first_seen_at": "2026-01-15T12:00:00",
            "location": "Remote",
        }

        record = TrackerRecord.from_dict(data)

        assert record.fingerprint == "abc123"
        assert record.source_mode == SourceMode.SINGLE
        assert record.status == ApplicationStatus.NEW
        assert record.location == "Remote"
