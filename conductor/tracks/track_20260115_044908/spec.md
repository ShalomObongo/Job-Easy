# Specification: Job Extractor

> Track ID: track_20260115_044908
> Type: Feature
> Priority: High
> Epic Reference: E2-S1, E2-S2

---

## Overview

Implement a Job Description (JD) extractor that uses Browser Use to navigate to job posting URLs and extract structured data using LLM-based extraction. The extractor leverages Browser Use's `output_model_schema` parameter with a Pydantic model to return validated, structured job data that downstream systems (fit scoring, tailoring) can consume.

---

## Functional Requirements

### FR-1: JD Extraction Schema (JobDescription Pydantic Model)

Define a Pydantic model representing the extracted job data:

**Basic Metadata:**
- `company: str` - Company name
- `role_title: str` - Job title/position
- `location: str | None` - Job location (city, state, country, or "Remote")
- `job_url: str` - Canonical URL of the job posting
- `apply_url: str | None` - Direct application URL (if different from job_url)
- `job_id: str | None` - Platform-specific job identifier (Greenhouse, Lever, Workday patterns)

**Job Description Content:**
- `description: str` - Full job description text
- `responsibilities: list[str]` - List of key responsibilities
- `qualifications: list[str]` - List of required/preferred qualifications

**Requirements Breakdown:**
- `required_skills: list[str]` - Must-have skills/technologies
- `preferred_skills: list[str]` - Nice-to-have skills/technologies
- `experience_years_min: int | None` - Minimum required years of experience
- `experience_years_max: int | None` - Maximum years of experience
- `education: str | None` - Required education level

**Compensation & Work Type:**
- `salary_min: int | None` - Minimum salary (if disclosed)
- `salary_max: int | None` - Maximum salary (if disclosed)
- `salary_currency: str | None` - Currency code (USD, EUR, etc.)
- `work_type: Literal["remote", "hybrid", "onsite"] | None`
- `employment_type: Literal["full-time", "part-time", "contract"] | None`

**Extraction Metadata:**
- `extracted_at: datetime` - Timestamp of extraction
- `extraction_source: str` - Detected job board (greenhouse, lever, workday, linkedin, etc.)

### FR-2: Browser Use Agent Integration

Use Browser Use's structured output feature:

```python
from browser_use import Agent, Browser
from browser_use.llm.openai.chat import ChatOpenAI

agent = Agent(
    task=f"Navigate to {url} and extract the job posting details",
    llm=ChatOpenAI(model="gpt-4o"),
    browser=browser,
    output_model_schema=JobDescription,  # Pydantic model for structured output
    use_vision="auto",  # Enable vision when helpful
    max_failures=3,  # Built-in retry logic
    step_timeout=60,  # Per-step timeout
)

history = await agent.run()
job_data = history.structured_output  # Returns JobDescription instance
```

### FR-3: Browser Configuration

Configure browser for job extraction:
- `headless=True` by default (configurable)
- `allowed_domains` - Restrict to job board domains
- `window_size={'width': 1280, 'height': 720}` - Standard viewport

### FR-4: Extraction Workflow

1. Accept job URL as input
2. Initialize Browser Use agent with JobDescription schema
3. Agent navigates to URL and extracts structured data
4. Return `JobDescription` from `history.structured_output`
5. Optionally save `jd.json` artifact to run directory
6. Integrate with tracker for fingerprinting

### FR-5: Error Handling

- Handle page load failures with meaningful errors
- Use `max_failures=3` for automatic retry
- Return `None` with logged error if extraction fails completely
- Support configurable `step_timeout` for slow pages

---

## Non-Functional Requirements

### NFR-1: Performance
- Extraction should complete within 60 seconds (configurable timeout)
- Support headless mode for faster execution

### NFR-2: Reliability
- Automatic retry via Browser Use's `max_failures` parameter
- Vision mode (`use_vision="auto"`) for complex page layouts
- Handle JavaScript-rendered content via browser automation

### NFR-3: Testability
- Unit tests for JobDescription schema validation
- Mocked agent tests for extraction logic
- Integration tests with real job board URLs

---

## Acceptance Criteria

1. **Schema completeness**: `JobDescription` Pydantic model passes validation tests
2. **Structured output**: Agent returns `history.structured_output` as `JobDescription` instance
3. **Multi-board support**: Successfully extracts from Greenhouse, Lever, and one generic job posting
4. **Artifact output**: Saves `jd.json` to configured output directory
5. **Tracker integration**: Returns data compatible with fingerprint computation (URL, company, title, location)
6. **Error resilience**: Handles failed extractions gracefully with logged errors
7. **Test coverage**: Unit tests for schema, mocked extraction tests, integration tests

---

## Out of Scope

- **Fit scoring**: Evaluating job-user match (separate track)
- **Resume tailoring**: Document generation (separate track)
- **Application form filling**: Runner functionality (separate track)
- **CAPTCHA handling**: Bot detection bypass
- **Batch extraction**: Multiple URLs in single run

---

## Technical Notes

### Browser Use Key Parameters
- `output_model_schema`: Pydantic model for structured output -> `history.structured_output`
- `use_vision="auto"`: Include screenshots when helpful
- `page_extraction_llm`: Optional separate LLM for extraction (cost optimization)
- `max_failures=3`: Built-in retry logic
- `step_timeout`: Per-step timeout in seconds
- `save_conversation_path`: Audit log path

### LLM Options
- `ChatBrowserUse()` - Browser Use's hosted LLM
- `ChatOpenAI(model="gpt-4o")` - OpenAI
- `ChatAnthropic()` - Anthropic Claude

### Fingerprint Integration
- Reuse `extract_job_id()` from `src/tracker/fingerprint.py` for Greenhouse/Lever/Workday patterns
- Use `normalize_url()` for canonical URL
- Compute fingerprint for tracker storage

---

## Dependencies

- Application Tracker (track_20260115_034749) - Completed
- Browser Use library (>=0.11.0)
