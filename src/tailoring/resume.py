"""Resume Tailoring Engine.

Transforms a user profile into a tailored resume based on a tailoring plan,
rewriting bullets to integrate keywords while maintaining truthfulness.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

from src.tailoring.config import TailoringConfig, get_tailoring_config
from src.tailoring.llm import LLMError, TailoringLLM
from src.tailoring.models import (
    TailoredBullet,
    TailoredResume,
    TailoredSection,
    TailoringPlan,
)

if TYPE_CHECKING:
    from src.extractor.models import JobDescription
    from src.scoring.models import UserProfile
    from src.tailoring.models import TailoringPlan

logger = logging.getLogger(__name__)

_ALLOWED_SECTION_NAMES = {"experience", "skills", "projects", "education", "certifications"}
_SECTION_TITLE_BY_NAME = {
    "experience": "Professional Experience",
    "skills": "Technical Skills",
    "projects": "Projects",
    "education": "Education",
    "certifications": "Certifications",
}


class TailoredBulletLLM(BaseModel):
    """LLM response structure for a tailored bullet.

    Some models return bullets as plain strings; accept and normalize them.
    """

    text: str = Field(..., description="Bullet point text")
    keywords_used: list[str] = Field(
        default_factory=list, description="Tailored bullet points"
    )

    @model_validator(mode="before")
    @classmethod
    def coerce_from_string(cls, data: object) -> object:
        if isinstance(data, str):
            return {"text": data}
        if isinstance(data, dict) and "text" not in data:
            if "bullet" in data:
                return {"text": data.get("bullet"), "keywords_used": data.get("keywords_used", [])}
            if "value" in data:
                return {"text": data.get("value"), "keywords_used": data.get("keywords_used", [])}
        return data


class TailoredSectionLLM(BaseModel):
    """LLM response structure for a tailored section.

    Some providers return slightly different keys (e.g., "type" instead of "name",
    or lists for "content"). Accept common variants and normalize them.
    """

    name: str = Field(
        ...,
        description="Section identifier",
        validation_alias=AliasChoices("name", "type"),
    )
    title: str = Field(
        ...,
        description="Display title",
        validation_alias=AliasChoices("title", "section_title", "sectionTitle"),
    )
    content: str = Field(default="", description="Section content if not bullet-based")
    bullets: list[TailoredBulletLLM] = Field(
        default_factory=list, description="Tailored bullet points"
    )

    @field_validator("content", mode="before")
    @classmethod
    def coerce_content_to_string(cls, v: object) -> str:
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        if isinstance(v, list):
            parts = [str(item).strip() for item in v if str(item).strip()]
            return "\n".join(parts)
        return str(v)

    @model_validator(mode="before")
    @classmethod
    def move_experience_list_content_to_bullets(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        raw_name = data.get("name") or data.get("type") or ""
        name_lower = str(raw_name).strip().lower()
        content = data.get("content")
        bullets = data.get("bullets")

        if bullets in (None, ""):
            bullets = []

        if isinstance(content, list) and not bullets:
            if "experience" in name_lower or "work" in name_lower:
                data["bullets"] = content
                data["content"] = ""

        return data


class TailoredResumeLLMResponse(BaseModel):
    """LLM response structure for tailored resume."""

    summary: str = Field(..., description="Tailored professional summary")
    sections: list[TailoredSectionLLM] = Field(
        default_factory=list, description="Resume sections in order"
    )
    keywords_used: list[str] = Field(
        default_factory=list, description="Keywords integrated throughout"
    )


RESUME_SYSTEM_PROMPT = """You are an expert resume writer. Your job is to transform a candidate's profile into a tailored resume optimized for a specific job.

You MUST return ONLY valid JSON matching the provided schema. No markdown, no code fences, no commentary.

Return an INSTANCE of the schema (actual resume data), NOT a JSON schema.

GOAL
- Create a high-quality, ATS-friendly resume tailored to the target job.
- Aim for a 1-page resume (2 pages max) by being selective and concise.

