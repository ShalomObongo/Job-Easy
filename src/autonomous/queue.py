"""Queue builder for autonomous mode."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any

from src.autonomous.models import LeadItem, QueuedJob
from src.tracker.fingerprint import compute_fingerprint, extract_job_id
from src.tracker.models import ApplicationStatus


@dataclass(frozen=True)
class QueueStats:
    total: int
    valid: int
    duplicates: int
    below_threshold: int
    queued: int


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _fingerprint_for_url(url: str) -> str:
    job_id = extract_job_id(url)
    return compute_fingerprint(
        url=url,
        job_id=job_id,
        company="",
        role="",
        location=None,
    )


class QueueManager:
    """Build and rank an autonomous mode queue."""

    def __init__(self) -> None:
        self._stats: QueueStats | None = None

    async def build_queue(
        self,
        leads: list[LeadItem],
        *,
        tracker_service: Any,
        extractor: Any,
        scorer: Any,
        profile: Any,
        min_score: float | None,
        include_skips: bool,
    ) -> list[QueuedJob]:
        queued: list[QueuedJob] = []
        duplicates = 0
        below_threshold = 0

        valid_leads = [lead for lead in leads if lead.valid]

        cache: dict[str, tuple[Any, Any]] = {}

        for lead in valid_leads:
            duplicate = await tracker_service.check_duplicate(
                url=lead.url,
                company="",
                role="",
                location=None,
            )

            if (
                duplicate is not None
                and duplicate.status == ApplicationStatus.SUBMITTED
            ):
                duplicates += 1
                continue

            if lead.url in cache:
                job, fit = cache[lead.url]
            else:
                job = await extractor.extract(lead.url)
                if job is None:
                    continue

                fit = await _maybe_await(scorer.evaluate(job, profile))
                cache[lead.url] = (job, fit)

            if not include_skips and getattr(fit, "recommendation", None) == "skip":
                continue

            score_value = getattr(getattr(fit, "fit_score", None), "total_score", None)
            if score_value is None:
                score_value = getattr(fit, "total_score", None)
            if (
                isinstance(score_value, (int, float))
                and min_score is not None
                and score_value < min_score
            ):
                below_threshold += 1
                continue

            fingerprint = (
                duplicate.fingerprint
                if duplicate is not None
                else _fingerprint_for_url(lead.url)
            )
            queued.append(
                QueuedJob(
                    url=getattr(job, "apply_url", None)
                    or getattr(job, "job_url", None)
                    or lead.url,
                    fingerprint=fingerprint,
                    job_description=job,
                    fit_result=fit,
                )
            )

        queued.sort(
            key=lambda item: item.fit_result.fit_score.total_score, reverse=True
        )

        self._stats = QueueStats(
            total=len(leads),
            valid=len(valid_leads),
            duplicates=duplicates,
            below_threshold=below_threshold,
            queued=len(queued),
        )
        return queued

    def get_stats(self) -> QueueStats:
        if self._stats is None:
            raise RuntimeError("Queue has not been built yet")
        return self._stats
