# Tailoring Module Documentation

**Module**: `src.tailoring`
**Purpose**: Resume and cover letter customization engine that transforms generic user profiles into job-specific, ATS-optimized application documents.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Data Models](#data-models)
5. [Services](#services)
6. [Configuration](#configuration)
7. [Template System](#template-system)
8. [Integration Points](#integration-points)
9. [Customization Strategies](#customization-strategies)
10. [API Reference](#api-reference)
11. [Usage Examples](#usage-examples)
12. [Error Handling](#error-handling)

---

## Overview

The tailoring module is a critical component of the Job-Easy application that bridges the gap between a user's general professional profile and job-specific application documents. It uses LLM-powered analysis to:

- **Extract and map keywords** from job descriptions to user skills
- **Generate evidence-based tailoring plans** that connect job requirements to user experience
- **Rewrite resume content** to emphasize relevant skills without fabricating experience
- **Generate personalized cover letters** with concrete evidence and proper structure
- **Render professional PDFs** using HTML/CSS templates and WeasyPrint
- **Create review packets** for human-in-the-loop (HITL) approval before submission

### Key Principles

1. **Truthfulness**: Never fabricate experience, skills, or accomplishments
2. **Evidence-Based**: All claims must be backed by actual user profile data
3. **ATS-Optimization**: Format and structure optimized for Applicant Tracking Systems
4. **Keyword Integration**: Natural integration of job-specific terminology
5. **Professional Quality**: Production-ready PDF documents suitable for submission

---

## Architecture

### High-Level Flow

```
┌─────────────────┐       ┌──────────────────┐
│  User Profile   │       │ Job Description  │
│  (from scoring) │       │ (from extractor) │
└────────┬────────┘       └────────┬─────────┘
         │                         │
         └────────────┬────────────┘
                      ▼
         ┌────────────────────────┐
         │  TailoringPlanService  │
         │  - Keyword matching    │
         │  - Evidence mapping    │
         │  - Section ordering    │
         │  - Rewrite suggestions │
         └────────────┬───────────┘
                      ▼
              ┌──────────────┐
              │ TailoringPlan │
              └──────┬───────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌────────────────────┐  ┌──────────────────┐
│ResumeTailoringServ.│  │CoverLetterService│
│ - Rewrite bullets  │  │ - Generate letter│
│ - Integrate keywords│ │ - Word count ctrl│
│ - Structure resume │  │ - Evidence hookup│
└─────────┬──────────┘  └────────┬─────────┘
          │                      │
          ▼                      ▼
   ┌──────────────┐      ┌──────────────┐
   │TailoredResume│      │ CoverLetter  │
   └──────┬───────┘      └──────┬───────┘
          │                     │
          └──────────┬──────────┘
                     ▼
            ┌────────────────┐
            │  PDFRenderer   │
            │ - HTML/CSS     │
            │ - WeasyPrint   │
            └────────┬───────┘
                     ▼
            ┌────────────────┐
            │  PDF Documents │
            │ - Resume PDF   │
            │ - Cover PDF    │
            └────────┬───────┘
                     ▼
         ┌──────────────────────┐
         │ ReviewPacketService  │
         │ - Summary of changes │
         │ - Keywords highlighted│
         │ - Evidence mapping   │
         └──────────────────────┘
```

### Module Structure

```
src/tailoring/
├── __init__.py           # Public API exports
├── config.py             # Configuration and settings
├── models.py             # Pydantic data models
├── service.py            # Main orchestration service
├── llm.py                # LLM client wrapper
├── plan.py               # Tailoring plan generation
├── resume.py             # Resume tailoring logic
├── cover_letter.py       # Cover letter generation
├── renderer.py           # PDF rendering engine
├── review.py             # Review packet creation
└── templates/
    ├── resume.html       # Resume HTML template
    ├── cover_letter.html # Cover letter HTML template
    └── styles.css        # Shared CSS styles
```

---

## Core Components

### TailoringService (Main Orchestrator)

**File**: `src/tailoring/service.py`

The primary entry point that orchestrates the complete tailoring pipeline.

**Responsibilities**:
- Coordinates all sub-services
- Manages the 5-step pipeline
- Handles errors and returns consolidated results
- Provides convenience methods for resume-only tailoring

**Pipeline Steps**:
1. Generate tailoring plan
2. Tailor resume
3. Generate cover letter (optional)
4. Render PDFs
5. Create review packet

### TailoringPlanService

**File**: `src/tailoring/plan.py`

Analyzes job descriptions against user profiles to create comprehensive tailoring strategies.

**Responsibilities**:
- Extract job keywords and match to user skills
- Map job requirements to user evidence (accomplishments, projects)
- Recommend resume section ordering
- Suggest bullet point rewrites with keyword integration
- Flag unsupported requirements (gaps in qualifications)

**LLM Interaction**: Uses structured output to generate `TailoringPlan` objects with strict schema validation.

### ResumeTailoringService

**File**: `src/tailoring/resume.py`

Transforms user profiles into job-specific resumes with keyword optimization.

**Responsibilities**:
- Generate professional summaries tailored to target role
- Rewrite experience bullets to integrate keywords naturally
- Organize sections based on job relevance
- Enforce strict formatting rules for ATS compatibility
- Validate output structure with retry logic

**Key Features**:
- **Strict Validation**: Enforces bullet format `ROLE, COMPANY (START – END) — [accomplishment]`
- **Bullet Limits**: 2-4 bullets per role, max 10 total for experience
- **Project Constraints**: 1-3 bullets for projects section
- **Multi-Attempt Generation**: Up to 4 attempts with targeted revision prompts
- **Post-Processing**: Applies non-fabricating cleanup if LLM output doesn't meet requirements

### CoverLetterService

**File**: `src/tailoring/cover_letter.py`

Generates personalized cover letters with evidence integration and word count control.

**Responsibilities**:
- Create compelling opening paragraphs
- Build evidence-based body sections
- Generate professional closings
- Enforce word count ranges (default: 300-400 words)
- Ensure company name appears in letter

**Structure**:
- **Opening**: 1 paragraph - hook with role/company mention, enthusiasm
- **Body**: 2-3 paragraphs - top qualifications with concrete evidence
- **Closing**: 1 paragraph - call to action, professional sign-off

**Word Count Control**:
- Revision pass if outside target range
- Deterministic padding (from profile work history, evidence mappings)
- Deterministic trimming (preserves opening/closing, trims body)

### PDFRenderer

**File**: `src/tailoring/renderer.py`

Converts tailored content to professional PDF documents using Jinja2 templates and WeasyPrint.

**Responsibilities**:
- Render HTML from Jinja2 templates
- Parse and structure resume sections for optimal display
- Handle experience/project bullet formatting
- Generate PDF files with proper styling
- Create deterministic filenames

**Rendering Features**:
- **Experience Parsing**: Extracts role, company, dates, accomplishments from structured bullets
- **Skills Grouping**: Organizes skills into labeled categories
- **Project Formatting**: Parses project name, context, description
- **Section Merging**: Consolidates multiple experience sections into cohesive flow
- **Section Ordering**: Ensures Experience before Projects for ATS compatibility

### ReviewPacketService

**File**: `src/tailoring/review.py`

Creates review summaries for human verification before document submission.

**Responsibilities**:
- Summarize tailoring changes made
- List keywords integrated
- Show requirement-to-evidence mappings
- Flag unsupported claims with severity
- Provide file paths to generated documents

---

## Data Models

All models are Pydantic-based with JSON serialization support.

### TailoringPlan

**File**: `src/tailoring/models.py`

Complete strategy for tailoring application documents.

```python
class TailoringPlan(BaseModel):
    job_url: str
    company: str
    role_title: str
    keyword_matches: list[KeywordMatch]
    evidence_mappings: list[EvidenceMapping]
    section_order: list[str]
    bullet_rewrites: list[BulletRewrite]
    unsupported_claims: list[UnsupportedClaim]
```

**Sub-Models**:

- **KeywordMatch**: Maps job keyword to user skill with confidence score (0-1)
- **EvidenceMapping**: Connects job requirement to user evidence with source and relevance score
- **BulletRewrite**: Suggests rewritten bullet with keywords added and reasoning
- **UnsupportedClaim**: Flags requirement without supporting evidence (warning/critical severity)

### TailoredResume

**File**: `src/tailoring/models.py`

Complete resume ready for PDF rendering.

```python
class TailoredResume(BaseModel):
    # Contact info
    name: str
    email: str
    phone: str | None
    location: str
    linkedin_url: str | None
    github_url: str | None

    # Content
    summary: str
    sections: list[TailoredSection]
    keywords_used: list[str]

    # Target job info
    target_job_url: str
    target_company: str
    target_role: str
```

**Sub-Models**:

- **TailoredSection**: Section with name, title, content, bullets
- **TailoredBullet**: Bullet text with keywords_used tracking

### CoverLetter

**File**: `src/tailoring/models.py`

Generated cover letter content.

```python
class CoverLetter(BaseModel):
    opening: str
    body: str
    closing: str
    full_text: str
    word_count: int

    target_job_url: str
    target_company: str
    target_role: str
    key_qualifications: list[str]
```

### DocReviewPacket

**File**: `src/tailoring/models.py`

Summary for human review before upload.

```python
class DocReviewPacket(BaseModel):
    job_url: str
    company: str
    role_title: str

    changes_summary: list[str]
    keywords_highlighted: list[str]
    requirements_vs_evidence: list[dict[str, Any]]

    resume_path: str
    cover_letter_path: str | None
    generated_at: datetime
```

---

## Services

### TailoringLLM

**File**: `src/tailoring/llm.py`

Unified LLM client with structured output support.

**Features**:
- Provider-agnostic interface (OpenAI, Anthropic, custom endpoints)
- Structured output with Pydantic model validation
- Automatic retry logic with exponential backoff
- Rate limit handling (8-second waits for rate limits)
- JSON extraction from markdown code fences
- Timeout configuration
- Reasoning effort parameter support

**Methods**:

```python
async def generate_structured(
    prompt: str,
    output_model: type[T],
    system_prompt: str | None = None,
) -> T:
    """Generate structured output matching a Pydantic model."""

async def generate_text(
    prompt: str,
    system_prompt: str | None = None,
) -> str:
    """Generate plain text response."""
```

**Provider Setup**:
- OpenAI: Direct API or custom base URL with `openai/` prefix
- Anthropic: Uses `ANTHROPIC_BASE_URL` env var, `anthropic/` prefix
- Custom: Any OpenAI-compatible endpoint via `llm_base_url`

---

## Configuration

### TailoringConfig

**File**: `src/tailoring/config.py`

Configuration settings with environment variable support.

**Settings**:

```python
class TailoringConfig(BaseSettings):
    # LLM settings (with EXTRACTOR_LLM_* fallback)
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_max_retries: int = 1
    llm_timeout: float = 300.0
    llm_reasoning_effort: str | None = None

    # Template settings
    template_dir: Path = Path("src/tailoring/templates")
    resume_template: str = "resume.html"
    cover_letter_template: str = "cover_letter.html"

    # Output settings
    output_dir: Path = Path("artifacts/docs")

    # Cover letter generation
    cover_letter_min_words: int = 300
    cover_letter_max_words: int = 400
```

**Environment Variables**:

Prefix: `TAILORING_` or `EXTRACTOR_LLM_` (fallback)

Examples:
```bash
TAILORING_LLM_PROVIDER=anthropic
TAILORING_LLM_MODEL=claude-3-5-sonnet-20241022
TAILORING_LLM_API_KEY=sk-...
TAILORING_LLM_BASE_URL=http://localhost:8000/v1
TAILORING_LLM_REASONING_EFFORT=medium
TAILORING_OUTPUT_DIR=./outputs
```

**Singleton Access**:

```python
from src.tailoring.config import get_tailoring_config

config = get_tailoring_config()
```

---

## Template System

### Jinja2 Templates

The module uses Jinja2 for HTML generation with WeasyPrint for PDF rendering.

**Template Location**: `src/tailoring/templates/`

#### Resume Template

**File**: `resume.html`

**Structure**:
- Header with contact info (name, email, phone, location, LinkedIn)
- Professional summary section
- Dynamic sections (experience, skills, projects, education, certifications)

**Special Rendering**:
- **Entries**: Structured experience/project items with heading, subheading, dates, bullets
- **Skill Groups**: Labeled skill categories with items separated by dots
- **Content Lines**: Multi-line content preserving intentional breaks
- **Content Items**: List items from comma-separated content

**Template Variables**:
```jinja2
{{ name }}
{{ email }}
{{ phone }}
{{ location }}
{{ linkedin_url }}
{{ github_url }}
{{ summary }}
{{ sections }}  # List of prepared sections with derived fields
{{ keywords_used }}
{{ styles }}    # Inline CSS from styles.css
```

#### Cover Letter Template

**File**: `cover_letter.html`

**Structure**:
- Header with date
- Opening paragraph
- Body paragraphs
- Closing paragraph

**Template Variables**:
```jinja2
{{ date }}
{{ opening }}
{{ body_paragraphs }}  # List of paragraphs
{{ closing }}
{{ target_company }}
{{ target_role }}
{{ styles }}
```

#### Styles

**File**: `styles.css`

Shared CSS for both resume and cover letter templates.

**Features**:
- Professional typography (system fonts)
- ATS-friendly layout (no complex CSS features)
- Print-optimized spacing
- Responsive section headers
- Bullet point styling

---

## Integration Points

### Dependencies on Other Modules

The tailoring module integrates with several other Job-Easy components:

#### 1. Extractor Module

**Import**: `from src.extractor.models import JobDescription`

**Usage**: Receives parsed job descriptions as input for tailoring.

**Data Flow**: JobDescription → TailoringPlanService → TailoringPlan

#### 2. Scoring Module

**Import**: `from src.scoring.models import UserProfile`

**Usage**: Receives scored user profiles as input for tailoring.

**Data Flow**: UserProfile → ResumeTailoringService → TailoredResume

#### 3. Runner Module

**File**: `src/runner/service.py`

**Integration**:
```python
tailoring_service = TailoringService(config=TailoringConfig(output_dir=run_dir))
tailoring_result = await tailoring_service.tailor(profile, job)
resume_path = tailoring_result.resume_path
cover_letter_path = tailoring_result.cover_letter_path
```

**Purpose**: Single-job orchestration uses tailoring to generate documents before application submission.

#### 4. Autonomous Module

**File**: `src/autonomous/runner.py`

**Integration**:
```python
tailoring_service = TailoringService(config=TailoringConfig(output_dir=run_dir))
result = await tailoring_service.tailor(self.profile, item.job_description)
```

**Purpose**: Batch processing uses tailoring for multiple jobs in queue.

#### 5. HITL Module

**Usage**: Review packets are presented to users via HITL prompts for approval before document upload.

---

## Customization Strategies

### Keyword Integration Strategy

The module employs sophisticated keyword integration:

1. **Extraction**: TailoringPlanService extracts keywords from job description
2. **Matching**: Maps job keywords to user skills with confidence scoring
3. **Natural Integration**: ResumeTailoringService rewrites bullets to include keywords contextually
4. **Validation**: Ensures keywords appear naturally, not as forced prefixes

**Example**:
- Original: "Developed APIs for the platform"
- Job Keywords: Python, FastAPI, RESTful
- Rewritten: "Developed RESTful APIs using Python and FastAPI, improving response times by 40%"

### Evidence Mapping Strategy

Connects job requirements to user accomplishments:

1. **Requirement Analysis**: Parse job responsibilities and qualifications
2. **Evidence Extraction**: Identify relevant accomplishments from work history
3. **Relevance Scoring**: Rate evidence relevance (0-1 scale)
4. **Source Tracking**: Record company and role where evidence originates
5. **Gap Detection**: Flag requirements without supporting evidence

**Example Mapping**:
- Requirement: "3+ years of backend development"
- Evidence: "Led backend development of payment processing system handling 10k transactions/day"
- Source: TechCorp Inc - Senior Software Engineer
- Relevance: 0.9

### Section Ordering Strategy

Optimizes resume structure for relevance:

1. **Job Analysis**: Determine which sections are most relevant to job
2. **Dynamic Ordering**: Reorder sections to prioritize relevant content
3. **ATS Compliance**: Maintain standard section names and structure
4. **Merge Experience**: Consolidate multiple experience entries into single section

**Default Order**: Experience → Skills → Projects → Education → Certifications

**Adjusted Example** (for data science role): Skills → Experience → Projects → Education → Certifications

### Bullet Rewriting Strategy

Enhances resume bullets while maintaining truthfulness:

1. **Identify Relevant Bullets**: Select bullets related to job requirements
2. **Keyword Analysis**: Determine which keywords to integrate
3. **Context Preservation**: Keep all factual claims (dates, metrics, companies)
4. **Natural Phrasing**: Rewrite to sound authentic, not keyword-stuffed
5. **Emphasis**: Highlight relevant aspects of existing experience

**Constraints**:
- NO fabrication of experience
- NO invention of new skills
- NO alteration of metrics or facts
- ONLY rephrasing of existing content

### Word Count Control (Cover Letters)

Ensures cover letters meet professional length standards:

1. **Target Range**: Default 300-400 words (configurable)
2. **Initial Generation**: LLM generates first draft
3. **Revision Pass**: If outside range, request revision with same facts
4. **Deterministic Padding**: Add truthful content from profile work history
5. **Deterministic Trimming**: Reduce body text while preserving opening/closing

**Padding Sources**:
- Work history descriptions
- Evidence mappings from plan
- Skills alignment statements

---

## API Reference

### Main Service Interface

#### TailoringService

```python
class TailoringService:
    def __init__(self, config: TailoringConfig | None = None):
        """Initialize the tailoring service."""

    async def tailor(
        self,
        profile: UserProfile,
        job: JobDescription,
        generate_cover_letter: bool = True,
    ) -> TailoringResult:
        """Run the complete tailoring pipeline.

        Returns:
            TailoringResult with all artifacts or error.
        """

    async def tailor_resume_only(
        self,
        profile: UserProfile,
        job: JobDescription,
    ) -> TailoringResult:
        """Tailor resume only, without cover letter."""
```

#### TailoringResult

```python
@dataclass
class TailoringResult:
    success: bool
    error: str | None = None

    # Generated artifacts
    plan: TailoringPlan | None = None
    resume: TailoredResume | None = None
    cover_letter: CoverLetter | None = None
    review_packet: DocReviewPacket | None = None

    # File paths
    resume_path: str | None = None
    cover_letter_path: str | None = None

    # Metadata
    completed_at: datetime
```

### Sub-Services

#### TailoringPlanService

```python
class TailoringPlanService:
    def __init__(self, config: TailoringConfig | None = None):
        """Initialize the tailoring plan service."""

    async def generate_plan(
        self,
        profile: UserProfile,
        job: JobDescription,
    ) -> TailoringPlan:
        """Generate a tailoring plan for a job application."""
```

#### ResumeTailoringService

```python
class ResumeTailoringService:
    def __init__(self, config: TailoringConfig | None = None):
        """Initialize the resume tailoring service."""

    async def tailor_resume(
        self,
        profile: UserProfile,
        job: JobDescription,
        plan: TailoringPlan,
    ) -> TailoredResume:
        """Generate a tailored resume for a job application."""
```

#### CoverLetterService

```python
class CoverLetterService:
    def __init__(self, config: TailoringConfig | None = None):
        """Initialize the cover letter service."""

    async def generate_cover_letter(
        self,
        profile: UserProfile,
        job: JobDescription,
        plan: TailoringPlan,
    ) -> CoverLetter:
        """Generate a cover letter for a job application."""
```

#### PDFRenderer

```python
class PDFRenderer:
    def __init__(self, config: TailoringConfig | None = None):
        """Initialize the PDF renderer."""

    def render_resume(self, resume: TailoredResume) -> RenderResult:
        """Render a tailored resume to PDF."""

    def render_cover_letter(self, cover: CoverLetter) -> RenderResult:
        """Render a cover letter to PDF."""

    def render_both(
        self,
        resume: TailoredResume,
        cover: CoverLetter,
    ) -> tuple[RenderResult, RenderResult]:
        """Render both resume and cover letter."""
```

#### ReviewPacketService

```python
class ReviewPacketService:
    def __init__(self, config: TailoringConfig | None = None):
        """Initialize the review packet service."""

    def create_review_packet(
        self,
        plan: TailoringPlan,
        resume: TailoredResume,
        resume_path: str,
        cover_letter: CoverLetter | None = None,
        cover_letter_path: str | None = None,
    ) -> DocReviewPacket:
        """Create a review packet summarizing tailoring changes."""
```

---

## Usage Examples

### Basic Usage

```python
from src.tailoring import TailoringService
from src.extractor.models import JobDescription
from src.scoring.models import UserProfile

# Initialize service
service = TailoringService()

# Tailor documents
result = await service.tailor(user_profile, job_description)

if result.success:
    print(f"Resume: {result.resume_path}")
    print(f"Cover Letter: {result.cover_letter_path}")
    print(f"Keywords: {', '.join(result.resume.keywords_used)}")
else:
    print(f"Error: {result.error}")
```

### Resume Only

```python
result = await service.tailor_resume_only(user_profile, job_description)

if result.success:
    print(f"Resume: {result.resume_path}")
    print(f"Sections: {len(result.resume.sections)}")
```

### Custom Configuration

```python
from src.tailoring import TailoringService, TailoringConfig
from pathlib import Path

config = TailoringConfig(
    llm_provider="anthropic",
    llm_model="claude-3-5-sonnet-20241022",
    output_dir=Path("./custom_output"),
    cover_letter_min_words=250,
    cover_letter_max_words=350,
)

service = TailoringService(config=config)
result = await service.tailor(user_profile, job_description)
```

### Accessing Sub-Components

```python
from src.tailoring import TailoringPlanService, ResumeTailoringService

# Generate plan only
plan_service = TailoringPlanService()
plan = await plan_service.generate_plan(user_profile, job_description)

print(f"Keywords: {len(plan.keyword_matches)}")
print(f"Evidence: {len(plan.evidence_mappings)}")
print(f"Warnings: {len(plan.unsupported_claims)}")

# Tailor resume with existing plan
resume_service = ResumeTailoringService()
resume = await resume_service.tailor_resume(user_profile, job_description, plan)
```

### Direct PDF Rendering

```python
from src.tailoring import PDFRenderer
from src.tailoring.models import TailoredResume

renderer = PDFRenderer()

# Render resume
result = renderer.render_resume(tailored_resume)
if result.success:
    print(f"PDF saved to: {result.file_path}")

# Render both documents
resume_result, cover_result = renderer.render_both(
    tailored_resume,
    cover_letter
)
```

### Review Packet Creation

```python
from src.tailoring import ReviewPacketService

review_service = ReviewPacketService()
packet = review_service.create_review_packet(
    plan=plan,
    resume=resume,
    resume_path="/path/to/resume.pdf",
    cover_letter=cover_letter,
    cover_letter_path="/path/to/cover.pdf",
)

print("Changes Summary:")
for change in packet.changes_summary:
    print(f"  - {change}")

print("\nKeywords:")
print(f"  {', '.join(packet.keywords_highlighted)}")

print("\nRequirements vs Evidence:")
for mapping in packet.requirements_vs_evidence:
    if mapping["matched"]:
        print(f"  ✓ {mapping['requirement']}")
        print(f"    → {mapping['evidence'][:80]}...")
    else:
        print(f"  ✗ {mapping['requirement']}: {mapping['reason']}")
```

---

## Error Handling

### Exception Types

#### LLMError

**Source**: `src.tailoring.llm.py`

Raised when LLM operations fail.

```python
class LLMError(Exception):
    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error
```

**Common Causes**:
- API timeout (exceeds `llm_timeout` setting)
- Rate limiting (429 errors)
- Invalid API key or credentials
- JSON parsing/validation failures
- Network connectivity issues

**Handling**:
```python
from src.tailoring.llm import LLMError

try:
    plan = await plan_service.generate_plan(profile, job)
except LLMError as e:
    if "timeout" in str(e).lower():
        # Increase TAILORING_LLM_TIMEOUT or use faster model
        pass
    elif "rate_limit" in str(e).lower():
        # Wait and retry, or upgrade API tier
        pass
    else:
        # General LLM failure
        logger.error(f"LLM error: {e}")
        if e.original_error:
            logger.error(f"Original: {e.original_error}")
```

### Retry Logic

#### Automatic Retries

The `TailoringLLM` class implements automatic retry logic:

- **Max Retries**: Configurable via `llm_max_retries` (default: 1)
- **Backoff Strategy**: Linear for rate limits (8s base), exponential for other errors (2s base)
- **No Retry Cases**: Parse/validation errors are not retried

#### Manual Retries (Resume Generation)

`ResumeTailoringService` uses multi-attempt generation with revision prompts:

1. **Attempt 1**: Initial generation
2. **Attempt 2**: Schema fix revision (if parse error)
3. **Attempt 3-4**: Format/structure fix revisions (if validation fails)

If all attempts fail, applies deterministic post-processing as fallback.

### Common Failure Scenarios

#### 1. Timeout Errors

**Symptom**: `LLM request timed out`

**Solutions**:
- Increase `TAILORING_LLM_TIMEOUT` (default: 300s)
- Use faster model (e.g., gpt-4o-mini instead of gpt-4o)
- Check network connectivity

#### 2. Rate Limiting

**Symptom**: `rate_limit` or `429` errors

**Solutions**:
- Automatic retry with 8-second waits
- Upgrade API tier for higher rate limits
- Reduce concurrent requests

#### 3. Validation Failures

**Symptom**: Resume doesn't meet structure requirements

**Handled By**: Multi-attempt generation with specific revision prompts

**Fallback**: Deterministic post-processing (may drop roles with insufficient bullets)

#### 4. Template Errors

**Symptom**: Missing template files

**Fallback**: Uses package-bundled templates from `src/tailoring/templates/`

#### 5. PDF Rendering Errors

**Symptom**: WeasyPrint failures

**Common Causes**:
- Missing fonts
- Invalid HTML/CSS
- File system permissions

**Handling**:
```python
result = renderer.render_resume(resume)
if not result.success:
    logger.error(f"Rendering failed: {result.error}")
```

### Logging

All services use Python's `logging` module with module-level loggers:

```python
logger = logging.getLogger(__name__)

# Log levels used:
logger.info("Starting tailoring pipeline...")
logger.warning("Failed to render cover letter...")
logger.error("Tailoring pipeline failed: {e}")
```

**Configure Logging**:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
```

---

## Advanced Topics

### Custom Templates

Override default templates by setting `template_dir`:

```python
from pathlib import Path

config = TailoringConfig(
    template_dir=Path("./my_templates"),
    resume_template="my_resume.html",
    cover_letter_template="my_cover.html",
)
```

**Template Requirements**:
- Must be valid Jinja2 templates
- Must accept documented template variables
- CSS can be inline or via `{{ styles }}` variable

### LLM Provider Configuration

#### OpenAI

```bash
TAILORING_LLM_PROVIDER=openai
TAILORING_LLM_MODEL=gpt-4o
TAILORING_LLM_API_KEY=sk-...
```

#### Anthropic

```bash
TAILORING_LLM_PROVIDER=anthropic
TAILORING_LLM_MODEL=claude-3-5-sonnet-20241022
TAILORING_LLM_API_KEY=sk-ant-...
```

#### Custom OpenAI-Compatible Endpoint

```bash
TAILORING_LLM_PROVIDER=openai
TAILORING_LLM_MODEL=my-model
TAILORING_LLM_BASE_URL=http://localhost:8000/v1
TAILORING_LLM_API_KEY=custom-key
```

#### Groq

```bash
TAILORING_LLM_BASE_URL=https://api.groq.com/openai/v1
TAILORING_LLM_MODEL=llama-3.1-70b-versatile
TAILORING_LLM_API_KEY=gsk_...
```

### Reasoning Effort

For models that support reasoning effort (e.g., o1, o3):

```bash
TAILORING_LLM_REASONING_EFFORT=medium
# Options: disable, none, minimal, low, medium, high, xhigh
```

Normalized values:
- `off`, `disabled`, `0`, `false` → `disable`
- Other values passed through as-is

---

## Testing

### Unit Tests

Run tailoring module tests:

```bash
pytest tests/tailoring/
```

### Integration Tests

Test with real LLM providers:

```bash
# Set up environment
export TAILORING_LLM_PROVIDER=openai
export TAILORING_LLM_API_KEY=sk-...

# Run integration tests
pytest tests/integration/test_tailoring.py
```

### Mock LLM for Testing

```python
from unittest.mock import AsyncMock, patch
from src.tailoring import TailoringService

@patch('src.tailoring.llm.acompletion')
async def test_tailoring(mock_acompletion):
    mock_acompletion.return_value = AsyncMock(
        choices=[
            AsyncMock(
                message=AsyncMock(
                    content='{"keyword_matches": [], ...}'
                )
            )
        ]
    )

    service = TailoringService()
    result = await service.tailor(profile, job)

    assert result.success
```

---

## Performance Considerations

### LLM Call Optimization

The tailoring pipeline makes multiple LLM calls:
1. Plan generation (1 call)
2. Resume tailoring (1-4 calls with retries)
3. Cover letter generation (1-2 calls with revision)

**Total**: 3-7 LLM calls per job

**Optimization Strategies**:
- Use faster models (e.g., gpt-4o-mini) for non-critical steps
- Adjust `llm_max_retries` to reduce retry attempts
- Cache tailoring plans for similar jobs (not implemented)

### PDF Rendering Performance

- **WeasyPrint**: CPU-intensive, ~1-2 seconds per PDF
- **Optimization**: Render in parallel for resume and cover letter

### Memory Usage

- **LLM Responses**: ~10-50 KB per response
- **PDF Files**: ~100-500 KB per document
- **Total per Job**: ~1 MB including all artifacts

---

## Future Enhancements

### Planned Features

1. **Template Customization UI**: Web interface for template editing
2. **A/B Testing**: Compare multiple resume versions
3. **Analytics**: Track keyword effectiveness and application success rates
4. **Multi-Language Support**: Generate documents in multiple languages
5. **Custom Sections**: Support for portfolios, publications, patents
6. **ATS Scoring**: Predict ATS compatibility score before submission

### Extensibility Points

- **Custom Renderers**: Add support for Word, LaTeX, plain text
- **Custom Prompts**: Override system prompts for specialized industries
- **Custom Validators**: Add industry-specific validation rules
- **Plugin System**: Allow third-party extensions for tailoring logic

---

## Troubleshooting

### Problem: Generated resume is too long

**Solution**:
- Check work history length in profile
- Adjust bullet limits in resume generation
- Use more selective section ordering

### Problem: Keywords not integrating naturally

**Solution**:
- Review keyword matching confidence scores
- Adjust LLM model (more capable models integrate better)
- Review bullet rewrite suggestions in plan

### Problem: Cover letter exceeds word count

**Solution**:
- Adjust `cover_letter_max_words` in config
- Review padding logic in `CoverLetterService`
- Use shorter work history descriptions in profile

### Problem: Unsupported claims flagged

**Solution**:
- Review user profile completeness
- Add missing skills/experience to profile
- Accept that some requirements may not be met (honesty principle)

### Problem: PDF rendering fails

**Solution**:
- Check WeasyPrint installation: `pip install weasyprint`
- Verify output directory exists and is writable
- Check template syntax for HTML/CSS errors

---

## Summary

The tailoring module is a sophisticated document generation engine that:

✅ Transforms generic profiles into job-specific resumes and cover letters
✅ Maintains truthfulness and evidence-based claims
✅ Optimizes for ATS compatibility and keyword matching
✅ Generates professional PDF documents ready for submission
✅ Provides human review opportunities before final submission
✅ Integrates seamlessly with Job-Easy's application pipeline

**Key Strengths**:
- LLM-powered intelligent content generation
- Strict validation and formatting rules
- Multi-attempt generation with revision prompts
- Comprehensive error handling and retry logic
- Modular, testable architecture

**Integration Points**: Extractor → Scoring → **Tailoring** → Runner → Autonomous

For detailed information on other modules, see:
- [Extractor Documentation](./extractor.md)
- [Scoring Documentation](./scoring.md)
- [Runner Documentation](./runner.md)
- [Autonomous Documentation](./autonomous.md)