CRITICAL RULES:
- NEVER fabricate experience, skills, or accomplishments
- Only rephrase and reorder EXISTING content from the profile
- You can emphasize relevant aspects but cannot invent new ones
- Keep all factual claims (dates, companies, titles, metrics) exactly as provided
- Integrate keywords naturally - don't just add them as prefixes

OUTPUT RULES
- Use the `summary` field for the professional summary. Do NOT create a separate summary section in `sections`.
- `sections` must be an ordered list of objects with keys: name, title, content, bullets.
- `sections[].name` must be one of: experience, skills, projects, education, certifications.
- Use professional section titles: Professional Experience, Technical Skills, Projects, Education, Certifications.
- Do not add filler sections like “Technical Tools / Platforms”. Put tools under Skills instead.
- Do not output empty bullets or placeholder text.

SUMMARY
- 2–3 sentences.
- Specific to the target role and required skills.
- Do not mention the company name; keep it role/skill focused.

EXPERIENCE (STRICT FORMAT — REQUIRED)
We render job headers from bullet prefixes. Every experience bullet MUST start with:
`{ROLE}, {COMPANY} ({START} – {END}) — `
- Use END="Present" if the role is current.
- Then write ONE accomplishment sentence (optional second sentence). Do not cram multiple accomplishments with semicolons.
- Pick 4+ (if not all) of the most relevant roles from the profile (or fewer if there is experience that is completely unnecessary. Otherwise dont leave any out).
- 2–4 bullets per role (total experience bullets <= 10).
- Each bullet should be: action verb + scope + tech + measurable outcome (ONLY if the profile provides a number).
- Do not claim CI/CD, unit tests, MongoDB, etc. unless explicitly supported by the profile text.

PROJECTS
- 1–3 bullets total.
- Format: `{PROJECT} — {what you built + tech + outcome}.`

SKILLS
- Use `content` as labeled lines, no paragraphs:
  - Example: `Frontend: React, Next.js, JavaScript, HTML, CSS`
  - Example: `Backend: Node.js, Express`
- 3–6 lines max.
- For skills: set `bullets` to [].

EDUCATION / CERTIFICATIONS
- Use `content` as one item per line, concise.
- For education/certifications: set `bullets` to [].

KEYWORDS_USED
- Return only keywords that actually appear in the summary/sections you wrote.

