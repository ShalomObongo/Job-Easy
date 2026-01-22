from __future__ import annotations

from datetime import date

from src.extractor.models import JobDescription
from src.runner.yolo import build_yolo_context, classify_question
from src.scoring.models import UserProfile, WorkExperience


def test_build_yolo_context_includes_job_and_user_fields() -> None:
    job = JobDescription(
        company="ACME",
        role_title="Engineer",
        job_url="https://example.com/jobs/1",
        description="We build things.",
        required_skills=["python"],
    )
    profile = UserProfile(
        name="Jane Doe",
        email="jane@example.com",
        location="NYC",
        skills=["python"],
        years_of_experience=5,
        work_history=[
            WorkExperience(
                company="ACME",
                title="Dev",
                start_date=date(2020, 1, 1),
                end_date=None,
                description="Did work.",
                skills_used=["python"],
            )
        ],
    )

    ctx = build_yolo_context(job=job, profile=profile)

    assert ctx["job"]["company"] == "ACME"
    assert ctx["job"]["role_title"] == "Engineer"
    assert ctx["user"]["name"] == "Jane Doe"
    assert ctx["user"]["years_of_experience"] == 5
    assert ctx["user"]["work_history"][0]["company"] == "ACME"


def test_build_yolo_context_truncates_long_job_description() -> None:
    long_text = "x" * 100
    job = JobDescription(
        company="ACME",
        role_title="Engineer",
        job_url="https://example.com/jobs/1",
        description=long_text,
    )
    profile = UserProfile(
        name="Jane Doe",
        email="jane@example.com",
        location="NYC",
        skills=["python"],
        years_of_experience=5,
    )

    ctx = build_yolo_context(job=job, profile=profile, max_job_description_chars=10)
    assert ctx["job"]["description"].startswith("x" * 10)
    assert "[TRUNCATED]" in ctx["job"]["description"]


def test_classify_question_categories() -> None:
    assert classify_question("What is your email?") == "contact"
    assert (
        classify_question("Will you now or in the future require sponsorship?")
        == "eligibility"
    )
    assert classify_question(
        "How many years of experience do you have with Python?"
    ) == ("experience")
    assert classify_question("What are your salary expectations?") == "compensation"
    assert classify_question("Why do you want to work here?") == "motivation"
    assert classify_question("What is your gender?") == "eeo"
