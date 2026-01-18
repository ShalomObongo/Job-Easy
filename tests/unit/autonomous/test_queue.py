from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

from src.autonomous.models import LeadItem
from src.autonomous.queue import QueueManager
from src.extractor.models import JobDescription
from src.scoring.models import ConstraintResult, FitResult, FitScore
from src.tracker.models import ApplicationStatus, SourceMode, TrackerRecord


def _fit_result(
    *,
    url: str,
    company: str,
    title: str,
    score: float,
    recommendation: str = "apply",
) -> FitResult:
    return FitResult(
        job_url=url,
        job_title=title,
        company=company,
        fit_score=FitScore(total_score=score, must_have_score=1.0),
        constraints=ConstraintResult(passed=True),
        recommendation=recommendation,  # type: ignore[arg-type]
        reasoning="test",
        evaluated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _tracker_record(url: str, status: ApplicationStatus) -> TrackerRecord:
    return TrackerRecord(
        fingerprint=f"fp:{url}",
        canonical_url=url,
        source_mode=SourceMode.SINGLE,
        company="ACME",
        role_title="Engineer",
        status=status,
        first_seen_at=datetime(2026, 1, 1, tzinfo=UTC),
        location=None,
    )


async def test_queue_manager_new_urls_are_added_to_queue() -> None:
    leads = [
        LeadItem(url="https://example.com/jobs/1", line_number=1, valid=True),
        LeadItem(url="https://example.com/jobs/2", line_number=2, valid=True),
    ]

    tracker = AsyncMock()
    tracker.check_duplicate = AsyncMock(return_value=None)

    extractor = AsyncMock()
    extractor.extract = AsyncMock(
        side_effect=[
            JobDescription(company="ACME", role_title="A", job_url=leads[0].url),
            JobDescription(company="ACME", role_title="B", job_url=leads[1].url),
        ]
    )

    scorer = AsyncMock()
    scorer.evaluate = AsyncMock(
        side_effect=[
            _fit_result(url=leads[0].url, company="ACME", title="A", score=0.1),
            _fit_result(url=leads[1].url, company="ACME", title="B", score=0.9),
        ]
    )

    queue = await QueueManager().build_queue(
        leads,
        tracker_service=tracker,
        extractor=extractor,
        scorer=scorer,
        profile=object(),
        min_score=None,
        include_skips=False,
    )

    assert [item.url for item in queue] == [leads[1].url, leads[0].url]
    assert len(queue) == 2


async def test_queue_manager_submitted_duplicates_are_filtered_out() -> None:
    leads = [
        LeadItem(url="https://example.com/jobs/1", line_number=1, valid=True),
        LeadItem(url="https://example.com/jobs/2", line_number=2, valid=True),
    ]

    tracker = AsyncMock()
    tracker.check_duplicate = AsyncMock(
        side_effect=[
            _tracker_record(leads[0].url, ApplicationStatus.SUBMITTED),
            None,
        ]
    )

    extractor = AsyncMock()
    extractor.extract = AsyncMock(
        return_value=JobDescription(
            company="ACME", role_title="B", job_url=leads[1].url
        )
    )

    scorer = AsyncMock()
    scorer.evaluate = AsyncMock(
        return_value=_fit_result(url=leads[1].url, company="ACME", title="B", score=0.9)
    )

    queue = await QueueManager().build_queue(
        leads,
        tracker_service=tracker,
        extractor=extractor,
        scorer=scorer,
        profile=object(),
        min_score=None,
        include_skips=False,
    )

    assert [item.url for item in queue] == [leads[1].url]
    extractor.extract.assert_awaited_once()


async def test_queue_manager_failed_or_skipped_duplicates_are_included() -> None:
    leads = [
        LeadItem(url="https://example.com/jobs/1", line_number=1, valid=True),
        LeadItem(url="https://example.com/jobs/2", line_number=2, valid=True),
    ]

    tracker = AsyncMock()
    tracker.check_duplicate = AsyncMock(
        side_effect=[
            _tracker_record(leads[0].url, ApplicationStatus.FAILED),
            _tracker_record(leads[1].url, ApplicationStatus.SKIPPED),
        ]
    )

    extractor = AsyncMock()
    extractor.extract = AsyncMock(
        side_effect=[
            JobDescription(company="ACME", role_title="A", job_url=leads[0].url),
            JobDescription(company="ACME", role_title="B", job_url=leads[1].url),
        ]
    )

    scorer = AsyncMock()
    scorer.evaluate = AsyncMock(
        side_effect=[
            _fit_result(url=leads[0].url, company="ACME", title="A", score=0.2),
            _fit_result(url=leads[1].url, company="ACME", title="B", score=0.3),
        ]
    )

    queue = await QueueManager().build_queue(
        leads,
        tracker_service=tracker,
        extractor=extractor,
        scorer=scorer,
        profile=object(),
        min_score=None,
        include_skips=False,
    )

    assert len(queue) == 2


async def test_queue_manager_min_score_filter_excludes_low_scoring_jobs() -> None:
    leads = [
        LeadItem(url="https://example.com/jobs/1", line_number=1, valid=True),
        LeadItem(url="https://example.com/jobs/2", line_number=2, valid=True),
    ]

    tracker = AsyncMock()
    tracker.check_duplicate = AsyncMock(return_value=None)

    extractor = AsyncMock()
    extractor.extract = AsyncMock(
        side_effect=[
            JobDescription(company="ACME", role_title="A", job_url=leads[0].url),
            JobDescription(company="ACME", role_title="B", job_url=leads[1].url),
        ]
    )

    scorer = AsyncMock()
    scorer.evaluate = AsyncMock(
        side_effect=[
            _fit_result(url=leads[0].url, company="ACME", title="A", score=0.59),
            _fit_result(url=leads[1].url, company="ACME", title="B", score=0.60),
        ]
    )

    queue = await QueueManager().build_queue(
        leads,
        tracker_service=tracker,
        extractor=extractor,
        scorer=scorer,
        profile=object(),
        min_score=0.6,
        include_skips=False,
    )

    assert [item.url for item in queue] == [leads[1].url]


async def test_queue_manager_include_skips_flag_controls_recommendation_filtering() -> (
    None
):
    leads = [
        LeadItem(url="https://example.com/jobs/1", line_number=1, valid=True),
        LeadItem(url="https://example.com/jobs/2", line_number=2, valid=True),
    ]

    async def run(include_skips: bool) -> list[str]:
        tracker = AsyncMock()
        tracker.check_duplicate = AsyncMock(return_value=None)

        jobs_by_url = {
            leads[0].url: JobDescription(
                company="ACME", role_title="A", job_url=leads[0].url
            ),
            leads[1].url: JobDescription(
                company="ACME", role_title="B", job_url=leads[1].url
            ),
        }

        extractor = AsyncMock()
        extractor.extract = AsyncMock(side_effect=lambda url: jobs_by_url.get(url))

        fits_by_url = {
            leads[0].url: _fit_result(
                url=leads[0].url,
                company="ACME",
                title="A",
                score=0.9,
                recommendation="skip",
            ),
            leads[1].url: _fit_result(
                url=leads[1].url,
                company="ACME",
                title="B",
                score=0.8,
            ),
        }

        scorer = AsyncMock()
        scorer.evaluate = AsyncMock(
            side_effect=lambda job, _profile: fits_by_url[job.job_url]
        )

        queue = await QueueManager().build_queue(
            leads,
            tracker_service=tracker,
            extractor=extractor,
            scorer=scorer,
            profile=object(),
            min_score=None,
            include_skips=include_skips,
        )
        return [item.url for item in queue]

    without_skips = await run(False)
    assert without_skips == [leads[1].url]

    with_skips = await run(True)
    assert with_skips == [leads[0].url, leads[1].url]


def test_queue_manager_get_stats_before_build_raises() -> None:
    manager = QueueManager()
    try:
        manager.get_stats()
    except RuntimeError as exc:
        assert "Queue has not been built" in str(exc)
    else:
        raise AssertionError("Expected QueueManager.get_stats() to raise RuntimeError")


async def test_queue_manager_stats_counts_total_valid_duplicates_below_threshold_queued() -> (
    None
):
    leads = [
        LeadItem(url="https://example.com/jobs/1", line_number=1, valid=True),
        LeadItem(url="https://example.com/jobs/2", line_number=2, valid=True),
        LeadItem(url="notaurl", line_number=3, valid=False, error="Invalid URL"),
    ]

    tracker = AsyncMock()
    tracker.check_duplicate = AsyncMock(
        side_effect=[
            _tracker_record(leads[0].url, ApplicationStatus.SUBMITTED),
            None,
        ]
    )

    extractor = AsyncMock()
    extractor.extract = AsyncMock(
        return_value=JobDescription(
            company="ACME", role_title="B", job_url=leads[1].url
        )
    )

    scorer = AsyncMock()
    scorer.evaluate = AsyncMock(
        return_value=_fit_result(url=leads[1].url, company="ACME", title="B", score=0.4)
    )

    manager = QueueManager()
    queue = await manager.build_queue(
        leads,
        tracker_service=tracker,
        extractor=extractor,
        scorer=scorer,
        profile=object(),
        min_score=0.5,
        include_skips=True,
    )

    stats = manager.get_stats()

    assert queue == []
    assert stats.total == 3
    assert stats.valid == 2
    assert stats.duplicates == 1
    assert stats.below_threshold == 1
    assert stats.queued == 0