"""


class ResumeTailoringService:
    """Service for generating tailored resumes.

    Takes a user profile and tailoring plan to produce a resume
    optimized for the target job with integrated keywords.
    """

    def __init__(self, config: TailoringConfig | None = None):
        """Initialize the resume tailoring service.

        Args:
            config: Optional TailoringConfig. Uses global config if not provided.
        """
        self.config = config or get_tailoring_config()
        self.llm = TailoringLLM(config=self.config)

    def _experience_bullet_has_required_prefix(self, text: str) -> bool:
        dash = r"[—–-]"
        patterns = [
            rf"^[^,\n]+,\s*[^()]+?\s*\([^)]+\)\s*{dash}\s*.+$",
        ]
        text = text.strip()
        return any(re.match(p, text) for p in patterns)

    def _parse_experience_bullet_header(self, text: str) -> tuple[str, str] | None:
        parsed = self._parse_experience_bullet_components(text)
        if parsed is None:
            return None
        return parsed["role"], parsed["company"]

    def _parse_experience_bullet_components(self, text: str) -> dict[str, str] | None:
        text = text.strip()
        dash = r"[—–-]"
        patterns = [
            rf"^(?P<role>[^,\n]+),\s*(?P<company>[^()]+?)\s*\((?P<dates>[^)]+)\)\s*(?:{dash}|:)\s*(?P<body>.+)$",
            rf"^(?P<role>[^()\n]+?)\s*{dash}\s*(?P<company>[^()]+?)\s*\((?P<dates>[^)]+)\)\s*(?:{dash}|:)\s*(?P<body>.+)$",
        ]
        for pattern in patterns:
            match = re.match(pattern, text)
            if not match:
                continue

            role = match.group("role").strip()
            company = match.group("company").strip()
            dates = match.group("dates").strip()
            body = match.group("body").strip()
            if not role or not company or not dates or not body:
                continue

            return {"role": role, "company": company, "dates": dates, "body": body}

        return None

    def _collect_resume_validation_issues(
        self,
        response: TailoredResumeLLMResponse,
        profile: UserProfile,
        plan: TailoringPlan,
    ) -> list[str]:
        issues: list[str] = []

        experience_section = next(
            (s for s in response.sections if s.name.strip().lower() == "experience"),
            None,
        )
        projects_section = next(
            (s for s in response.sections if s.name.strip().lower() == "projects"),
            None,
        )

        if profile.work_history and experience_section is None:
            issues.append("Missing required experience section.")

        if experience_section is not None:
            if not experience_section.bullets:
                issues.append("Experience section must contain bullets.")
            else:
                # All experience bullets must follow the strict prefix format.
                bad_prefixes = [
                    b.text
                    for b in experience_section.bullets
                    if not self._experience_bullet_has_required_prefix(b.text)
                ]
                if bad_prefixes:
                    sample = "; ".join(t[:80] for t in bad_prefixes[:3])
                    issues.append(
                        "All experience bullets must start with "
                        "`ROLE, COMPANY (START – END) — `. "
                        f"Invalid examples: {sample}"
                    )

                per_role: dict[tuple[str, str], int] = {}
                for bullet in experience_section.bullets:
                    parsed = self._parse_experience_bullet_header(bullet.text)
                    if parsed is None:
                        # Already reported above; keep parsing issues actionable.
                        continue
                    per_role[parsed] = per_role.get(parsed, 0) + 1

                if per_role:
                    if len(per_role) > 5:
                        issues.append(
                            f"Include at most 5 roles in experience (got {len(per_role)})."
                        )

                    total_bullets = len(experience_section.bullets)
                    if total_bullets > 10:
                        issues.append(
                            f"Experience must have <= 10 bullets total (got {total_bullets})."
                        )

                    for (role, company), count in sorted(
                        per_role.items(), key=lambda x: (-x[1], x[0][0])
                    ):
                        if count < 2 or count > 4:
                            issues.append(
                                f"Experience role '{role}' at '{company}' must have 2–4 bullets (got {count})."
                            )
                else:
                    issues.append(
                        "Could not parse experience bullet headers. "
                        "Ensure each bullet begins with `ROLE, COMPANY (START – END) — `."
                    )

        if projects_section is not None:
            bullet_count = len(projects_section.bullets)
            if bullet_count < 1 or bullet_count > 3:
                issues.append(
                    f"Projects section must have 1–3 bullets total (got {bullet_count})."
                )

        # If the plan expects a projects section, enforce it exists with bullets.
        plan_order = [str(s).strip().lower() for s in (plan.section_order or [])]
        if "projects" in plan_order:
            if projects_section is None:
                issues.append("Plan requests a projects section, but none was produced.")
            elif not projects_section.bullets:
                issues.append("Projects section must include 1–3 bullets.")

        return issues

    def _apply_strict_postprocessing(
        self,
        response: TailoredResumeLLMResponse,
        profile: UserProfile,
        plan: TailoringPlan,
    ) -> TailoredResumeLLMResponse:
        """Apply strict, non-fabricating cleanup so rendering rules are met.

        This is a last-resort safety net: it may drop roles with too-few bullets
        instead of inventing new accomplishments.
        """
        response = self._normalize_resume_response(response, plan, profile)

        experience_section = next(
            (s for s in response.sections if s.name.strip().lower() == "experience"),
            None,
        )
        if experience_section is not None and experience_section.bullets:
            role_order: list[tuple[str, str]] = []
            role_dates: dict[tuple[str, str], str] = {}
            role_bodies: dict[tuple[str, str], list[str]] = {}

            for bullet in experience_section.bullets:
                parsed = self._parse_experience_bullet_components(bullet.text)
                if parsed is None:
                    continue

                key = (parsed["role"], parsed["company"])
                if key not in role_bodies:
                    role_bodies[key] = []
                    role_order.append(key)
                    role_dates[key] = parsed["dates"]
                role_bodies[key].append(parsed["body"])

            cleaned_bullets: list[TailoredBulletLLM] = []
            roles_kept = 0
            for role_company in role_order:
                if roles_kept >= 5:
                    break

                bodies = role_bodies.get(role_company, [])
                if len(bodies) < 2:
                    continue

                dates = role_dates.get(role_company, "")
                role, company = role_company

                for body in bodies[:4]:
                    cleaned_bullets.append(
                        TailoredBulletLLM(
                            text=f"{role}, {company} ({dates}) — {body}".strip()
                        )
                    )

                roles_kept += 1

            experience_section.bullets = cleaned_bullets[:10]

        projects_section = next(
            (s for s in response.sections if s.name.strip().lower() == "projects"),
            None,
        )
        if projects_section is not None:
            if len(projects_section.bullets) > 3:
                projects_section.bullets = projects_section.bullets[:3]
            elif len(projects_section.bullets) < 1:
                response.sections = [s for s in response.sections if s is not projects_section]

        return response

    def _resume_output_is_acceptable(
        self, response: TailoredResumeLLMResponse, profile: UserProfile
    ) -> bool:
        # Backwards-compatible wrapper used in tests/other callers.
        empty_plan = TailoringPlan(
            job_url="",
            company="",
            role_title="",
            keyword_matches=[],
            evidence_mappings=[],
            section_order=[],
            bullet_rewrites=[],
            unsupported_claims=[],
        )
        return not self._collect_resume_validation_issues(
            response=response,
            profile=profile,
            plan=empty_plan,
        )

    async def tailor_resume(
        self,
        profile: UserProfile,
        job: JobDescription,
        plan: TailoringPlan,
    ) -> TailoredResume:
        """Generate a tailored resume for a job application.

        Args:
            profile: User's profile with skills and experience.
            job: Job description to tailor for.
            plan: Tailoring plan with keyword matches and evidence mappings.

        Returns:
            TailoredResume ready for rendering.
        """
        logger.info(f"Tailoring resume for {job.company} - {job.role_title}")

        # Generate the tailored resume using LLM
        resume = await self._generate_resume_with_llm(profile, job, plan)

        logger.info(
            f"Generated tailored resume with {len(resume.sections)} sections, "
            f"{len(resume.keywords_used)} keywords"
        )

        return resume

    async def _generate_resume_with_llm(
        self,
        profile: UserProfile,
        job: JobDescription,
        plan: TailoringPlan,
    ) -> TailoredResume:
        """Generate the tailored resume using LLM.

        Args:
            profile: User's profile.
            job: Job description.
            plan: Tailoring plan.

        Returns:
            TailoredResume generated by LLM.
        """
        base_prompt = self._build_prompt(profile, job, plan)
        prompt = base_prompt
        response: TailoredResumeLLMResponse | None = None

        for attempt in range(4):
            try:
                response = await self.llm.generate_structured(
                    prompt=prompt,
                    output_model=TailoredResumeLLMResponse,
                    system_prompt=RESUME_SYSTEM_PROMPT,
                )
            except LLMError as e:
                if attempt >= 2:
                    raise
                prompt = f"""{base_prompt}

