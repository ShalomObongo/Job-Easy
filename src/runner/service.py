"""Single-job orchestration service.

Wires tracker → extractor → scoring → tailoring → application runner.
"""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import Any

from src.hitl import tools as hitl
from src.runner.agent import create_application_agent, create_browser, get_runner_llm
from src.runner.domains import is_prohibited, record_allowed_domain
from src.runner.models import ApplicationRunResult, RunStatus
from src.tailoring.config import TailoringConfig
from src.tailoring.service import TailoringService
from src.tracker.models import ApplicationStatus, SourceMode
from src.tracker.repository import TrackerRepository
from src.tracker.service import TrackerService

logger = logging.getLogger(__name__)


class SingleJobApplicationService:
    """End-to-end service for running a single application attempt."""

    def __init__(
        self,
        *,
        settings: Any,
        tracker_repository: Any,
        tracker_service: Any,
        extractor: Any,
        scoring_service: Any,
        profile_service: Any,
        tailoring_service: Any | None = None,
    ) -> None:
        self.settings = settings
        self.tracker_repository = tracker_repository
        self.tracker_service = tracker_service
        self.extractor = extractor
        self.scoring_service = scoring_service
        self.profile_service = profile_service
        self.tailoring_service = tailoring_service

    async def run(self, url: str) -> ApplicationRunResult:
        """Run a single job application flow from URL."""
        run_notes: list[str] = []
        prohibited_domains = list(getattr(self.settings, "prohibited_domains", []))
        if prohibited_domains and is_prohibited(url, prohibited_domains):
            return ApplicationRunResult(
                success=False,
                status=RunStatus.BLOCKED,
                errors=["Domain is prohibited by configuration"],
            )

        duplicate = await self.tracker_service.check_duplicate(
            url=url,
            company="",
            role="",
            location=None,
        )

        fingerprint: str | None = getattr(duplicate, "fingerprint", None)
        if duplicate is not None and duplicate.status == ApplicationStatus.SUBMITTED:
            proceed = hitl.prompt_yes_no(
                f"Tracker indicates this job was already submitted. Proceed anyway?\n{url}"
            )
            if not proceed:
                return ApplicationRunResult(
                    success=True,
                    status=RunStatus.DUPLICATE_SKIPPED,
                    notes=["duplicate_detected"],
                )

            reason = hitl.prompt_free_text(
                "Optional override reason (press Enter to skip)"
            )
            await self.tracker_service.record_override(
                fingerprint=duplicate.fingerprint,
                reason=reason or None,
            )

        job = await self.extractor.extract(url)
        if job is None:
            if fingerprint:
                await self.tracker_service.update_status(
                    fingerprint, ApplicationStatus.FAILED
                )
            return ApplicationRunResult(
                success=False,
                status=RunStatus.FAILED,
                errors=["Job extraction failed"],
            )

        start_url = job.apply_url or job.job_url or url
        if start_url != url:
            run_notes.append(f"canonical_start_url={start_url}")

        # Second-pass duplicate check with extracted job details (handles redirects/aggregators).
        if duplicate is None:
            canonical_duplicate = await self.tracker_service.check_duplicate(
                url=start_url,
                company=job.company,
                role=job.role_title,
                location=job.location,
            )
            if (
                canonical_duplicate is not None
                and canonical_duplicate.status == ApplicationStatus.SUBMITTED
            ):
                proceed = hitl.prompt_yes_no(
                    "Tracker indicates this job was already submitted. Proceed anyway?\n"
                    f"{start_url}"
                )
                if not proceed:
                    return ApplicationRunResult(
                        success=True,
                        status=RunStatus.DUPLICATE_SKIPPED,
                        notes=["duplicate_detected"],
                    )

                reason = hitl.prompt_free_text(
                    "Optional override reason (press Enter to skip)"
                )
                await self.tracker_service.record_override(
                    fingerprint=canonical_duplicate.fingerprint,
                    reason=reason or None,
                )

            duplicate = canonical_duplicate
            fingerprint = getattr(duplicate, "fingerprint", None)

        if fingerprint is None:
            fingerprint = await self.tracker_service.create_record(
                url=start_url,
                company=job.company,
                role=job.role_title,
                location=job.location,
                source_mode=SourceMode.SINGLE,
            )

        run_dir = (
            Path(getattr(self.settings, "output_dir", Path("./artifacts")))
            / "runs"
            / fingerprint
        )
        run_dir.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(Exception):
            job.save_json(run_dir / "jd.json")

        profile = self.profile_service.load_profile()
        fit = self.scoring_service.evaluate(job, profile)

        fit_summary_func = getattr(self.scoring_service, "format_result", None)
        fit_summary = (
            fit_summary_func(fit)
            if callable(fit_summary_func)
            else getattr(fit, "reasoning", str(fit))
        )

        if fit.recommendation == "skip":
            logger.info("Fit scoring result:\n%s", fit_summary)

            proceed = hitl.prompt_yes_no(
                "Fit scoring recommends SKIP. Proceed with application anyway?\n\n"
                f"{fit_summary}"
            )
            if not proceed:
                await self.tracker_service.update_status(
                    fingerprint, ApplicationStatus.SKIPPED
                )
                return ApplicationRunResult(
                    success=True,
                    status=RunStatus.SKIPPED,
                    notes=run_notes
                    + [f"fit_decision={fit.recommendation}", fit.reasoning],
                )
            run_notes.append("override_fit_skip")

        if fit.recommendation == "review":
            logger.info("Fit scoring result:\n%s", fit_summary)
            proceed = hitl.prompt_yes_no(
                f"Fit score recommends REVIEW. Proceed with application?\n{fit.reasoning}"
            )
            if not proceed:
                await self.tracker_service.update_status(
                    fingerprint, ApplicationStatus.SKIPPED
                )
                return ApplicationRunResult(success=True, status=RunStatus.SKIPPED)

        tailoring_service = self.tailoring_service
        if tailoring_service is None:
            tailoring_config = TailoringConfig(output_dir=run_dir)
            tailoring_service = TailoringService(config=tailoring_config)

        tailoring_result = await tailoring_service.tailor(profile, job)
        if not getattr(tailoring_result, "success", False):
            await self.tracker_service.update_status(
                fingerprint, ApplicationStatus.FAILED
            )
            error_message = (
                getattr(tailoring_result, "error", None) or "Tailoring failed"
            )
            return ApplicationRunResult(
                success=False,
                status=RunStatus.FAILED,
                errors=[error_message],
            )

        resume_path = getattr(tailoring_result, "resume_path", None)
        cover_letter_path = getattr(tailoring_result, "cover_letter_path", None)

        approved = hitl.prompt_yes_no(
            "Documents are ready. Approve resume/cover letter for upload?"
        )
        if not approved:
            return ApplicationRunResult(
                success=True,
                status=RunStatus.STOPPED_BEFORE_SUBMIT,
                notes=run_notes,
            )

        result = await self._run_application_flow(
            job_url=start_url,
            run_dir=run_dir,
            profile=profile,
            resume_path=resume_path,
            cover_letter_path=cover_letter_path,
        )

        if result.status == RunStatus.SUBMITTED:
            await self.tracker_repository.update_proof(
                fingerprint,
                proof_text=result.proof_text,
                screenshot_path=result.proof_screenshot_path,
            )
            await self.tracker_repository.update_artifacts(
                fingerprint,
                resume_artifact_path=resume_path,
                cover_letter_artifact_path=cover_letter_path,
            )
            await self.tracker_service.update_status(
                fingerprint, ApplicationStatus.SUBMITTED
            )

        if run_notes:
            result.notes.extend(run_notes)
        return result

    async def _run_application_flow(
        self,
        *,
        job_url: str,
        run_dir: Path,
        profile: Any,
        resume_path: str | None,
        cover_letter_path: str | None,
    ) -> ApplicationRunResult:
        """Run the Browser Use application agent and persist artifacts."""
        prohibited_domains = list(getattr(self.settings, "prohibited_domains", []))
        allowlist_log_path = getattr(
            self.settings, "allowlist_log_path", Path("./data/allowlist.log")
        )

        llm = get_runner_llm(self.settings)
        if llm is None:
            return ApplicationRunResult(
                success=False,
                status=RunStatus.FAILED,
                errors=["No LLM configured for runner"],
            )

        sensitive_data: dict[str, str] = {}
        name_value = getattr(profile, "name", None)
        if name_value:
            name_str = str(name_value).strip()
            if name_str:
                sensitive_data["full_name"] = name_str
                parts = [p for p in name_str.split() if p]
                if parts:
                    sensitive_data["first_name"] = parts[0]
                    if len(parts) > 1:
                        sensitive_data["last_name"] = " ".join(parts[1:])
        for key, attr in (
            ("email", "email"),
            ("phone", "phone"),
            ("location", "location"),
            ("linkedin_url", "linkedin_url"),
        ):
            value = getattr(profile, attr, None)
            if value:
                sensitive_data[key] = str(value)

        available_file_paths = [p for p in [resume_path, cover_letter_path] if p]
        conversation_path = run_dir / "conversation.jsonl"

        browser = None
        try:
            browser = create_browser(
                self.settings, prohibited_domains=prohibited_domains
            )
            agent = create_application_agent(
                job_url=job_url,
                browser=browser,
                llm=llm,
                available_file_paths=available_file_paths,
                save_conversation_path=conversation_path,
                qa_bank_path=getattr(
                    self.settings, "qa_bank_path", Path("./data/qa_bank.json")
                ),
                sensitive_data=sensitive_data,
                max_failures=getattr(self.settings, "runner_max_failures", 3),
                max_actions_per_step=getattr(
                    self.settings, "runner_max_actions_per_step", 4
                ),
                step_timeout=getattr(self.settings, "runner_step_timeout", 120),
                use_vision=getattr(self.settings, "runner_use_vision", "auto"),
            )

            history = await agent.run()
            structured = getattr(history, "structured_output", None)
            result = structured or ApplicationRunResult(
                success=False, status=RunStatus.FAILED, errors=["No structured output"]
            )

            with contextlib.suppress(Exception):
                result.visited_urls = list(history.urls())
            if result.visited_urls:
                result.final_url = result.visited_urls[-1]

            for visited in result.visited_urls:
                if prohibited_domains and is_prohibited(visited, prohibited_domains):
                    continue
                with contextlib.suppress(Exception):
                    record_allowed_domain(visited, allowlist_log_path)

            with contextlib.suppress(Exception):
                result.save_json(run_dir / "application_result.json")

            return result
        except Exception as e:
            logger.exception("Runner agent failed: %s", e)
            return ApplicationRunResult(
                success=False, status=RunStatus.FAILED, errors=[str(e)]
            )
        finally:
            if browser is not None:
                with contextlib.suppress(Exception):
                    await browser.close()


async def run_single_job(url: str, *, settings: Any) -> ApplicationRunResult:
    """Convenience entry point for CLI usage."""
    repository = TrackerRepository(settings.tracker_db_path)
    await repository.initialize()

    try:
        service = SingleJobApplicationService(
            settings=settings,
            tracker_repository=repository,
            tracker_service=TrackerService(repository),
            extractor=_default_extractor(),
            scoring_service=_default_scoring_service(),
            profile_service=_default_profile_service(),
            tailoring_service=None,
        )
        return await service.run(url)
    finally:
        with contextlib.suppress(Exception):
            await repository.close()


def _default_extractor() -> Any:
    from src.extractor.service import JobExtractor

    return JobExtractor()


def _default_scoring_service() -> Any:
    from src.scoring.service import FitScoringService

    return FitScoringService()


def _default_profile_service() -> Any:
    from src.scoring.profile import ProfileService

    return ProfileService()
