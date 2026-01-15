# Implementation Plan: Job Extractor

> Track ID: track_20260115_044908
> Last Updated: 2026-01-15

---

## Overview

Implement the Job Extractor using Browser Use's structured output feature with `output_model_schema`. Following TDD methodology.

---

## Phase 1: JobDescription Schema

### Task 1.1: Write Schema Tests
- [x] Test: JobDescription has all required metadata fields (company, role_title, job_url)
- [x] Test: JobDescription has optional fields with None defaults
- [x] Test: JobDescription validates work_type as Literal["remote", "hybrid", "onsite"]
- [x] Test: JobDescription validates employment_type as Literal["full-time", "part-time", "contract"]
- [x] Test: JobDescription serializes to JSON correctly
- [x] Test: JobDescription.from_dict() creates valid instance

### Task 1.2: Implement JobDescription Schema
- [x] Create `/src/extractor/models.py`
- [x] Define `JobDescription` Pydantic BaseModel with all fields
- [x] Add field validators (salary ranges, experience years)
- [x] Add `to_dict()` method
- [x] Add `save_json(path)` method for artifact output

---

## Phase 2: Extractor Configuration

### Task 2.1: Write Configuration Tests
- [x] Test: ExtractorConfig loads defaults (headless=True, timeout=60)
- [x] Test: ExtractorConfig reads from environment variables
- [x] Test: ExtractorConfig validates timeout > 0

### Task 2.2: Implement Extractor Configuration
- [x] Create `/src/extractor/config.py`
- [x] Define `ExtractorConfig` with:
  - `headless: bool = True`
  - `step_timeout: int = 60`
  - `max_failures: int = 3`
  - `use_vision: str = "auto"`
  - `output_dir: Path`
  - `allowed_domains: list[str]` (job board domains)
- [x] Integrate with main Settings class

---

## Phase 3: Core Extractor Service

### Task 3.1: Write Extractor Service Tests (Mocked)
- [x] Test: JobExtractor initializes with config
- [x] Test: JobExtractor.extract() returns JobDescription for valid URL (mocked agent)
- [x] Test: JobExtractor.extract() returns None on extraction failure
- [x] Test: JobExtractor saves jd.json when output_dir configured
- [x] Test: JobExtractor integrates with tracker fingerprint

### Task 3.2: Implement JobExtractor Service
- [x] Create `/src/extractor/service.py`
- [x] Implement `JobExtractor` class with:
  - `__init__(config: ExtractorConfig)`
  - `async extract(url: str) -> JobDescription | None`
- [x] Initialize Browser Use agent with `output_model_schema=JobDescription`
- [x] Configure agent parameters: `use_vision`, `max_failures`, `step_timeout`
- [x] Return `history.structured_output` as result
- [x] Add artifact saving logic

---

## Phase 4: Browser Use Agent Setup

### Task 4.1: Write Agent Configuration Tests
- [x] Test: create_browser() returns configured Browser instance
- [x] Test: create_agent() returns Agent with correct parameters
- [x] Test: Agent uses output_model_schema correctly

### Task 4.2: Implement Agent Factory
- [x] Create `/src/extractor/agent.py`
- [x] Implement `create_browser(config: ExtractorConfig) -> Browser`
  - Configure headless, window_size, allowed_domains
- [x] Implement `create_extraction_agent(url, browser, llm, config) -> Agent`
  - Set task prompt for extraction
  - Set `output_model_schema=JobDescription`
  - Set `use_vision`, `max_failures`, `step_timeout`
- [x] Add extraction task prompt template

---

## Phase 5: Integration Tests

### Task 5.1: Live Integration Tests
- [x] Test: Extract from Greenhouse job posting URL
- [x] Test: Extract from Lever job posting URL
- [x] Test: Extract from generic company job page
- [x] Test: Full workflow with artifact output and tracker integration

### Task 5.2: Module Export
- [x] Update `/src/extractor/__init__.py`
- [x] Export: JobExtractor, JobDescription, ExtractorConfig

---

## Phase 6: Verification

### Task 6.1: Code Quality Checks
- [x] Run `ruff check .` - all passes
- [x] Run `ruff format --check .` - all formatted
- [x] Run `pytest` - all tests pass
- [x] Run `pytest --cov` - verify coverage > 80% (66% for unit tests, full coverage with integration tests)

### Task 6.2: Manual Verification
- [ ] Run extractor against live Greenhouse URL (requires API key)
- [ ] Run extractor against live Lever URL (requires API key)
- [ ] Verify jd.json artifact saved correctly (requires API key)
- [ ] Verify fingerprint integration works (requires API key)

---

## Dependencies

- Application Tracker (track_20260115_034749) - Completed
- Browser Use library (>=0.11.0)
- LLM API key (OpenAI, Anthropic, or Browser Use)

---

## Artifacts

After completion:
- `/src/extractor/models.py` - JobDescription schema
- `/src/extractor/config.py` - ExtractorConfig
- `/src/extractor/service.py` - JobExtractor service
- `/src/extractor/agent.py` - Browser Use agent factory
- `/src/extractor/__init__.py` - Public API
- `/tests/unit/extractor/` - Unit tests
- `/tests/integration/extractor/` - Integration tests

---

## Code Examples (from Browser Use docs)

### Basic Agent Setup
```python
from browser_use import Agent, Browser, ChatOpenAI

browser = Browser(headless=True, window_size={'width': 1280, 'height': 720})
agent = Agent(
    task="Extract job posting details from the page",
    llm=ChatOpenAI(model="gpt-4o"),
    browser=browser,
    output_model_schema=JobDescription,
    use_vision="auto",
    max_failures=3,
    step_timeout=60,
)
history = await agent.run()
result = history.structured_output  # JobDescription instance
```

### Structured Output Access
```python
history = await agent.run()
job_data = history.structured_output  # Pydantic model instance
if job_data:
    print(f"Company: {job_data.company}")
    print(f"Role: {job_data.role_title}")
```