---

# REVISION REQUEST (SCHEMA FIX)

Your previous response did not match the required JSON schema.
Return ONLY a JSON object with keys: summary, sections, keywords_used.

Requirements:
- `summary`: string (2–3 sentences).
- `sections`: array of section objects with keys: name, title, content, bullets.
- `sections[].name` must be one of: experience, skills, projects, education, certifications.
- `sections[].content` must be a string (use newline separators for multi-line content).
- `sections[].bullets` must be an array (for experience/projects) or [] (skills/education/certifications).

Error was: {e}
"""
                continue

            response = self._normalize_resume_response(response, plan, profile)
            issues = self._collect_resume_validation_issues(
                response=response, profile=profile, plan=plan
            )
            if not issues:
                break

            prompt = f"""{base_prompt}

---

# REVISION REQUEST (FORMAT + STRUCTURE FIXES)

The JSON was valid but it violates required resume structure rules. Fix ONLY formatting/structure (do not add new facts).

Required fixes:
- Ensure there is an Experience section.
- Every Experience bullet MUST start with: `ROLE, COMPANY (START – END) — ` (END can be Present).
- Every role in Experience MUST have 2–4 bullets. If you cannot produce >=2 truthful bullets for a role, REMOVE that role entirely.
- Total Experience bullets <= 10.
- Projects section (if present) MUST have 1–3 bullets total (format: `{{PROJECT}} — ...`).
- Avoid semicolons; no empty bullets; do not invent facts.

