from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

from src.autonomous.models import BatchResult
from src.extractor.models import JobDescription
from src.runner.models import ApplicationRunResult, RunStatus
from src.scoring.models import (
    ConstraintResult,
    Education,
    FitResult,
    FitScore,
    UserProfile,
    WorkExperience,
)
from src.tailoring.models import DocReviewPacket
from src.tailoring.service import TailoringResult


def test_cli_single_mode_calls_pipeline_service(monkeypatch) -> None:
    from src.__main__ import main

    mock = AsyncMock(
        return_value=ApplicationRunResult(success=True, status=RunStatus.SKIPPED)
    )
    monkeypatch.setattr("src.runner.service.run_single_job", mock, raising=False)

    exit_code = main(["single", "https://example.com/jobs/123"])

    assert exit_code == 0
    mock.assert_awaited_once()


def test_cli_single_mode_missing_url_errors_cleanly() -> None:
    from src.__main__ import main

    assert main(["single"]) == 1


def test_cli_autonomous_mode_calls_autonomous_service(monkeypatch, tmp_path) -> None:
    from src.__main__ import main

    leads_file = tmp_path / "leads.txt"
    leads_file.write_text("https://example.com/jobs/123\n", encoding="utf-8")

    mock = AsyncMock(
        return_value=BatchResult(
            processed=0,
            submitted=0,
            skipped=0,
            failed=0,
            duration_seconds=0.0,
            job_results=[],
        )
    )
    monkeypatch.setattr("src.autonomous.service.run_autonomous", mock, raising=False)

    exit_code = main(["autonomous", str(leads_file), "--yes"])

    assert exit_code == 0
    mock.assert_awaited_once()


def test_cli_parser_supports_component_subcommands() -> None:
    from src.__main__ import create_parser

    parser = create_parser()

    assert (
        parser.parse_args(["extract", "https://example.com/jobs/123"]).mode == "extract"
    )

    score_args = parser.parse_args(
        ["score", "--jd", "jd.json", "--profile", "profile.yaml"]
    )
    assert score_args.mode == "score"

    tailor_args = parser.parse_args(
        ["tailor", "--jd", "jd.json", "--profile", "profile.yaml"]
    )
    assert tailor_args.mode == "tailor"

    apply_args = parser.parse_args(
        ["apply", "https://example.com/jobs/123", "--resume", "resume.pdf"]
    )
    assert apply_args.mode == "apply"

    apply_args = parser.parse_args(
        [
            "apply",
            "https://example.com/jobs/123",
            "--resume",
            "resume.pdf",
            "--profile",
            "profile.yaml",
        ]
    )
    assert apply_args.profile == Path("profile.yaml")

    queue_args = parser.parse_args(["queue", "leads.txt", "--profile", "profile.yaml"])
    assert queue_args.mode == "queue"

    tracker_args = parser.parse_args(["tracker", "stats"])
    assert tracker_args.mode == "tracker"

    tracker_args = parser.parse_args(["tracker", "lookup", "--fingerprint", "abc123"])
    assert tracker_args.mode == "tracker"
    assert tracker_args.tracker_cmd == "lookup"

    tracker_args = parser.parse_args(["tracker", "recent", "--limit", "5"])
    assert tracker_args.tracker_cmd == "recent"

    tracker_args = parser.parse_args(
        ["tracker", "mark", "--fingerprint", "abc123", "--status", "submitted"]
    )
    assert tracker_args.tracker_cmd == "mark"


def test_cli_parser_component_subcommands_accept_out_run_dir() -> None:
    from src.__main__ import create_parser

    parser = create_parser()

    assert parser.parse_args(
        ["extract", "https://example.com/jobs/123", "--out-run-dir", "out"]
    ).out_run_dir == Path("out")

    assert parser.parse_args(
        [
            "score",
            "--jd",
            "jd.json",
            "--profile",
            "profile.yaml",
            "--out-run-dir",
            "out",
        ]
    ).out_run_dir == Path("out")

    assert parser.parse_args(
        [
            "tailor",
            "--jd",
            "jd.json",
            "--profile",
            "profile.yaml",
            "--out-run-dir",
            "out",
        ]
    ).out_run_dir == Path("out")

    assert parser.parse_args(
        [
            "apply",
            "https://example.com/jobs/123",
            "--resume",
            "resume.pdf",
            "--out-run-dir",
            "out",
        ]
    ).out_run_dir == Path("out")

    assert parser.parse_args(
        [
            "queue",
            "leads.txt",
            "--profile",
            "profile.yaml",
            "--out-run-dir",
            "out",
        ]
    ).out_run_dir == Path("out")


