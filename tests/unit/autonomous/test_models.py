from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from src.autonomous.models import (
    BatchResult,
    JobResult,
    LeadItem,
    QueuedJob,
    QueueStatus,
)
from src.extractor.models import JobDescription
from src.scoring.models import ConstraintResult, FitResult, FitScore


def test_lead_item_valid_requires_no_error() -> None:
    with pytest.raises(ValueError, match="error must be None when valid=True"):
        LeadItem(
            url="https://example.com",
            line_number=1,
            valid=True,
            error="unexpected",
        )


def test_lead_item_invalid_requires_error() -> None:
    with pytest.raises(ValueError, match="error is required when valid=False"):
        LeadItem(
            url="https://example.com",
            line_number=1,
            valid=False,
            error=None,
        )


def test_queue_status_values() -> None:
    assert {status.value for status in QueueStatus} == {
        "pending",
        "processing",
        "completed",
        "failed",
        "skipped",
    }


def test_queued_job_to_dict_is_json_serializable() -> None:
    job = JobDescription(
        company="ACME",
        role_title="Software Engineer",
        job_url="https://example.com/jobs/123",
    )
    fit = FitResult(
        job_url=job.job_url,
        job_title=job.role_title,
        company=job.company,
        fit_score=FitScore(total_score=0.9, must_have_score=1.0),
        constraints=ConstraintResult(passed=True),
        recommendation="apply",
        reasoning="Looks good",
        evaluated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    queued = QueuedJob(
        url=job.job_url,
        fingerprint="abc123",
        job_description=job,
        fit_result=fit,
        status=QueueStatus.PENDING,
    )

    payload = queued.to_dict()
    json.dumps(payload)  # must not raise

    assert payload["status"] == "pending"
    assert payload["job_description"]["company"] == "ACME"
    assert payload["fit_result"]["recommendation"] == "apply"
    assert payload["fit_result"]["evaluated_at"] == "2026-01-01T00:00:00+00:00"


def test_batch_result_to_dict_is_json_serializable() -> None:
    results = [
        JobResult(
            url="https://example.com/jobs/123",
            fingerprint="abc123",
            status=QueueStatus.COMPLETED,
            error=None,
            duration_seconds=1.25,
        )
    ]
    batch = BatchResult(
        processed=1,
        submitted=1,
        skipped=0,
        failed=0,
        duration_seconds=1.25,
        job_results=results,
    )

    payload = batch.to_dict()
    json.dumps(payload)  # must not raise

    assert payload["processed"] == 1
    assert payload["job_results"][0]["status"] == "completed"