Detected violations:
{chr(10).join(f"- {issue}" for issue in issues[:12])}

## Previous JSON (revise this)
{response.model_dump_json(indent=2)}
"""

        if response is None:
            raise RuntimeError("Resume generation failed unexpectedly.")

        response = self._normalize_resume_response(response, plan, profile)
        issues = self._collect_resume_validation_issues(
            response=response, profile=profile, plan=plan
        )
        if issues:
            response = self._apply_strict_postprocessing(response, profile, plan)
            issues = self._collect_resume_validation_issues(
                response=response, profile=profile, plan=plan
            )
        if issues:
            raise RuntimeError(
                "Resume generation did not meet required structure after revisions: "
                + "; ".join(issues[:8])
            )

        # Convert LLM response to TailoredResume with contact info from profile
        return TailoredResume(
            name=profile.name,
            email=profile.email,
            phone=profile.phone,
            location=profile.location,
            linkedin_url=profile.linkedin_url,
            summary=response.summary,
            sections=[
                TailoredSection(
                    name=s.name,
                    title=s.title,
                    content=s.content,
                    bullets=[TailoredBullet(text=b.text, keywords_used=b.keywords_used) for b in s.bullets],
                )
                for s in response.sections
            ],
            keywords_used=response.keywords_used,
            target_job_url=job.job_url,
            target_company=job.company,
            target_role=job.role_title,
        )

    def _normalize_resume_response(
        self,
        response: TailoredResumeLLMResponse,
        plan: TailoringPlan,
        profile: UserProfile,
    ) -> TailoredResumeLLMResponse:
        def canonical_section_name(value: str) -> str:
            name = re.sub(r"[^a-z]+", " ", str(value).strip().lower()).strip()
            if name in _ALLOWED_SECTION_NAMES:
                return name
            if "experience" in name or "work" in name:
                return "experience"
            if "skill" in name:
                return "skills"
            if "project" in name:
                return "projects"
            if "education" in name:
                return "education"
            if "cert" in name or "training" in name:
                return "certifications"
            return name

        normalized_by_name: dict[str, TailoredSectionLLM] = {}
        for section in response.sections:
            name = canonical_section_name(section.name)
            if name not in _ALLOWED_SECTION_NAMES:
                continue

            title = _SECTION_TITLE_BY_NAME.get(name, section.title)
            content = (section.content or "").strip()
            bullets = [
                TailoredBulletLLM(text=b.text.strip(), keywords_used=b.keywords_used or [])
                for b in section.bullets
                if b.text and b.text.strip()
            ]

            # Enforce section-specific structure.
            if name in {"experience", "projects"}:
                if not bullets and content:
                    lines = [
                        re.sub(r"^[\s•\-\*]+", "", line).strip()
                        for line in content.splitlines()
                        if line.strip()
                    ]
                    if lines:
                        bullets = [TailoredBulletLLM(text=line) for line in lines]
                        content = ""
                content = ""
            else:
                if not content and bullets:
                    content = "\n".join(b.text for b in bullets)
                bullets = []

            normalized_by_name[name] = TailoredSectionLLM(
                name=name,
                title=title,
                content=content,
                bullets=bullets,
            )

        plan_order = [
            canonical_section_name(s)
            for s in getattr(plan, "section_order", []) or []
            if canonical_section_name(s) in _ALLOWED_SECTION_NAMES
        ]
        default_order = ["experience", "skills", "projects", "education", "certifications"]
        order = plan_order or default_order

        ordered_sections: list[TailoredSectionLLM] = []
        for name in order:
            section = normalized_by_name.get(name)
            if section is not None:
                ordered_sections.append(section)
        for name, section in normalized_by_name.items():
            if name not in {s.name for s in ordered_sections}:
                ordered_sections.append(section)

        # Ensure we have an experience section if the profile has work history.
        if profile.work_history and "experience" not in normalized_by_name:
            ordered_sections.insert(
                0,
                TailoredSectionLLM(
                    name="experience",
                    title=_SECTION_TITLE_BY_NAME["experience"],
                    content="",
                    bullets=[],
                ),
            )

        response.sections = ordered_sections
        return response

    def _build_prompt(
        self,
        profile: UserProfile,
        job: JobDescription,
        plan: TailoringPlan,
    ) -> str:
        """Build the prompt for resume tailoring.

        Args:
            profile: User's profile.
            job: Job description.
            plan: Tailoring plan.

        Returns:
            Formatted prompt string.
        """
        # Format work history
        work_history_text = ""
        for exp in profile.work_history:
            end = exp.end_date or "Present"
            work_history_text += f"""
