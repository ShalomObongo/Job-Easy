"""Prompt builders for LLM-based fit scoring."""

from __future__ import annotations

import json

from src.extractor.models import JobDescription
from src.scoring.config import ScoringConfig
from src.scoring.models import UserProfile

SCORING_LLM_SYSTEM_PROMPT = """You are a job-candidate fit scoring assistant.

You must follow these rules:
- Be truthful. Do NOT fabricate candidate skills, experience, education, or credentials.
- Only claim the candidate matches an item if it is supported by the provided UserProfile.
- If the job posting is missing key information (salary, location, visa policy, must-haves), record that as risk_flags.
- Output MUST be valid JSON only (no markdown), matching the required schema.
"""


def build_llm_fit_prompt(
    *,
    job: JobDescription,
    profile: UserProfile,
    config: ScoringConfig,
) -> str:
    """Build the user prompt for LLM-based fit scoring."""
    job_payload = job.model_dump(mode="json")
    profile_payload = profile.model_dump(mode="json")
    review_cutoff = max(0.0, config.fit_score_threshold - config.review_margin)

    return "\n".join(
        [
            "Evaluate the candidate's fit for the job.",
            "",
            "Scoring guidance:",
            "- Score range: 0.0 to 1.0",
            "- Recommendation buckets:",
            f"  - apply: score >= {config.fit_score_threshold:.2f}",
            (
                f"  - review: score >= {review_cutoff:.2f} and < "
                f"{config.fit_score_threshold:.2f}"
            ),
            "  - skip: score below review range",
            "",
            "Must-have/preferred extraction:",
            "- Prefer using job.required_skills/job.preferred_skills when present.",
            "- If those are empty, infer must-haves and preferences from job.qualifications/job.description.",
            "- Return must_have_matched/must_have_missing using concise strings.",
            "",
            "Return risk_flags for uncertainties such as:",
            "- visa_policy_unknown",
            "- salary_missing",
            "- location_missing",
            "- requirements_incomplete",
            "- missing_must_haves",
            "",
            "JobDescription (JSON):",
            json.dumps(job_payload, ensure_ascii=True),
            "",
            "UserProfile (JSON):",
            json.dumps(profile_payload, ensure_ascii=True),
        ]
    )
