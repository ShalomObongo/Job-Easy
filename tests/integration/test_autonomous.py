from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.autonomous.service import AutonomousService
from src.extractor.models import JobDescription
from src.scoring.models import ConstraintResult, FitResult, FitScore
from src.tracker.models import ApplicationStatus, SourceMode
from src.tracker.repository import TrackerRepository
from src.tracker.service import TrackerService

pytestmark = [pytest.mark.integration]


def _fit_result(job: JobDescription, score: float = 0.9) -> FitResult:
    return FitResult(
        job_url=job.job_url,
        job_title=job.role_title,
        company=job.company,
        fit_score=FitScore(total_score=score, must_have_score=1.0),
        constraints=ConstraintResult(passed=True),
        recommendation="apply",
        reasoning="test",
        evaluated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_autonomous_dry_run_end_to_end_with_stubs(tmp_path: Path) -> None:
    db_path = tmp_path / "tracker.db"
    repo = TrackerRepository(db_path)
    await repo.initialize()
    tracker_service = TrackerService(repo)

    leads_file = tmp_path / "leads.txt"
    leads_file.write_text(
        "https://example.com/jobs/1\nhttps://example.com/jobs/2\n",
        encoding="utf-8",
    )

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
        evaluate=AsyncMock(side_effect=lambda job, _profile: _fit_result(job))
    )
    profile_service = SimpleNamespace(load_profile=lambda: object())

    single_job_service = SimpleNamespace(run=AsyncMock())
    tailoring_service = SimpleNamespace(
        tailor=AsyncMock(return_value=SimpleNamespace(success=True))
    )

    settings = SimpleNamespace(output_dir=tmp_path, max_applications_per_day=10)

    service = AutonomousService(
        settings=settings,
        tracker_service=tracker_service,
        extractor=extractor,
        scoring_service=scoring_service,
        profile_service=profile_service,
        single_job_service=single_job_service,
        tailoring_service=tailoring_service,
        confirm_callback=None,
    )

    result = await service.run(
        leads_file=leads_file,
        dry_run=True,
        min_score=None,
        include_skips=False,
        assume_yes=True,
    )

    assert result.processed == 2
    assert result.skipped == 0
    single_job_service.run.assert_not_awaited()
    assert tailoring_service.tailor.await_count == 2

    await repo.close()


@pytest.mark.asyncio
async def test_autonomous_skips_submitted_duplicates_via_tracker(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "tracker.db"
    repo = TrackerRepository(db_path)
    await repo.initialize()
    tracker_service = TrackerService(repo)

    dup_url = "https://example.com/jobs/dup"
    fingerprint = await tracker_service.create_record(
        url=dup_url,
        company="ACME",
        role="Engineer",
        location=None,
        source_mode=SourceMode.AUTONOMOUS,
    )
    await tracker_service.update_status(fingerprint, ApplicationStatus.SUBMITTED)

    leads_file = tmp_path / "leads.txt"
    leads_file.write_text(
        f"{dup_url}\nhttps://example.com/jobs/new\n",
        encoding="utf-8",
    )

    extractor = SimpleNamespace(
        extract=AsyncMock(
            side_effect=[
                JobDescription(
                    company="ACME",
                    role_title="New",
                    job_url="https://example.com/jobs/new",
                )
            ]
        )
    )
    scoring_service = SimpleNamespace(
        evaluate=AsyncMock(
            side_effect=lambda job, _profile: _fit_result(job, score=0.9)
        )
    )
    profile_service = SimpleNamespace(load_profile=lambda: object())

    single_job_service = SimpleNamespace(run=AsyncMock())
    tailoring_service = SimpleNamespace(
        tailor=AsyncMock(return_value=SimpleNamespace(success=True))
    )

    settings = SimpleNamespace(output_dir=tmp_path, max_applications_per_day=10)

    service = AutonomousService(
        settings=settings,
        tracker_service=tracker_service,
        extractor=extractor,
        scoring_service=scoring_service,
        profile_service=profile_service,
        single_job_service=single_job_service,
        tailoring_service=tailoring_service,
        confirm_callback=None,
    )

    result = await service.run(
        leads_file=leads_file,
        dry_run=True,
        min_score=None,
        include_skips=False,
        assume_yes=True,
    )

    assert result.processed == 1
    assert result.skipped == 0

    await repo.close()


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.skipif(
    not any(
        os.getenv(key)
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "BROWSER_USE_API_KEY"]
    ),
    reason="No LLM API key available for live extraction",
)
async def test_queue_building_with_real_extraction_smoke(tmp_path: Path) -> None:
    """Optional smoke test that exercises QueueManager with real extraction."""
    from src.autonomous.models import LeadItem
    from src.autonomous.queue import QueueManager
    from src.extractor.service import JobExtractor
    from src.scoring.profile import ProfileService
    from src.scoring.service import FitScoringService

    db_path = tmp_path / "tracker.db"
    repo = TrackerRepository(db_path)
    await repo.initialize()
    tracker_service = TrackerService(repo)

    extractor = JobExtractor()
    scoring = FitScoringService()
    profile = ProfileService().load_profile()

    url = "https://boards.greenhouse.io/anthropic/jobs/4020300007"
    leads = [LeadItem(url=url, line_number=1, valid=True)]

    queue = await QueueManager().build_queue(
        leads,
        tracker_service=tracker_service,
        extractor=extractor,
        scorer=scoring,
        profile=profile,
        min_score=None,
        include_skips=True,
    )

    assert isinstance(queue, list)

    await repo.close()
