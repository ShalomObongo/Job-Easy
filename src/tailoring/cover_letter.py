"""Cover Letter Generator.

Generates personalized cover letters based on user profile, job description,
and tailoring plan with word count targeting and evidence integration.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from src.tailoring.config import TailoringConfig, get_tailoring_config
from src.tailoring.llm import TailoringLLM
from src.tailoring.models import CoverLetter

if TYPE_CHECKING:
    from src.extractor.models import JobDescription
    from src.scoring.models import UserProfile
    from src.tailoring.models import TailoringPlan

logger = logging.getLogger(__name__)


class CoverLetterLLMResponse(BaseModel):
    """LLM response structure for cover letter generation."""

    opening: str = Field(..., description="Opening paragraph with hook")
    body: str = Field(..., description="Body with qualifications and evidence")
    closing: str = Field(..., description="Closing with call to action")
    key_qualifications: list[str] = Field(
        default_factory=list, description="Key qualifications highlighted"
    )


COVER_LETTER_SYSTEM_PROMPT = """You are an expert cover letter writer. Your job is to create a compelling, personalized cover letter for a job application.

**CRITICAL: You MUST respond with valid JSON matching the EXACT schema below. Use the EXACT field names shown. No variations allowed.**

STRUCTURE:
1. **Opening** (1 paragraph): Hook that mentions the specific role and company, shows enthusiasm
2. **Body** (2-3 paragraphs): Top 2-3 qualifications with concrete evidence, map accomplishments to job requirements
3. **Closing** (1 paragraph): Express enthusiasm, call to action, professional sign-off

CRITICAL RULES:
- NEVER fabricate experience, skills, or accomplishments
- Only reference actual experience from the candidate's profile
- Keep specific metrics and facts exactly as provided
- Personalize for the specific company and role
- Maintain professional but authentic tone
- Target word count of {min_words}-{max_words} words (MUST be within range; aim for ~1 page by staying closer to {min_words} when possible)
- Avoid repetition: do NOT restate the opening hook in the body, and avoid repeating the role/company name in every paragraph

WRITING TIPS:
- Lead with your strongest, most relevant qualification
- Use specific numbers and achievements (from profile only)
- Show you understand the company's needs
- Connect your experience directly to job requirements
- End with confidence but not arrogance

===== REQUIRED JSON SCHEMA =====
You MUST return a JSON object with these EXACT fields:

{{
  "opening": "Dear Hiring Manager,\\n\\nI am excited to apply for the Software Engineer position at TechCorp. With over 5 years of experience building scalable applications and a proven track record of delivering high-impact solutions, I am confident I can contribute to your team's success.",
  "body": "In my current role at StartupXYZ, I led the development of a microservices architecture that improved system reliability by 99.9% and reduced deployment time by 60%. This experience directly aligns with your need for engineers who can build robust, scalable systems.\\n\\nAdditionally, my expertise in Python and React has enabled me to deliver full-stack solutions that serve over 100,000 daily active users. I am particularly drawn to TechCorp's mission of democratizing technology access, which resonates with my passion for building user-centric products.",
  "closing": "I would welcome the opportunity to discuss how my experience in distributed systems and my passion for clean, maintainable code can contribute to TechCorp's continued growth. Thank you for considering my application.\\n\\nSincerely,\\nJohn Doe",
  "key_qualifications": [
    "5+ years building scalable applications",
    "Expertise in Python and React",
    "Led microservices architecture improving reliability to 99.9%"
  ]
}}

===== FIELD REQUIREMENTS =====

For opening (REQUIRED - string):
- The opening paragraph that hooks the reader
- Include the role and company name
- Show genuine enthusiasm
- 2-4 sentences

For body (REQUIRED - string):
- The main body paragraphs (2-3 paragraphs separated by \\n\\n)
- Connect your qualifications to job requirements
- Use specific metrics and achievements from the profile
- Do NOT repeat the opening hook or company name excessively

For closing (REQUIRED - string):
- Final paragraph with call to action
- Express enthusiasm for the opportunity
- Include professional sign-off

For key_qualifications (REQUIRED - array of strings):
- List of 3-5 key qualifications highlighted in the letter
- Brief phrases, not full sentences

