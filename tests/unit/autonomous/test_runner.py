from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

from src.autonomous.models import QueuedJob, QueueStatus
from src.autonomous.runner import BatchRunner
from src.extractor.models import JobDescription
from src.runner.models import ApplicationRunResult, RunStatus
from src.scoring.models import ConstraintResult, FitResult, FitScore


def _queued_job(url: str, score: float = 0.5) -> QueuedJob:
    job = JobDescription(company="ACME", role_title="Engineer", job_url=url)
    fit = FitResult(
        job_url=url,
        job_title=job.role_title,
        company=job.company,
        fit_score=FitScore(total_score=score, must_have_score=1.0),
        constraints=ConstraintResult(passed=True),
        recommendation="apply",
        reasoning="test",
        evaluated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return QueuedJob(
        url=url, fingerprint=f"fp:{url}", job_description=job, fit_result=fit
    )


async def test_batch_runner_processes_jobs_sequentially(tmp_path: Path) -> None:
    queue = [
        _queued_job("https://example.com/jobs/1"),
        _queued_job("https://example.com/jobs/2"),
    ]

    called: list[str] = []

    async def _run(url: str):
        called.append(url)
        return ApplicationRunResult(success=True, status=RunStatus.SUBMITTED)

    single_job_service = AsyncMock()
    single_job_service.run = AsyncMock(side_effect=_run)

    runner = BatchRunner(
        single_job_service=single_job_service,
        tailoring_service=None,
        profile=None,
        output_dir=tmp_path,
    )
    result = await runner.run(queue, dry_run=False)

    assert called == [job.url for job in queue]
    assert result.processed == 2
    assert result.submitted == 2
    assert all(job.status == QueueStatus.COMPLETED for job in queue)


async def test_batch_runner_continues_after_individual_job_failure(
    tmp_path: Path,
) -> None:
    queue = [
        _queued_job("https://example.com/jobs/1"),
        _queued_job("https://example.com/jobs/2"),
        _queued_job("https://example.com/jobs/3"),
    ]

    called: list[str] = []

    async def _run(url: str):
        called.append(url)
        if url.endswith("/2"):
            raise RuntimeError("boom")
        return ApplicationRunResult(success=True, status=RunStatus.SUBMITTED)

    single_job_service = AsyncMock()
    single_job_service.run = AsyncMock(side_effect=_run)

    runner = BatchRunner(
        single_job_service=single_job_service,
        tailoring_service=None,
        profile=None,
        output_dir=tmp_path,
    )
    result = await runner.run(queue, dry_run=False)

    assert called == [job.url for job in queue]
    assert result.processed == 3
    assert result.submitted == 2
    assert result.failed == 1
    assert queue[1].status == QueueStatus.FAILED
    assert queue[0].status == QueueStatus.COMPLETED
    assert queue[2].status == QueueStatus.COMPLETED


async def test_batch_runner_dry_run_skips_browser_automation(tmp_path: Path) -> None:
    queue = [
        _queued_job("https://example.com/jobs/1"),
        _queued_job("https://example.com/jobs/2"),
    ]

    single_job_service = AsyncMock()
    single_job_service.run = AsyncMock()

    tailoring_service = AsyncMock()
    tailoring_service.tailor = AsyncMock(return_value=AsyncMock(success=True))

    runner = BatchRunner(
        single_job_service=single_job_service,
        tailoring_service=tailoring_service,
        profile=object(),
        output_dir=tmp_path,
    )
    result = await runner.run(queue, dry_run=True)

    assert result.processed == 2
    assert result.submitted == 0
    assert result.skipped == 0
    single_job_service.run.assert_not_awaited()
    assert tailoring_service.tailor.await_count == 2
    assert all(job.status == QueueStatus.COMPLETED for job in queue)
    assert (tmp_path / "runs").exists()


async def test_batch_runner_tracks_progress_counts_correctly(tmp_path: Path) -> None:
    queue = [
        _queued_job("https://example.com/jobs/1"),
        _queued_job("https://example.com/jobs/2"),
        _queued_job("https://example.com/jobs/3"),
    ]

    async def _run(url: str):
        if url.endswith("/1"):
            return ApplicationRunResult(success=True, status=RunStatus.SUBMITTED)
        if url.endswith("/2"):
            return ApplicationRunResult(success=True, status=RunStatus.SKIPPED)
        return ApplicationRunResult(
            success=False, status=RunStatus.FAILED, errors=["x"]
        )

    single_job_service = AsyncMock()
    single_job_service.run = AsyncMock(side_effect=_run)

    runner = BatchRunner(
        single_job_service=single_job_service,
        tailoring_service=None,
        profile=None,
        output_dir=tmp_path,
    )
    result = await runner.run(queue, dry_run=False)

    assert result.processed == 3
    assert result.submitted == 1
    assert result.skipped == 1
    assert result.failed == 1


async def test_batch_runner_handles_graceful_shutdown_on_cancelled_job(
    tmp_path: Path,
) -> None:
    queue = [
        _queued_job("https://example.com/jobs/1"),
        _queued_job("https://example.com/jobs/2"),
    ]

    async def _run(_url: str):
        raise asyncio.CancelledError()

    single_job_service = AsyncMock()
    single_job_service.run = AsyncMock(side_effect=_run)

    runner = BatchRunner(
        single_job_service=single_job_service,
        tailoring_service=None,
        profile=None,
        output_dir=tmp_path,
    )
    result = await runner.run(queue, dry_run=False)

    assert result.processed == 1
    assert result.failed == 1
    assert queue[0].status == QueueStatus.FAILED
    assert queue[1].status == QueueStatus.PENDING
