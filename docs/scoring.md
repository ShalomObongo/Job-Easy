# Scoring Module Documentation

## Overview

The **Scoring Module** (`src/scoring/`) is a core component of Job-Easy that evaluates the fit between job opportunities and a candidate's profile. It provides intelligent job-candidate matching by analyzing skills, experience, education, and various constraints to produce actionable recommendations.

### Purpose

The scoring module serves as a critical decision-making layer in the Job-Easy pipeline:
- **Evaluates job-candidate compatibility** using multi-factor scoring algorithms
- **Enforces hard and soft constraints** (visa, salary, location, work type)
- **Generates actionable recommendations** (apply, skip, review)
- **Prevents wasted effort** on poor-fit opportunities
- **Prioritizes high-quality matches** in autonomous batch processing

### Position in the Job-Easy Pipeline

```
Tracker → Extractor → [SCORING] → Tailoring → Application Runner
```

The scoring module:
1. Receives `JobDescription` from the **Extractor** module
2. Compares against `UserProfile` loaded by the **Profile Service**
3. Outputs `FitResult` with scoring breakdown and recommendation
4. Influences **Runner** and **Autonomous** modules' decision-making
5. Used by **Tailoring** module to access profile data

---

## Architecture

### File Structure

```
src/scoring/
├── __init__.py           # Public API exports
├── models.py             # Data models (UserProfile, FitScore, FitResult, etc.)
├── config.py             # Configuration settings and weights
├── service.py            # FitScoringService - main scoring logic
├── profile.py            # ProfileService - profile loading/validation
└── matchers.py           # Skill matching utilities (fuzzy matching, normalization)
```

### Key Components

1. **FitScoringService** - Main scoring orchestrator
2. **ProfileService** - Profile loading and validation
3. **Skill Matchers** - Fuzzy skill matching and normalization
4. **Configuration** - Weights, thresholds, and constraint modes
5. **Data Models** - Type-safe representations of profiles and results

---

## Core Models

### UserProfile

Comprehensive candidate profile containing personal information, skills, experience, and preferences.

```python
class UserProfile(BaseModel):
    # Basic Info
    name: str
    email: str
    phone: str | None
    location: str
    linkedin_url: str | None

    # Skills & Experience
    skills: list[str]
    years_of_experience: int
    current_title: str
    summary: str

    # History
    work_history: list[WorkExperience]
    education: list[Education]
    certifications: list[Certification]

    # Constraints and Preferences
    work_type_preferences: list[Literal["remote", "hybrid", "onsite"]]
    target_locations: list[str] | None
    visa_sponsorship_needed: bool
    min_salary: int | None
    preferred_salary: int | None
    salary_currency: str
    experience_level: Literal["entry", "mid", "senior", "lead", "executive"]
```

**Profile Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | str | Yes | Candidate full name |
| `email` | str | Yes | Contact email |
| `phone` | str | No | Contact phone |
| `location` | str | Yes | Current location |
| `linkedin_url` | str | No | LinkedIn profile URL |
| `skills` | list[str] | Yes | Skills/technologies |
| `years_of_experience` | int | Yes | Total years of experience (≥0) |
| `current_title` | str | No | Current job title |
| `summary` | str | No | Professional summary |
| `work_history` | list[WorkExperience] | No | Past positions |
| `education` | list[Education] | No | Education history |
| `certifications` | list[Certification] | No | Certifications/training |
| `work_type_preferences` | list[str] | No | Acceptable work types (default: all) |
| `target_locations` | list[str] | No | Acceptable cities/regions (None = any) |
| `visa_sponsorship_needed` | bool | No | Whether sponsorship required (default: False) |
| `min_salary` | int | No | Minimum acceptable salary |
| `preferred_salary` | int | No | Target salary |
| `salary_currency` | str | No | Currency code (default: USD) |
| `experience_level` | str | No | Experience level (default: mid) |

**Related Models:**

```python
class WorkExperience(BaseModel):
    company: str
    title: str
    start_date: date
    end_date: date | None
    description: str
    skills_used: list[str]

class Education(BaseModel):
    institution: str
    degree: str
    field: str
    graduation_year: int | None

class Certification(BaseModel):
    name: str
    issuer: str | None
    date_awarded: date | None
    expires: date | None
    url: str | None
```

### FitScore

Detailed scoring breakdown for a job evaluation.

```python
@dataclass
class FitScore:
    total_score: float                    # Weighted total (0.0-1.0)
    must_have_score: float                # Required skills match (0.0-1.0)
    must_have_matched: list[str]          # Matched required skills
    must_have_missing: list[str]          # Missing required skills
    preferred_score: float                # Preferred skills match (0.0-1.0)
    preferred_matched: list[str]          # Matched preferred skills
    experience_score: float               # Experience match (0.0-1.0)
    experience_reasoning: str             # Explanation of experience score
    education_score: float                # Education match (0.0-1.0)
    education_reasoning: str              # Explanation of education score
```

**Score Components:**

All score components are normalized to `[0.0, 1.0]` range where:
- `1.0` = Perfect match
- `0.5` = Partial match
- `0.0` = No match

### ConstraintResult

Result of evaluating hard/soft constraints against a job.

```python
@dataclass
class ConstraintResult:
    passed: bool                          # Whether all hard constraints passed
    hard_violations: list[str]            # Hard constraint violations (causes skip)
    soft_warnings: list[str]              # Soft warnings (informational only)
```

**Constraint Types:**

- **Hard Violations**: Block application (passed=False)
  - Example: "Job may not offer visa sponsorship" (when visa_strict=True)
  - Example: "Salary below minimum salary" (when salary_strict=True)

- **Soft Warnings**: Informational only (passed=True)
  - Example: "Work type 'onsite' not in profile preferences" (when location_strict=False)
  - Example: "Salary currency mismatch"

### FitResult

Full evaluation result for a job application.

```python
@dataclass
class FitResult:
    job_url: str
    job_title: str
    company: str
    fit_score: FitScore
    constraints: ConstraintResult
    recommendation: Literal["apply", "skip", "review"]
    reasoning: str
    evaluated_at: datetime
```

**Recommendations:**

- **`apply`**: High fit score (≥ threshold), all constraints passed
- **`review`**: Borderline fit score (threshold - margin), all constraints passed
- **`skip`**: Low fit score (< threshold - margin) OR hard constraint violated

---

## Configuration

### ScoringConfig

Configuration settings for the fit scoring system.

