#!/usr/bin/env python3
"""Manual test script for the Job Extractor.

Usage:
    python scripts/test_extractor.py <job_url>

Example:
    python scripts/test_extractor.py https://boards.greenhouse.io/anthropic/jobs/4020300007
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings
from src.extractor import JobExtractor, get_extractor_config


def _is_readable_file(path: Path | None) -> bool:
    if path is None:
        return False
    try:
        return path.is_file() and os.access(path, os.R_OK)
    except Exception:
        return False


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_extractor.py <job_url>")
        print("\nExample:")
        print(
            "  python scripts/test_extractor.py https://boards.greenhouse.io/anthropic/jobs/4020300007"
        )
        sys.exit(1)

    url = sys.argv[1]
    print(f"\n{'=' * 60}")
    print("Job Extractor Manual Test")
    print(f"{'=' * 60}")
    print(f"URL: {url}\n")

    # Show current config
    config = get_extractor_config()
    settings = get_settings()
    print("Configuration:")
    print(f"  LLM Provider: {config.llm_provider}")
    print(f"  LLM Model: {config.llm_model or 'default'}")
    print(f"  LLM Base URL: {config.llm_base_url or 'default'}")
    print(f"  Headless: {config.headless}")
    print(f"  Use Vision: {config.use_vision}")
    print(f"  Output Dir: {config.output_dir}")
    print(f"  Use Existing Chrome Profile: {settings.use_existing_chrome_profile}")
    if settings.use_existing_chrome_profile:
        print(f"  Chrome User Data Dir: {settings.chrome_user_data_dir}")
        print(f"  Chrome Profile Dir: {settings.chrome_profile_dir}")
        print(f"  Chrome Profile Mode: {settings.chrome_profile_mode}")
    print()

    if settings.use_existing_chrome_profile and settings.chrome_user_data_dir:
        preferences_path = (
            Path(settings.chrome_user_data_dir)
            / settings.chrome_profile_dir
            / "Preferences"
        )
        local_state_path = Path(settings.chrome_user_data_dir) / "Local State"
        if local_state_path.exists() and not _is_readable_file(local_state_path):
            print("Note: Chrome 'Local State' is not readable (likely root-owned).")
            print(
                "      Job-Easy will use a lightweight temp snapshot of your profile."
            )
            print(f"      Local State: {local_state_path}")
            print()
        elif not _is_readable_file(preferences_path):
            print(
                "Note: Chrome Preferences file is not readable; profile reuse may be partial."
            )
            print(f"      Preferences: {preferences_path}")
            print()

    # Create extractor and run
    extractor = JobExtractor(config=config)

    print("Starting extraction...")
    print("(This may take 30-60 seconds)\n")

    result = await extractor.extract(url, save_artifact=True)

    if result is None:
        print("❌ Extraction failed - no result returned")
        print("\nPossible issues:")
        print("  - Check your LLM API key is valid")
        print("  - Ensure the URL is accessible")
        print("  - Check the logs for errors")
        sys.exit(1)

    print("✅ Extraction successful!\n")
    print(f"{'=' * 60}")
    print("Extracted Job Description")
    print(f"{'=' * 60}")
    print(f"Company: {result.company}")
    print(f"Role: {result.role_title}")
    print(f"Location: {result.location or 'Not specified'}")
    print(f"Work Type: {result.work_type or 'Not specified'}")
    print(f"Employment Type: {result.employment_type or 'Not specified'}")
    print(f"Source: {result.extraction_source}")
    print()

    if result.salary_min or result.salary_max:
        salary = f"${result.salary_min or '?'} - ${result.salary_max or '?'}"
        if result.salary_currency:
            salary += f" {result.salary_currency}"
        print(f"Salary: {salary}")

    if result.experience_years_min or result.experience_years_max:
        exp = f"{result.experience_years_min or '?'} - {result.experience_years_max or '?'} years"
        print(f"Experience: {exp}")

    if result.required_skills:
        print(f"\nRequired Skills: {', '.join(result.required_skills[:10])}")

    if result.preferred_skills:
        print(f"Preferred Skills: {', '.join(result.preferred_skills[:10])}")

    if result.responsibilities:
        print(f"\nResponsibilities ({len(result.responsibilities)} items):")
        for r in result.responsibilities[:5]:
            print(f"  • {r[:80]}{'...' if len(r) > 80 else ''}")

    print(f"\n{'=' * 60}")
    print(f"Artifact saved to: {config.output_dir / 'jd.json'}")
    print(f"{'=' * 60}\n")

    # Also print full JSON
    print("Full JSON output:")
    print(json.dumps(result.to_dict(), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
