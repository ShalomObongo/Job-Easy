from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.autonomous.service import AutonomousService
from src.extractor.models import JobDescription
from src.runner.models import ApplicationRunResult, RunStatus
from src.scoring.models import ConstraintResult, FitResult, FitScore
from src.tracker.models import ApplicationStatus, SourceMode, TrackerRecord


def _fit_result(
    job: JobDescription, score: float, recommendation: str = "apply"
) -> FitResult:
    return FitResult(
        job_url=job.job_url,
        job_title=job.role_title,
        company=job.company,
        fit_score=FitScore(total_score=score, must_have_score=1.0),
        constraints=ConstraintResult(passed=True),
        recommendation=recommendation,  # type: ignore[arg-type]
        reasoning="test",
        evaluated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _submitted_record(url: str) -> TrackerRecord:
    return TrackerRecord(
        fingerprint="fp",
        canonical_url=url,
        source_mode=SourceMode.SINGLE,
        company="ACME",
        role_title="Engineer",
        status=ApplicationStatus.SUBMITTED,
        first_seen_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_autonomous_service_full_pipeline_from_file_to_batch_result(
    tmp_path: Path,
) -> None:
    leads_file = tmp_path / "leads.txt"
    leads_file.write_text(
        "https://example.com/jobs/1\nhttps://example.com/jobs/2\n",
        encoding="utf-8",
    )

    settings = SimpleNamespace(output_dir=tmp_path, max_applications_per_day=10)

    tracker_service = SimpleNamespace(check_duplicate=AsyncMock(return_value=None))

    extractor = SimpleNamespace(
        extract=AsyncMock(
            side_effect=[
                JobDescription(
                    company="ACME", role_title="A", job_url="https://example.com/jobs/1"
                ),
                JobDescription(
                    company="ACME", role_title="B", job_url="https://example.com/jobs/2"
                ),
            ]
        )
    )

    scoring_service = SimpleNamespace(
        evaluate=AsyncMock(
            side_effect=[
                _fit_result(
                    JobDescription(
                        company="ACME",
                        role_title="A",
                        job_url="https://example.com/jobs/1",
                    ),
                    0.2,
                ),
                _fit_result(
                    JobDescription(
                        company="ACME",
                        role_title="B",
                        job_url="https://example.com/jobs/2",
                    ),
                    0.8,
                ),
            ]
        )
    )

    profile_service = SimpleNamespace(load_profile=lambda: object())

    single_job_service = SimpleNamespace(
        run=AsyncMock(
            return_value=ApplicationRunResult(success=True, status=RunStatus.SUBMITTED)
        )
    )

    confirm = AsyncMock(return_value=True)

    service = AutonomousService(
        settings=settings,
        tracker_service=tracker_service,
        extractor=extractor,
        scoring_service=scoring_service,
        profile_service=profile_service,
        single_job_service=single_job_service,
        tailoring_service=None,
        confirm_callback=confirm,
    )

    result = await service.run(
        leads_file=leads_file,
        dry_run=False,
        min_score=None,
        include_skips=False,
        assume_yes=False,
    )

    assert result.processed == 2
    assert result.submitted == 2
    confirm.assert_awaited_once()


@pytest.mark.asyncio
async def test_autonomous_service_respects_dry_run_flag(tmp_path: Path) -> None:
    leads_file = tmp_path / "leads.txt"
    leads_file.write_text("https://example.com/jobs/1\n", encoding="utf-8")

    settings = SimpleNamespace(output_dir=tmp_path, max_applications_per_day=10)

    tracker_service = SimpleNamespace(check_duplicate=AsyncMock(return_value=None))
    extractor = SimpleNamespace(
        extract=AsyncMock(
            return_value=JobDescription(
                company="ACME", role_title="A", job_url="https://example.com/jobs/1"
            )
        )
    )
    scoring_service = SimpleNamespace(
        evaluate=AsyncMock(
            return_value=_fit_result(
                JobDescription(
                    company="ACME", role_title="A", job_url="https://example.com/jobs/1"
                ),
                0.8,
            )
        )
    )
    profile_service = SimpleNamespace(load_profile=lambda: object())

    single_job_service = SimpleNamespace(run=AsyncMock())
    tailoring_service = SimpleNamespace(
        tailor=AsyncMock(return_value=SimpleNamespace(success=True))
    )

    service = AutonomousService(
        settings=settings,
        tracker_service=tracker_service,
        extractor=extractor,
        scoring_service=scoring_service,
        profile_service=profile_service,
        single_job_service=single_job_service,
        tailoring_service=tailoring_service,
        confirm_callback=AsyncMock(return_value=True),
    )

    result = await service.run(
        leads_file=leads_file,
        dry_run=True,
        min_score=None,
        include_skips=False,
        assume_yes=True,
    )

    assert result.processed == 1
    assert result.submitted == 0
    assert result.skipped == 0
    single_job_service.run.assert_not_awaited()
    tailoring_service.tailor.assert_awaited()


@pytest.mark.asyncio
async def test_autonomous_service_respects_min_score_filter(tmp_path: Path) -> None:
    leads_file = tmp_path / "leads.txt"
    leads_file.write_text(
        "https://example.com/jobs/1\nhttps://example.com/jobs/2\n", encoding="utf-8"
    )

    settings = SimpleNamespace(output_dir=tmp_path, max_applications_per_day=10)
    tracker_service = SimpleNamespace(check_duplicate=AsyncMock(return_value=None))
    extractor = SimpleNamespace(
        extract=AsyncMock(
            side_effect=[
                JobDescription(
                    company="ACME", role_title="A", job_url="https://example.com/jobs/1"
                ),
                JobDescription(
                    company="ACME", role_title="B", job_url="https://example.com/jobs/2"
                ),
            ]
        )
    )
    scoring_service = SimpleNamespace(
        evaluate=AsyncMock(
            side_effect=[
                _fit_result(
                    JobDescription(
                        company="ACME",
                        role_title="A",
                        job_url="https://example.com/jobs/1",
                    ),
                    0.4,
                ),
                _fit_result(
                    JobDescription(
                        company="ACME",
                        role_title="B",
                        job_url="https://example.com/jobs/2",
                    ),
                    0.9,
                ),
            ]
        )
    )
    profile_service = SimpleNamespace(load_profile=lambda: object())
    single_job_service = SimpleNamespace(
        run=AsyncMock(
            return_value=ApplicationRunResult(success=True, status=RunStatus.SUBMITTED)
        )
    )

    service = AutonomousService(
        settings=settings,
        tracker_service=tracker_service,
        extractor=extractor,
        scoring_service=scoring_service,
        profile_service=profile_service,
        single_job_service=single_job_service,
        tailoring_service=None,
        confirm_callback=AsyncMock(return_value=True),
    )

    result = await service.run(
        leads_file=leads_file,
        dry_run=False,
        min_score=0.5,
        include_skips=False,
        assume_yes=True,
    )

    assert result.processed == 1
    assert result.submitted == 1


@pytest.mark.asyncio
async def test_autonomous_service_handles_empty_queue_gracefully(
    tmp_path: Path,
) -> None:
    leads_file = tmp_path / "leads.txt"
    leads_file.write_text("", encoding="utf-8")

    settings = SimpleNamespace(output_dir=tmp_path, max_applications_per_day=10)
    tracker_service = SimpleNamespace(check_duplicate=AsyncMock())
    extractor = SimpleNamespace(extract=AsyncMock())
    scoring_service = SimpleNamespace(evaluate=AsyncMock())
    profile_service = SimpleNamespace(load_profile=lambda: object())
    single_job_service = SimpleNamespace(run=AsyncMock())
    confirm = AsyncMock()

    service = AutonomousService(
        settings=settings,
        tracker_service=tracker_service,
        extractor=extractor,
        scoring_service=scoring_service,
        profile_service=profile_service,
        single_job_service=single_job_service,
        tailoring_service=None,
        confirm_callback=confirm,
    )

    result = await service.run(
        leads_file=leads_file,
        dry_run=False,
        min_score=None,
        include_skips=False,
        assume_yes=False,
    )

    assert result.processed == 0
    assert result.job_results == []
    confirm.assert_not_awaited()


@pytest.mark.asyncio
async def test_autonomous_service_handles_all_duplicate_queue(tmp_path: Path) -> None:
    leads_file = tmp_path / "leads.txt"
    leads_file.write_text("https://example.com/jobs/1\n", encoding="utf-8")

    settings = SimpleNamespace(output_dir=tmp_path, max_applications_per_day=10)
    tracker_service = SimpleNamespace(
        check_duplicate=AsyncMock(
            return_value=_submitted_record("https://example.com/jobs/1")
        )
    )
    extractor = SimpleNamespace(extract=AsyncMock())
    scoring_service = SimpleNamespace(evaluate=AsyncMock())
    profile_service = SimpleNamespace(load_profile=lambda: object())
    single_job_service = SimpleNamespace(run=AsyncMock())
    confirm = AsyncMock()

    service = AutonomousService(
        settings=settings,
        tracker_service=tracker_service,
        extractor=extractor,
        scoring_service=scoring_service,
        profile_service=profile_service,
        single_job_service=single_job_service,
        tailoring_service=None,
        confirm_callback=confirm,
    )

    result = await service.run(
        leads_file=leads_file,
        dry_run=False,
        min_score=None,
        include_skips=False,
        assume_yes=False,
    )

    assert result.processed == 0
    confirm.assert_not_awaited()
