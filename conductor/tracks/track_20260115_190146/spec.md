# Specification: Fit Scoring

> Track ID: track_20260115_190146
> Type: Feature
> Priority: High
> Epic Reference: E2-S3 (Fit scoring rules), E2-S4 (Constraint checks)

---

## Overview

Implement a Fit Scoring system that evaluates job-candidate compatibility by matching job requirements from `JobDescription` against a user profile. Uses a weighted scoring algorithm with configurable constraints to produce an apply/skip recommendation.

This track completes Epic E2 (Job Extraction & Fit Scoring) by adding the scoring and constraint logic that consumes the `JobDescription` output from the Job Extractor.

---

## Functional Requirements

### FR-1: User Profile Models

**UserProfile Pydantic Model:**

Basic Info:
- `name: str` - Candidate's full name (required)
- `email: str` - Contact email (required)
- `phone: str | None` - Contact phone
- `location: str` - Current location (city, state/country)
- `linkedin_url: str | None` - LinkedIn profile URL

Skills & Experience:
- `skills: list[str]` - List of all skills/technologies (required)
- `years_of_experience: int` - Total years of professional experience (required)
- `current_title: str` - Current job title
- `summary: str` - Brief professional summary

Work History:
- `work_history: list[WorkExperience]` - Past positions
  - `company: str`
  - `title: str`
  - `start_date: date`
  - `end_date: date | None`
  - `description: str`
  - `skills_used: list[str]`

Education:
- `education: list[Education]` - Degrees/certifications
  - `institution: str`
  - `degree: str` - e.g., "High School", "Associate", "Bachelor's", "Master's", "PhD"
  - `field: str` - e.g., "Computer Science"
  - `graduation_year: int | None`

Constraints (for job filtering):
- `work_type_preferences: list[Literal["remote", "hybrid", "onsite"]]` - Acceptable work types
- `target_locations: list[str] | None` - Acceptable cities/regions (None = any location OK)
- `visa_sponsorship_needed: bool` - Whether candidate requires visa sponsorship
- `min_salary: int | None` - Minimum acceptable salary
- `preferred_salary: int | None` - Target salary
- `salary_currency: str` - Currency code (default: "USD")
- `experience_level: Literal["entry", "mid", "senior", "lead", "executive"]`

### FR-2: Scoring Models

**FitScore** (dataclass):
- `total_score: float` - Overall score 0.0 - 1.0
- `must_have_score: float` - Score for required skills match
- `must_have_matched: list[str]` - Skills that matched
- `must_have_missing: list[str]` - Required skills not found in profile
- `preferred_score: float` - Score for preferred skills match
- `preferred_matched: list[str]` - Preferred skills that matched
- `experience_score: float` - Experience match score
- `experience_reasoning: str` - Explanation of experience score
- `education_score: float` - Education match score
- `education_reasoning: str` - Explanation of education score

**ConstraintResult** (dataclass):
- `passed: bool` - True if all hard constraints passed
- `hard_violations: list[str]` - Reasons for automatic skip
- `soft_warnings: list[str]` - Issues that don't block but should be noted

**FitResult** (dataclass):
- `job_url: str` - URL of the evaluated job
- `job_title: str` - Title of the job
- `company: str` - Company name
- `fit_score: FitScore` - Detailed scoring breakdown
- `constraints: ConstraintResult` - Constraint check results
- `recommendation: Literal["apply", "skip", "review"]` - Final recommendation
- `reasoning: str` - Human-readable explanation
- `evaluated_at: datetime` - Timestamp of evaluation

### FR-3: Configuration

**ScoringConfig** (Pydantic BaseSettings with `SCORING_` prefix):

Profile Settings:
- `profile_path: str` - Path to user profile file (default: "profiles/profile.yaml")

Threshold Settings:
- `fit_score_threshold: float` - Minimum score for "apply" recommendation (default: 0.75)
- `review_margin: float` - Margin around threshold for "review" recommendation (default: 0.05)

Scoring Weights (must sum to 1.0):
- `weight_must_have: float` - Weight for required skills (default: 0.40)
- `weight_preferred: float` - Weight for preferred skills (default: 0.20)
- `weight_experience: float` - Weight for experience match (default: 0.25)
- `weight_education: float` - Weight for education match (default: 0.15)

Matching Settings:
- `skill_fuzzy_match: bool` - Enable fuzzy skill matching (default: True)
- `skill_fuzzy_threshold: float` - Similarity threshold for fuzzy match (default: 0.85)
- `experience_tolerance_years: int` - Tolerance for experience mismatch (default: 2)