### {exp.title} at {exp.company}
**Dates:** {exp.start_date} - {end}
**Description:** {exp.description}
**Skills Used:** {", ".join(exp.skills_used)}
"""

        # Format education
        education_text = ""
        for edu in profile.education:
            grad = f" ({edu.graduation_year})" if edu.graduation_year else ""
            education_text += (
                f"- {edu.degree} in {edu.field} from {edu.institution}{grad}\n"
            )

        # Format certifications / training
        certifications_text = ""
        for cert in getattr(profile, "certifications", []):
            issuer = f" — {cert.issuer}" if getattr(cert, "issuer", None) else ""
            date_awarded = (
                f" ({cert.date_awarded})" if getattr(cert, "date_awarded", None) else ""
            )
            url = f" — {cert.url}" if getattr(cert, "url", None) else ""
            certifications_text += f"- {cert.name}{issuer}{date_awarded}{url}\n"

        # Format keyword matches from plan
        keywords_text = ", ".join(
            f"{m.job_keyword} (matched to: {m.user_skill})"
            for m in plan.keyword_matches[:10]  # Top 10 keywords
        )

        # Format section order
        section_order = [
            s for s in (plan.section_order or []) if str(s).strip().lower() != "summary"
        ]
        section_order_text = " -> ".join(section_order)

        # Format evidence mappings
        evidence_text = ""
        for mapping in plan.evidence_mappings[:5]:  # Top 5 evidence items
            evidence_text += f"- {mapping.requirement}: {mapping.evidence} (from {mapping.source_company})\n"

        prompt = f"""# TARGET JOB

**Company:** {job.company}
**Role:** {job.role_title}
**Required Skills:** {", ".join(job.required_skills) if job.required_skills else "Not specified"}
**Preferred Skills:** {", ".join(job.preferred_skills) if job.preferred_skills else "None"}

---

# CANDIDATE PROFILE

**Name:** {profile.name}
**Current Title:** {profile.current_title}
**Location:** {profile.location}
**Years of Experience:** {profile.years_of_experience}

## Original Summary
{profile.summary}

## Skills
{", ".join(profile.skills)}

## Work History (to be rewritten with keywords)
{work_history_text}

## Education
{education_text or "Not specified"}

## Certifications / Training
{certifications_text or "Not specified"}

---

# TAILORING PLAN

## Keywords to Integrate
{keywords_text or "Use skills from job requirements"}

## Section Order
{section_order_text or "experience -> skills -> projects -> education -> certifications"}

## Key Evidence to Highlight
{evidence_text or "Use strongest matches from work history"}

---

# INSTRUCTIONS

Generate a tailored resume by:
1. Writing a compelling 2-3 sentence summary highlighting {profile.years_of_experience} years of experience and relevant skills
2. Creating experience sections with rewritten bullets that naturally integrate the keywords above
3. Including a skills section with relevant skills grouped appropriately
4. Including an education section
5. Including a certifications/training section if provided

Remember:
- ONLY use information from the candidate's actual profile above
- DO NOT invent new experiences, companies, or achievements
- Integrate keywords naturally - don't just prepend them
- Keep specific metrics and facts exactly as provided
- Order sections as: {section_order_text or "experience -> skills -> projects -> education -> certifications"}
"""
        return prompt
