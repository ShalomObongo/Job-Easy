"""Fit scoring service implementation."""

from __future__ import annotations

import re

from src.extractor.models import JobDescription
from src.scoring.config import ScoringConfig, get_scoring_config
from src.scoring.llm import ScoringLLM, ScoringLLMError
from src.scoring.matchers import expand_skills, find_matching_skills
from src.scoring.models import (
    ConstraintResult,
    FitResult,
    FitScore,
    LLMFitEvaluation,
    UserProfile,
)
from src.scoring.prompts import SCORING_LLM_SYSTEM_PROMPT, build_llm_fit_prompt


class FitScoringService:
    """Service for computing fit scores and recommendations."""

    def __init__(self, config: ScoringConfig | None = None) -> None:
        self.config = config or get_scoring_config()

        self._llm: ScoringLLM | None = None
        if self.config.scoring_mode == "llm":
            self._llm = ScoringLLM(config=self.config)

    def _recommendation_from_score(
        self, *, score: float, constraints: ConstraintResult
    ) -> str:
        threshold = self.config.fit_score_threshold
        margin = self.config.review_margin

        if not constraints.passed:
            return "skip"
        if score >= threshold:
            return "apply"
        if score >= max(0.0, threshold - margin):
            return "review"
        return "skip"

    def _format_deterministic_reasoning(
        self, *, fit_score: FitScore, constraints: ConstraintResult
    ) -> str:
        threshold = self.config.fit_score_threshold

        reasoning_parts: list[str] = []
        reasoning_parts.append(
            f"fit_score={fit_score.total_score:.2f} threshold={threshold:.2f}"
        )
        if fit_score.must_have_missing:
            reasoning_parts.append(
                f"missing_required_skills={', '.join(fit_score.must_have_missing)}"
            )
        if not constraints.passed:
            reasoning_parts.append(
                f"hard_violations={'; '.join(constraints.hard_violations)}"
            )
        elif constraints.soft_warnings:
            reasoning_parts.append(f"warnings={'; '.join(constraints.soft_warnings)}")

        return " | ".join(reasoning_parts)

    def _llm_to_fit_score(
        self, *, job: JobDescription, llm: LLMFitEvaluation
    ) -> FitScore:
        required_total = len(llm.must_have_matched) + len(llm.must_have_missing)
        if required_total:
            must_have_score = len(llm.must_have_matched) / required_total
        else:
            must_have_score = 1.0

        preferred_total = len(job.preferred_skills or [])
        if preferred_total:
            preferred_score = len(llm.preferred_matched) / preferred_total
        else:
            preferred_score = 1.0

        return FitScore(
            total_score=llm.total_score,
            must_have_score=must_have_score,
            must_have_matched=llm.must_have_matched,
            must_have_missing=llm.must_have_missing,
            preferred_score=preferred_score,
            preferred_matched=llm.preferred_matched,
            experience_score=1.0,
            experience_reasoning="",
            education_score=1.0,
            education_reasoning="",
            risk_flags=llm.risk_flags,
        )

    def _build_available_skills(self, profile: UserProfile) -> list[str]:
        """Build a broad skill inventory from structured profile fields."""
        available: list[str] = []
        available.extend(profile.skills or [])
        for exp in profile.work_history:
            available.extend(exp.skills_used or [])

        text_sources: list[str] = []
        if profile.current_title:
            text_sources.append(profile.current_title)
        if profile.summary:
            text_sources.append(profile.summary)
        for exp in profile.work_history:
            if exp.description:
                text_sources.append(exp.description)

        corpus = " ".join(text_sources).lower()
        if corpus:
            if re.search(r"\btest", corpus):
                available.append("testing")
            if re.search(r"\bdebug", corpus) or "optim" in corpus:
                available.append("debugging")
            if re.search(r"\bjavascript\b|\bjs\b", corpus):
                available.append("javascript")
            if re.search(r"\bhtml\b", corpus):
                available.append("html")
            if re.search(r"\bcss\b", corpus):
                available.append("css")
            if re.search(r"\breact\b", corpus):
                available.append("react")
            if re.search(r"\bnext\.js\b|\bnextjs\b", corpus):
                available.append("next.js")
            if re.search(r"\bmongo(db)?\b", corpus):
                available.append("mongodb")
            if re.search(r"\bjquery\b", corpus):
                available.append("jquery")

        return expand_skills(available)

    def score_skills(
        self, job: JobDescription, profile: UserProfile
    ) -> tuple[float, list[str], list[str], float, list[str]]:
        """Score required and preferred skills against a profile.

        Returns:
            must_have_score, must_have_matched, must_have_missing,
            preferred_score, preferred_matched
        """
        required = job.required_skills or []
        preferred = job.preferred_skills or []
        available = self._build_available_skills(profile)

        if not required:
            must_have_score = 1.0
            must_have_matched: list[str] = []
            must_have_missing: list[str] = []
        else:
            must_have_matched, must_have_missing = find_matching_skills(
                required=required,
                available=available,
                fuzzy=self.config.skill_fuzzy_match,
                threshold=self.config.skill_fuzzy_threshold,
            )
            must_have_score = len(must_have_matched) / len(required)

        if not preferred:
            preferred_score = 1.0
            preferred_matched: list[str] = []
        else:
            preferred_matched, _preferred_missing = find_matching_skills(
                required=preferred,
                available=available,
                fuzzy=self.config.skill_fuzzy_match,
                threshold=self.config.skill_fuzzy_threshold,
            )
            preferred_score = len(preferred_matched) / len(preferred)

        return (
            must_have_score,
            must_have_matched,
            must_have_missing,
            preferred_score,
            preferred_matched,
        )

    def score_experience(
        self, job: JobDescription, profile: UserProfile
    ) -> tuple[float, str]:
        """Score experience match between job requirements and profile."""
        tolerance = max(0, self.config.experience_tolerance_years)
        years = profile.years_of_experience
        min_years = job.experience_years_min
        max_years = job.experience_years_max

        if min_years is None and max_years is None:
            return 1.0, "No experience requirement"

        if min_years is not None and years < min_years:
            delta = min_years - years
            if delta > tolerance:
                return 0.0, f"Below minimum experience by {delta} year(s)"
            score = 1.0 - (delta / (tolerance + 1))
            return score, f"Below minimum experience by {delta} year(s)"

        if max_years is not None and years > max_years:
            delta = years - max_years
            if delta > tolerance:
                return 0.0, f"Above maximum experience by {delta} year(s)"
            score = 1.0 - (delta / (tolerance + 1))
            return score, f"Above maximum experience by {delta} year(s)"

        return 1.0, "Within required experience range"

    def score_education(
        self, job: JobDescription, profile: UserProfile
    ) -> tuple[float, str]:
        """Score education match between job requirements and profile."""
        required = job.education
        if not required:
            return 1.0, "No education requirement"

        required_level = _education_level(required)
        if required_level is None:
            return 1.0, "Unknown education requirement"

        profile_level = _highest_education_level(profile)
        if profile_level is None:
            return 0.0, "No education listed"

        if profile_level >= required_level:
            return 1.0, "Meets education requirement"

        diff = required_level - profile_level
        if diff == 1:
            return 0.5, "One level below education requirement"
        return 0.0, "Below education requirement"

    def calculate_fit_score(
        self, job: JobDescription, profile: UserProfile
    ) -> FitScore:
        """Calculate weighted fit score with detailed breakdown."""
        (
            must_have_score,
            must_have_matched,
            must_have_missing,
            preferred_score,
            preferred_matched,
        ) = self.score_skills(job, profile)
        experience_score, experience_reasoning = self.score_experience(job, profile)
        education_score, education_reasoning = self.score_education(job, profile)

        total_score = (
            self.config.weight_must_have * must_have_score
            + self.config.weight_preferred * preferred_score
            + self.config.weight_experience * experience_score
            + self.config.weight_education * education_score
        )

        return FitScore(
            total_score=total_score,
            must_have_score=must_have_score,
            must_have_matched=must_have_matched,
            must_have_missing=must_have_missing,
            preferred_score=preferred_score,
            preferred_matched=preferred_matched,
            experience_score=experience_score,
            experience_reasoning=experience_reasoning,
            education_score=education_score,
            education_reasoning=education_reasoning,
        )

    def check_constraints(
        self, job: JobDescription, profile: UserProfile
    ) -> ConstraintResult:
        """Check constraints and return hard violations and soft warnings."""
        hard_violations: list[str] = []
        soft_warnings: list[str] = []

        self._check_location_and_work_type(job, profile, hard_violations, soft_warnings)
        self._check_visa(job, profile, hard_violations, soft_warnings)
        self._check_experience_constraint(job, profile, hard_violations, soft_warnings)
        self._check_salary(job, profile, hard_violations, soft_warnings)

        if hard_violations:
            return ConstraintResult(
                passed=False,
                hard_violations=hard_violations,
                soft_warnings=soft_warnings,
            )
        return ConstraintResult(
            passed=True,
            hard_violations=[],
            soft_warnings=soft_warnings,
        )

    def evaluate(self, job: JobDescription, profile: UserProfile) -> FitResult:
        """Run full evaluation: scoring, constraints, and recommendation."""
        constraints = self.check_constraints(job, profile)

        if self.config.scoring_mode != "llm":
            fit_score = self.calculate_fit_score(job, profile)
            recommendation = self._recommendation_from_score(
                score=fit_score.total_score, constraints=constraints
            )
            reasoning = self._format_deterministic_reasoning(
                fit_score=fit_score, constraints=constraints
            )
            return FitResult(
                job_url=job.job_url,
                job_title=job.role_title,
                company=job.company,
                fit_score=fit_score,
                constraints=constraints,
                recommendation=recommendation,  # type: ignore[arg-type]
                reasoning=reasoning,
                score_source="deterministic",
            )

        baseline_fit_score = self.calculate_fit_score(job, profile)
        baseline_recommendation = self._recommendation_from_score(
            score=baseline_fit_score.total_score, constraints=constraints
        )

        llm_client = self._llm or ScoringLLM(config=self.config)
        prompt = build_llm_fit_prompt(job=job, profile=profile, config=self.config)

        try:
            llm_eval = llm_client.generate_structured(
                prompt=prompt,
                output_model=LLMFitEvaluation,
                system_prompt=SCORING_LLM_SYSTEM_PROMPT,
            )
        except ScoringLLMError:
            reasoning = self._format_deterministic_reasoning(
                fit_score=baseline_fit_score, constraints=constraints
            )
            return FitResult(
                job_url=job.job_url,
                job_title=job.role_title,
                company=job.company,
                fit_score=baseline_fit_score,
                constraints=constraints,
                recommendation=baseline_recommendation,  # type: ignore[arg-type]
                reasoning=reasoning,
                score_source="fallback_deterministic",
            )

        llm_fit_score = self._llm_to_fit_score(job=job, llm=llm_eval)
        recommendation = llm_eval.recommendation
        if not constraints.passed:
            recommendation = "skip"

        return FitResult(
            job_url=job.job_url,
            job_title=job.role_title,
            company=job.company,
            fit_score=llm_fit_score,
            constraints=constraints,
            recommendation=recommendation,
            reasoning=llm_eval.reasoning,
            score_source="llm",
            baseline_fit_score=baseline_fit_score,
            baseline_recommendation=baseline_recommendation,  # type: ignore[arg-type]
        )

    def format_result(self, result: FitResult) -> str:
        """Format FitResult for CLI output."""
        lines: list[str] = []
        lines.append(f"{result.company} — {result.job_title}")
        lines.append(f"URL: {result.job_url}")

        source = (
            getattr(result, "score_source", "deterministic") or "deterministic"
        ).upper()
        lines.append(
            "Recommendation: "
            f"{result.recommendation.upper()} "
            f"(score={result.fit_score.total_score:.2f}, source={source})"
        )
        lines.append(
            "Scores: "
            f"must_have={result.fit_score.must_have_score:.2f} "
            f"preferred={result.fit_score.preferred_score:.2f} "
            f"experience={result.fit_score.experience_score:.2f} "
            f"education={result.fit_score.education_score:.2f}"
        )
        if result.fit_score.must_have_matched:
            lines.append(
                f"Must-have matched: {', '.join(result.fit_score.must_have_matched)}"
            )
        if result.fit_score.must_have_missing:
            lines.append(
                f"Must-have missing: {', '.join(result.fit_score.must_have_missing)}"
            )
        if result.fit_score.preferred_matched:
            lines.append(
                f"Preferred matched: {', '.join(result.fit_score.preferred_matched)}"
            )

        if result.fit_score.risk_flags:
            lines.append(f"Risk flags: {', '.join(result.fit_score.risk_flags)}")

        if (
            result.baseline_fit_score is not None
            and result.baseline_recommendation is not None
        ):
            lines.append(
                "Baseline (deterministic): "
                f"{result.baseline_recommendation.upper()} "
                f"(score={result.baseline_fit_score.total_score:.2f})"
            )

        if result.constraints.passed:
            lines.append("Constraints: PASSED")
        else:
            lines.append("Constraints: FAILED")
        if result.constraints.hard_violations:
            lines.append(
                f"Hard violations: {', '.join(result.constraints.hard_violations)}"
            )
        if result.constraints.soft_warnings:
            lines.append(f"Warnings: {', '.join(result.constraints.soft_warnings)}")

        lines.append(f"Reasoning: {result.reasoning}")
        return "\n".join(lines)

    def _check_location_and_work_type(
        self,
        job: JobDescription,
        profile: UserProfile,
        hard_violations: list[str],
        soft_warnings: list[str],
    ) -> None:
        strict = self.config.location_strict

        job_work_type = job.work_type or _infer_work_type_from_location(job.location)
        if job_work_type and job_work_type not in profile.work_type_preferences:
            message = f"Work type '{job_work_type}' not in profile preferences"
            (hard_violations if strict else soft_warnings).append(message)

        if job_work_type == "remote":
            return

        targets = profile.target_locations
        if not targets:
            return

        job_location = (job.location or "").strip()
        if not job_location:
            message = "Job location is missing"
            (hard_violations if strict else soft_warnings).append(message)
            return

        if any(_location_matches(job_location, target) for target in targets):
            return

        message = f"Job location '{job_location}' not in target locations"
        (hard_violations if strict else soft_warnings).append(message)

    def _check_visa(
        self,
        job: JobDescription,
        profile: UserProfile,
        hard_violations: list[str],
        soft_warnings: list[str],
    ) -> None:
        if not profile.visa_sponsorship_needed:
            return

        supports = _job_supports_visa_sponsorship(job)
        if supports is True:
            return

        strict = self.config.visa_strict
        message = "Job may not offer visa sponsorship"
        (hard_violations if strict else soft_warnings).append(message)

    def _check_experience_constraint(
        self,
        job: JobDescription,
        profile: UserProfile,
        hard_violations: list[str],
        soft_warnings: list[str],
    ) -> None:
        years = profile.years_of_experience
        tolerance = max(0, self.config.experience_tolerance_years)

        min_years = job.experience_years_min
        max_years = job.experience_years_max
        if min_years is None and max_years is None:
            return

        if min_years is not None and years < min_years:
            delta = min_years - years
            if delta > tolerance:
                hard_violations.append(f"Below minimum experience by {delta} year(s)")
            else:
                soft_warnings.append(f"Below minimum experience by {delta} year(s)")

        if max_years is not None and years > max_years:
            delta = years - max_years
            if delta > tolerance:
                hard_violations.append(f"Above maximum experience by {delta} year(s)")
            else:
                soft_warnings.append(f"Above maximum experience by {delta} year(s)")

    def _check_salary(
        self,
        job: JobDescription,
        profile: UserProfile,
        hard_violations: list[str],
        soft_warnings: list[str],
    ) -> None:
        min_salary = profile.min_salary
        if min_salary is None:
            return

        if job.salary_min is None and job.salary_max is None:
            return

        if (
            job.salary_currency
            and profile.salary_currency
            and job.salary_currency.upper() != profile.salary_currency.upper()
        ):
            soft_warnings.append(
                "Salary currency mismatch "
                f"(job={job.salary_currency}, profile={profile.salary_currency})"
            )

        below_min = False
        if job.salary_max is not None and job.salary_max < min_salary:
            below_min = True
        elif job.salary_min is not None and job.salary_min < min_salary:
            if job.salary_max is None or job.salary_max < min_salary:
                below_min = True
            else:
                soft_warnings.append(
                    f"Salary range overlaps minimum salary (min_salary={min_salary})"
                )

        if below_min:
            strict = self.config.salary_strict
            message = f"Salary below minimum salary (min_salary={min_salary})"
            (hard_violations if strict else soft_warnings).append(message)