Constraint Modes (True = hard constraint causing skip, False = soft warning):
- `location_strict: bool` - Strict location matching (default: False)
- `visa_strict: bool` - Strict visa requirement (default: True)
- `salary_strict: bool` - Strict salary filtering (default: False)

### FR-4: Profile Service

**ProfileService class:**
- `load_profile(path: Path | str | None = None) -> UserProfile` - Load and validate profile from YAML/JSON
- `validate_profile(profile: UserProfile) -> list[str]` - Return warnings for incomplete profile

### FR-5: Scoring Service

**FitScoringService class:**
- `score_skills(job: JobDescription, profile: UserProfile) -> tuple[float, list[str], list[str]]` - Score skill match
- `score_experience(job: JobDescription, profile: UserProfile) -> tuple[float, str]` - Score experience match
- `score_education(job: JobDescription, profile: UserProfile) -> tuple[float, str]` - Score education match
- `calculate_fit_score(job: JobDescription, profile: UserProfile) -> FitScore` - Calculate weighted fit score
- `check_constraints(job: JobDescription, profile: UserProfile) -> ConstraintResult` - Check all constraints
- `evaluate(job: JobDescription, profile: UserProfile) -> FitResult` - Full evaluation with recommendation
- `format_result(result: FitResult) -> str` - Format for CLI output

### FR-6: Skill Matching Utilities

**Matchers module:**
- `normalize_skill(skill: str) -> str` - Normalize skill name (lowercase, strip whitespace)
- `skills_match(skill1: str, skill2: str, fuzzy: bool = True, threshold: float = 0.85) -> bool` - Check if skills match
- `find_matching_skills(required: list[str], available: list[str], fuzzy: bool = True) -> tuple[list[str], list[str]]` - Find matched and missing skills

---

## Non-Functional Requirements

### NFR-1: Performance
- Scoring without LLM: < 100ms per job
- Profile loading: < 50ms

### NFR-2: Configurability
- All weights configurable via environment variables or config file
- All constraint modes toggleable
- Threshold configurable per deployment

### NFR-3: Testability
- Unit tests for each scoring component
- Unit tests for each constraint type
- Integration tests with sample JD + profile combinations
- Minimum 80% code coverage

---

## Acceptance Criteria

1. `UserProfile` Pydantic model validates correctly with all fields
2. Profile loads from YAML/JSON file at configured path
3. Skill matching works case-insensitively with optional fuzzy matching
4. Weighted scoring produces consistent 0.0-1.0 scores
5. Location constraint correctly filters based on work_type and target_locations
6. Visa constraint flags jobs for candidates needing sponsorship
7. Experience constraint filters jobs outside tolerance range
8. Salary constraint filters jobs below minimum salary
9. Recommendation returns apply/skip/review with clear reasoning
10. All settings configurable via environment variables
11. Unit tests pass for all scoring and constraint logic
12. Integration test demonstrates end-to-end scoring flow

---

## Out of Scope

- LLM-based scoring evaluation (uses weighted algorithm only)
- Resume tailoring (covered in E3 Tailoring track)
- Resume parsing from PDF/DOCX (optional future enhancement)
- Multi-profile support (single active profile)
- Historical scoring analytics

---

## Technical Notes

### Integration Points
- Receives `JobDescription` from `/src/extractor/models.py`
- Uses configuration pattern from `/src/config/settings.py`
- Follows module structure from existing codebase

### File Structure
```
/src/scoring/
├── __init__.py        # Exports: FitScoringService, UserProfile, FitResult, etc.
├── models.py          # UserProfile, WorkExperience, Education, FitScore, ConstraintResult, FitResult
├── config.py          # ScoringConfig with singleton pattern
├── profile.py         # ProfileService for loading profiles
├── service.py         # FitScoringService main class
└── matchers.py        # Skill matching utilities

/tests/unit/scoring/
├── __init__.py
├── test_models.py
├── test_config.py
├── test_profile.py
├── test_service.py
└── test_matchers.py

/tests/integration/scoring/
├── __init__.py
└── test_scoring_integration.py

/profiles/
├── profile.example.yaml
└── .gitkeep
```

---

## Dependencies

- **Job Extractor** (track_20260115_044908) - Provides `JobDescription` model
- **Configuration System** (track_20260115_032209) - Settings pattern and utilities