```python
class ScoringConfig(BaseSettings):
    # Profile settings
    profile_path: Path = Path("profiles/profile.yaml")

    # Threshold settings
    fit_score_threshold: float = 0.75          # Minimum score for 'apply'
    review_margin: float = 0.05                # Margin for 'review' recommendation

    # Scoring weights (must sum to 1.0)
    weight_must_have: float = 0.40             # Required skills weight
    weight_preferred: float = 0.20             # Preferred skills weight
    weight_experience: float = 0.25            # Experience match weight
    weight_education: float = 0.15             # Education match weight

    # Matching settings
    skill_fuzzy_match: bool = True             # Enable fuzzy skill matching
    skill_fuzzy_threshold: float = 0.85        # Similarity threshold for fuzzy matching
    experience_tolerance_years: int = 2        # Tolerance for experience mismatch

    # Constraint modes
    location_strict: bool = False              # Hard location constraint
    visa_strict: bool = True                   # Hard visa constraint
    salary_strict: bool = False                # Hard salary constraint
```

**Environment Variables:**

All settings can be overridden via environment variables with `SCORING_` prefix:

```bash
export SCORING_FIT_SCORE_THRESHOLD=0.80
export SCORING_WEIGHT_MUST_HAVE=0.50
export SCORING_WEIGHT_PREFERRED=0.15
export SCORING_WEIGHT_EXPERIENCE=0.25
export SCORING_WEIGHT_EDUCATION=0.10
export SCORING_SKILL_FUZZY_THRESHOLD=0.90
export SCORING_VISA_STRICT=true
```

**Configuration Singleton:**

```python
from src.scoring import get_scoring_config, reset_scoring_config

# Get singleton instance
config = get_scoring_config()

# Reset (useful for testing)
reset_scoring_config()
```

---

## Scoring Algorithms

### Overall Fit Score Calculation

The total fit score is a weighted combination of four components:

```
total_score = (weight_must_have × must_have_score) +
              (weight_preferred × preferred_score) +
              (weight_experience × experience_score) +
              (weight_education × education_score)
```

**Default Weights:**
- Must-have skills: 40%
- Preferred skills: 20%
- Experience: 25%
- Education: 15%

**Total = 100%** (validated at runtime)

### 1. Skills Scoring

#### Must-Have Skills (Required Skills)

```
must_have_score = matched_count / total_required_count
```

**Algorithm:**
1. Extract required skills from job description
2. Build candidate's available skills inventory from:
   - Profile's `skills` field
   - `skills_used` from each work experience
   - Inferred skills from text (current_title, summary, work descriptions)
3. Expand candidate skills using skill implications (e.g., React → JavaScript, HTML, CSS)
4. Match required skills against available skills (with optional fuzzy matching)
5. Calculate percentage of required skills matched

**Example:**
```
Job requires: ["Python", "SQL", "Docker"]
Candidate has: ["Python", "SQL", "AWS"]

Matched: ["Python", "SQL"]
Missing: ["Docker"]
Score: 2/3 = 0.667
```

#### Preferred Skills

```
preferred_score = matched_count / total_preferred_count
```

Same algorithm as must-have skills, but for preferred/nice-to-have skills.

**Special Cases:**
- Empty required skills → `must_have_score = 1.0`
- Empty preferred skills → `preferred_score = 1.0`

#### Skill Matching Logic

