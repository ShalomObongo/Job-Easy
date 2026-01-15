"""Integration tests for scoring end-to-end flow."""

from __future__ import annotations

from pathlib import Path


def test_scoring_integration_apply_recommendation():
    """Should produce an apply recommendation for a strong match."""
    from src.extractor.models import JobDescription
    from src.scoring.config import ScoringConfig
    from src.scoring.profile import ProfileService
    from src.scoring.service import FitScoringService

    repo_root = Path(__file__).resolve().parents[3]
    profile_path = repo_root / "profiles" / "profile.example.yaml"

    config = ScoringConfig(_env_file=None, fit_score_threshold=0.75, review_margin=0.05)
    profile = ProfileService(config=config).load_profile(profile_path)

    job = JobDescription(
        company="ExampleCo",
        role_title="Software Engineer",
        job_url="https://example.com/jobs/123",
        required_skills=["Python", "SQL"],
        preferred_skills=["AWS"],
        experience_years_min=3,
        experience_years_max=6,
        education="Bachelor's",
        work_type="remote",
        salary_min=130000,
        salary_max=160000,
        salary_currency="USD",
    )

    result = FitScoringService(config=config).evaluate(job, profile)

    assert result.recommendation == "apply"
    assert result.fit_score.total_score >= config.fit_score_threshold
    assert result.constraints.passed is True


def test_scoring_integration_skip_recommendation():
    """Should produce a skip recommendation for a poor match."""
    from src.extractor.models import JobDescription
    from src.scoring.config import ScoringConfig
    from src.scoring.profile import ProfileService
    from src.scoring.service import FitScoringService

    repo_root = Path(__file__).resolve().parents[3]
    profile_path = repo_root / "profiles" / "profile.example.yaml"

    config = ScoringConfig(_env_file=None, fit_score_threshold=0.75, review_margin=0.05)
    profile = ProfileService(config=config).load_profile(profile_path)

    job = JobDescription(
        company="ExampleCo",
        role_title="Software Engineer",
        job_url="https://example.com/jobs/456",
        required_skills=["Java"],
        preferred_skills=[],
        work_type="remote",
    )

    result = FitScoringService(config=config).evaluate(job, profile)

    assert result.recommendation == "skip"
    assert result.fit_score.total_score < config.fit_score_threshold
