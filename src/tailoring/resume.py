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

_ALLOWED_SECTION_NAMES = {
    "experience",
    "skills",
    "projects",
    "education",
    "certifications",
}
_SECTION_TITLE_BY_NAME = {
    "experience": "Professional Experience",
    "skills": "Technical Skills",
    "projects": "Projects",
    "education": "Education",
    "certifications": "Certifications",
}
_CANONICAL_SECTION_ORDER = [
    "experience",
    "skills",
    "certifications",
    "education",
    "projects",
]


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
                return {
                    "text": data.get("bullet"),
                    "keywords_used": data.get("keywords_used", []),
                }
            if "value" in data:
                return {
                    "text": data.get("value"),
                    "keywords_used": data.get("keywords_used", []),
                }
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

        if (
            isinstance(content, list)
            and not bullets
            and ("experience" in name_lower or "work" in name_lower)
        ):
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
- 1–4 bullets per role (use 1 only when profile evidence is sparse; otherwise use 2–4).
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

    def _normalize_text_token(self, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", str(value).strip().lower())
        return re.sub(r"\s+", " ", normalized).strip()

    def _tokens_match(self, left: str, right: str) -> bool:
        if not left or not right:
            return False
        if left == right or left in right or right in left:
            return True
        left_tokens = set(left.split())
        right_tokens = set(right.split())
        overlap = left_tokens & right_tokens
        if not overlap:
            return False
        return len(overlap) >= min(2, len(left_tokens), len(right_tokens))

    def _role_company_exists_in_profile(
        self, role: str, company: str, profile: UserProfile
    ) -> bool:
        role_norm = self._normalize_text_token(role)
        company_norm = self._normalize_text_token(company)
        for exp in profile.work_history:
            exp_role = self._normalize_text_token(exp.title)
            exp_company = self._normalize_text_token(exp.company)
            if self._tokens_match(role_norm, exp_role) and self._tokens_match(
                company_norm, exp_company
            ):
                return True
        return False

    def _has_limited_role_evidence(
        self, role: str, company: str, profile: UserProfile
    ) -> bool:
        role_norm = self._normalize_text_token(role)
        company_norm = self._normalize_text_token(company)
        for exp in profile.work_history:
            exp_role = self._normalize_text_token(exp.title)
            exp_company = self._normalize_text_token(exp.company)
            if not (
                self._tokens_match(role_norm, exp_role)
                and self._tokens_match(company_norm, exp_company)
            ):
                continue
            description = (exp.description or "").strip()
            sentences = [
                s.strip() for s in re.split(r"[.!?]+", description) if s.strip()
            ]
            return (
                len(sentences) <= 1
                and len(exp.skills_used) <= 3
                and len(description) <= 160
            )
        return False

    def _minimum_bullets_for_role(
        self, role: str, company: str, profile: UserProfile
    ) -> int:
        return 1 if self._has_limited_role_evidence(role, company, profile) else 2

    def _plan_has_project_grounding(
        self, profile: UserProfile, plan: TailoringPlan
    ) -> bool:
        project_pattern = re.compile(
            r"\b(project|portfolio|open[- ]source|side project)\b", re.IGNORECASE
        )
        for mapping in plan.evidence_mappings:
            text = f"{mapping.requirement} {mapping.evidence}"
            if project_pattern.search(text):
                return True
        for rewrite in plan.bullet_rewrites:
            if project_pattern.search(f"{rewrite.original} {rewrite.suggested}"):
                return True
        for exp in profile.work_history:
            if project_pattern.search(exp.description or ""):
                return True
        return False

    def _extract_claim_keywords(self, requirement: str) -> list[str]:
        stop_words = {
            "ability",
            "across",
            "align",
            "and",
            "at",
            "build",
            "building",
            "create",
            "develop",
            "driven",
            "enable",
            "ensure",
            "experience",
            "for",
            "from",
            "have",
            "in",
            "knowledge",
            "maintain",
            "must",
            "of",
            "operational",
            "or",
            "outcomes",
            "plus",
            "preferred",
            "process",
            "required",
            "requirement",
            "requirements",
            "responsible",
            "role",
            "scalable",
            "solutions",
            "strong",
            "support",
            "teams",
            "the",
            "to",
            "using",
            "with",
            "work",
            "workflow",
            "years",
            "year",
        }
        tokens = re.findall(r"[A-Za-z0-9#+./-]+", requirement)
        return [
            t
            for t in tokens
            if len(t) >= 3 and t.lower() not in stop_words and not t.isdigit()
        ]

    def _normalize_lookup_text(self, value: str) -> str:
        text = re.sub(r"[^a-z0-9#+./-]+", " ", str(value or "").lower())
        return re.sub(r"\s+", " ", text).strip()

    def _value_in_lookup_text(self, value: str, lookup_text: str) -> bool:
        normalized_value = self._normalize_lookup_text(value)
        if not normalized_value:
            return False
        return bool(
            re.search(
                rf"(?<![a-z0-9]){re.escape(normalized_value)}(?![a-z0-9])",
                lookup_text,
            )
        )

    def _build_profile_lookup_text(self, profile: UserProfile) -> str:
        parts: list[str] = [
            profile.name,
            profile.current_title,
            profile.summary,
            " ".join(profile.skills),
        ]

        for exp in profile.work_history:
            parts.extend(
                [
                    exp.company,
                    exp.title,
                    exp.description,
                    " ".join(exp.skills_used),
                ]
            )

        for edu in profile.education:
            parts.extend([edu.institution, edu.degree, edu.field])

        for cert in getattr(profile, "certifications", []) or []:
            parts.extend(
                [
                    getattr(cert, "name", ""),
                    getattr(cert, "issuer", ""),
                    getattr(cert, "url", ""),
                ]
            )

        return self._normalize_lookup_text(" ".join(p for p in parts if p))

    def _collect_unsupported_claim_issues(
        self,
        response: TailoredResumeLLMResponse,
        plan: TailoringPlan,
        profile: UserProfile,
    ) -> list[str]:
        text_parts = [response.summary]
        for section in response.sections:
            text_parts.append(section.content)
            text_parts.extend(bullet.text for bullet in section.bullets)
        combined = self._normalize_lookup_text(
            " ".join(part for part in text_parts if part)
        )
        profile_lookup = self._build_profile_lookup_text(profile)
        issues: list[str] = []
        for claim in plan.unsupported_claims:
            for keyword in self._extract_claim_keywords(claim.requirement):
                # If the profile already contains this keyword, it is valid evidence.
                # Unsupported-claim hints are noisy and should only block out-of-profile terms.
                if self._value_in_lookup_text(keyword, profile_lookup):
                    continue
                if self._value_in_lookup_text(keyword, combined):
                    issues.append(
                        "Resume appears to include unsupported claim keyword "
                        f"'{keyword}' from requirement '{claim.requirement}'."
                    )
                    break
        return issues

    def _expand_keyword_phrase(self, raw_keyword: str) -> list[str]:
        cleaned = str(raw_keyword or "").strip().strip(".,;:")
        if not cleaned:
            return []
        parts = re.split(r"\s*(?:,|/|\||\bor\b|\band\b)\s*", cleaned, flags=re.I)
        expanded = [part.strip().strip(".,;:") for part in parts if part.strip()]
        if expanded:
            return expanded
        return [cleaned]

    def _extract_target_keywords(
        self, job: JobDescription, plan: TailoringPlan
    ) -> list[str]:
        raw_keywords: list[str] = []
        raw_keywords.extend(str(skill) for skill in (job.required_skills or []))
        raw_keywords.extend(str(skill) for skill in (job.preferred_skills or []))
        raw_keywords.extend(match.job_keyword for match in plan.keyword_matches)
        keywords: list[str] = []
        seen: set[str] = set()
        for raw in raw_keywords:
            for expanded in self._expand_keyword_phrase(raw):
                normalized = expanded.casefold()
                if not expanded or normalized in seen:
                    continue
                seen.add(normalized)
                keywords.append(expanded)
        return keywords

    def _keyword_appears_in_text(self, text: str, keyword: str) -> bool:
        if not keyword:
            return False
        if re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text, flags=re.IGNORECASE):
            return True
        return keyword.lower() in text.lower()

    def _recompute_keywords_used(
        self,
        response: TailoredResumeLLMResponse,
        job: JobDescription,
        plan: TailoringPlan,
    ) -> list[str]:
        text_parts = [response.summary]
        for section in response.sections:
            text_parts.append(section.content)
            text_parts.extend(b.text for b in section.bullets)
        combined_text = "\n".join(part for part in text_parts if part).strip()
        keywords_used: list[str] = []
        for keyword in self._extract_target_keywords(job, plan):
            if self._keyword_appears_in_text(combined_text, keyword):
                keywords_used.append(keyword)
        return keywords_used

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
                        min_bullets = self._minimum_bullets_for_role(
                            role, company, profile
                        )
                        if count < min_bullets or count > 4:
                            issues.append(
                                f"Experience role '{role}' at '{company}' must have "
                                f"{min_bullets}–4 bullets (got {count})."
                            )
                        if not self._role_company_exists_in_profile(
                            role, company, profile
                        ):
                            issues.append(
                                "Experience includes role/company not found in "
                                f"profile: '{role}' at '{company}'."
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

        # Only require projects when grounded evidence exists in plan/profile.
        plan_order = [str(s).strip().lower() for s in (plan.section_order or [])]
        projects_grounded = self._plan_has_project_grounding(profile, plan)
        if "projects" in plan_order and projects_grounded:
            if projects_section is None:
                issues.append(
                    "Plan requests a projects section, but none was produced."
                )
            elif not projects_section.bullets:
                issues.append("Projects section must include 1–3 bullets.")

        issues.extend(self._collect_unsupported_claim_issues(response, plan, profile))

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
                role, company = role_company
                if not self._role_company_exists_in_profile(role, company, profile):
                    continue

                min_bullets = self._minimum_bullets_for_role(role, company, profile)
                if len(bodies) < min_bullets:
                    continue

                dates = role_dates.get(role_company, "")

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
                response.sections = [
                    s for s in response.sections if s is not projects_section
                ]

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
- Every role in Experience MUST have 1–4 bullets. Use 1 only when the profile has sparse evidence for that role; otherwise use 2–4.
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

        response.keywords_used = self._recompute_keywords_used(response, job, plan)

        # Convert LLM response to TailoredResume with contact info from profile
        return TailoredResume(
            name=profile.name,
            email=profile.email,
            phone=profile.phone,
            location=profile.location,
            linkedin_url=profile.linkedin_url,
            github_url=profile.github_url,
            summary=response.summary,
            sections=[
                TailoredSection(
                    name=s.name,
                    title=s.title,
                    content=s.content,
                    bullets=[
                        TailoredBullet(text=b.text, keywords_used=b.keywords_used)
                        for b in s.bullets
                    ],
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
        _ = plan

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
                TailoredBulletLLM(
                    text=b.text.strip(), keywords_used=b.keywords_used or []
                )
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

        ordered_sections: list[TailoredSectionLLM] = []
        for name in _CANONICAL_SECTION_ORDER:
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
        certifications = list(getattr(profile, "certifications", []) or [])
        for cert in certifications:
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

        # Use canonical section order for stable, recruiter-friendly output.
        section_order = list(_CANONICAL_SECTION_ORDER)
        if not certifications:
            section_order.remove("certifications")
        section_order_text = " -> ".join(section_order)

        # Format evidence mappings
        evidence_text = ""
        for mapping in plan.evidence_mappings[:5]:  # Top 5 evidence items
            evidence_text += f"- {mapping.requirement}: {mapping.evidence} (from {mapping.source_company})\n"

        # Format bullet rewrite hints from plan
        rewrite_hints_text = ""
        for rewrite in plan.bullet_rewrites[:8]:
            keywords = ", ".join(rewrite.keywords_added[:5]) or "None"
            rewrite_hints_text += (
                f"- Original: {rewrite.original}\n"
                f"  Suggested emphasis: {rewrite.suggested}\n"
                f"  Keywords to preserve: {keywords}\n"
            )

        # Format unsupported claims as explicit do-not-claim constraints
        unsupported_claims_text = ""
        for claim in plan.unsupported_claims[:10]:
            unsupported_claims_text += (
                f"- Do not claim: {claim.requirement} "
                f"({claim.severity}) — {claim.reason}\n"
            )

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
{certifications_text if certifications_text.strip() else "(None provided — omit this section in the final resume.)"}

---

# TAILORING PLAN

## Keywords to Integrate
{keywords_text or "Use skills from job requirements"}

## Section Order
{section_order_text or "experience -> skills -> certifications -> education -> projects"}

## Key Evidence to Highlight
{evidence_text or "Use strongest matches from work history"}

## Bullet Rewrite Hints
{rewrite_hints_text or "Use the strongest profile accomplishments and preserve truthfulness."}

## Unsupported Claims (Hard Constraints)
{unsupported_claims_text or "None explicitly flagged."}

---

# INSTRUCTIONS

Generate a tailored resume by:
1. Writing a compelling 2-3 sentence summary highlighting {profile.years_of_experience} years of experience and relevant skills
2. Creating experience sections with rewritten bullets that naturally integrate the keywords above
3. Including a skills section with relevant skills grouped appropriately
4. Including an education section
5. Including a certifications/training section **only if certifications are provided**. If none are provided, **omit the section entirely** (do not write “Not specified”).

Remember:
- ONLY use information from the candidate's actual profile above
- DO NOT invent new experiences, companies, or achievements
- NEVER include unsupported claims listed above
- Integrate keywords naturally - don't just prepend them
- Keep specific metrics and facts exactly as provided
- Order sections as: {section_order_text or "experience -> skills -> certifications -> education -> projects"}
"""
        return prompt