**Normalization:**
1. Lowercase conversion
2. Whitespace normalization
3. Remove surrounding punctuation (preserve `+`, `#`, `.` for C++, C#, Node.js)
4. Remove content in parentheses

**Canonical Mapping:**
```python
{
    "js": "javascript",
    "nodejs": "node.js",
    "reactjs": "react",
    "nextjs": "next.js",
    "html5": "html",
    "css3": "css",
    "mongo db": "mongodb",
    # ... and more
}
```

**Skill Implications:**
```python
{
    "react": {"javascript", "html", "css"},
    "next.js": {"react", "javascript", "html", "css"},
    "node.js": {"javascript"},
    "full stack development": {"javascript", "html", "css", "testing", "debugging"},
}
```

**Fuzzy Matching:**

When `skill_fuzzy_match=True`, uses `difflib.SequenceMatcher` for similarity:

```python
similarity = SequenceMatcher(None, skill1_canonical, skill2_canonical).ratio()
match = similarity >= skill_fuzzy_threshold  # default 0.85
```

**Examples:**
- "Python" matches "python" (exact after normalization)
- "JavaScript" matches "js" (via alias)
- "PostgreSQL" matches "postgres" (0.89 similarity)
- "React" implies "javascript", "html", "css" (skill expansion)

### 2. Experience Scoring

```python
def score_experience(job: JobDescription, profile: UserProfile) -> (float, str):
    tolerance = experience_tolerance_years  # default: 2 years
    years = profile.years_of_experience
    min_years = job.experience_years_min
    max_years = job.experience_years_max

    if no requirements:
        return 1.0, "No experience requirement"

    if years < min_years:
        delta = min_years - years
        if delta > tolerance:
            return 0.0, f"Below minimum experience by {delta} year(s)"
        score = 1.0 - (delta / (tolerance + 1))
        return score, f"Below minimum experience by {delta} year(s)"

    if years > max_years:
        delta = years - max_years
        if delta > tolerance:
            return 0.0, f"Above maximum experience by {delta} year(s)"
        score = 1.0 - (delta / (tolerance + 1))
        return score, f"Above maximum experience by {delta} year(s)"

    return 1.0, "Within required experience range"
```

**Scoring Logic:**

| Condition | Score | Reasoning |
|-----------|-------|-----------|
| No requirement | 1.0 | "No experience requirement" |
| Within range | 1.0 | "Within required experience range" |
| 1 year below (tolerance=2) | 0.67 | "Below minimum experience by 1 year(s)" |
| 2 years below | 0.33 | "Below minimum experience by 2 year(s)" |
| 3+ years below | 0.0 | "Below minimum experience by 3 year(s)" |
| Same for above max | ... | ... |

**Examples:**

```
# Job requires 3-5 years, candidate has 5 years, tolerance=2
→ Score: 1.0 (within range)

# Job requires 5+ years, candidate has 4 years, tolerance=2
→ Score: 0.67 (1 year below, within tolerance)

# Job requires 3+ years, candidate has 0 years, tolerance=2
→ Score: 0.0 (3 years below, exceeds tolerance)
```

### 3. Education Scoring

```python
def score_education(job: JobDescription, profile: UserProfile) -> (float, str):
    required = job.education
    if not required:
        return 1.0, "No education requirement"

    required_level = _education_level(required)
    profile_level = _highest_education_level(profile)

    if profile_level >= required_level:
        return 1.0, "Meets education requirement"

    diff = required_level - profile_level
    if diff == 1:
        return 0.5, "One level below education requirement"

    return 0.0, "Below education requirement"
```

**Education Levels:**

| Level | Value | Keywords |
|-------|-------|----------|
| PhD/Doctorate | 5 | "phd", "doctor" |
| Master's | 4 | "master" |
| Bachelor's | 3 | "bachelor" |
| Associate's | 2 | "associate" |
| High School | 1 | "high school" |
| Unknown | None | - |

**Scoring Logic:**

| Condition | Score | Reasoning |
|-----------|-------|-----------|
| No requirement | 1.0 | "No education requirement" |
| Profile ≥ required | 1.0 | "Meets education requirement" |
| 1 level below | 0.5 | "One level below education requirement" |
| 2+ levels below | 0.0 | "Below education requirement" |
| No education listed | 0.0 | "No education listed" |

**Examples:**

```
# Job requires Bachelor's, candidate has Master's
→ Score: 1.0 (exceeds requirement)

# Job requires Master's, candidate has Bachelor's
→ Score: 0.5 (one level below)

# Job requires Master's, candidate has High School
→ Score: 0.0 (two levels below)
```

---

## Constraint Evaluation

Constraints are evaluated independently of scoring and can cause a job to be skipped regardless of fit score.

### Constraint Types

Each constraint can be configured as:
- **Hard constraint** (`strict=True`): Violation causes `passed=False` and "skip" recommendation
- **Soft warning** (`strict=False`): Violation adds to `soft_warnings` but allows application

### 1. Location and Work Type Constraints

```python
def _check_location_and_work_type(
    job: JobDescription,
    profile: UserProfile,
    hard_violations: list[str],
    soft_warnings: list[str],
) -> None:
    strict = config.location_strict  # default: False

    # Check work type preference
    job_work_type = job.work_type or _infer_work_type_from_location(job.location)
    if job_work_type and job_work_type not in profile.work_type_preferences:
        message = f"Work type '{job_work_type}' not in profile preferences"
        (hard_violations if strict else soft_warnings).append(message)

    # Remote jobs skip location check
    if job_work_type == "remote":
        return

    # Check location match
    targets = profile.target_locations
    if not targets:
        return  # None = any location acceptable

    job_location = job.location or ""
    if not job_location:
        message = "Job location is missing"
        (hard_violations if strict else soft_warnings).append(message)
        return

    if any(_location_matches(job_location, target) for target in targets):
        return  # Location matches

    message = f"Job location '{job_location}' not in target locations"
    (hard_violations if strict else soft_warnings).append(message)
```

**Location Matching:**
- Case-insensitive substring matching
- "New York, NY" matches target "New York"
- "San Francisco" matches target "San Francisco, CA"

**Work Type Inference:**
- If `job.location` contains "remote" → infer "remote"
- Otherwise use `job.work_type` or None

### 2. Visa Sponsorship Constraints

```python
def _check_visa(
    job: JobDescription,
    profile: UserProfile,
    hard_violations: list[str],
    soft_warnings: list[str],
) -> None:
    if not profile.visa_sponsorship_needed:
        return  # No check needed

    supports = _job_supports_visa_sponsorship(job)
    if supports is True:
        return  # Job explicitly supports visa

    strict = config.visa_strict  # default: True
    message = "Job may not offer visa sponsorship"
    (hard_violations if strict else soft_warnings).append(message)
```

**Visa Sponsorship Detection:**

Searches job description, qualifications, and responsibilities for patterns:

**Negative Patterns** (returns False):
- "no visa sponsorship"
- "no sponsorship"
- "cannot sponsor"
- "can't sponsor"
- "must be authorized to work"
- "without sponsorship"

**Positive Patterns** (returns True):
- "visa sponsorship available"
- "will sponsor"
- "sponsorship available"
- "we sponsor visas"
- "can sponsor visas"

**Ambiguous** (returns None):
- No clear indication → treated as "may not offer" with warning

### 3. Experience Constraints

```python
def _check_experience_constraint(
    job: JobDescription,
    profile: UserProfile,
    hard_violations: list[str],
    soft_warnings: list[str],
) -> None:
    years = profile.years_of_experience
    tolerance = config.experience_tolerance_years  # default: 2

    min_years = job.experience_years_min
    max_years = job.experience_years_max

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
```

**Constraint Logic:**

- Within tolerance → soft warning
- Exceeds tolerance → hard violation

**Example:**

```
# tolerance = 2 years

Job requires 5+ years, candidate has 4 years
→ Soft warning: "Below minimum experience by 1 year(s)"

Job requires 5+ years, candidate has 2 years
→ Hard violation: "Below minimum experience by 3 year(s)"

Job requires 3-5 years, candidate has 8 years
→ Hard violation: "Above maximum experience by 3 year(s)"
```

### 4. Salary Constraints

```python
def _check_salary(
    job: JobDescription,
    profile: UserProfile,
    hard_violations: list[str],
    soft_warnings: list[str],
) -> None:
    min_salary = profile.min_salary
    if min_salary is None:
        return  # No minimum salary specified

    if job.salary_min is None and job.salary_max is None:
        return  # No salary information available

    # Check currency mismatch
    if (job.salary_currency and profile.salary_currency and
        job.salary_currency.upper() != profile.salary_currency.upper()):
        soft_warnings.append(
            f"Salary currency mismatch (job={job.salary_currency}, profile={profile.salary_currency})"
        )

    # Check if salary is below minimum
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
        strict = config.salary_strict  # default: False
        message = f"Salary below minimum salary (min_salary={min_salary})"
        (hard_violations if strict else soft_warnings).append(message)
```

**Salary Logic:**

| Job Salary Range | Profile Min | Result |
|------------------|-------------|--------|
| 100k-150k | 120k | Soft warning: overlaps |
| 80k-100k | 120k | Below min |
| 130k-160k | 120k | Pass |
| Not disclosed | Any | Pass (no check) |

---

## Recommendation Logic

The final recommendation combines fit score and constraint results:

```python
def evaluate(job: JobDescription, profile: UserProfile) -> FitResult:
    fit_score = calculate_fit_score(job, profile)
    constraints = check_constraints(job, profile)

    threshold = config.fit_score_threshold  # default: 0.75
    margin = config.review_margin          # default: 0.05

    if not constraints.passed:
        recommendation = "skip"
    elif fit_score.total_score >= threshold:
        recommendation = "apply"
    elif fit_score.total_score >= (threshold - margin):
        recommendation = "review"
    else:
        recommendation = "skip"

    # Generate reasoning string
    reasoning_parts = [
        f"fit_score={fit_score.total_score:.2f} threshold={threshold:.2f}"
    ]
    if fit_score.must_have_missing:
        reasoning_parts.append(
            f"missing_required_skills={', '.join(fit_score.must_have_missing)}"
        )
    if not constraints.passed:
        reasoning_parts.append(
            f"hard_violations={'; '.join(constraints.hard_violations)}"
        )
    elif constraints.soft_warnings:
        reasoning_parts.append(
            f"warnings={'; '.join(constraints.soft_warnings)}"
        )

    reasoning = " | ".join(reasoning_parts)

    return FitResult(...)
```

### Decision Boundaries

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  Constraint Violation?                              │
│  ├─ YES → "skip" (regardless of score)              │
│  └─ NO → Check fit score:                           │
│           ├─ ≥ 0.75 (threshold)       → "apply"     │
│           ├─ ≥ 0.70 (threshold-margin) → "review"   │
│           └─ < 0.70                    → "skip"     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Thresholds (default):**
- Apply: ≥ 0.75
- Review: 0.70-0.74
- Skip: < 0.70 OR constraint violation

**Customizable:**
```bash
export SCORING_FIT_SCORE_THRESHOLD=0.80
export SCORING_REVIEW_MARGIN=0.10
# Apply: ≥ 0.80, Review: 0.70-0.79, Skip: < 0.70
```

---

## API Reference

### FitScoringService

Main service for computing fit scores and recommendations.

```python
class FitScoringService:
    def __init__(self, config: ScoringConfig | None = None) -> None:
        """Initialize with optional custom configuration."""

    def score_skills(
        self, job: JobDescription, profile: UserProfile
    ) -> tuple[float, list[str], list[str], float, list[str]]:
        """Score required and preferred skills against a profile.

        Returns:
            (must_have_score, must_have_matched, must_have_missing,
             preferred_score, preferred_matched)
        """

    def score_experience(
        self, job: JobDescription, profile: UserProfile
    ) -> tuple[float, str]:
        """Score experience match between job requirements and profile.

        Returns:
            (score, reasoning)
        """

    def score_education(
        self, job: JobDescription, profile: UserProfile
    ) -> tuple[float, str]:
        """Score education match between job requirements and profile.

        Returns:
            (score, reasoning)
        """

    def calculate_fit_score(
        self, job: JobDescription, profile: UserProfile
    ) -> FitScore:
        """Calculate weighted fit score with detailed breakdown."""

    def check_constraints(
        self, job: JobDescription, profile: UserProfile
    ) -> ConstraintResult:
        """Check constraints and return hard violations and soft warnings."""

    def evaluate(
        self, job: JobDescription, profile: UserProfile
    ) -> FitResult:
        """Run full evaluation: scoring, constraints, and recommendation."""

    def format_result(self, result: FitResult) -> str:
        """Format FitResult for CLI output."""
```

**Usage Example:**

```python
from src.scoring import FitScoringService
from src.extractor.models import JobDescription

service = FitScoringService()

job = JobDescription(
    company="ExampleCo",
    role_title="Backend Engineer",
    job_url="https://example.com/jobs/123",
    required_skills=["Python", "SQL", "AWS"],
    preferred_skills=["Docker", "Kubernetes"],
    experience_years_min=3,
    experience_years_max=6,
    education="Bachelor's",
    work_type="remote",
    salary_min=130000,
    salary_max=160000,
    salary_currency="USD",
)

profile = profile_service.load_profile()
result = service.evaluate(job, profile)

print(f"Recommendation: {result.recommendation}")
print(f"Fit Score: {result.fit_score.total_score:.2f}")
print(f"Reasoning: {result.reasoning}")
```

### ProfileService

Service for loading and validating user profiles.

```python
class ProfileService:
    def __init__(self, config: ScoringConfig | None = None) -> None:
        """Initialize with optional custom configuration."""

    def load_profile(self, path: Path | str | None = None) -> UserProfile:
        """Load and validate a profile from YAML or JSON.

        Args:
            path: Path to profile file. If None, uses config.profile_path.

        Returns:
            UserProfile instance.

        Raises:
            FileNotFoundError: If profile file doesn't exist.
            ValidationError: If profile data is invalid.
        """

    def validate_profile(self, profile: UserProfile) -> list[str]:
        """Return warnings for incomplete profiles.

        Returns:
            List of warning messages for missing optional fields.
        """
```

**Usage Example:**

```python
from src.scoring import ProfileService
from pathlib import Path

service = ProfileService()

# Load from default path (profiles/profile.yaml)
profile = service.load_profile()

# Load from custom path
profile = service.load_profile(Path("profiles/custom.yaml"))

# Validate profile
warnings = service.validate_profile(profile)
if warnings:
    print("Profile warnings:", warnings)
```

### Skill Matching Functions

```python
def normalize_skill(skill: str) -> str:
    """Normalize a skill string for comparison.

    Performs lowercasing, whitespace normalization, and trims common
    surrounding punctuation while preserving meaningful characters
    like '+', '#', and '.' (e.g. 'C++', 'C#', 'Node.js').
    """

def skills_match(
    skill1: str, skill2: str, fuzzy: bool = True, threshold: float = 0.85
) -> bool:
    """Return True if two skills are considered a match."""

def find_matching_skills(
    required: list[str],
    available: list[str],
    fuzzy: bool = True,
    threshold: float = 0.85,
) -> tuple[list[str], list[str]]:
    """Return the subset of required skills that match, and those missing.

    Returns:
        (matched, missing)
    """

def expand_skills(skills: list[str]) -> list[str]:
    """Return a normalized + inferred list of skills for matching.

    Used by fit scoring to infer high-confidence fundamentals for common stacks
    (e.g. 'React' implies 'JavaScript/HTML/CSS').
    """
```

**Usage Example:**

```python
from src.scoring.matchers import find_matching_skills, expand_skills

required = ["Python", "SQL", "Docker"]
available = ["python", "postgresql", "aws"]

matched, missing = find_matching_skills(
    required, available, fuzzy=True, threshold=0.85
)
print(f"Matched: {matched}")  # ["Python", "SQL"]
print(f"Missing: {missing}")  # ["Docker"]

# Expand skills with implications
expanded = expand_skills(["React", "Next.js"])
print(expanded)  # ["css", "html", "javascript", "next.js", "react"]
```

---

## Dependencies

### Internal Dependencies

The scoring module depends on other Job-Easy modules:

| Module | Usage | Import |
|--------|-------|--------|
| **extractor** | JobDescription model | `from src.extractor.models import JobDescription` |

The scoring module is used by:

| Module | Usage |
|--------|-------|
| **runner** | Evaluate fit before applying, HITL gates for skip/review |
| **autonomous** | Build queue, filter by min_score, rank by fit score |
| **tailoring** | Access UserProfile for resume/cover letter generation |
| **hitl** | Display fit results for user confirmation |

### External Dependencies

```toml
# pyproject.toml
pydantic = "^2.0"           # Data models and validation
pydantic-settings = "^2.0"  # Configuration management
pyyaml = "^6.0"             # YAML profile parsing
```

**Standard Library:**
- `dataclasses` - FitScore, ConstraintResult, FitResult
- `datetime` - Timestamp tracking
- `difflib.SequenceMatcher` - Fuzzy skill matching
- `pathlib` - File path handling
- `re` - Skill normalization and text extraction
- `json` - JSON profile parsing

---

## Integration with Other Modules

### 1. Extractor Module

**Dependency Flow:** Extractor → Scoring

```python
from src.extractor.models import JobDescription

# Extractor provides JobDescription
job = await extractor.extract(url)

# Scoring evaluates JobDescription
result = scoring_service.evaluate(job, profile)
```

**Key Fields Used:**
- `required_skills`, `preferred_skills` - Skills scoring
- `experience_years_min`, `experience_years_max` - Experience scoring
- `education` - Education scoring
- `location`, `work_type` - Location constraints
- `salary_min`, `salary_max`, `salary_currency` - Salary constraints
- `description`, `qualifications`, `responsibilities` - Visa detection

### 2. Runner Module

**Dependency Flow:** Runner → Scoring

```python
from src.runner.service import SingleJobApplicationService

# Runner uses scoring for fit evaluation
profile = profile_service.load_profile()
fit = scoring_service.evaluate(job, profile)

# HITL gate for "skip" recommendation
if fit.recommendation == "skip":
    proceed = hitl.prompt_yes_no(
        f"Fit scoring recommends SKIP. Proceed anyway?\n{fit.reasoning}"
    )
    if not proceed:
        await tracker_service.update_status(fingerprint, ApplicationStatus.SKIPPED)
        return ApplicationRunResult(success=True, status=RunStatus.SKIPPED)

# HITL gate for "review" recommendation
if fit.recommendation == "review":
    proceed = hitl.prompt_yes_no(
        f"Fit score recommends REVIEW. Proceed?\n{fit.reasoning}"
    )
    if not proceed:
        await tracker_service.update_status(fingerprint, ApplicationStatus.SKIPPED)
        return ApplicationRunResult(success=True, status=RunStatus.SKIPPED)
```

**Key Integration Points:**
- Load profile via `ProfileService`
- Evaluate fit via `FitScoringService.evaluate()`
- Display results via `FitScoringService.format_result()`
- HITL gates for skip/review recommendations
- Update tracker based on recommendation

### 3. Autonomous Module

**Dependency Flow:** Autonomous → Scoring

```python
from src.autonomous.queue import QueueManager

# Queue builder uses scoring to filter and rank jobs
queue = await queue_manager.build_queue(
    leads,
    tracker_service=tracker_service,
    extractor=extractor,
    scorer=scoring_service,  # FitScoringService
    profile=profile,
    min_score=min_score,     # Filter threshold
    include_skips=include_skips,
)

# Queue is sorted by fit score (highest first)
queue.sort(key=lambda item: item.fit_result.fit_score.total_score, reverse=True)
```

**Key Integration Points:**
- Evaluate fit for each lead: `scorer.evaluate(job, profile)`
- Filter by recommendation: skip jobs with `recommendation == "skip"` (unless `include_skips=True`)
- Filter by score: skip jobs with `total_score < min_score`
- Rank by score: sort queue by `fit_score.total_score` descending
- Cache results: store `(job, fit)` tuples to avoid re-evaluation

### 4. Tailoring Module

**Dependency Flow:** Tailoring → Scoring (UserProfile only)

```python
from src.scoring.models import UserProfile

# Tailoring uses UserProfile for resume/cover letter generation
async def tailor(
    profile: UserProfile,
    job: JobDescription,
    generate_cover_letter: bool = True,
) -> TailoringResult:
    # Use profile.name, profile.skills, profile.work_history, etc.
    plan = await plan_service.generate_plan(profile, job)
    resume = await resume_service.tailor_resume(profile, job, plan)
    cover_letter = await cover_letter_service.generate_cover_letter(profile, job, plan)
```

**Key Integration Points:**
- Import `UserProfile` model
- Use profile data for tailoring content
- No direct scoring logic usage

### 5. Tracker Module

**Dependency Flow:** Tracker ← Scoring (indirect via Runner)

```python
# Tracker stores application status based on scoring recommendations
if fit.recommendation == "skip":
    await tracker_service.update_status(fingerprint, ApplicationStatus.SKIPPED)
```

**Key Integration Points:**
- No direct dependency
- Indirect through Runner's use of scoring results

---

## Usage Examples

### Basic Scoring

```python
from src.scoring import FitScoringService, ProfileService
from src.extractor.models import JobDescription

# Load profile
profile_service = ProfileService()
profile = profile_service.load_profile()

# Create job description
job = JobDescription(
    company="TechCorp",
    role_title="Senior Python Engineer",
    job_url="https://example.com/jobs/123",
    required_skills=["Python", "Django", "PostgreSQL"],
    preferred_skills=["AWS", "Docker"],
    experience_years_min=5,
    experience_years_max=8,
    education="Bachelor's",
    work_type="remote",
    salary_min=140000,
    salary_max=180000,
    salary_currency="USD",
)

# Evaluate fit
scoring_service = FitScoringService()
result = scoring_service.evaluate(job, profile)

# Display results
print(scoring_service.format_result(result))
```

**Output:**
```
TechCorp — Senior Python Engineer
URL: https://example.com/jobs/123
Recommendation: APPLY (score=0.89)
Scores: must_have=1.00 preferred=0.50 experience=1.00 education=1.00
Must-have matched: Python, Django, PostgreSQL
Preferred matched: Docker
Constraints: PASSED
Reasoning: fit_score=0.89 threshold=0.75
```

### Custom Configuration

```python
from src.scoring import FitScoringService, ScoringConfig
from pathlib import Path

# Custom configuration
config = ScoringConfig(
    profile_path=Path("profiles/senior.yaml"),
    fit_score_threshold=0.80,
    review_margin=0.10,
    weight_must_have=0.50,
    weight_preferred=0.15,
    weight_experience=0.25,
    weight_education=0.10,
    skill_fuzzy_threshold=0.90,
    experience_tolerance_years=1,
    location_strict=True,
    visa_strict=True,
    salary_strict=True,
)

service = FitScoringService(config=config)
result = service.evaluate(job, profile)
```

### Component Scoring

```python
from src.scoring import FitScoringService

service = FitScoringService()

# Score skills only
must_score, must_matched, must_missing, pref_score, pref_matched = \
    service.score_skills(job, profile)

print(f"Must-have: {must_score:.2f}")
print(f"  Matched: {must_matched}")
print(f"  Missing: {must_missing}")
print(f"Preferred: {pref_score:.2f}")
print(f"  Matched: {pref_matched}")

# Score experience only
exp_score, exp_reasoning = service.score_experience(job, profile)
print(f"Experience: {exp_score:.2f} - {exp_reasoning}")

# Score education only
edu_score, edu_reasoning = service.score_education(job, profile)
print(f"Education: {edu_score:.2f} - {edu_reasoning}")

# Check constraints only
constraints = service.check_constraints(job, profile)
print(f"Passed: {constraints.passed}")
if constraints.hard_violations:
    print(f"Violations: {constraints.hard_violations}")
if constraints.soft_warnings:
    print(f"Warnings: {constraints.soft_warnings}")
```

### Batch Processing

```python
from src.scoring import FitScoringService, ProfileService
from src.extractor.models import JobDescription

service = FitScoringService()
profile = ProfileService().load_profile()

jobs = [...]  # List of JobDescription objects

results = [service.evaluate(job, profile) for job in jobs]

# Filter by recommendation
apply_jobs = [r for r in results if r.recommendation == "apply"]
review_jobs = [r for r in results if r.recommendation == "review"]
skip_jobs = [r for r in results if r.recommendation == "skip"]

# Sort by score
ranked = sorted(results, key=lambda r: r.fit_score.total_score, reverse=True)

print(f"Apply: {len(apply_jobs)}")
print(f"Review: {len(review_jobs)}")
print(f"Skip: {len(skip_jobs)}")

# Top 5 jobs
for result in ranked[:5]:
    print(f"{result.fit_score.total_score:.2f} - {result.company} - {result.job_title}")
```

### Profile Validation

```python
from src.scoring import ProfileService

service = ProfileService()
profile = service.load_profile()

# Validate profile
warnings = service.validate_profile(profile)

if warnings:
    print("Profile has warnings:")
    for warning in warnings:
        print(f"  - {warning}")
else:
    print("Profile is complete!")

# Profile info
print(f"Name: {profile.name}")
print(f"Email: {profile.email}")
print(f"Skills: {', '.join(profile.skills)}")
print(f"Experience: {profile.years_of_experience} years")
print(f"Education: {len(profile.education)} degree(s)")
print(f"Work History: {len(profile.work_history)} position(s)")
```

---

## Command-Line Interface

### Score Command

```bash
# Score a job against profile
python -m src score --jd artifacts/runs/<run_id>/jd.json --profile profiles/profile.yaml

# Score with custom output directory
python -m src score --jd jd.json --profile profile.yaml --out-run-dir ./output

# Score with custom profile
python -m src score --jd jd.json --profile profiles/senior.yaml
```

**Output Files:**
- `fit_result.json` - Full FitResult JSON
- Console output - Formatted scoring summary

**Example Output:**
```
TechCorp — Senior Backend Engineer
URL: https://example.com/jobs/123
Recommendation: APPLY (score=0.87)
Scores: must_have=0.90 preferred=0.75 experience=1.00 education=1.00
Must-have matched: Python, Django, PostgreSQL, Redis
Must-have missing: Kubernetes
Preferred matched: AWS, Docker, CI/CD
Constraints: PASSED
Warnings: Salary currency mismatch (job=EUR, profile=USD)
Reasoning: fit_score=0.87 threshold=0.75 | warnings=Salary currency mismatch (job=EUR, profile=USD)
```

### Queue Command

```bash
# Build ranked queue from leads file
python -m src queue leads.txt --profile profiles/profile.yaml

# Filter by minimum score
python -m src queue leads.txt --profile profile.yaml --min-score 0.80

# Include jobs marked as "skip"
python -m src queue leads.txt --profile profile.yaml --include-skips

# Limit queue size
python -m src queue leads.txt --profile profile.yaml --limit 10

# Output to custom directory
python -m src queue leads.txt --profile profile.yaml --out-run-dir ./output
```

**Output Files:**
- `queue.json` - Ranked queue with fit results

**Example Output:**
```
Queue built: 15 jobs (from 50 leads)
  - Duplicates skipped: 10
  - Below threshold: 20
  - Below min-score: 5

Top 5 jobs:
1. 0.92 - TechCorp - Senior Python Engineer
2. 0.89 - DataCo - Backend Engineer
3. 0.85 - CloudCorp - Software Engineer
4. 0.82 - StartupCo - Full Stack Engineer
5. 0.78 - EnterpriseCo - Python Developer
```

---

## Testing

### Unit Tests

Located in `tests/unit/scoring/`:

```bash
# Run all scoring tests
pytest tests/unit/scoring/

# Run specific test file
pytest tests/unit/scoring/test_service.py

# Run specific test
pytest tests/unit/scoring/test_service.py::TestScoreSkills::test_score_skills_must_have_100_percent_match_returns_one
```

**Test Coverage:**
- `test_service.py` - FitScoringService logic
- `test_profile.py` - ProfileService loading/validation
- `test_matchers.py` - Skill matching algorithms
- `test_config.py` - Configuration validation
- `test_models.py` - Data model validation

### Integration Tests

Located in `tests/integration/scoring/`:

```bash
# Run integration tests
pytest tests/integration/scoring/

# Run specific integration test
pytest tests/integration/scoring/test_scoring_integration.py::test_scoring_integration_apply_recommendation
```

**Integration Test Scenarios:**
- End-to-end evaluation with real profile
- Apply recommendation for strong match
- Skip recommendation for poor match
- Review recommendation for borderline match
- Constraint violation scenarios

### Test Profile

Use `profiles/profile.example.yaml` for testing:

```yaml
name: "Jane Doe"
email: "jane.doe@example.com"
location: "New York, NY"
skills: ["Python", "SQL", "AWS", "Docker", "PostgreSQL"]
years_of_experience: 5
current_title: "Software Engineer"
work_history:
  - company: "ExampleCo"
    title: "Software Engineer"
    start_date: 2021-06-01
    description: "Built backend APIs and data pipelines."
    skills_used: ["Python", "PostgreSQL", "AWS"]
education:
  - institution: "Example University"
    degree: "Bachelor's"
    field: "Computer Science"
    graduation_year: 2019
work_type_preferences: ["remote", "hybrid"]
min_salary: 120000
salary_currency: "USD"
```

---

## Error Handling

### Common Errors

#### ProfileService Errors

```python
# FileNotFoundError - Profile not found
try:
    profile = service.load_profile(Path("nonexistent.yaml"))
except FileNotFoundError as e:
    print(f"Profile not found: {e}")

# ValidationError - Invalid profile data
try:
    profile = service.load_profile(Path("invalid.yaml"))
except pydantic.ValidationError as e:
    print(f"Invalid profile: {e}")
```

#### ScoringConfig Errors

```python
# ValueError - Weights don't sum to 1.0
try:
    config = ScoringConfig(
        weight_must_have=0.50,
        weight_preferred=0.20,
        weight_experience=0.20,
        weight_education=0.20,  # Sum = 1.10
    )
except ValueError as e:
    print(f"Invalid weights: {e}")
    # "Scoring weights must sum to 1.0. Got 1.100000..."

# ValueError - Invalid threshold
try:
    config = ScoringConfig(fit_score_threshold=1.5)
except ValueError as e:
    print(f"Invalid threshold: {e}")
```

#### FitScore Errors

```python
# ValueError - Score out of range
try:
    score = FitScore(
        total_score=1.5,  # Must be 0.0-1.0
        must_have_score=1.0,
    )
except ValueError as e:
    print(f"Invalid score: {e}")
    # "total_score must be between 0.0 and 1.0 (got 1.5)"
```

#### ConstraintResult Errors

```python
# ValueError - Inconsistent state
try:
    constraints = ConstraintResult(
        passed=True,
        hard_violations=["Some violation"],  # Can't be True with violations
    )
except ValueError as e:
    print(f"Invalid constraints: {e}")
    # "ConstraintResult.passed=True is incompatible with hard_violations"
```

---

## Performance Considerations

### Skill Matching Performance

**Optimization:**
- Skills are normalized and canonicalized once
- Fuzzy matching uses efficient `difflib.SequenceMatcher`
- Skill expansion is cached within single evaluation

**Complexity:**
- Normalization: O(n) where n = number of skills
- Exact matching: O(n × m) where n = required, m = available
- Fuzzy matching: O(n × m × k) where k = average skill length

**Recommendation:**
- Keep skill lists concise (< 50 skills)
- Use exact matching for large-scale batch processing
- Enable fuzzy matching for better user experience

### Batch Processing

```python
# Efficient batch scoring
service = FitScoringService()  # Reuse service instance
profile = ProfileService().load_profile()  # Load profile once

results = [service.evaluate(job, profile) for job in jobs]
```

**Best Practices:**
- Reuse `FitScoringService` instance
- Load profile once, evaluate many jobs
- Use multiprocessing for very large batches (100+ jobs)

### Caching

The autonomous module caches extraction and scoring results:

```python
# QueueManager caches (job, fit) tuples
cache: dict[str, tuple[Any, Any]] = {}

for lead in valid_leads:
    if lead.url in cache:
        job, fit = cache[lead.url]  # Reuse cached result
    else:
        job = await extractor.extract(lead.url)
        fit = await scorer.evaluate(job, profile)
        cache[lead.url] = (job, fit)  # Cache for future use
```

---

## Best Practices

### 1. Profile Maintenance

**Keep profiles up-to-date:**
- Update skills regularly as you learn new technologies
- Add recent work experience and certifications
- Review and adjust constraints (location, salary, work type)

**Use specific skills:**
```yaml
# Good
skills:
  - "Python 3.11"
  - "Django 4.2"
  - "PostgreSQL 15"
  - "AWS EC2"
  - "Docker Compose"

# Avoid vague skills
skills:
  - "Programming"
  - "Web Development"
  - "Cloud"
```

### 2. Configuration Tuning

**Adjust weights based on priorities:**
```python
# Prioritize required skills over experience
config = ScoringConfig(
    weight_must_have=0.50,  # Increase from 0.40
    weight_preferred=0.15,  # Decrease from 0.20
    weight_experience=0.20,  # Decrease from 0.25
    weight_education=0.15,
)

# Prioritize experience for senior roles
config = ScoringConfig(
    weight_must_have=0.30,
    weight_preferred=0.15,
    weight_experience=0.40,  # Increase from 0.25
    weight_education=0.15,
)
```

**Adjust thresholds for filtering:**
```python
# Stricter filtering (fewer applications)
config = ScoringConfig(
    fit_score_threshold=0.85,  # Increase from 0.75
    review_margin=0.05,
)

# Relaxed filtering (more applications)
config = ScoringConfig(
    fit_score_threshold=0.65,  # Decrease from 0.75
    review_margin=0.10,
)
```

### 3. Constraint Configuration

**Use strict mode for critical constraints:**
```python
config = ScoringConfig(
    visa_strict=True,     # Block non-sponsoring jobs
    salary_strict=True,   # Block below-minimum salary jobs
    location_strict=False,  # Allow location flexibility
)
```

**Use soft warnings for flexible constraints:**
```python
config = ScoringConfig(
    visa_strict=False,    # Warn but don't block
    salary_strict=False,  # Warn but don't block
    location_strict=False,
)
```

### 4. Skill Matching

**Enable fuzzy matching for better coverage:**
```python
config = ScoringConfig(
    skill_fuzzy_match=True,
    skill_fuzzy_threshold=0.85,  # Balanced threshold
)
```

**Adjust fuzzy threshold:**
```python
# Stricter matching (fewer false positives)
config = ScoringConfig(
    skill_fuzzy_threshold=0.95,
)

# Relaxed matching (more matches, some false positives)
config = ScoringConfig(
    skill_fuzzy_threshold=0.75,
)
```

### 5. Recommendation Review

**Always review borderline cases:**
- Don't blindly trust "apply" recommendations
- Review "review" recommendations carefully
- Consider overriding "skip" for interesting roles

**Use HITL gates:**
```python
# Runner automatically prompts for skip/review
if fit.recommendation == "skip":
    proceed = hitl.prompt_yes_no(
        f"Fit scoring recommends SKIP. Proceed anyway?\n{fit.reasoning}"
    )
```

---

## Troubleshooting

### Profile Not Loading

**Problem:** `FileNotFoundError: Profile not found`

**Solutions:**
1. Check file path: `ls -la profiles/profile.yaml`
2. Verify file permissions: `chmod 644 profiles/profile.yaml`
3. Use absolute path: `service.load_profile(Path("/full/path/to/profile.yaml"))`
4. Check environment variable: `echo $SCORING_PROFILE_PATH`

### Invalid Profile Data

**Problem:** `ValidationError: Invalid profile`

**Solutions:**
1. Check YAML syntax: `yamllint profiles/profile.yaml`
2. Validate dates: Use `YYYY-MM-DD` format
3. Check required fields: `name`, `email`, `location`, `skills`, `years_of_experience`
4. Review field types: Ensure integers are not quoted, lists use `- item` syntax

**Example:**
```yaml
# Correct
years_of_experience: 5
skills:
  - "Python"
  - "SQL"

# Incorrect
years_of_experience: "5"  # Should be int, not string
skills: Python, SQL       # Should be list, not string
```

### Low Fit Scores

**Problem:** All jobs score below threshold

**Solutions:**
1. Update profile skills: Add more relevant skills
2. Adjust weights: Increase weight for strongest areas
3. Lower threshold: Decrease `fit_score_threshold`
4. Review skill matching: Enable fuzzy matching
5. Check skill normalization: Ensure skills match canonical forms

### Skill Matching Issues

**Problem:** Known skills not matching

**Solutions:**
1. Check skill normalization: `normalize_skill("PostgreSQL")` → `"postgresql"`
2. Use canonical names: "JavaScript" instead of "JS"
3. Enable fuzzy matching: `skill_fuzzy_match=True`
4. Adjust threshold: Lower `skill_fuzzy_threshold`
5. Add skill aliases: Contribute to `_SKILL_ALIASES` dict

### Configuration Errors

**Problem:** `ValueError: Scoring weights must sum to 1.0`

**Solutions:**
1. Verify weight sum: `0.40 + 0.20 + 0.25 + 0.15 = 1.00`
2. Use calculator for precision
3. Check environment variables: Ensure all weights are set correctly

**Example:**
```bash
# Incorrect
export SCORING_WEIGHT_MUST_HAVE=0.50
export SCORING_WEIGHT_PREFERRED=0.20
# Missing experience and education weights!

# Correct
export SCORING_WEIGHT_MUST_HAVE=0.50
export SCORING_WEIGHT_PREFERRED=0.15
export SCORING_WEIGHT_EXPERIENCE=0.25
export SCORING_WEIGHT_EDUCATION=0.10
```

---

## Future Enhancements

### Planned Features

1. **Machine Learning Scoring**
   - Train on historical application outcomes
   - Learn personalized weights from user feedback
   - Predict acceptance probability

2. **Dynamic Weight Adjustment**
   - Automatically adjust weights based on job type
   - Senior roles: increase experience weight
   - Junior roles: decrease experience weight, increase education weight

3. **Company Fit Scoring**
   - Company culture match
   - Company size preferences
   - Industry preferences

4. **Advanced Skill Matching**
   - Skill taxonomy (backend → Python, Django, PostgreSQL)
   - Skill proficiency levels (beginner, intermediate, expert)
   - Skill recency (weight recent experience higher)

5. **Multi-Profile Support**
   - Different profiles for different job types
   - Profile versioning and history
   - Profile A/B testing

6. **Constraint Optimization**
   - Constraint relaxation suggestions
   - Constraint impact analysis
   - Constraint negotiation recommendations

### Contributing

To contribute to the scoring module:

1. Add new skill aliases to `matchers.py::_SKILL_ALIASES`
2. Add skill implications to `matchers.py::_SKILL_IMPLICATIONS`
3. Improve scoring algorithms in `service.py`
4. Add configuration options in `config.py`
5. Enhance constraint logic in `service.py::_check_*` methods
6. Add tests for new features

**Guidelines:**
- Maintain backward compatibility
- Add unit tests for new features
- Update documentation
- Follow existing code style
- Use type hints

---

## Appendix

### Complete Example Profile

```yaml
# Complete Job-Easy profile with all fields
name: "Jane Doe"
email: "jane.doe@example.com"
phone: "+1-555-555-5555"
location: "New York, NY"
linkedin_url: "https://www.linkedin.com/in/janedoe"

skills:
  - "Python"
  - "Django"
  - "FastAPI"
  - "PostgreSQL"
  - "Redis"
  - "AWS"
  - "Docker"
  - "Kubernetes"
  - "CI/CD"
  - "Git"

years_of_experience: 8
current_title: "Senior Backend Engineer"
summary: |
  Senior backend engineer with 8 years of experience building scalable web services
  and APIs. Expert in Python, Django, and PostgreSQL. Strong background in cloud
  infrastructure (AWS) and containerization (Docker, Kubernetes).

work_history:
  - company: "TechCorp Inc"
    title: "Senior Backend Engineer"
    start_date: 2021-06-01
    end_date: null
    description: |
      Lead backend engineer for the platform team. Designed and implemented
      microservices architecture serving 10M+ requests/day.
    skills_used:
      - "Python"
      - "FastAPI"
      - "PostgreSQL"
      - "Redis"
      - "AWS"
      - "Docker"
      - "Kubernetes"

  - company: "StartupCo"
    title: "Backend Engineer"
    start_date: 2019-01-01
    end_date: 2021-05-31
    description: |
      Built REST APIs and data pipelines. Optimized database queries resulting
      in 50% performance improvement.
    skills_used:
      - "Python"
      - "Django"
      - "PostgreSQL"
      - "Celery"
      - "AWS"

  - company: "ConsultingCo"
    title: "Junior Developer"
    start_date: 2017-06-01
    end_date: 2018-12-31
    description: |
      Developed web applications for clients using Python and Django.
    skills_used:
      - "Python"
      - "Django"
      - "MySQL"
      - "JavaScript"

education:
  - institution: "MIT"
    degree: "Master's"
    field: "Computer Science"
    graduation_year: 2017

  - institution: "University of Example"
    degree: "Bachelor's"
    field: "Computer Engineering"
    graduation_year: 2015

certifications:
  - name: "AWS Certified Solutions Architect"
    issuer: "Amazon Web Services"
    date_awarded: 2022-06-15
    expires: 2025-06-15
    url: "https://aws.amazon.com/certification/"

  - name: "Kubernetes Administrator (CKA)"
    issuer: "CNCF"
    date_awarded: 2023-01-10
    expires: null

work_type_preferences:
  - "remote"
  - "hybrid"

target_locations:
  - "New York"
  - "San Francisco"
  - "Remote"

visa_sponsorship_needed: false
min_salary: 150000
preferred_salary: 180000
salary_currency: "USD"
experience_level: "senior"
```

### Skill Aliases Reference

```python
_SKILL_ALIASES = {
    # JavaScript ecosystem
    "js": "javascript",
    "javascript": "javascript",
    "typescript": "typescript",
    "nodejs": "node.js",
    "node js": "node.js",
    "node.js": "node.js",
    "react": "react",
    "reactjs": "react",
    "react.js": "react",
    "react js": "react",
    "nextjs": "next.js",
    "next js": "next.js",
    "next.js": "next.js",

    # Python
    "python3": "python",
    "python": "python",
    "numpy": "numpy",

    # Web technologies
    "html5": "html",
    "html": "html",
    "css3": "css",
    "css": "css",

    # Databases
    "mongo db": "mongodb",
    "mongodb": "mongodb",

    # Frontend libraries
    "jquery": "jquery",
}
```

### Skill Implications Reference

```python
_SKILL_IMPLICATIONS = {
    # Web stacks
    "react": {"javascript", "html", "css"},
    "next.js": {"react", "javascript", "html", "css"},
    "node.js": {"javascript"},

    # Broad skill buckets
    "full stack development": {"javascript", "html", "css", "testing", "debugging"},
    "software development": {"testing", "debugging"},
    "mobile software development": {"software development"},
}
```

### Education Level Mapping

```python
_EDUCATION_LEVELS = {
    "high school": 1,
    "associate": 2,
    "bachelor": 3,
    "master": 4,
    "phd": 5,
    "doctor": 5,
}
```

---

## Summary

The **Scoring Module** is a sophisticated job-candidate matching system that:

1. **Evaluates fit** using multi-factor weighted scoring (skills, experience, education)
2. **Enforces constraints** (visa, salary, location, work type) with configurable hard/soft modes
3. **Generates recommendations** (apply, skip, review) based on scores and constraints
4. **Provides detailed breakdowns** for transparency and debugging
5. **Integrates seamlessly** with other Job-Easy modules (extractor, runner, autonomous, tailoring)

**Key Strengths:**
- Type-safe models with Pydantic validation
- Flexible configuration via environment variables
- Intelligent skill matching with fuzzy logic
- Transparent scoring with detailed reasoning
- Production-ready error handling

**Use Cases:**
- Single job evaluation in runner mode
- Batch filtering and ranking in autonomous mode
- Profile-driven application decisions
- HITL gates for human oversight

For questions or contributions, please see the project repository.
