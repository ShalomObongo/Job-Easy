"""Main entry point for Job-Easy application."""

import argparse
import asyncio
import contextlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from src import __version__
from src.config.settings import Settings
from src.utils.logging import configure_logging


def _min_score(value: str) -> float:
    score = float(value)
    if not (0.0 <= score <= 1.0):
        raise argparse.ArgumentTypeError("--min-score must be between 0.0 and 1.0")
    return score


def _timestamp_run_id(prefix: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}"


def _resolve_run_dir(
    settings: Settings, *, prefix: str, out_run_dir: Path | None
) -> Path:
    if out_run_dir is not None:
        run_dir = out_run_dir
    else:
        run_dir = settings.output_dir / "runs" / _timestamp_run_id(prefix)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    def _default(value: object):
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            return to_dict()
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            return model_dump(mode="json")
        return str(value)

    path.write_text(
        json.dumps(payload, indent=2, default=_default),
        encoding="utf-8",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="job-easy",
        description="Job-Easy: Browser Use-powered job application automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src single https://example.com/jobs/123
  python -m src autonomous leads.txt

For more information, see the documentation in docs/
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Set the log level (overrides settings)",
    )

    subparsers = parser.add_subparsers(
        dest="mode",
        title="modes",
        description="Available operating modes",
    )

    # Single job mode
    single_parser = subparsers.add_parser(
        "single",
        help="Process a single job application",
    )
    single_parser.add_argument(
        "url",
        nargs="?",
        help="URL of the job posting to apply to",
    )
    single_parser.add_argument(
        "--yolo",
        action="store_true",
        help="Enable runner YOLO mode (best-effort auto-answering)",
    )
    single_parser.add_argument(
        "--yes",
        action="store_true",
        help=(
            "Assume 'yes' for fit-skip/review and document-approval prompts "
            "(final submit still requires typing YES)"
        ),
    )
    single_parser.add_argument(
        "--auto-submit",
        action="store_true",
        help=(
            "Automatically confirm final submit without human prompt. "
            "Requires --yolo and --yes to be enabled."
        ),
    )

    # Autonomous mode
    autonomous_parser = subparsers.add_parser(
        "autonomous",
        help="Run in autonomous mode (batch processing)",
    )
    autonomous_parser.add_argument(
        "leads_file",
        type=Path,
        help="Path to a text file with one job URL per line",
    )
    autonomous_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Score and generate documents without applying",
    )
    autonomous_parser.add_argument(
        "--min-score",
        type=_min_score,
        default=None,
        help="Skip jobs below this overall score (0.0-1.0)",
    )
    autonomous_parser.add_argument(
        "--include-skips",
        action="store_true",
        help="Include jobs even if fit scoring recommends skip",
    )
    autonomous_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt before processing",
    )
    autonomous_parser.add_argument(
        "--yolo",
        action="store_true",
        help="Enable runner YOLO mode (best-effort auto-answering)",
    )
    autonomous_parser.add_argument(
        "--auto-submit",
        action="store_true",
        help=(
            "Automatically confirm final submit without human prompt. "
            "Requires --yolo and --yes to be enabled."
        ),
    )

    # Component mode: extract
    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract job description only (URL -> jd.json)",
    )
    extract_parser.add_argument(
        "url",
        help="URL of the job posting to extract",
    )
    extract_parser.add_argument(
        "--out-run-dir",
        type=Path,
        default=None,
        help="Optional output run directory (defaults under artifacts/runs/)",
    )

    # Component mode: score
    score_parser = subparsers.add_parser(
        "score",
        help="Score fit only (jd.json + profile -> FitResult)",
    )
    score_parser.add_argument("--jd", type=Path, required=True, help="Path to jd.json")
    score_parser.add_argument(
        "--profile",
        type=Path,
        required=True,
        help="Path to profile (YAML or JSON)",
    )
    score_parser.add_argument(
        "--out-run-dir",
        type=Path,
        default=None,
        help="Optional output run directory (defaults under artifacts/runs/)",
    )

    # Component mode: score-eval
    score_eval_parser = subparsers.add_parser(
        "score-eval",
        help="Evaluate and compare deterministic vs LLM fit scoring",
    )
    score_eval_parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to jd.json, queue.json, or a directory containing jd.json files",
    )
    score_eval_parser.add_argument(
        "--profile",
        type=Path,
        required=True,
        help="Path to profile (YAML or JSON)",
    )
    score_eval_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on jobs evaluated (cost control)",
    )
    score_eval_parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from an existing report in the run directory",
    )
    score_eval_parser.add_argument(
        "--out-run-dir",
        type=Path,
        default=None,
        help="Optional output run directory (defaults under artifacts/runs/)",
    )

    # Component mode: tailor
    tailor_parser = subparsers.add_parser(
        "tailor",
        help="Tailor documents only (jd.json + profile -> PDFs)",
    )
    tailor_parser.add_argument("--jd", type=Path, required=True, help="Path to jd.json")
    tailor_parser.add_argument(
        "--profile",
        type=Path,
        required=True,
        help="Path to profile (YAML or JSON)",
    )
    tailor_parser.add_argument(
        "--no-cover-letter",
        action="store_true",
        help="Disable cover letter generation",
    )
    tailor_parser.add_argument(
        "--out-run-dir",
        type=Path,
        default=None,
        help="Optional output run directory (defaults under artifacts/runs/)",
    )

    # Component mode: apply
    apply_parser = subparsers.add_parser(
        "apply",
        help="Run runner only (URL + resume/cover letter -> application)",
    )
    apply_parser.add_argument("url", help="URL of the job posting or application form")
    apply_parser.add_argument(
        "--resume",
        type=Path,
        required=True,
        help="Path to resume file to upload",
    )
    apply_parser.add_argument(
        "--cover-letter",
        type=Path,
        required=False,
        help="Optional path to cover letter file to upload",
    )
    apply_parser.add_argument(
        "--profile",
        type=Path,
        default=None,
        help="Optional path to profile (YAML or JSON) for form filling",
    )
    apply_parser.add_argument(
        "--jd",
        type=Path,
        default=None,
        help="Optional path to jd.json (required for --yolo)",
    )
    apply_parser.add_argument(
        "--yolo",
        action="store_true",
        help="Enable runner YOLO mode (requires --profile and --jd)",
    )
    apply_parser.add_argument(
        "--out-run-dir",
        type=Path,
        default=None,
        help="Optional output run directory (defaults under artifacts/runs/)",
    )

    # Component mode: queue
    queue_parser = subparsers.add_parser(
        "queue",
        help="Build autonomous queue only (leads -> ranked queue)",
    )
    queue_parser.add_argument(
        "leads_file",
        type=Path,
        help="Path to a text file with one job URL per line",
    )
    queue_parser.add_argument(
        "--profile",
        type=Path,
        required=True,
        help="Path to profile (YAML or JSON)",
    )
    queue_parser.add_argument(
        "--min-score",
        type=_min_score,
        default=None,
        help="Skip jobs below this overall score (0.0-1.0)",
    )
    queue_parser.add_argument(
        "--include-skips",
        action="store_true",
        help="Include jobs even if fit scoring recommends skip",
    )
    queue_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of queue entries printed/written",
    )
    queue_parser.add_argument(
        "--out-run-dir",
        type=Path,
        default=None,
        help="Optional output run directory (defaults under artifacts/runs/)",
    )

    # Component mode: tracker
    tracker_parser = subparsers.add_parser(
        "tracker",
        help="Tracker utilities (lookup, recent, stats, mark)",
    )
    tracker_subparsers = tracker_parser.add_subparsers(
        dest="tracker_cmd",
        title="tracker",
        description="Tracker operations",
        required=True,
    )

    tracker_stats = tracker_subparsers.add_parser("stats", help="Show tracker stats")
    tracker_stats.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Override tracker DB path (defaults to settings)",
    )

    tracker_lookup = tracker_subparsers.add_parser("lookup", help="Lookup record")
    tracker_lookup.add_argument(
        "--fingerprint",
        type=str,
        default=None,
        help="Fingerprint to lookup",
    )
    tracker_lookup.add_argument(
        "--url",
        type=str,
        default=None,
        help="Canonical URL to lookup",
    )
    tracker_lookup.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Override tracker DB path (defaults to settings)",
    )

    tracker_recent = tracker_subparsers.add_parser("recent", help="List recent records")
    tracker_recent.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of records",
    )
    tracker_recent.add_argument(
        "--status",
        type=str,
        default=None,
        help="Optional status filter (new/submitted/skipped/failed)",
    )
    tracker_recent.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Override tracker DB path (defaults to settings)",
    )

    tracker_mark = tracker_subparsers.add_parser("mark", help="Update a record")
    tracker_mark.add_argument(
        "--fingerprint",
        type=str,
        required=True,
        help="Fingerprint to update",
    )
    tracker_mark.add_argument(
        "--status",
        type=str,
        required=True,
        help="New status (new/submitted/skipped/failed)",
    )
    tracker_mark.add_argument(
        "--proof-text",
        type=str,
        default=None,
        help="Optional proof text",
    )
    tracker_mark.add_argument(
        "--proof-screenshot",
        type=Path,
        default=None,
        help="Optional proof screenshot path",
    )
    tracker_mark.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Override tracker DB path (defaults to settings)",
    )

    return parser


