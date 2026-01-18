"""Autonomous mode orchestration service."""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from src.autonomous.leads import LeadFileParser
from src.autonomous.models import BatchResult
from src.autonomous.queue import QueueManager
from src.autonomous.runner import BatchProgressEvent, BatchRunner
from src.hitl import tools as hitl

logger = logging.getLogger(__name__)

ConfirmCallback = Callable[[str], bool | Awaitable[bool]]
ProgressCallback = Callable[[BatchProgressEvent], None]


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class AutonomousService:
    """High-level service for autonomous batch processing."""

    def __init__(
        self,
        *,
        settings: Any,
        tracker_service: Any,
        extractor: Any,
        scoring_service: Any,
        profile_service: Any,
        single_job_service: Any,
        tailoring_service: Any | None = None,
        confirm_callback: ConfirmCallback | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.settings = settings
        self.tracker_service = tracker_service
        self.extractor = extractor
        self.scoring_service = scoring_service
        self.profile_service = profile_service
        self.single_job_service = single_job_service
        self.tailoring_service = tailoring_service
        self.confirm_callback = confirm_callback
        self.progress_callback = progress_callback

        self.lead_parser = LeadFileParser()
        self.queue_manager = QueueManager()

    async def run(
        self,
        *,
        leads_file: Path,
        dry_run: bool = False,
        min_score: float | None = None,
        include_skips: bool = False,
        assume_yes: bool = False,
    ) -> BatchResult:
        leads = self.lead_parser.parse(leads_file)
        profile = self.profile_service.load_profile()

        queue = await self.queue_manager.build_queue(
            leads,
            tracker_service=self.tracker_service,
            extractor=self.extractor,
            scorer=self.scoring_service,
            profile=profile,
            min_score=min_score,
            include_skips=include_skips,
        )

        limit = getattr(self.settings, "max_applications_per_day", None)
        if isinstance(limit, int) and limit > 0:
            queue = queue[:limit]

        if not queue:
            return BatchResult(
                processed=0,
                submitted=0,
                skipped=0,
                failed=0,
                duration_seconds=0.0,
                job_results=[],
            )

        if not assume_yes:
            summary = self._format_queue_summary(leads_file, queue)

            if self.confirm_callback is not None:
                confirmed = bool(await _maybe_await(self.confirm_callback(summary)))
            else:
                confirmed = bool(hitl.prompt_yes_no(summary))

            if not confirmed:
                return BatchResult(
                    processed=0,
                    submitted=0,
                    skipped=0,
                    failed=0,
                    duration_seconds=0.0,
                    job_results=[],
                )

        runner = BatchRunner(
            single_job_service=self.single_job_service,
            tailoring_service=self.tailoring_service,
            profile=profile,
            output_dir=getattr(self.settings, "output_dir", Path("./artifacts")),
            progress_callback=self.progress_callback,
        )
        return await runner.run(queue, dry_run=dry_run)

    def _format_queue_summary(self, leads_file: Path, queue: list[Any]) -> str:
        stats = None
        with_lead_counts = []
        try:
            stats = self.queue_manager.get_stats()
        except Exception:
            stats = None

        if stats is not None:
            with_lead_counts.append(
                f"Leads: total={stats.total} valid={stats.valid} "
                f"duplicates_skipped={stats.duplicates} below_threshold={stats.below_threshold}"
            )

        with_lead_counts.append(f"Queue size: {len(queue)}")
        with_lead_counts.append(f"Leads file: {leads_file}")
        with_lead_counts.append(
            "Proceed with batch processing? (This will still prompt before any submit)"
        )
        return "\n".join(with_lead_counts)


async def run_autonomous(
    leads_file: Path,
    *,
    settings: Any,
    dry_run: bool = False,
    min_score: float | None = None,
    include_skips: bool = False,
    assume_yes: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> BatchResult:
    """Convenience entry point for CLI usage."""
    from src.extractor.service import JobExtractor
    from src.runner.service import SingleJobApplicationService
    from src.scoring.profile import ProfileService
    from src.scoring.service import FitScoringService
    from src.tracker.models import SourceMode
    from src.tracker.repository import TrackerRepository
    from src.tracker.service import TrackerService

    repository = TrackerRepository(settings.tracker_db_path)
    await repository.initialize()

    try:
        tracker_service = TrackerService(repository)
        extractor = JobExtractor()
        scoring_service = FitScoringService()
        profile_service = ProfileService()

        single_job_service = SingleJobApplicationService(
            settings=settings,
            tracker_repository=repository,
            tracker_service=tracker_service,
            extractor=extractor,
            scoring_service=scoring_service,
            profile_service=profile_service,
            tailoring_service=None,
            source_mode=SourceMode.AUTONOMOUS,
        )

        service = AutonomousService(
            settings=settings,
            tracker_service=tracker_service,
            extractor=extractor,
            scoring_service=scoring_service,
            profile_service=profile_service,
            single_job_service=single_job_service,
            tailoring_service=None,
            confirm_callback=None,
            progress_callback=progress_callback,
        )
        return await service.run(
            leads_file=leads_file,
            dry_run=dry_run,
            min_score=min_score,
            include_skips=include_skips,
            assume_yes=assume_yes,
        )
    finally:
        await repository.close()
