"""Main entry point for Job-Easy application."""

import argparse
import asyncio
import sys

from src import __version__
from src.config.settings import Settings
from src.utils.logging import configure_logging


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="job-easy",
        description="Job-Easy: Browser Use-powered job application automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src single https://example.com/jobs/123
  python -m src autonomous

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
    subparsers.add_parser(
        "autonomous",
        help="Run in autonomous mode (batch processing)",
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
        # TODO: Implement autonomous mode
        print("Autonomous mode not yet implemented")

    return 0


if __name__ == "__main__":
    sys.exit(main())
