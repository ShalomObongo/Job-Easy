"""Tailoring Plan Generator.

Generates a tailoring plan by analyzing a job description against a user profile,
extracting keywords, mapping evidence, and providing rewrite suggestions.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from src.tailoring.config import TailoringConfig, get_tailoring_config
from src.tailoring.llm import TailoringLLM
from src.tailoring.models import (
    BulletRewrite,
    EvidenceMapping,
    KeywordMatch,
    TailoringPlan,
    UnsupportedClaim,
)

if TYPE_CHECKING:
    from src.extractor.models import JobDescription
    from src.scoring.models import UserProfile

logger = logging.getLogger(__name__)


class TailoringPlanLLMResponse(BaseModel):
    """LLM response structure for tailoring plan generation."""

    keyword_matches: list[KeywordMatch] = Field(
        default_factory=list,
        description="Keywords from job matched to user skills",
    )
    evidence_mappings: list[EvidenceMapping] = Field(
        default_factory=list,
        description="Job requirements mapped to user evidence",
    )
    section_order: list[str] = Field(
        default_factory=list,
        description="Recommended resume section order for this job",
    )
    bullet_rewrites: list[BulletRewrite] = Field(
        default_factory=list,
        description="Suggested bullet point rewrites",
    )
    unsupported_claims: list[UnsupportedClaim] = Field(
        default_factory=list,
        description="Job requirements without user evidence",
    )


PLAN_SYSTEM_PROMPT = """You are an expert resume tailoring assistant. Your job is to analyze a job description and a candidate's profile to create a tailoring plan.

Your analysis must:
1. Extract key skills and requirements from the job description
2. Match them to the candidate's actual skills and experience
3. Map the candidate's evidence (accomplishments, projects) to job requirements
4. Flag any requirements the candidate cannot support with evidence
5. Suggest how to reorder resume sections and rewrite bullets for maximum impact

CRITICAL RULES:
- NEVER fabricate experience or skills the candidate doesn't have
- Only use evidence that exists in the candidate's profile
- Be honest about gaps - flag requirements without supporting evidence
- Focus on rephrasing existing experience to highlight relevant keywords
- Prioritize required skills over preferred skills

For keyword_matches:
- Match job keywords to user skills with confidence scores (0-1)
- 1.0 = exact match, 0.8+ = strong match, 0.5-0.8 = partial match

For evidence_mappings:
- Connect specific job requirements to concrete user accomplishments
- Use actual text from the user's work history
- Include source company and role

For section_order:
- Recommend section order based on what's most relevant for this job
- Common sections: summary, experience, skills, education, projects, certifications

For bullet_rewrites:
- Suggest how to rewrite existing bullets to include job keywords
- Never invent new accomplishments - only rephrase existing ones
- List the keywords being added

