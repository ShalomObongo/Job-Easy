from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.extractor.models import JobDescription
from src.runner.models import ApplicationRunResult, RunStatus
from src.scoring.models import ConstraintResult, FitResult, FitScore
from src.tailoring.service import TailoringResult
from src.tracker.models import ApplicationStatus, SourceMode, TrackerRecord


def _make_fit_result(job: JobDescription, recommendation: str) -> FitResult:
    return FitResult(
        job_url=job.job_url,
        job_title=job.role_title,
        company=job.company,
        fit_score=FitScore(total_score=1.0, must_have_score=1.0),
        constraints=ConstraintResult(passed=True),
        recommendation=recommendation,  # type: ignore[arg-type]
        reasoning="test",
    )


@pytest.mark.asyncio
async def test_duplicate_found_triggers_prompt_and_override_logging(
    tmp_path: Path, monkeypatch
) -> None:
    from src.runner.service import SingleJobApplicationService

    settings = SimpleNamespace(
        output_dir=tmp_path,
        auto_submit=False,
        prohibited_domains=[],
        allowlist_log_path=tmp_path / "allowlist.log",
        qa_bank_path=tmp_path / "qa.json",
    )

    duplicate = TrackerRecord(
        fingerprint="fp",
        canonical_url="https://example.com/jobs/123",
        source_mode=SourceMode.SINGLE,
        company="Acme",
        role_title="Engineer",
        status=ApplicationStatus.SUBMITTED,
        first_seen_at=__import__("datetime").datetime.now(),
    )

    tracker_repo = SimpleNamespace(
        update_proof=AsyncMock(),
        update_artifacts=AsyncMock(),
    )
    tracker_service = SimpleNamespace(
        check_duplicate=AsyncMock(return_value=duplicate),
        create_record=AsyncMock(return_value="fp"),
        record_override=AsyncMock(),
        update_status=AsyncMock(),
    )

    job = JobDescription(
        company="Acme", role_title="Engineer", job_url=duplicate.canonical_url
    )
    extractor = SimpleNamespace(extract=AsyncMock(return_value=job))
    scoring = SimpleNamespace(
        evaluate=lambda _job, _profile: _make_fit_result(job, "skip")
    )
    profile_service = SimpleNamespace(load_profile=lambda *_args, **_kwargs: object())
    tailoring = SimpleNamespace(
        tailor=AsyncMock(return_value=TailoringResult(success=False))
    )

    monkeypatch.setattr("src.hitl.tools.prompt_yes_no", lambda _q: True)
    monkeypatch.setattr("src.hitl.tools.prompt_free_text", lambda _q: "because")

    service = SingleJobApplicationService(
        settings=settings,
        tracker_repository=tracker_repo,
        tracker_service=tracker_service,
        extractor=extractor,
        scoring_service=scoring,
        profile_service=profile_service,
        tailoring_service=tailoring,
    )

    await service.run("https://example.com/jobs/123")

    tracker_service.record_override.assert_awaited_once()