def _education_level(value: str) -> int | None:
    normalized = value.lower().strip()
    if "phd" in normalized or "doctor" in normalized:
        return 5
    if "master" in normalized:
        return 4
    if "bachelor" in normalized:
        return 3
    if "associate" in normalized:
        return 2
    if "high school" in normalized:
        return 1
    return None


def _highest_education_level(profile: UserProfile) -> int | None:
    levels = [_education_level(e.degree) for e in profile.education]
    levels = [level for level in levels if level is not None]
    if not levels:
        return None
    return max(levels)


def _infer_work_type_from_location(location: str | None) -> str | None:
    if not location:
        return None
    value = location.lower()
    if "remote" in value:
        return "remote"
    return None


def _location_matches(job_location: str, target_location: str) -> bool:
    job_norm = job_location.lower().strip()
    target_norm = target_location.lower().strip()
    if not target_norm:
        return False
    return target_norm in job_norm or job_norm in target_norm


def _job_supports_visa_sponsorship(job: JobDescription) -> bool | None:
    text_parts: list[str] = []
    if job.description:
        text_parts.append(job.description)
    if job.qualifications:
        text_parts.extend(job.qualifications)
    if job.responsibilities:
        text_parts.extend(job.responsibilities)

    text = " ".join(text_parts).lower()
    if not text:
        return None

    negative_patterns = [
        "no visa sponsorship",
        "no sponsorship",
        "without sponsorship",
        "cannot sponsor",
        "can't sponsor",
        "do not sponsor",
        "don't sponsor",
        "unable to sponsor",
        "not provide sponsorship",
        "not offer sponsorship",
        "must be authorized to work",
    ]
    if any(pat in text for pat in negative_patterns):
        return False

    positive_patterns = [
        "visa sponsorship available",
        "will sponsor",
        "sponsorship available",
        "we sponsor visas",
        "can sponsor visas",
        "sponsor visa",
    ]
    if any(pat in text for pat in positive_patterns):
        return True

    return None
