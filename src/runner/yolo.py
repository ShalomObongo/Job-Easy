"""YOLO mode helpers for the application runner.

YOLO mode is an opt-in runner behavior that provides full job + user context to the
Browser Use agent so it can answer application questions best-effort without
prompting the user.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from src.extractor.models import JobDescription
from src.scoring.models import UserProfile

YOLO_CONTEXT_VERSION = 1

type QuestionCategory = Literal[
    "contact",
    "eligibility",
    "experience",
    "compensation",
    "motivation",
    "eeo",
    "other",
]

type FieldType = Literal[
    "text",
    "textarea",
    "select",
    "radio",
    "checkbox",
    "number",
    "unknown",
]

_WHITESPACE_RE = re.compile(r"\s+")


def classify_question(question: str) -> QuestionCategory:
    """Heuristic question classifier for YOLO mode scoping."""
    normalized = _WHITESPACE_RE.sub(" ", question.strip().lower())

    eeo_terms = (
        "voluntary self-identification",
        "gender",
        "race",
        "ethnicity",
        "veteran",
        "disability",
        "pronouns",
        "sexual orientation",
        "equal employment",
        "eeo",
    )
    if any(term in normalized for term in eeo_terms):
        return "eeo"

    motivation_terms = (
        "why do you want",
        "why are you interested",
        "why this company",
        "why this role",
        "why us",
        "why join",
        "why work",
        "what excites you",
        "cover letter",
        "tell us why",
        "what interests you",
    )
    if any(term in normalized for term in motivation_terms):
        return "motivation"

    compensation_terms = (
        "salary",
        "compensation",
        "expected pay",
        "desired pay",
        "pay range",
        "wage",
        "hourly",
        "rate",
        "bonus",
        "equity",
    )
    if any(term in normalized for term in compensation_terms):
        return "compensation"

    eligibility_terms = (
        "authorized to work",
        "work authorization",
        "legally authorized",
        "require sponsorship",
        "visa",
        "sponsorship",
        "relocate",
        "relocation",
        "start date",
        "notice period",
        "citizen",
        "citizenship",
        "security clearance",
    )
    if any(term in normalized for term in eligibility_terms):
        return "eligibility"

    contact_terms = (
        "first name",
        "last name",
        "full name",
        "email",
        "e-mail",
        "phone",
        "linkedin",
        "website",
        "portfolio",
        "address",
        "city",
        "state",
        "zip",
        "postal",
        "country",
    )
    if any(term in normalized for term in contact_terms):
        return "contact"

    experience_terms = (
        "years of experience",
        "experience with",
        "describe your experience",
        "proficient",
        "familiar with",
        "technologies",
        "skills",
        "tools",
        "framework",
        "programming language",
    )
    if any(term in normalized for term in experience_terms):
        return "experience"

    return "other"


def _truncate(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n[TRUNCATED]"


def build_yolo_context(
    *,
    job: JobDescription,
    profile: UserProfile,
    max_job_description_chars: int = 12000,
    max_profile_entry_description_chars: int = 4000,
) -> dict[str, Any]:
    """Build a JSON-serializable hybrid context payload for YOLO mode."""
    job_data = job.model_dump(mode="json")
    profile_data = profile.model_dump(mode="json")

    job_description = job_data.get("description")
    if isinstance(job_description, str):
        job_description = _truncate(job_description, max_job_description_chars)
    else:
        job_description = None

    work_history: list[dict[str, Any]] = []
    raw_history = profile_data.get("work_history")
    if isinstance(raw_history, list):
        for item in raw_history:
            if not isinstance(item, dict):
                continue
            description = item.get("description")
            if isinstance(description, str):
                item = dict(item)
                item["description"] = _truncate(
                    description,
                    max_profile_entry_description_chars,
                )
            work_history.append(item)

    return {
        "version": YOLO_CONTEXT_VERSION,
        "job": {
            "company": job_data.get("company"),
            "role_title": job_data.get("role_title"),
            "job_url": job_data.get("job_url"),
            "apply_url": job_data.get("apply_url"),
            "job_id": job_data.get("job_id"),
            "location": job_data.get("location"),
            "work_type": job_data.get("work_type"),
            "employment_type": job_data.get("employment_type"),
            "salary_min": job_data.get("salary_min"),
            "salary_max": job_data.get("salary_max"),
            "salary_currency": job_data.get("salary_currency"),
            "experience_years_min": job_data.get("experience_years_min"),
            "experience_years_max": job_data.get("experience_years_max"),
            "education": job_data.get("education"),
            "required_skills": job_data.get("required_skills", []),
            "preferred_skills": job_data.get("preferred_skills", []),
            "responsibilities": job_data.get("responsibilities", []),
            "qualifications": job_data.get("qualifications", []),
            "description": job_description,
            "extraction_source": job_data.get("extraction_source"),
            "extracted_at": job_data.get("extracted_at"),
        },
        "user": {
            "name": profile_data.get("name"),
            "email": profile_data.get("email"),
            "phone": profile_data.get("phone"),
            "location": profile_data.get("location"),
            "linkedin_url": profile_data.get("linkedin_url"),
            "skills": profile_data.get("skills", []),
            "years_of_experience": profile_data.get("years_of_experience"),
            "current_title": profile_data.get("current_title"),
            "summary": profile_data.get("summary"),
            "work_history": work_history,
            "education": profile_data.get("education", []),
            "certifications": profile_data.get("certifications", []),
            "preferences": {
                "work_type_preferences": profile_data.get("work_type_preferences", []),
                "target_locations": profile_data.get("target_locations"),
                "visa_sponsorship_needed": profile_data.get(
                    "visa_sponsorship_needed", False
                ),
                "min_salary": profile_data.get("min_salary"),
                "preferred_salary": profile_data.get("preferred_salary"),
                "salary_currency": profile_data.get("salary_currency"),
                "experience_level": profile_data.get("experience_level"),
            },
        },
    }


def _normalize_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value.strip().lower())


def choose_safe_option(options: list[str]) -> str | None:
    """Pick a safe option text from a list of UI options.

    Preference order:
    1) "Prefer not to say" / "Prefer not to disclose" variants
    2) "Decline to answer" variants
    3) "Other" variants
    """
    if not options:
        return None

    prefer_not_terms = (
        "prefer not to say",
        "prefer not to disclose",
        "prefer not to answer",
        "i prefer not to say",
        "i do not wish to answer",
        "decline to answer",
        "do not wish to answer",
    )

    for option in options:
        normalized = _normalize_text(option)
        if (
            any(term in normalized for term in prefer_not_terms)
            or "prefer not" in normalized
        ):
            return option
        if "decline" in normalized and "answer" in normalized:
            return option

    for option in options:
        normalized = _normalize_text(option)
        if (
            normalized == "other"
            or normalized.startswith("other ")
            or normalized.startswith("other/")
        ):
            return option

    return None


def _split_name(full_name: str) -> tuple[str | None, str | None]:
    parts = [p for p in full_name.strip().split() if p]
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def resolve_yolo_answer(
    question: str,
    *,
    yolo_context: dict[str, Any] | None,
    field_type: str | None = None,
    options: list[str] | None = None,
) -> tuple[str, str]:
    """Resolve a best-effort answer using the injected job+user context.

    Returns:
        (answer, category)
    """
    category = str(classify_question(question))
    normalized_q = _normalize_text(question)

    ctx = yolo_context if isinstance(yolo_context, dict) else {}
    job = ctx.get("job") if isinstance(ctx.get("job"), dict) else {}
    user = ctx.get("user") if isinstance(ctx.get("user"), dict) else {}
    preferences = (
        user.get("preferences") if isinstance(user.get("preferences"), dict) else {}
    )

    if category == "contact":
        full_name = str(user.get("name") or "").strip()
        first_name, last_name = _split_name(full_name)

        if "first name" in normalized_q:
            return (first_name or ""), category
        if "last name" in normalized_q or "surname" in normalized_q:
            return (last_name or ""), category
        if "full name" in normalized_q or normalized_q == "name":
            return (full_name or ""), category
        if "email" in normalized_q:
            return (str(user.get("email") or "").strip()), category
        if "phone" in normalized_q or "mobile" in normalized_q:
            return (str(user.get("phone") or "").strip()), category
        if "linkedin" in normalized_q:
            return (str(user.get("linkedin_url") or "").strip()), category
        if (
            "location" in normalized_q
            or "city" in normalized_q
            or "address" in normalized_q
        ):
            return (str(user.get("location") or "").strip()), category

        return "", category

    if category == "experience":
        if "years" in normalized_q and "experience" in normalized_q:
            value = user.get("years_of_experience")
            if isinstance(value, (int, float)):
                return str(int(value)), category
            return "", category

        current_title = str(user.get("current_title") or "").strip()
        if current_title and "current" in normalized_q and "title" in normalized_q:
            return current_title, category

        return "", category

    if category == "eligibility":
        sponsorship_needed = bool(preferences.get("visa_sponsorship_needed", False))
        if (
            "sponsor" in normalized_q
            or "sponsorship" in normalized_q
            or "visa" in normalized_q
        ):
            return ("Yes" if sponsorship_needed else "No"), category
        if "authorized" in normalized_q and "work" in normalized_q:
            # Best-effort default. If the profile doesn't explicitly say otherwise,
            # we assume the user is authorized to work.
            return "Yes", category
        return "", category

    if category == "compensation":
        value = preferences.get("preferred_salary")
        if not isinstance(value, (int, float)):
            value = preferences.get("min_salary")
        if not isinstance(value, (int, float)):
            value = job.get("salary_min")
        if isinstance(value, (int, float)):
            return str(int(value)), category
        return "", category

    if category == "eeo":
        if options:
            safe = choose_safe_option(options)
            if safe is not None:
                return safe, category
        return "", category

    if category == "motivation":
        company = str(job.get("company") or "").strip()
        role = str(job.get("role_title") or "").strip()
        required_skills = (
            job.get("required_skills")
            if isinstance(job.get("required_skills"), list)
            else []
        )
        user_skills = user.get("skills") if isinstance(user.get("skills"), list) else []

        req = [str(s).strip() for s in required_skills if str(s).strip()][:3]
        have = [str(s).strip() for s in user_skills if str(s).strip()]
        matched = [
            s for s in have if _normalize_text(s) in {_normalize_text(r) for r in req}
        ]

        skills_phrase = ", ".join(matched or req)
        if not skills_phrase:
            skills_phrase = "the role's requirements"

        return (
            (
                f"I'm excited about the {role or 'role'} at {company or 'your company'} "
                f"because it aligns with my background in {skills_phrase}. "
                "In my recent work, I've built and supported production systems, and I enjoy "
                "shipping practical improvements for users. "
                "I'm looking forward to bringing that experience to this position and continuing to grow."
            ),
            category,
        )

    # Fallback for unknown categories
    if options:
        safe = choose_safe_option(options)
        if safe is not None:
            return safe, category

    normalized_field = _normalize_text(field_type or "")
    if normalized_field in {"text", "textarea"}:
        return "N/A", category
    return "", category