===== RESPOND WITH ONLY THE JSON OBJECT. NO MARKDOWN FENCES, NO EXPLANATORY TEXT. =====
"""


class CoverLetterService:
    """Service for generating cover letters.

    Creates personalized cover letters with proper structure,
    word count targeting, and evidence integration.
    """

    def __init__(self, config: TailoringConfig | None = None):
        """Initialize the cover letter service.

        Args:
            config: Optional TailoringConfig. Uses global config if not provided.
        """
        self.config = config or get_tailoring_config()
        self.llm = TailoringLLM(config=self.config)

    async def generate_cover_letter(
        self,
        profile: UserProfile,
        job: JobDescription,
        plan: TailoringPlan,
    ) -> CoverLetter:
        """Generate a cover letter for a job application.

        Args:
            profile: User's profile with skills and experience.
            job: Job description to tailor for.
            plan: Tailoring plan with evidence mappings.

        Returns:
            CoverLetter ready for rendering.
        """
        logger.info(f"Generating cover letter for {job.company} - {job.role_title}")

        # Generate the cover letter using LLM
        cover = await self._generate_cover_letter_with_llm(profile, job, plan)

        logger.info(
            f"Generated cover letter with {cover.word_count} words, "
            f"{len(cover.key_qualifications)} key qualifications"
        )

        return cover

    async def _generate_cover_letter_with_llm(
        self,
        profile: UserProfile,
        job: JobDescription,
        plan: TailoringPlan,
    ) -> CoverLetter:
        """Generate the cover letter using LLM.

        Args:
            profile: User's profile.
            job: Job description.
            plan: Tailoring plan.

        Returns:
            CoverLetter generated by LLM.
        """
        min_words = self.config.cover_letter_min_words
        max_words = self.config.cover_letter_max_words
        base_prompt = self._build_prompt(profile, job, plan)
        system_prompt = COVER_LETTER_SYSTEM_PROMPT.format(
            min_words=min_words,
            max_words=max_words,
        )

        prompt = base_prompt
        response: CoverLetterLLMResponse | None = None
        full_text = ""
        word_count = 0

        # We enforce the configured word-count range with one revision pass.
        for _attempt in range(2):
            response = await self.llm.generate_structured(
                prompt=prompt,
                output_model=CoverLetterLLMResponse,
                system_prompt=system_prompt,
            )

            opening = response.opening.strip()
            body = response.body.strip()
            closing = response.closing.strip()

            opening = self._ensure_company_mentioned(opening, body, closing, job)
            full_text = self._format_full_text(opening, body, closing)
            word_count = self._count_words(full_text)

            if min_words <= word_count <= max_words:
                break

            prompt = f"""{base_prompt}

---

# REVISION REQUEST

The draft below is **{word_count} words**. Rewrite it to be **{min_words}-{max_words} words**.

Rules:
- Keep the same facts and evidence. Do not add new claims.
- Keep the same role/company and overall tone.
- Do not repeat the opening hook in the body.
- Preserve structure: opening (1 paragraph), body (2-3 paragraphs), closing (1 paragraph).

## Draft (for revision)

### Opening
{response.opening}

### Body
{response.body}

