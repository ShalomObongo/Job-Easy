from __future__ import annotations

from src.extractor.models import JobDescription
from src.runner.skyvern_prompt import build_runner_prompt


def test_build_runner_prompt_preserves_http_upload_reference() -> None:
    upload_url = "http://127.0.0.1:9999/files/token/resume.pdf"
    job = JobDescription(
        company="Example",
        role_title="Software Engineer",
        job_url="https://example.com/job",
    )
    prompt = build_runner_prompt(
        job_url="https://example.com/apply",
        job=job,
        profile=None,
        resume_path=upload_url,
        cover_letter_path=None,
        yolo_mode=False,
        yolo_context=None,
        auto_submit=False,
    )

    assert f"- Resume: {upload_url}" in prompt
    assert "http:/127.0.0.1" not in prompt


def test_build_runner_prompt_includes_cover_letter_disambiguation_rules() -> None:
    job = JobDescription(
        company="Example",
        role_title="Software Engineer",
        job_url="https://example.com/job",
    )
    prompt = build_runner_prompt(
        job_url="https://example.com/apply",
        job=job,
        profile=None,
        resume_path="http://127.0.0.1:9999/files/token/resume.pdf",
        cover_letter_path="http://127.0.0.1:9999/files/token/cover.pdf",
        yolo_mode=False,
        yolo_context=None,
        auto_submit=False,
    )

    assert "Never upload the cover letter PDF into Resume/CV upload controls." in prompt
    assert "If a cover letter field is a text area/editor" in prompt


def test_build_runner_prompt_uses_yolo_job_context_when_job_missing() -> None:
    prompt = build_runner_prompt(
        job_url="https://example.com/apply",
        job=None,
        profile=None,
        resume_path=None,
        cover_letter_path=None,
        yolo_mode=True,
        yolo_context={
            "job": {
                "company": "Turaco",
                "role_title": "Software Engineer",
                "required_skills": ["Java", "SQL"],
            }
        },
        auto_submit=False,
    )

    assert "Job targeting context:" in prompt
    assert "- Company: Turaco" in prompt
    assert "- Required skills: Java, SQL" in prompt


def test_build_runner_prompt_includes_full_form_completion_guardrails() -> None:
    job = JobDescription(
        company="Wave",
        role_title="Data Scientist",
        job_url="https://example.com/job",
    )
    prompt = build_runner_prompt(
        job_url="https://example.com/apply",
        job=job,
        profile=None,
        resume_path=None,
        cover_letter_path=None,
        yolo_mode=True,
        yolo_context={"job": {"company": "Wave", "role_title": "Data Scientist"}},
        auto_submit=True,
    )

    assert "Do not mark the task complete immediately after identity fields or uploads." in prompt
    assert "Treat any required dropdown still showing 'Select...' as incomplete." in prompt
