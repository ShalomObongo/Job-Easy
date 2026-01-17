# test_tailoring_manual.py
import asyncio
import json
from pathlib import Path

import yaml

from src.extractor.models import JobDescription
from src.scoring.models import UserProfile
from src.tailoring import TailoringService, get_tailoring_config


async def main():
    # Show current config
    config = get_tailoring_config()
    print("=== Tailoring Config ===")
    print(f"Provider: {config.llm_provider}")
    print(f"Model: {config.llm_model}")
    print(f"Base URL: {config.llm_base_url}")
    print()

    # Load real profile from YAML
    profile_path = Path("profiles/profile.yaml")
    with open(profile_path) as f:
        profile_data = yaml.safe_load(f)
    profile = UserProfile(**profile_data)
    print(f"=== Profile: {profile.name} ===")
    print(f"Title: {profile.current_title}")
    print(f"Skills: {', '.join(profile.skills[:5])}...")
    print()

    # Load real job from JSON
    jd_path = Path("artifacts/jd.json")
    with open(jd_path) as f:
        jd_data = json.load(f)
    job = JobDescription(**jd_data)
    print(f"=== Job: {job.role_title} at {job.company} ===")
    print(f"Location: {job.location}")
    print(f"Required: {', '.join(job.required_skills[:5])}...")
    print()

    print("=== Running Tailoring Pipeline ===")
    service = TailoringService()
    result = await service.tailor(profile, job)

    print(f"\nSuccess: {result.success}")
    if result.error:
        print(f"Error: {result.error}")
        return

    print("\n=== Results ===")
    print(f"Resume PDF: {result.resume_path}")
    print(f"Cover Letter PDF: {result.cover_letter_path}")

    if result.plan:
        print(f"\n=== Keyword Matches ({len(result.plan.keyword_matches)}) ===")
        for m in result.plan.keyword_matches:
            print(f"  - {m.job_keyword} -> {m.user_skill} ({m.confidence:.0%})")

        if result.plan.evidence_mappings:
            print(f"\n=== Evidence Mappings ({len(result.plan.evidence_mappings)}) ===")
            for e in result.plan.evidence_mappings[:3]:
                print(f"  - {e.requirement[:50]}...")
                print(f"    Evidence: {e.evidence[:50]}...")

    if result.cover_letter:
        print(f"\n=== Cover Letter ({result.cover_letter.word_count} words) ===")
        print(result.cover_letter.full_text[:500] + "...")

    if result.review_packet:
        print("\n=== Review Packet ===")
        print(f"Changes: {len(result.review_packet.changes_summary)} items")
        for change in result.review_packet.changes_summary[:3]:
            print(f"  - {change}")


if __name__ == "__main__":
    asyncio.run(main())
