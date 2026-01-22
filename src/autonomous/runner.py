"""Batch runner for autonomous mode."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.autonomous.models import BatchResult, JobResult, QueuedJob, QueueStatus
from src.runner.models import RunStatus
from src.tailoring.config import TailoringConfig
from src.tailoring.service import TailoringService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchProgressEvent:
    index: int
    total: int
    url: str
    status: QueueStatus
    processed: int
    submitted: int
    skipped: int
    failed: int


class BatchRunner:
    """Process queued jobs sequentially."""

    def __init__(
        self,
        *,
        single_job_service: Any,
        tailoring_service: Any | None,
        profile: Any,
        output_dir: Path,
        progress_callback: Callable[[BatchProgressEvent], None] | None = None,
    ) -> None:
        self.single_job_service = single_job_service
        self.tailoring_service = tailoring_service
        self.profile = profile
        self.output_dir = output_dir
        self.progress_callback = progress_callback

    async def run(self, queue: list[QueuedJob], *, dry_run: bool) -> BatchResult:
        processed = 0
        submitted = 0
        skipped = 0
        failed = 0
        job_results: list[JobResult] = []

        start_time = time.monotonic()

        stop_event = asyncio.Event()
        current_task: asyncio.Task | None = None

        def _request_stop() -> None:
            stop_event.set()
            if current_task is not None:
                current_task.cancel()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(Exception):
                loop.add_signal_handler(sig, _request_stop)

        try:
            for index, item in enumerate(queue, start=1):
                if stop_event.is_set():
                    break

                item.status = QueueStatus.PROCESSING
                self._emit_progress(
                    index=index,
                    total=len(queue),
                    url=item.url,
                    status=item.status,
                    processed=processed,
                    submitted=submitted,
                    skipped=skipped,
                    failed=failed,
                )

                job_start = time.monotonic()
                error: str | None = None

                try:
                    if dry_run:
                        await self._run_dry_run(item)
                        item.status = QueueStatus.COMPLETED
                        processed += 1
                    else:
                        run_kwargs: dict[str, Any] = {
                            "job": item.job_description,
                        }
                        if self.profile is not None:
                            run_kwargs["profile"] = self.profile

                        current_task = asyncio.create_task(
                            self.single_job_service.run(item.url, **run_kwargs)
                        )
                        run_result = await current_task

                        status = getattr(run_result, "status", None)
                        if status == RunStatus.SUBMITTED:
                            item.status = QueueStatus.COMPLETED
                            submitted += 1
                        elif status in {
                            RunStatus.SKIPPED,
                            RunStatus.DUPLICATE_SKIPPED,
                            RunStatus.STOPPED_BEFORE_SUBMIT,
                        }:
                            item.status = QueueStatus.SKIPPED
                            skipped += 1
                        else:
                            item.status = QueueStatus.FAILED
                            failed += 1
                            errors = getattr(run_result, "errors", None) or []
                            if errors:
                                error = str(errors[0])
                        processed += 1

                except asyncio.CancelledError:
                    item.status = QueueStatus.FAILED
                    failed += 1
                    processed += 1
                    error = "interrupted"
                    job_results.append(
                        JobResult(
                            url=item.url,
                            fingerprint=item.fingerprint,
                            status=item.status,
                            error=error,
                            duration_seconds=time.monotonic() - job_start,
                        )
                    )
                    break
                except Exception as exc:
                    logger.exception("Job failed: %s", exc)
                    item.status = QueueStatus.FAILED
                    failed += 1
                    processed += 1
                    error = str(exc)
                finally:
                    current_task = None

                duration = time.monotonic() - job_start
                job_results.append(
                    JobResult(
                        url=item.url,
                        fingerprint=item.fingerprint,
                        status=item.status,
                        error=error,
                        duration_seconds=duration,
                    )
                )

                self._emit_progress(
                    index=index,
                    total=len(queue),
                    url=item.url,
                    status=item.status,
                    processed=processed,
                    submitted=submitted,
                    skipped=skipped,
                    failed=failed,
                )

        finally:
            for sig in (signal.SIGINT, signal.SIGTERM):
                with contextlib.suppress(Exception):
                    loop.remove_signal_handler(sig)

        return BatchResult(
            processed=processed,
            submitted=submitted,
            skipped=skipped,
            failed=failed,
            duration_seconds=time.monotonic() - start_time,
            job_results=job_results,
        )

    async def _run_dry_run(self, item: QueuedJob) -> None:
        """Generate tailored documents without running browser automation."""
        if self.profile is None:
            raise RuntimeError("profile is required for dry-run mode")

        run_dir = self.output_dir / "runs" / item.fingerprint
        run_dir.mkdir(parents=True, exist_ok=True)

        tailoring_service = self.tailoring_service
        if tailoring_service is None:
            tailoring_service = TailoringService(
                config=TailoringConfig(output_dir=run_dir)
            )

        result = await tailoring_service.tailor(self.profile, item.job_description)
        if not getattr(result, "success", False):
            raise RuntimeError(getattr(result, "error", None) or "Tailoring failed")

    def _emit_progress(
        self,
        *,
        index: int,
        total: int,
        url: str,
        status: QueueStatus,
        processed: int,
        submitted: int,
        skipped: int,
        failed: int,
    ) -> None:
        if self.progress_callback is None:
            return
        event = BatchProgressEvent(
            index=index,
            total=total,
            url=url,
            status=status,
            processed=processed,
            submitted=submitted,
            skipped=skipped,
            failed=failed,
        )
        with contextlib.suppress(Exception):
            self.progress_callback(event)
