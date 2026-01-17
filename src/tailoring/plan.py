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

**CRITICAL: You MUST respond with valid JSON matching the EXACT schema below. Use the EXACT field names shown. No variations allowed.**

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

===== REQUIRED JSON SCHEMA =====
You MUST return a JSON object with these EXACT fields:

{
  "keyword_matches": [
    {
      "job_keyword": "Python",
      "user_skill": "Python programming",
      "confidence": 0.95
    }
  ],
  "evidence_mappings": [
    {
      "requirement": "3+ years of backend development",
      "evidence": "Led backend development of payment processing system handling 10k transactions/day",
      "source_company": "TechCorp Inc",
      "source_role": "Senior Software Engineer",
      "relevance_score": 0.9
    }
  ],
  "section_order": ["experience", "skills", "projects", "education", "certifications"],
  "bullet_rewrites": [
    {
      "original": "Developed APIs for the platform",
      "suggested": "Developed RESTful APIs using Python and FastAPI, improving response times by 40%",
      "keywords_added": ["Python", "FastAPI", "RESTful APIs"],
      "emphasis_reason": "Added specific technologies mentioned in job requirements"
    }
  ],
  "unsupported_claims": [
    {
      "requirement": "Kubernetes experience required",
      "reason": "No Kubernetes experience found in candidate's profile",
      "severity": "critical"
    }
  ]
}

===== FIELD REQUIREMENTS =====

For keyword_matches (REQUIRED FIELDS: job_keyword, user_skill, confidence):
- "job_keyword": The exact keyword from the job posting (string)
- "user_skill": The matching skill from user's profile (string)
- "confidence": Match confidence 0.0-1.0 (number). 1.0=exact, 0.8+=strong, 0.5-0.8=partial

For evidence_mappings (REQUIRED FIELDS: requirement, evidence, source_company, source_role, relevance_score):
- "requirement": The job requirement being addressed (string)
- "evidence": Specific accomplishment text from user's profile (string)
- "source_company": Company where the evidence is from (string)
- "source_role": Role/title where the evidence is from (string)
- "relevance_score": How relevant this evidence is 0.0-1.0 (number)

For section_order:
- Array of section identifiers in recommended order.
- IMPORTANT: The resume summary is generated separately and is NOT a section. Do NOT include "summary" here.
- Allowed values (lowercase only): "experience", "skills", "projects", "education", "certifications"
- Do not invent extra sections (e.g., "tools", "platforms", "interests") and do not repeat sections

For bullet_rewrites (REQUIRED FIELDS: original, suggested, keywords_added, emphasis_reason):
- "original": The original bullet text from user's resume (string)
- "suggested": The rewritten bullet with keywords (string)
- "keywords_added": Array of keywords added in the rewrite (array of strings)
- "emphasis_reason": Why this rewrite improves the bullet (string)

For unsupported_claims (REQUIRED FIELDS: requirement, reason, severity):
- "requirement": The requirement that cannot be supported (string)
- "reason": Why there's no supporting evidence (string)
- "severity": Either "warning" (preferred skills) or "critical" (must-have skills)

===== RESPOND WITH ONLY THE JSON OBJECT. NO MARKDOWN FENCES, NO EXPLANATORY TEXT. =====
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

        section_order = self._normalize_section_order(response.section_order)

        return TailoringPlan(
            job_url=job.job_url,
            company=job.company,
            role_title=job.role_title,
            keyword_matches=response.keyword_matches,
            evidence_mappings=response.evidence_mappings,
            section_order=section_order,
            bullet_rewrites=response.bullet_rewrites,
            unsupported_claims=response.unsupported_claims,
        )

    def _normalize_section_order(self, section_order: list[str]) -> list[str]:
        allowed = ("experience", "skills", "projects", "education", "certifications")
        normalized: list[str] = []
        seen: set[str] = set()

        for raw in section_order or []:
            value = str(raw).strip().lower()
            if not value or value == "summary":
                continue

            if "experience" in value or value.startswith("work"):
                value = "experience"
            elif "skill" in value:
                value = "skills"
            elif "project" in value:
                value = "projects"
            elif "education" in value:
                value = "education"
            elif "cert" in value or "training" in value:
                value = "certifications"

            if value in allowed and value not in seen:
                normalized.append(value)
                seen.add(value)

        if not normalized:
            return list(allowed)

        # Ensure a stable, ATS-friendly default ordering for any missing sections.
        for value in allowed:
            if value not in seen:
                normalized.append(value)
        return normalized

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
