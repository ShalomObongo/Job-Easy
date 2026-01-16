"""Resume Tailoring Engine.

Transforms a user profile into a tailored resume based on a tailoring plan,
rewriting bullets to integrate keywords while maintaining truthfulness.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from src.tailoring.config import TailoringConfig, get_tailoring_config
from src.tailoring.llm import TailoringLLM
from src.tailoring.models import TailoredBullet, TailoredResume, TailoredSection

if TYPE_CHECKING:
    from src.extractor.models import JobDescription
    from src.scoring.models import UserProfile
    from src.tailoring.models import TailoringPlan

logger = logging.getLogger(__name__)


class TailoredSectionLLM(BaseModel):
    """LLM response structure for a tailored section."""

    name: str = Field(..., description="Section identifier")
    title: str = Field(..., description="Display title")
    content: str = Field(default="", description="Section content if not bullet-based")
    bullets: list[TailoredBullet] = Field(
        default_factory=list, description="Tailored bullet points"
    )


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
- `sections` should be an ordered list using only these names: experience, skills, projects, education, certifications.
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
- Pick up to 5 most relevant roles from the profile (or fewer if needed).
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

EDUCATION / CERTIFICATIONS
- Use `content` as one item per line, concise.

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
            rf"^[^,\n]+,\s*[^()]+?(?:\s*\([^)]+\))?\s*(?:{dash}|:)\s*.+$",
            rf"^[^()\n]+?\s*{dash}\s*[^()]+?(?:\s*\([^)]+\))?\s*(?:{dash}|:)\s*.+$",
        ]
        text = text.strip()
        return any(re.match(p, text) for p in patterns)

    def _resume_output_is_acceptable(
        self, response: TailoredResumeLLMResponse, profile: UserProfile
    ) -> bool:
        # Require an experience section when the profile has work history.
        experience_sections = [
            s
            for s in response.sections
            if "experience" in s.name.lower() or "experience" in s.title.lower()
        ]
        if profile.work_history and not experience_sections:
            return False

        if experience_sections:
            exp = experience_sections[0]
            if not exp.bullets:
                return False

            matching = sum(
                1
                for b in exp.bullets
                if b.text.strip() and self._experience_bullet_has_required_prefix(b.text)
            )
            # We need enough prefixed bullets to reliably render job headers.
            if matching < max(2, int(0.6 * len(exp.bullets))):
                return False

        return True

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

        for _attempt in range(2):
            response = await self.llm.generate_structured(
                prompt=prompt,
                output_model=TailoredResumeLLMResponse,
                system_prompt=RESUME_SYSTEM_PROMPT,
            )

            if self._resume_output_is_acceptable(response, profile):
                break

            prompt = f"""{base_prompt}

---

# REVISION REQUEST (FORMAT FIXES)

The JSON was valid but the formatting is not renderable. Fix ONLY formatting (do not add new facts).

Required fixes:
- Ensure there is an Experience section.
- Every Experience bullet MUST start with: `ROLE, COMPANY (START – END) — ` (END can be Present).
- Keep 2–4 bullets per role; avoid semicolons; no empty bullets.

## Previous JSON (revise this)
{response.model_dump_json(indent=2)}
"""

        if response is None:
            raise RuntimeError("Resume generation failed unexpectedly.")

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
                    bullets=s.bullets,
                )
                for s in response.sections
            ],
            keywords_used=response.keywords_used,
            target_job_url=job.job_url,
            target_company=job.company,
            target_role=job.role_title,
        )

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
        section_order_text = " -> ".join(plan.section_order)

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
{section_order_text or "summary -> experience -> skills -> education"}

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
- Order sections as: {section_order_text or "summary -> experience -> skills -> education"}
"""
        return prompt