def test_cli_queue_mode_writes_queue_json(monkeypatch, tmp_path) -> None:
    from src.__main__ import main
    from src.autonomous.models import QueuedJob

    leads_file = tmp_path / "leads.txt"
    leads_file.write_text("https://example.com/jobs/123\n", encoding="utf-8")

    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text("{}\n", encoding="utf-8")

    # Patch queue building
    fit = FitResult(
        job_url="https://example.com/jobs/123",
        job_title="Engineer",
        company="Acme",
        fit_score=FitScore(total_score=0.9, must_have_score=1.0),
        constraints=ConstraintResult(passed=True),
        recommendation="apply",
        reasoning="ok",
    )

    def _load_profile(_self, _path=None):
        return UserProfile(
            name="Test User",
            email="test@example.com",
            phone=None,
            location="Remote",
            linkedin_url=None,
            skills=["python"],
            years_of_experience=5,
            current_title="",
            summary="",
            work_history=[],
            education=[],
        )

    monkeypatch.setattr(
        "src.scoring.profile.ProfileService.load_profile", _load_profile
    )

    from src.autonomous.queue import QueueStats

    async def _build_queue(_self, _leads, **_kwargs):
        _self._stats = QueueStats(
            total=1,
            valid=1,
            duplicates=0,
            below_threshold=0,
            queued=1,
        )

        job = JobDescription(company="Acme", role_title="Engineer", job_url=fit.job_url)
        return [
            QueuedJob(
                url=fit.job_url,
                fingerprint="abc123",
                job_description=job,
                fit_result=fit,
            )
        ]

    monkeypatch.setattr("src.autonomous.queue.QueueManager.build_queue", _build_queue)

    exit_code = main(
        [
            "queue",
            str(leads_file),
            "--profile",
            str(profile_path),
            "--out-run-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "queue.json").exists()


def test_cli_extract_mode_writes_jd_json(monkeypatch, tmp_path) -> None:
    from src.__main__ import main
    from src.extractor.models import JobDescription

    url = "https://example.com/jobs/123"
    mock = AsyncMock(
        return_value=JobDescription(company="Acme", role_title="Engineer", job_url=url)
    )
    monkeypatch.setattr("src.extractor.service.JobExtractor.extract", mock)

    exit_code = main(["extract", url, "--out-run-dir", str(tmp_path)])

    assert exit_code == 0
    assert (tmp_path / "jd.json").exists()
    mock.assert_awaited_once()


def test_cli_score_mode_writes_fit_result_json(monkeypatch, tmp_path) -> None:
    from src.__main__ import main

    jd_path = tmp_path / "jd.json"
    jd_path.write_text(
        json.dumps(
            {
                "company": "Acme",
                "role_title": "Engineer",
                "job_url": "https://example.com/jobs/123",
                "location": "Remote",
            }
        ),
        encoding="utf-8",
    )

    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text("{}\n", encoding="utf-8")

    fit = FitResult(
        job_url="https://example.com/jobs/123",
        job_title="Engineer",
        company="Acme",
        fit_score=FitScore(total_score=1.0, must_have_score=1.0),
        constraints=ConstraintResult(passed=True),
        recommendation="apply",
        reasoning="ok",
    )

    dummy_profile = UserProfile(
        name="Test User",
        email="test@example.com",
        phone=None,
        location="Remote",
        linkedin_url=None,
        skills=["python"],
        years_of_experience=5,
        current_title="",
        summary="",
        work_history=[
            WorkExperience(
                company="Acme",
                title="Engineer",
                start_date=date(2020, 1, 1),
                end_date=None,
                description="Did things",
                skills_used=["python"],
            )
        ],
        education=[
            Education(
                institution="Uni",
                degree="Bachelor",
                field="CS",
                graduation_year=2019,
            )
        ],
    )

    def _load_profile(_self, _path=None):
        return dummy_profile

    def _evaluate(_self, _job, _profile):
        return fit

    monkeypatch.setattr(
        "src.scoring.profile.ProfileService.load_profile", _load_profile
    )
    monkeypatch.setattr("src.scoring.service.FitScoringService.evaluate", _evaluate)

    exit_code = main(
        [
            "score",
            "--jd",
            str(jd_path),
            "--profile",
            str(profile_path),
            "--out-run-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "fit_result.json").exists()


def test_cli_tailor_mode_writes_review_packet_json(monkeypatch, tmp_path) -> None:
    from src.__main__ import main

    jd_path = tmp_path / "jd.json"
    jd_path.write_text(
        json.dumps(
            {
                "company": "Acme",
                "role_title": "Engineer",
                "job_url": "https://example.com/jobs/123",
                "location": "Remote",
            }
        ),
        encoding="utf-8",
    )

    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text("{}\n", encoding="utf-8")

    dummy_profile = UserProfile(
        name="Test User",
        email="test@example.com",
        phone=None,
        location="Remote",
        linkedin_url=None,
        skills=["python"],
        years_of_experience=5,
        current_title="",
        summary="",
        work_history=[],
        education=[],
    )

    def _load_profile(_self, _path=None):
        return dummy_profile

    async def _tailor(_self, _profile, _job, generate_cover_letter=True):
        resume_path = str(tmp_path / "resume.pdf")
        Path(resume_path).write_text("pdf", encoding="utf-8")

        cover_path = None
        if generate_cover_letter:
            cover_path = str(tmp_path / "cover.pdf")
            Path(cover_path).write_text("pdf", encoding="utf-8")

        packet = DocReviewPacket(
            job_url="https://example.com/jobs/123",
            company="Acme",
            role_title="Engineer",
            changes_summary=[],
            keywords_highlighted=[],
            requirements_vs_evidence=[],
            resume_path=resume_path,
            cover_letter_path=cover_path,
        )

        return TailoringResult(
            success=True,
            error=None,
            plan=None,
            resume=None,
            cover_letter=None,
            review_packet=packet,
            resume_path=resume_path,
            cover_letter_path=cover_path,
        )

    monkeypatch.setattr(
        "src.scoring.profile.ProfileService.load_profile", _load_profile
    )
    monkeypatch.setattr("src.tailoring.service.TailoringService.tailor", _tailor)

    exit_code = main(
        [
            "tailor",
            "--jd",
            str(jd_path),
            "--profile",
            str(profile_path),
            "--out-run-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "review_packet.json").exists()
