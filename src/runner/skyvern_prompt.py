"""Prompt and schema builders for Skyvern-backed job application runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.extractor.models import JobDescription


def build_runner_prompt(
    *,
    job_url: str,
    job: JobDescription | None,
    profile: Any,
    resume_path: str | None,
    cover_letter_path: str | None,
    yolo_mode: bool,
    yolo_context: dict[str, Any] | None,
    auto_submit: bool,
) -> str:
    """Build a strict runner prompt for Skyvern task execution."""
    profile_summary = _profile_summary(profile)
    job_summary = _job_summary(job=job, yolo_context=yolo_context)
    upload_summary = _upload_summary(resume_path, cover_letter_path)
    yolo_section = _yolo_section(yolo_mode=yolo_mode, yolo_context=yolo_context)
    submit_mode = "enabled" if auto_submit else "disabled"

    return (
        "You are completing a real job application form.\n\n"
        f"Start URL: {job_url}\n\n"
        "Primary goal:\n"
        "- Navigate to the employer's apply flow and fill all required fields truthfully.\n"
        "- Upload the supplied resume and cover letter only in the correct fields.\n"
        "- Do not fabricate experience, qualifications, dates, compensation, or credentials.\n"
        "- Never attempt CAPTCHA/2FA bypass; if blocked by OTP/CAPTCHA, stop and report status=blocked.\n\n"
        f"Job targeting context:\n{job_summary}\n\n"
        f"Applicant profile summary:\n{profile_summary}\n\n"
        f"Available files:\n{upload_summary}\n\n"
        "Upload execution rules:\n"
        "- For every upload action, set action.file_url to one of the exact URLs above.\n"
        "- Do not only click Attach/Upload buttons without an upload file_url.\n\n"
        "Upload field disambiguation rules:\n"
        "- Resume/CV upload controls must use only the Resume file URL.\n"
        "- Never upload the cover letter PDF into Resume/CV upload controls.\n"
        "- Upload the cover letter PDF only when the control label/help text explicitly indicates cover letter or supporting document upload.\n"
        "- If no explicit cover-letter upload control exists, do not force a cover-letter upload.\n\n"
        "Field completion rules:\n"
        "- For required dropdowns/comboboxes, pick the closest truthful option if exact text is unavailable.\n"
        "- If a school/company/program value is missing, use 'Other' / 'Not listed' when available and continue.\n"
        "- Never loop repeatedly on a missing option; apply best-effort truthful fallback once and move on.\n\n"
        "Form completeness guardrails:\n"
        "- Do not mark the task complete immediately after identity fields or uploads.\n"
        "- Before complete/submit, scroll through the entire application form (including embedded iframes) and handle every required field marked with '*'.\n"
        "- Treat any required dropdown still showing 'Select...' as incomplete.\n"
        "- If any required field remains unanswered, continue filling instead of issuing complete.\n\n"
        "Answer quality rules:\n"
        "- For open-text responses about experience/projects/impact, tailor answers to this specific job using the job context and applicant history.\n"
        "- Prefer concrete, truthful examples (technologies, scope, outcomes) drawn from the applicant profile/work history.\n"
        "- Do not paste generic profile summaries; rewrite each answer to match the specific question and role requirements.\n"
        "- If a cover letter field is a text area/editor, write a tailored cover letter directly in that text field.\n"
        "- Use cover-letter PDF upload only for dedicated file-upload fields, not text fields.\n\n"
        f"YOLO mode: {'enabled' if yolo_mode else 'disabled'}\n"
        f"Auto-submit mode: {submit_mode}\n\n"
        f"{yolo_section}\n\n"
        "Submission policy:\n"
        "- Only submit if all required fields are complete and truthful.\n"
        "- If auto-submit is disabled, stop right before final submit with status=stopped_before_submit.\n"
        "- If auto-submit is enabled, proceed through final submit only when the form is complete.\n\n"
        "When unknown required questions appear:\n"
        "- If YOLO is disabled, stop with status=blocked and include the question text in errors.\n"
        "- If YOLO is enabled, answer using best effort from profile/job context. If still unknown, set status=blocked.\n\n"
        "At the end, produce result fields matching the provided extraction schema."
    )


def build_data_extraction_schema() -> dict[str, Any]:
    """Return extraction schema for normalized ApplicationRunResult mapping."""
    return {
        "type": "object",
        "properties": {
            "success": {
                "type": "boolean",
                "description": "True only if workflow reached a terminal acceptable outcome.",
            },
            "status": {
                "type": "string",
                "description": (
                    "One of: submitted, stopped_before_submit, failed, blocked, "
                    "skipped, duplicate_skipped."
                ),
            },
            "proof_text": {
                "type": "string",
                "description": "Visible confirmation text after submit if present.",
            },
            "final_url": {
                "type": "string",
                "description": "The final page URL where the run ended.",
            },
            "errors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Fatal or blocking issues.",
            },
            "notes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Non-fatal execution notes and caveats.",
            },
            "visited_urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Any URLs visited during execution that are available.",
            },
        },
        "required": ["status"],
    }


def build_workflow_data(
    *,
    prompt: str,
    job: JobDescription | None,
    profile: Any,
    resume_path: str | None,
    cover_letter_path: str | None,
) -> dict[str, Any]:
    """Build workflow input data for optional pre-defined Skyvern workflows."""
    payload: dict[str, Any] = {
        "prompt": prompt,
        "job_url": job.apply_url
        if job and job.apply_url
        else (job.job_url if job else None),
        "company": getattr(job, "company", None) if job else None,
        "role_title": getattr(job, "role_title", None) if job else None,
        "profile": _safe_profile_dict(profile),
        "resume_path": resume_path,
        "cover_letter_path": cover_letter_path,
    }
    return {k: v for k, v in payload.items() if v is not None}


def _profile_summary(profile: Any) -> str:
    if profile is None:
        return "- No profile provided."

    rows: list[str] = []
    for key, attr in (
        ("Full name", "name"),
        ("Email", "email"),
        ("Phone", "phone"),
        ("Location", "location"),
        ("LinkedIn", "linkedin_url"),
        ("GitHub", "github_url"),
    ):
        value = getattr(profile, attr, None)
        if value:
            rows.append(f"- {key}: {value}")

    skills = getattr(profile, "skills", None)
    if isinstance(skills, list) and skills:
        rows.append(f"- Skills: {', '.join(str(skill) for skill in skills[:20])}")

    years = getattr(profile, "years_of_experience", None)
    if years is not None:
        rows.append(f"- Years of experience: {years}")

    work_history = getattr(profile, "work_history", None)
    if isinstance(work_history, list):
        for item in work_history[:3]:
            if item is None:
                continue
            company = _safe_attr(item, "company")
            title = _safe_attr(item, "title")
            if not company and not title:
                continue
            descriptor = " / ".join(
                [part for part in (title, company) if part and part.strip()]
            )
            description = _safe_attr(item, "description")
            if description:
                description = _truncate_text(description, 180)
                rows.append(f"- Experience: {descriptor} — {description}")
            else:
                rows.append(f"- Experience: {descriptor}")

    if not rows:
        rows.append("- Profile available but key fields are empty.")
    return "\n".join(rows)


def _upload_summary(resume_path: str | None, cover_letter_path: str | None) -> str:
    rows: list[str] = []
    if resume_path:
        rows.append(f"- Resume: {_format_upload_reference(resume_path)}")
    if cover_letter_path:
        rows.append(f"- Cover letter: {_format_upload_reference(cover_letter_path)}")
    if not rows:
        rows.append("- No upload files provided.")
    return "\n".join(rows)


def _format_upload_reference(value: str) -> str:
    text = str(value).strip()
    if text.startswith(("http://", "https://", "file://")):
        return text
    return str(Path(text))


def _yolo_section(*, yolo_mode: bool, yolo_context: dict[str, Any] | None) -> str:
    if not yolo_mode:
        return "YOLO context: not provided."
    if not yolo_context:
        return "YOLO context: enabled but empty."
    return "YOLO context payload:\n" + json.dumps(yolo_context, indent=2, default=str)


def _safe_profile_dict(profile: Any) -> dict[str, Any]:
    if profile is None:
        return {}
    model_dump = getattr(profile, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="json")
    to_dict = getattr(profile, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    if hasattr(profile, "__dict__"):
        return {
            key: value
            for key, value in vars(profile).items()
            if not key.startswith("_")
        }
    return {"value": str(profile)}


def _job_summary(
    *,
    job: JobDescription | None,
    yolo_context: dict[str, Any] | None,
) -> str:
    payload = _resolve_job_payload(job=job, yolo_context=yolo_context)
    if not payload:
        return "- No structured job description provided."

    rows: list[str] = []
    for label, key in (
        ("Company", "company"),
        ("Role", "role_title"),
        ("Location", "location"),
        ("Employment type", "employment_type"),
        ("Work type", "work_type"),
        ("Education", "education"),
    ):
        value = payload.get(key)
        if value is not None and str(value).strip():
            rows.append(f"- {label}: {value}")

    for label, key in (
        ("Required skills", "required_skills"),
        ("Preferred skills", "preferred_skills"),
        ("Responsibilities", "responsibilities"),
        ("Qualifications", "qualifications"),
    ):
        value = payload.get(key)
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            if cleaned:
                rows.append(f"- {label}: {', '.join(cleaned[:10])}")

    description = payload.get("description")
    if description is not None and str(description).strip():
        rows.append(f"- Job summary: {_truncate_text(str(description), 600)}")

    if not rows:
        return "- Structured job object provided but key fields are empty."
    return "\n".join(rows)


def _resolve_job_payload(
    *,
    job: JobDescription | None,
    yolo_context: dict[str, Any] | None,
) -> dict[str, Any]:
    if job is not None:
        return job.model_dump(mode="json")
    if isinstance(yolo_context, dict):
        candidate = yolo_context.get("job")
        if isinstance(candidate, dict):
            return candidate
    return {}


def _safe_attr(item: Any, field: str) -> str | None:
    value = item.get(field) if isinstance(item, dict) else getattr(item, field, None)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _truncate_text(text: str, max_chars: int) -> str:
    value = str(text).strip()
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3].rstrip() + "..."