def main(args: list[str] | None = None) -> int:
    """Main entry point for the application.

    Args:
        args: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = create_parser()
    parsed = parser.parse_args(args)

    # Load settings
    try:
        settings = Settings()
    except Exception as e:
        print(f"Error loading settings: {e}", file=sys.stderr)
        return 1

    # Configure logging
    log_level = parsed.log_level or settings.log_level
    logger = configure_logging(level=log_level)

    if getattr(parsed, "yolo", False):
        settings.runner_yolo_mode = True

    if getattr(parsed, "yes", False):
        settings.runner_assume_yes = True

    # If no mode specified, show help
    if parsed.mode is None:
        parser.print_help()
        return 0

    runner_modes = {"single", "autonomous", "apply"}
    auto_submit_requested = bool(getattr(parsed, "auto_submit", False)) or bool(
        getattr(settings, "runner_auto_submit", False)
    )
    if parsed.mode in runner_modes and auto_submit_requested:
        if not settings.runner_yolo_mode or not settings.runner_assume_yes:
            print(
                "Error: auto-submit requires both YOLO mode and assume-yes to be enabled "
                "(--yolo/--yes or RUNNER_YOLO_MODE/RUNNER_ASSUME_YES).",
                file=sys.stderr,
            )
            return 1
        settings.runner_auto_submit = True

    logger.info(f"Job-Easy v{__version__} starting in {parsed.mode} mode")

    # Handle modes
    if parsed.mode == "extract":
        from src.extractor.service import JobExtractor

        run_dir = _resolve_run_dir(
            settings,
            prefix="extract",
            out_run_dir=getattr(parsed, "out_run_dir", None),
        )

        extractor = JobExtractor()
        job = asyncio.run(extractor.extract(parsed.url))
        if job is None:
            return 1

        job.save_json(run_dir / "jd.json")
        print(f"Wrote: {run_dir / 'jd.json'}")
        print(f"Company: {job.company}")
        print(f"Role: {job.role_title}")
        if job.location:
            print(f"Location: {job.location}")
        if job.extraction_source:
            print(f"Source: {job.extraction_source}")
        if job.apply_url:
            print(f"Apply URL: {job.apply_url}")

        return 0

    if parsed.mode == "score":
        from src.extractor.models import JobDescription
        from src.scoring.profile import ProfileService
        from src.scoring.service import FitScoringService

        run_dir = _resolve_run_dir(
            settings,
            prefix="score",
            out_run_dir=getattr(parsed, "out_run_dir", None),
        )

        jd_data = _load_json(parsed.jd)
        job = JobDescription.from_dict(jd_data)

        profile_service = ProfileService()
        profile = profile_service.load_profile(parsed.profile)

        scoring_service = FitScoringService()
        fit = scoring_service.evaluate(job, profile)

        # Print a readable summary
        print(scoring_service.format_result(fit))

        fit_payload = {
            "job_url": fit.job_url,
            "job_title": fit.job_title,
            "company": fit.company,
            "score_source": getattr(fit, "score_source", None),
            "fit_score": {
                "total_score": fit.fit_score.total_score,
                "must_have_score": fit.fit_score.must_have_score,
                "must_have_matched": fit.fit_score.must_have_matched,
                "must_have_missing": fit.fit_score.must_have_missing,
                "preferred_score": fit.fit_score.preferred_score,
                "preferred_matched": fit.fit_score.preferred_matched,
                "experience_score": fit.fit_score.experience_score,
                "experience_reasoning": fit.fit_score.experience_reasoning,
                "education_score": fit.fit_score.education_score,
                "education_reasoning": fit.fit_score.education_reasoning,
                "risk_flags": getattr(fit.fit_score, "risk_flags", []),
            },
            "baseline": None,
            "constraints": {
                "passed": fit.constraints.passed,
                "hard_violations": fit.constraints.hard_violations,
                "soft_warnings": fit.constraints.soft_warnings,
            },
            "recommendation": fit.recommendation,
            "reasoning": fit.reasoning,
            "evaluated_at": fit.evaluated_at.isoformat(),
        }

        baseline_fit_score = getattr(fit, "baseline_fit_score", None)
        baseline_recommendation = getattr(fit, "baseline_recommendation", None)
        if baseline_fit_score is not None and baseline_recommendation is not None:
            fit_payload["baseline"] = {
                "recommendation": baseline_recommendation,
                "fit_score": {
                    "total_score": baseline_fit_score.total_score,
                    "must_have_score": baseline_fit_score.must_have_score,
                    "must_have_matched": baseline_fit_score.must_have_matched,
                    "must_have_missing": baseline_fit_score.must_have_missing,
                    "preferred_score": baseline_fit_score.preferred_score,
                    "preferred_matched": baseline_fit_score.preferred_matched,
                    "experience_score": baseline_fit_score.experience_score,
                    "experience_reasoning": baseline_fit_score.experience_reasoning,
                    "education_score": baseline_fit_score.education_score,
                    "education_reasoning": baseline_fit_score.education_reasoning,
                    "risk_flags": getattr(baseline_fit_score, "risk_flags", []),
                },
            }

        output_path = run_dir / "fit_result.json"
        _write_json(output_path, fit_payload)
        print(f"Wrote: {output_path}")

        return 0

    if parsed.mode == "score-eval":
        from src.scoring.config import ScoringConfig
        from src.scoring.evaluation import (
            build_score_eval_report,
            load_job_descriptions,
            summarize_score_eval_items,
        )
        from src.scoring.profile import ProfileService
        from src.scoring.service import FitScoringService

        run_dir = _resolve_run_dir(
            settings,
            prefix="score-eval",
            out_run_dir=getattr(parsed, "out_run_dir", None),
        )

        profile = ProfileService().load_profile(parsed.profile)

        all_jobs = load_job_descriptions(parsed.input)
        jobs_to_eval = all_jobs

        report_path = run_dir / "score_eval_report.json"
        existing_items: list[dict] = []
        existing_urls: set[str] = set()

        if getattr(parsed, "resume", False) and report_path.exists():
            existing = _load_json(report_path)
            if isinstance(existing, dict) and isinstance(existing.get("items"), list):
                existing_items = [
                    item for item in existing["items"] if isinstance(item, dict)
                ]
                for item in existing_items:
                    url = item.get("job_url")
                    if isinstance(url, str) and url:
                        existing_urls.add(url)
            jobs_to_eval = [job for job in all_jobs if job.job_url not in existing_urls]

        deterministic_scorer = FitScoringService(
            config=ScoringConfig(scoring_mode="deterministic")
        )
        llm_scorer = FitScoringService(config=ScoringConfig(scoring_mode="llm"))

        new_report = build_score_eval_report(
            jobs=jobs_to_eval,
            profile=profile,
            deterministic_scorer=deterministic_scorer,
            llm_scorer=llm_scorer,
            limit=getattr(parsed, "limit", None),
        )

        report = new_report
        if existing_items:
            combined_items = existing_items + new_report.get("items", [])
            report = {
                "summary": summarize_score_eval_items(
                    total_jobs=len(all_jobs),
                    items=combined_items,
                ),
                "items": combined_items,
            }

        _write_json(report_path, report)
        print(f"Wrote: {report_path}")

        summary = report.get("summary") if isinstance(report, dict) else None
        if isinstance(summary, dict):
            print(
                "Jobs: "
                f"total={summary.get('total_jobs')} evaluated={summary.get('evaluated')} "
                f"disagreements={summary.get('disagreements')} llm_failures={summary.get('llm_failures')}"
            )

        return 0

    if parsed.mode == "tailor":
        from src.extractor.models import JobDescription
        from src.scoring.profile import ProfileService
        from src.tailoring.config import TailoringConfig
        from src.tailoring.service import TailoringService

        run_dir = _resolve_run_dir(
            settings,
            prefix="tailor",
            out_run_dir=getattr(parsed, "out_run_dir", None),
        )

        jd_data = _load_json(parsed.jd)
        job = JobDescription.from_dict(jd_data)

        profile_service = ProfileService()
        profile = profile_service.load_profile(parsed.profile)

        config = TailoringConfig(output_dir=run_dir)
        tailoring_service = TailoringService(config=config)

        result = asyncio.run(
            tailoring_service.tailor(
                profile,
                job,
                generate_cover_letter=not parsed.no_cover_letter,
            )
        )
        if not getattr(result, "success", False):
            print(getattr(result, "error", None) or "Tailoring failed", file=sys.stderr)
            return 1

        review_packet_path = run_dir / "review_packet.json"
        review_packet = getattr(result, "review_packet", None)
        if review_packet is not None:
            _write_json(review_packet_path, review_packet.to_dict())
        else:
            _write_json(
                review_packet_path,
                {
                    "resume_path": getattr(result, "resume_path", None),
                    "cover_letter_path": getattr(result, "cover_letter_path", None),
                },
            )

        print(f"Wrote: {review_packet_path}")
        if getattr(result, "resume_path", None):
            print(f"Resume: {result.resume_path}")
        if getattr(result, "cover_letter_path", None):
            print(f"Cover letter: {result.cover_letter_path}")

        return 0

    if parsed.mode == "apply":
        from src.hitl.tools import create_hitl_tools
        from src.runner.agent import (
            create_application_agent,
            create_browser,
            get_runner_llm,
        )

        run_dir = _resolve_run_dir(
            settings,
            prefix="apply",
            out_run_dir=getattr(parsed, "out_run_dir", None),
        )

        llm = get_runner_llm(settings)
        if llm is None:
            print("No LLM configured for runner", file=sys.stderr)
            return 1

        available_file_paths = [str(parsed.resume)]
        if getattr(parsed, "cover_letter", None):
            available_file_paths.append(str(parsed.cover_letter))

        sensitive_data: dict[str, str | dict[str, str]] = {}
        profile = None
        if getattr(parsed, "profile", None):
            from src.scoring.profile import ProfileService

            profile = ProfileService().load_profile(parsed.profile)
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
                ("github_url", "github_url"),
            ):
                value = getattr(profile, attr, None)
                if value:
                    sensitive_data[key] = str(value)

        conversation_path = run_dir / "conversation.jsonl"

        prohibited = list(getattr(settings, "prohibited_domains", []))
        browser = None
        try:
            browser = create_browser(settings, prohibited_domains=prohibited)

            yolo_mode = bool(getattr(settings, "runner_yolo_mode", False))
            assume_yes = bool(getattr(settings, "runner_assume_yes", False))
            auto_submit_requested = bool(getattr(settings, "runner_auto_submit", False))
            auto_submit = bool(auto_submit_requested and yolo_mode and assume_yes)
            yolo_context = None

            domain = urlparse(parsed.url).netloc.strip().lower()
            qa_scope_hints = []

            if yolo_mode:
                if profile is None or getattr(parsed, "jd", None) is None:
                    print(
                        "Error: --yolo requires --profile and --jd",
                        file=sys.stderr,
                    )
                    return 1

                from src.extractor.models import JobDescription
                from src.runner.yolo import build_yolo_context
                from src.tracker.fingerprint import compute_fingerprint, extract_job_id

                jd_data = _load_json(parsed.jd)
                job = JobDescription.from_dict(jd_data)

                job_id = job.job_id or extract_job_id(
                    job.apply_url or job.job_url or parsed.url
                )
                job_fingerprint = compute_fingerprint(
                    url=job.apply_url or job.job_url or parsed.url,
                    job_id=job_id,
                    company=job.company,
                    role=job.role_title,
                    location=job.location,
                )

                company_key = str(job.company or "").strip().lower()
                qa_scope_hints.append(("job", job_fingerprint))
                if company_key:
                    qa_scope_hints.append(("company", company_key))
                if domain:
                    qa_scope_hints.append(("domain", domain))
                qa_scope_hints.append(("global", None))

                yolo_context = build_yolo_context(job=job, profile=profile)
            else:
                if domain:
                    qa_scope_hints.append(("domain", domain))
                qa_scope_hints.append(("global", None))

            agent = create_application_agent(
                job_url=parsed.url,
                browser=browser,
                llm=llm,
                tools=create_hitl_tools(auto_submit=auto_submit),
                available_file_paths=available_file_paths,
                save_conversation_path=conversation_path,
                qa_bank_path=getattr(
                    settings, "qa_bank_path", Path("./data/qa_bank.json")
                ),
                qa_scope_hints=qa_scope_hints,
                sensitive_data=sensitive_data or None,
                yolo_mode=yolo_mode,
                yolo_context=yolo_context,
                auto_submit=auto_submit,
                max_failures=getattr(settings, "runner_max_failures", 3),
                max_actions_per_step=getattr(
                    settings, "runner_max_actions_per_step", 4
                ),
                step_timeout=getattr(settings, "runner_step_timeout", 120),
                use_vision=getattr(settings, "runner_use_vision", "auto"),
            )

            history = asyncio.run(agent.run())
            structured = getattr(history, "structured_output", None)
            result = structured
            if result is None:
                print("Runner did not produce structured output", file=sys.stderr)
                return 1

            with open(run_dir / "application_result.json", "w", encoding="utf-8") as f:
                f.write(result.model_dump_json(indent=2))

            print(f"Status: {result.status.value}")
            print(f"Wrote: {run_dir / 'application_result.json'}")
            if result.errors:
                print("Errors:")
                for err in result.errors:
                    print(f"- {err}")
            if result.proof_text:
                print(f"Proof: {result.proof_text}")

            return 0 if getattr(result, "success", False) else 1
        finally:
            if browser is not None:
                with contextlib.suppress(Exception):
                    asyncio.run(browser.close())

    if parsed.mode == "tracker":
        from src.tracker.models import ApplicationStatus
        from src.tracker.repository import TrackerRepository

        db_path = getattr(parsed, "db", None) or settings.tracker_db_path
        repo = TrackerRepository(db_path)
        asyncio.run(repo.initialize())

        try:
            if parsed.tracker_cmd == "stats":
                counts = asyncio.run(repo.get_status_counts())
                for status in ApplicationStatus:
                    print(f"{status.value}: {counts.get(status, 0)}")
                return 0

            if parsed.tracker_cmd == "lookup":
                if parsed.fingerprint:
                    record = asyncio.run(repo.get_by_fingerprint(parsed.fingerprint))
                elif parsed.url:
                    record = asyncio.run(repo.get_by_url(parsed.url))
                else:
                    print("Provide --fingerprint or --url", file=sys.stderr)
                    return 1

                if record is None:
                    print("Not found")
                    return 1

                print(json.dumps(record.to_dict(), indent=2))
                return 0

            if parsed.tracker_cmd == "recent":
                status_filter = None
                if parsed.status:
                    status_value = str(parsed.status).strip().lower()
                    try:
                        status_filter = ApplicationStatus(status_value)
                    except Exception:
                        print("Invalid --status", file=sys.stderr)
                        return 1

                records = asyncio.run(
                    repo.list_recent(limit=parsed.limit, status_filter=status_filter)
                )
                for rec in records:
                    print(
                        f"{rec.first_seen_at.isoformat()} {rec.status.value} {rec.fingerprint} {rec.company} {rec.role_title}"
                    )
                return 0

            if parsed.tracker_cmd == "mark":
                status_value = str(parsed.status).strip().lower()
                try:
                    status = ApplicationStatus(status_value)
                except Exception:
                    print("Invalid --status", file=sys.stderr)
                    return 1

                asyncio.run(repo.update_status(parsed.fingerprint, status))
                if parsed.proof_text or parsed.proof_screenshot:
                    asyncio.run(
                        repo.update_proof(
                            parsed.fingerprint,
                            proof_text=parsed.proof_text,
                            screenshot_path=str(parsed.proof_screenshot)
                            if parsed.proof_screenshot
                            else None,
                        )
                    )
                print("ok")
                return 0

            print("Unknown tracker command", file=sys.stderr)
            return 1
        finally:
            asyncio.run(repo.close())

    if parsed.mode == "queue":
        from src.autonomous.leads import LeadFileParser
        from src.autonomous.queue import QueueManager
        from src.extractor.service import JobExtractor
        from src.scoring.profile import ProfileService
        from src.scoring.service import FitScoringService
        from src.tracker.repository import TrackerRepository
        from src.tracker.service import TrackerService

        run_dir = _resolve_run_dir(
            settings,
            prefix="queue",
            out_run_dir=getattr(parsed, "out_run_dir", None),
        )

        leads_file: Path = parsed.leads_file
        if not leads_file.exists():
            print(f"Error: leads file not found: {leads_file}", file=sys.stderr)
            return 1

        profile = ProfileService().load_profile(parsed.profile)

        repo = TrackerRepository(settings.tracker_db_path)
        asyncio.run(repo.initialize())
        try:
            tracker_service = TrackerService(repo)
            extractor = JobExtractor()
            scorer = FitScoringService()

            leads = LeadFileParser().parse(leads_file)
            queue_manager = QueueManager()
            queue = asyncio.run(
                queue_manager.build_queue(
                    leads,
                    tracker_service=tracker_service,
                    extractor=extractor,
                    scorer=scorer,
                    profile=profile,
                    min_score=parsed.min_score,
                    include_skips=parsed.include_skips,
                )
            )

            stats = queue_manager.get_stats()
            print(
                "Leads: "
                f"total={stats.total} valid={stats.valid} "
                f"duplicates_skipped={stats.duplicates} below_threshold={stats.below_threshold} "
                f"queued={stats.queued}"
            )

            if parsed.limit is not None:
                queue = queue[: parsed.limit]

            payload = {
                "stats": {
                    "total": stats.total,
                    "valid": stats.valid,
                    "duplicates": stats.duplicates,
                    "below_threshold": stats.below_threshold,
                    "queued": stats.queued,
                },
                "items": [item.to_dict() for item in queue],
            }
            output_path = run_dir / "queue.json"
            _write_json(output_path, payload)
            print(f"Wrote: {output_path}")

            for item in queue:
                url = getattr(item, "url", None) or (
                    item.get("url") if isinstance(item, dict) else None
                )
                fingerprint = getattr(item, "fingerprint", None) or (
                    item.get("fingerprint") if isinstance(item, dict) else None
                )

                score_obj = None
                fit_result = getattr(item, "fit_result", None)
                if fit_result is None and isinstance(item, dict):
                    fit_result = item.get("fit_result")
                if fit_result is not None:
                    score_obj = getattr(
                        getattr(fit_result, "fit_score", None), "total_score", None
                    )

                if isinstance(score_obj, (int, float)):
                    print(f"{score_obj:.2f} {fingerprint} {url}")
                else:
                    print(f"{fingerprint} {url}")

            return 0
        finally:
            asyncio.run(repo.close())

    if parsed.mode == "single":
        if not parsed.url:
            logger.error("URL is required for single mode")
            print("Error: URL is required for single mode", file=sys.stderr)
            return 1
        logger.info(f"Processing job URL: {parsed.url}")
        from src.runner import service as runner_service

        result = asyncio.run(
            runner_service.run_single_job(parsed.url, settings=settings)
        )
        print(f"Status: {result.status.value}")
        if result.errors:
            print("Errors:")
            for err in result.errors:
                print(f"- {err}")
        if result.notes:
            print("Notes:")
            for note in result.notes:
                print(f"- {note}")
        if result.proof_text:
            print(f"Proof: {result.proof_text}")

        return 0 if result.success else 1

    elif parsed.mode == "autonomous":
        logger.info("Starting autonomous mode")
        if not getattr(parsed, "leads_file", None):
            logger.error("leads_file is required for autonomous mode")
            print("Error: leads_file is required for autonomous mode", file=sys.stderr)
            return 1

        leads_file: Path = parsed.leads_file
        if not leads_file.exists():
            print(f"Error: leads file not found: {leads_file}", file=sys.stderr)
            return 1

        from src.autonomous.service import run_autonomous

        def _progress(event) -> None:
            print(
                f"[{event.index}/{event.total}] {event.status.value}: {event.url} "
                f"(processed={event.processed} submitted={event.submitted} "
                f"skipped={event.skipped} failed={event.failed})"
            )

        result = asyncio.run(
            run_autonomous(
                leads_file,
                settings=settings,
                dry_run=parsed.dry_run,
                min_score=parsed.min_score,
                include_skips=parsed.include_skips or parsed.dry_run,
                assume_yes=parsed.yes,
                progress_callback=_progress,
            )
        )

        print("\nBatch complete.")
        print(
            "Totals: "
            f"processed={result.processed} submitted={result.submitted} "
            f"skipped={result.skipped} failed={result.failed}"
        )
        if result.job_results:
            print("\nResults:")
            for job in result.job_results:
                summary = f"- {job.status.value}: {job.url}"
                if job.error:
                    summary += f" ({job.error})"
                print(summary)
        if result.failed:
            return 1
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
