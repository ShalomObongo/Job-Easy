"""Main entry point for Job-Easy application."""

import argparse
import asyncio
import sys
from pathlib import Path

from src import __version__
from src.config.settings import Settings
from src.utils.logging import configure_logging


def _min_score(value: str) -> float:
    score = float(value)
    if not (0.0 <= score <= 1.0):
        raise argparse.ArgumentTypeError("--min-score must be between 0.0 and 1.0")
    return score


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

    # If no mode specified, show help
    if parsed.mode is None:
        parser.print_help()
        return 0

    logger.info(f"Job-Easy v{__version__} starting in {parsed.mode} mode")

    # Handle modes
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