For unsupported_claims:
- Flag required skills/experience the candidate doesn't have
- Mark as "warning" for preferred requirements, "critical" for must-haves
"""


class TailoringPlanService:
    """Service for generating tailoring plans.

    Analyzes job descriptions against user profiles to create
    comprehensive tailoring plans with keyword matching,
    evidence mapping, and rewrite suggestions.
    """

    def __init__(self, config: TailoringConfig | None = None):
        """Initialize the tailoring plan service.

        Args:
            config: Optional TailoringConfig. Uses global config if not provided.
        """
        self.config = config or get_tailoring_config()
        self.llm = TailoringLLM(config=self.config)

    async def generate_plan(
        self,
        profile: UserProfile,
        job: JobDescription,
    ) -> TailoringPlan:
        """Generate a tailoring plan for a job application.

        Args:
            profile: User's profile with skills and experience.
            job: Job description to tailor for.

        Returns:
            TailoringPlan with keyword matches, evidence mappings,
            section order, bullet rewrites, and unsupported claims.
        """
        logger.info(f"Generating tailoring plan for {job.company} - {job.role_title}")

        # Generate the plan using LLM
        plan = await self._generate_plan_with_llm(profile, job)

        logger.info(
            f"Generated plan with {len(plan.keyword_matches)} keyword matches, "
            f"{len(plan.evidence_mappings)} evidence mappings, "
            f"{len(plan.unsupported_claims)} warnings"
        )

        return plan

    async def _generate_plan_with_llm(
        self,
        profile: UserProfile,
        job: JobDescription,
    ) -> TailoringPlan:
        """Generate the tailoring plan using LLM.

        Args:
            profile: User's profile.
            job: Job description.

        Returns:
            TailoringPlan generated by LLM.
        """
        prompt = self._build_prompt(profile, job)

        response = await self.llm.generate_structured(
            prompt=prompt,
            output_model=TailoringPlanLLMResponse,
            system_prompt=PLAN_SYSTEM_PROMPT,
        )

        return TailoringPlan(
            job_url=job.job_url,
            company=job.company,
            role_title=job.role_title,
            keyword_matches=response.keyword_matches,
            evidence_mappings=response.evidence_mappings,
            section_order=response.section_order,
            bullet_rewrites=response.bullet_rewrites,
            unsupported_claims=response.unsupported_claims,
        )

    def _build_prompt(self, profile: UserProfile, job: JobDescription) -> str:
        """Build the prompt for tailoring plan generation.

        Args:
            profile: User's profile.
            job: Job description.

        Returns:
            Formatted prompt string.
        """
        # Format work history
        work_history_text = ""
        for exp in profile.work_history:
            end = exp.end_date or "Present"
            work_history_text += f"""
### {exp.title} at {exp.company} ({exp.start_date} - {end})
{exp.description}
Skills used: {", ".join(exp.skills_used)}
"""

        # Format education
        education_text = ""
        for edu in profile.education:
            grad = f" ({edu.graduation_year})" if edu.graduation_year else ""
            education_text += (
                f"- {edu.degree} in {edu.field} from {edu.institution}{grad}\n"
            )

        # Format certifications/training (if provided)
        certifications_text = ""
        for cert in getattr(profile, "certifications", []):
            issuer = f" — {cert.issuer}" if getattr(cert, "issuer", None) else ""
            date_awarded = (
                f" ({cert.date_awarded})" if getattr(cert, "date_awarded", None) else ""
            )
            certifications_text += f"- {cert.name}{issuer}{date_awarded}\n"

        # Format job requirements
        responsibilities_text = "\n".join(f"- {r}" for r in job.responsibilities)
        qualifications_text = "\n".join(f"- {q}" for q in job.qualifications)
        required_skills_text = (
            ", ".join(job.required_skills) if job.required_skills else "Not specified"
        )
        preferred_skills_text = (
            ", ".join(job.preferred_skills) if job.preferred_skills else "None"
        )

        prompt = f"""# JOB DESCRIPTION

**Company:** {job.company}
**Role:** {job.role_title}
**Location:** {job.location or "Not specified"}

## Full Description
{job.description or "Not provided"}

## Responsibilities
{responsibilities_text or "Not specified"}

## Qualifications
{qualifications_text or "Not specified"}

## Required Skills
{required_skills_text}

## Preferred Skills
{preferred_skills_text}

## Experience Level
{job.experience_years_min or "?"} - {job.experience_years_max or "?"} years

---

# CANDIDATE PROFILE

**Name:** {profile.name}
**Current Title:** {profile.current_title}
**Location:** {profile.location}
**Years of Experience:** {profile.years_of_experience}

## Professional Summary
{profile.summary}

## Skills
{", ".join(profile.skills)}

## Work History
{work_history_text}

## Education
{education_text or "Not specified"}

## Certifications / Training
{certifications_text or "Not specified"}

---

Please analyze this job description and candidate profile to create a comprehensive tailoring plan. Focus on:

1. **Keyword Matches**: Identify job keywords that match the candidate's skills
2. **Evidence Mapping**: Connect job requirements to specific accomplishments from the candidate's work history
3. **Section Order**: Recommend the optimal section order for the resume
4. **Bullet Rewrites**: Suggest how to reword existing bullets to incorporate job keywords
5. **Unsupported Claims**: Flag any requirements the candidate cannot support with evidence

Remember: NEVER fabricate experience. Only rephrase existing evidence to highlight relevant keywords.
"""
        return prompt