@pytest.mark.asyncio
async def test_skip_decision_updates_tracker_and_exits_before_applying(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from src.runner.service import SingleJobApplicationService

    settings = SimpleNamespace(
        output_dir=tmp_path,
        auto_submit=False,
        prohibited_domains=[],
        allowlist_log_path=tmp_path / "allowlist.log",
        qa_bank_path=tmp_path / "qa.json",
    )

    tracker_repo = SimpleNamespace(
        update_proof=AsyncMock(), update_artifacts=AsyncMock()
    )
    tracker_service = SimpleNamespace(
        check_duplicate=AsyncMock(return_value=None),
        create_record=AsyncMock(return_value="fp"),
        record_override=AsyncMock(),
        update_status=AsyncMock(),
    )

    job = JobDescription(
        company="Acme", role_title="Engineer", job_url="https://example.com/jobs/123"
    )
    extractor = SimpleNamespace(extract=AsyncMock(return_value=job))
    scoring = SimpleNamespace(
        evaluate=lambda _job, _profile: _make_fit_result(job, "skip")
    )
    profile_service = SimpleNamespace(load_profile=lambda *_args, **_kwargs: object())
    tailoring = SimpleNamespace(
        tailor=AsyncMock(return_value=TailoringResult(success=False))
    )

    service = SingleJobApplicationService(
        settings=settings,
        tracker_repository=tracker_repo,
        tracker_service=tracker_service,
        extractor=extractor,
        scoring_service=scoring,
        profile_service=profile_service,
        tailoring_service=tailoring,
    )

    service._run_application_flow = AsyncMock()  # type: ignore[attr-defined]

    # Decline proceeding when fit scoring recommends SKIP.
    monkeypatch.setattr("src.hitl.tools.prompt_yes_no", lambda _q: False)

    await service.run("https://example.com/jobs/123")

    tracker_service.update_status.assert_awaited_once_with(
        "fp", ApplicationStatus.SKIPPED
    )
    service._run_application_flow.assert_not_awaited()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_apply_decision_generates_artifacts_then_calls_runner(
    tmp_path: Path, monkeypatch
) -> None:
    from src.runner.service import SingleJobApplicationService

    settings = SimpleNamespace(
        output_dir=tmp_path,
        auto_submit=False,
        prohibited_domains=[],
        allowlist_log_path=tmp_path / "allowlist.log",
        qa_bank_path=tmp_path / "qa.json",
    )

    tracker_repo = SimpleNamespace(
        update_proof=AsyncMock(), update_artifacts=AsyncMock()
    )
    tracker_service = SimpleNamespace(
        check_duplicate=AsyncMock(return_value=None),
        create_record=AsyncMock(return_value="fp"),
        record_override=AsyncMock(),
        update_status=AsyncMock(),
    )

    job = JobDescription(
        company="Acme", role_title="Engineer", job_url="https://example.com/jobs/123"
    )
    extractor = SimpleNamespace(extract=AsyncMock(return_value=job))
    scoring = SimpleNamespace(
        evaluate=lambda _job, _profile: _make_fit_result(job, "apply")
    )
    profile_service = SimpleNamespace(load_profile=lambda *_args, **_kwargs: object())

    tailoring = SimpleNamespace(
        tailor=AsyncMock(
            return_value=TailoringResult(
                success=True,
                resume_path=str(tmp_path / "resume.pdf"),
                cover_letter_path=str(tmp_path / "cover.pdf"),
            )
        )
    )

    monkeypatch.setattr("src.hitl.tools.prompt_yes_no", lambda _q: True)

    service = SingleJobApplicationService(
        settings=settings,
        tracker_repository=tracker_repo,
        tracker_service=tracker_service,
        extractor=extractor,
        scoring_service=scoring,
        profile_service=profile_service,
        tailoring_service=tailoring,
    )

    service._run_application_flow = AsyncMock(  # type: ignore[attr-defined]
        return_value=ApplicationRunResult(
            success=False, status=RunStatus.STOPPED_BEFORE_SUBMIT
        )
    )

    await service.run("https://example.com/jobs/123")

    service._run_application_flow.assert_awaited()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_submission_updates_tracker_with_proof_and_artifact_paths(
    tmp_path: Path, monkeypatch
) -> None:
    from src.runner.service import SingleJobApplicationService

    settings = SimpleNamespace(
        output_dir=tmp_path,
        auto_submit=False,
        prohibited_domains=[],
        allowlist_log_path=tmp_path / "allowlist.log",
        qa_bank_path=tmp_path / "qa.json",
    )

    tracker_repo = SimpleNamespace(
        update_proof=AsyncMock(), update_artifacts=AsyncMock()
    )
    tracker_service = SimpleNamespace(
        check_duplicate=AsyncMock(return_value=None),
        create_record=AsyncMock(return_value="fp"),
        record_override=AsyncMock(),
        update_status=AsyncMock(),
    )

    job = JobDescription(
        company="Acme", role_title="Engineer", job_url="https://example.com/jobs/123"
    )
    extractor = SimpleNamespace(extract=AsyncMock(return_value=job))
    scoring = SimpleNamespace(
        evaluate=lambda _job, _profile: _make_fit_result(job, "apply")
    )
    profile_service = SimpleNamespace(load_profile=lambda *_args, **_kwargs: object())
    tailoring = SimpleNamespace(
        tailor=AsyncMock(
            return_value=TailoringResult(
                success=True,
                resume_path=str(tmp_path / "resume.pdf"),
                cover_letter_path=str(tmp_path / "cover.pdf"),
            )
        )
    )

    monkeypatch.setattr("src.hitl.tools.prompt_yes_no", lambda _q: True)

    service = SingleJobApplicationService(
        settings=settings,
        tracker_repository=tracker_repo,
        tracker_service=tracker_service,
        extractor=extractor,
        scoring_service=scoring,
        profile_service=profile_service,
        tailoring_service=tailoring,
    )

    service._run_application_flow = AsyncMock(  # type: ignore[attr-defined]
        return_value=ApplicationRunResult(
            success=True,
            status=RunStatus.SUBMITTED,
            proof_text="Application received",
            proof_screenshot_path="proof.png",
        )
    )

    await service.run("https://example.com/jobs/123")

    tracker_repo.update_proof.assert_awaited_once_with(
        "fp", proof_text="Application received", screenshot_path="proof.png"
    )
    tracker_repo.update_artifacts.assert_awaited_once_with(
        "fp",
        resume_artifact_path=str(tmp_path / "resume.pdf"),
        cover_letter_artifact_path=str(tmp_path / "cover.pdf"),
    )
    tracker_service.update_status.assert_awaited_once_with(
        "fp", ApplicationStatus.SUBMITTED
    )
