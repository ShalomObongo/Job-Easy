from __future__ import annotations

from datetime import date

from src.extractor.models import JobDescription
from src.runner.yolo import build_yolo_context, choose_safe_option, resolve_yolo_answer
from src.scoring.models import Education, UserProfile, WorkExperience


def _context() -> dict:
    job = JobDescription(
        company="ACME",
        role_title="Engineer",
        job_url="https://example.com/jobs/1",
        description="We build things.",
        required_skills=["python", "sql"],
    )
    profile = UserProfile(
        name="Jane Doe",
        email="jane@example.com",
        phone="555-555-5555",
        location="NYC",
        linkedin_url="https://linkedin.com/in/jane",
        github_url="https://github.com/jane",
        skills=["python", "linux"],
        years_of_experience=5,
        preferred_salary=65000,
        work_history=[
            WorkExperience(
                company="Widgets Inc",
                title="Developer",
                start_date=date(2020, 1, 1),
                end_date=None,
                description="Built internal tools.",
                skills_used=["python"],
            )
        ],
        education=[
            Education(
                institution="Example University",
                degree="Bachelor's",
                field="Computer Science",
                graduation_year=2020,
            )
        ],
    )
    return build_yolo_context(job=job, profile=profile)


def test_choose_safe_option_prefers_prefer_not_to_say() -> None:
    options = ["Female", "Male", "Prefer not to say", "Other"]
    assert choose_safe_option(options) == "Prefer not to say"


def test_choose_safe_option_falls_back_to_other() -> None:
    options = ["Option A", "Other"]
    assert choose_safe_option(options) == "Other"


def test_resolve_yolo_answer_returns_contact_email() -> None:
    ctx = _context()
    answer, category = resolve_yolo_answer(
        "What is your email?",
        yolo_context=ctx,
        field_type="text",
        options=None,
    )

    assert category == "contact"
    assert answer == "jane@example.com"


def test_resolve_yolo_answer_returns_contact_github_url() -> None:
    ctx = _context()
    answer, category = resolve_yolo_answer(
        "GitHub profile URL",
        yolo_context=ctx,
        field_type="text",
        options=None,
    )

    assert category == "contact"
    assert answer == "https://github.com/jane"


def test_resolve_yolo_answer_for_eeo_selects_prefer_not_to_say() -> None:
    ctx = _context()
    answer, category = resolve_yolo_answer(
        "What is your gender?",
        yolo_context=ctx,
        field_type="select",
        options=["Female", "Male", "Prefer not to say"],
    )

    assert category == "eeo"
    assert answer == "Prefer not to say"


def test_resolve_yolo_answer_for_motivation_includes_company_and_role() -> None:
    ctx = _context()
    answer, category = resolve_yolo_answer(
        "Why do you want to work here?",
        yolo_context=ctx,
        field_type="textarea",
        options=None,
    )

    assert category == "motivation"
    assert "ACME" in answer
    assert "Engineer" in answer


def test_resolve_yolo_answer_for_compensation_selects_salary_range_option() -> None:
    ctx = _context()
    answer, category = resolve_yolo_answer(
        "What is your desired salary range?",
        yolo_context=ctx,
        field_type="select",
        options=["$50,000 - $60,000", "$60,000 - $70,000", "$70,000 - $80,000"],
    )

    assert category == "compensation"
    assert answer == "$60,000 - $70,000"


def test_resolve_yolo_answer_for_education_selects_best_matching_option() -> None:
    ctx = _context()
    answer, category = resolve_yolo_answer(
        "What is your highest level of education?",
        yolo_context=ctx,
        field_type="select",
        options=[
            "High school",
            "Bachelor's degree",
            "Master's degree",
            "PhD",
        ],
    )

    assert category == "education"
    assert answer == "Bachelor's degree"