### Closing
{response.closing}
"""

        if response is None:
            raise RuntimeError("Cover letter generation failed unexpectedly.")

        # If the model still missed the range after the revision pass, apply a
        # deterministic adjustment so downstream consumers/tests aren't flaky.
        body = self._pad_body_to_min_words(
            opening=opening,
            body=body,
            closing=closing,
            profile=profile,
            job=job,
            plan=plan,
            min_words=min_words,
        )
        body = self._trim_body_to_max_words(
            opening=opening,
            body=body,
            closing=closing,
            max_words=max_words,
        )
        full_text = self._format_full_text(opening, body, closing)
        word_count = self._count_words(full_text)

        return CoverLetter(
            opening=opening,
            body=body,
            closing=closing,
            full_text=full_text,
            word_count=word_count,
            target_job_url=job.job_url,
            target_company=job.company,
            target_role=job.role_title,
            key_qualifications=response.key_qualifications,
        )

    def _ensure_company_mentioned(
        self,
        opening: str,
        body: str,
        closing: str,
        job: JobDescription,
    ) -> str:
        """Ensure the company name appears somewhere in the letter.

        Some models occasionally omit the company despite instructions; add a
        lightweight sentence to the opening in that case.
        """
        company = (job.company or "").strip()
        if not company:
            return opening

        combined = f"{opening} {body} {closing}"
        if company in combined:
            return opening

        role = (job.role_title or "this role").strip() or "this role"
        sentence = f"I'm excited to apply for the {role} position at {company}."
        opening = opening.strip()
        if not opening:
            return sentence
        if opening.endswith((".", "!", "?")):
            return f"{opening} {sentence}"
        return f"{opening}. {sentence}"

    def _format_full_text(self, opening: str, body: str, closing: str) -> str:
        """Format the complete cover letter text consistently."""
        return f"{opening}\n\n{body}\n\n{closing}".strip()

    def _count_words(self, text: str) -> int:
        """Count words in a text (whitespace-delimited)."""
        return len(text.split())

    def _trim_text_to_words(self, text: str, max_words: int) -> str:
        """Trim a string to at most `max_words` words."""
        if max_words <= 0:
            return ""
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]).strip()

    def _trim_body_to_max_words(
        self,
        *,
        opening: str,
        body: str,
        closing: str,
        max_words: int,
    ) -> str:
        """Trim body text so total letter word-count stays under max_words."""
        if max_words <= 0:
            return ""

        non_body_words = self._count_words(opening) + self._count_words(closing)
        allowed_body_words = max_words - non_body_words
        if allowed_body_words <= 0:
            return ""
        return self._trim_text_to_words(body, allowed_body_words)

    def _pad_body_to_min_words(
        self,
        *,
        opening: str,
        body: str,
        closing: str,
        profile: UserProfile,
        job: JobDescription,
        plan: TailoringPlan,
        min_words: int,
    ) -> str:
        """Pad body text (without fabricating) until the letter meets min_words."""
        if min_words <= 0:
            return body

        current_body = body.strip()
        if (
            self._count_words(self._format_full_text(opening, current_body, closing))
            >= min_words
        ):
            return current_body

        candidates: list[str] = []

        # Prefer verbatim work history summaries from the profile (truthful source).
        for exp in profile.work_history[:3]:
            desc = (exp.description or "").strip()
            if not desc:
                continue
            if desc.endswith((".", "!", "?")):
                desc = desc[:-1]
            candidates.append(f"In my role as {exp.title} at {exp.company}, {desc}.")

        # Use evidence mappings as short supporting context (generated but grounded in the profile).
        for mapping in plan.evidence_mappings[:3]:
            evidence = (mapping.evidence or "").strip()
            if not evidence:
                continue
            if not evidence.endswith((".", "!", "?")):
                evidence += "."
            candidates.append(evidence)

        # Add a lightweight skills alignment line.
        job_skills = [s.strip() for s in (job.required_skills or []) if s.strip()]
        profile_skills = [s.strip() for s in (profile.skills or []) if s.strip()]
        overlap = {
            s.lower(): s
            for s in job_skills
            if s.lower() in {p.lower() for p in profile_skills}
        }
        overlap_list = list(overlap.values())
        if overlap_list:
            skills_str = ", ".join(overlap_list[:8])
            candidates.append(
                f"Technically, I've worked extensively with {skills_str}, and I'm comfortable applying these skills to the responsibilities outlined for this role."
            )

        for paragraph in candidates:
            if (
                self._count_words(
                    self._format_full_text(opening, current_body, closing)
                )
                >= min_words
            ):
                break
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            current_body = (
                f"{current_body}\n\n{paragraph}" if current_body else paragraph
            ).strip()

        return current_body

    def _build_prompt(
        self,
        profile: UserProfile,
        job: JobDescription,
        plan: TailoringPlan,
    ) -> str:
        """Build the prompt for cover letter generation.

        Args:
            profile: User's profile.
            job: Job description.
            plan: Tailoring plan.

        Returns:
            Formatted prompt string.
        """
        # Format work history highlights
        work_highlights = ""
        for exp in profile.work_history[:3]:  # Top 3 roles
            end = exp.end_date or "Present"
            work_highlights += f"""
### {exp.title} at {exp.company} ({exp.start_date} - {end})
{exp.description}
"""

        # Format evidence mappings from plan
        evidence_text = ""
        for mapping in plan.evidence_mappings[:5]:
            evidence_text += f"- Job needs: {mapping.requirement}\n  Your evidence: {mapping.evidence}\n"

        # Format job requirements
        responsibilities = "\n".join(f"- {r}" for r in job.responsibilities[:5])
        required_skills = (
            ", ".join(job.required_skills) if job.required_skills else "Not specified"
        )

        prompt = f"""# TARGET JOB

**Company:** {job.company}
**Role:** {job.role_title}
**Location:** {job.location or "Not specified"}

## About the Role
{job.description or "Not provided"}

## Key Responsibilities
{responsibilities or "Not specified"}

## Required Skills
{required_skills}

---

# CANDIDATE PROFILE

**Name:** {profile.name}
**Current Title:** {profile.current_title}
**Years of Experience:** {profile.years_of_experience}

## Professional Summary
{profile.summary}

## Relevant Experience
{work_highlights}

## Key Skills
{", ".join(profile.skills[:15])}

---

# EVIDENCE MAPPING (from tailoring plan)

{evidence_text or "Use the strongest matches from the candidate profile."}

---

# INSTRUCTIONS

Write a compelling cover letter for {profile.name} applying to the {job.role_title} position at {job.company}.

Requirements:
1. Opening paragraph: Express enthusiasm for this specific role at {job.company}
2. Body (2-3 paragraphs): Highlight top 2-3 qualifications with concrete evidence from the profile
3. Closing paragraph: Express eagerness to discuss further, professional sign-off

Target word count: {self.config.cover_letter_min_words}-{self.config.cover_letter_max_words} words

Remember:
- ONLY use information from the candidate's actual profile
- DO NOT invent new experiences or achievements
- Keep specific metrics exactly as provided
- Make it personal to {job.company} - not a generic letter
"""
        return prompt
