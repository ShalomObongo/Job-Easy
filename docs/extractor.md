# Extractor Module Documentation

## Overview

The **extractor** module is responsible for extracting structured job description data from job posting URLs using Browser Use with LLM-based extraction. It navigates to job posting pages, extracts comprehensive job information, and returns a structured `JobDescription` model that can be used by downstream modules for scoring, tailoring, and application.

### Purpose

- Navigate to job posting URLs using a headless or headed browser
- Extract structured job data using LLM-powered web scraping
- Support multiple job boards (Greenhouse, Lever, Workday, LinkedIn, Indeed, Glassdoor)
- Detect job board sources and extract platform-specific job IDs
- Provide configuration for different LLM providers (OpenAI, Anthropic, Browser Use)
- Handle Chrome profile management for authenticated sessions

### Key Features

- **Browser Use Integration**: Uses Browser Use library for AI-powered browser automation
- **Structured Output**: Returns validated Pydantic models with comprehensive job data
- **Multi-LLM Support**: Supports OpenAI, Anthropic, and Browser Use LLM providers with auto-detection
- **Chrome Profile Management**: Can reuse existing Chrome profiles for authenticated sessions
- **Job Board Detection**: Automatically detects source platforms from URLs
- **Job ID Extraction**: Extracts platform-specific job IDs using URL pattern matching
- **Configurable**: Extensive configuration via environment variables or ExtractorConfig

## Architecture

### Module Structure

```
src/extractor/
├── __init__.py          # Public API exports
├── models.py            # JobDescription data model
├── config.py            # ExtractorConfig settings
├── agent.py             # Browser Use agent factory functions
└── service.py           # JobExtractor main service class
```

### Data Flow

```
URL → JobExtractor.extract()
    ↓
Create Browser (agent.py)
    ↓
Create LLM (agent.py)
    ↓
Create Extraction Agent (agent.py)
    ↓
Run Agent with structured output schema
    ↓
Extract JobDescription
    ↓
Detect source & job_id
    ↓
Return JobDescription model
```

### Component Relationships

```
JobExtractor (service.py)
    ├── ExtractorConfig (config.py)
    ├── JobDescription (models.py)
    └── Agent Factories (agent.py)
        ├── create_browser()
        ├── create_extraction_agent()
        ├── get_llm()
        └── _create_chrome_profile_snapshot()
```

## Key Components

### 1. JobDescription Model (`models.py`)

The core data model representing extracted job posting data.

**Class**: `JobDescription`

**Required Fields**:
- `company: str` - Company name
- `role_title: str` - Job title/position
- `job_url: str` - Canonical URL of the job posting

**Optional Fields**:
- `location: str | None` - Job location or "Remote"
- `apply_url: str | None` - Direct application URL
- `job_id: str | None` - Platform-specific job identifier
- `description: str | None` - Full job description text
- `responsibilities: list[str]` - List of key responsibilities
- `qualifications: list[str]` - Required/preferred qualifications
- `required_skills: list[str]` - Must-have skills/technologies
- `preferred_skills: list[str]` - Nice-to-have skills/technologies
- `experience_years_min: int | None` - Minimum years of experience
- `experience_years_max: int | None` - Maximum years of experience
- `education: str | None` - Required education level
- `salary_min: int | None` - Minimum salary
- `salary_max: int | None` - Maximum salary
- `salary_currency: str | None` - Currency code (USD, EUR, etc.)
- `work_type: Literal["remote", "hybrid", "onsite"] | None` - Work arrangement
- `employment_type: Literal["full-time", "part-time", "contract"] | None` - Employment type
- `extracted_at: datetime` - Timestamp of extraction (auto-generated)
- `extraction_source: str | None` - Detected job board

**Methods**:
- `to_dict() -> dict` - Serialize to dictionary
- `from_dict(data: dict) -> JobDescription` - Deserialize from dictionary
- `save_json(path: Path | str) -> None` - Save to JSON file

**Example**:
```python
from src.extractor.models import JobDescription

job = JobDescription(
    company="ExampleCo",
    role_title="Senior Software Engineer",
    job_url="https://example.com/jobs/123",
    location="San Francisco, CA",
    required_skills=["Python", "Django", "PostgreSQL"],
    work_type="hybrid",
    employment_type="full-time"
)

# Save to file
job.save_json("artifacts/jd.json")
```

---

### 2. ExtractorConfig (`config.py`)

Configuration settings for the extractor module using Pydantic Settings.

**Class**: `ExtractorConfig`

**Browser Settings**:
- `headless: bool` - Run browser in headless mode (default: True)
- `window_width: int` - Browser window width (default: 1280)
- `window_height: int` - Browser window height (default: 720)

**Agent Settings**:
- `step_timeout: int` - Timeout per step in seconds (default: 60)
- `max_failures: int` - Maximum retry attempts (default: 3)
- `use_vision: str` - Vision mode: "auto", "true", or "false" (default: "auto")

**Output Settings**:
- `output_dir: Path` - Directory for artifacts (default: "./artifacts")

**Domain Restrictions**:
- `allowed_domains: list[str]` - List of allowed domains for navigation (default: [])

**LLM Settings**:
- `llm_provider: str` - Provider: "openai", "anthropic", "browser_use", or "auto" (default: "auto")
- `llm_base_url: str | None` - Base URL for custom LLM endpoints
- `llm_api_key: str | None` - API key for LLM provider
- `llm_model: str | None` - Model ID (e.g., "gpt-4o", "claude-sonnet-4-20250514")
- `llm_reasoning_effort: str | None` - Reasoning effort level for supported models

**Chrome Profile Settings**:
- `keep_browser_use_temp_dirs: bool` - Keep temp directories (default: False)

**Environment Variables**:
All settings can be configured via environment variables with the `EXTRACTOR_` prefix:
- `EXTRACTOR_HEADLESS=true`
- `EXTRACTOR_LLM_PROVIDER=openai`
- `EXTRACTOR_LLM_API_KEY=sk-...`
- `EXTRACTOR_LLM_MODEL=gpt-4o`
- etc.

**Functions**:
- `get_extractor_config() -> ExtractorConfig` - Get singleton instance
- `reset_extractor_config() -> None` - Reset singleton (for testing)

**Example**:
```python
from src.extractor.config import ExtractorConfig, get_extractor_config

# Use default config
config = get_extractor_config()

# Or create custom config
config = ExtractorConfig(
    headless=False,
    llm_provider="anthropic",
    llm_model="claude-sonnet-4-20250514",
    step_timeout=120
)
```

---

### 3. JobExtractor Service (`service.py`)

The main service class for extracting job descriptions from URLs.

**Class**: `JobExtractor`

**Attributes**:
- `config: ExtractorConfig` - Configuration settings

**Methods**:

#### `__init__(config: ExtractorConfig | None = None)`
Initialize the JobExtractor with optional custom configuration.

#### `async extract(url: str, save_artifact: bool = False) -> JobDescription | None`
Extract job description from a URL.

**Parameters**:
- `url: str` - The job posting URL to extract from
- `save_artifact: bool` - Whether to save jd.json artifact (default: False)

**Returns**:
- `JobDescription | None` - Extracted job description or None if extraction fails

**Workflow**:
1. Creates browser instance
2. Gets LLM instance (tries configured provider or auto-detects)
3. Creates extraction agent with JobDescription schema
4. Runs agent to extract structured data
5. Detects job board source from URL
6. Sets extraction timestamp
7. Attempts to extract job_id if not provided by LLM
8. Optionally saves artifact to `config.output_dir / "jd.json"`
9. Cleans up browser resources

**Example**:
```python
import asyncio
from src.extractor.service import JobExtractor

async def main():
    extractor = JobExtractor()
    job = await extractor.extract(
        url="https://boards.greenhouse.io/company/jobs/12345",
        save_artifact=True
    )

    if job:
        print(f"Extracted: {job.company} - {job.role_title}")
        print(f"Source: {job.extraction_source}")
        print(f"Job ID: {job.job_id}")
    else:
        print("Extraction failed")

asyncio.run(main())
```

**Internal Methods**:

#### `_run_extraction_agent(url: str) -> JobDescription | None`
Runs the Browser Use agent to extract job data. Handles browser lifecycle, LLM initialization, agent creation, and cleanup.

#### `_cleanup_browser_use_temp_profile(browser)`
Deletes Browser Use temp user_data_dir directories to prevent disk bloat.

#### `_get_llm()`
Gets the LLM instance for extraction using agent.get_llm().

#### `_detect_source(url: str) -> str`
Detects the job board source from URL patterns.

**Supported Sources**:
- `lever` - jobs.lever.co
- `greenhouse` - boards.greenhouse.io
- `workday` - myworkdayjobs.com
- `linkedin` - linkedin.com
- `indeed` - indeed.com
- `glassdoor` - glassdoor.com
- `generic` - fallback for unknown sources

---

### 4. Agent Factory (`agent.py`)

Factory functions for creating Browser Use components.

**Functions**:

#### `create_browser(config: ExtractorConfig) -> Browser`
Creates a Browser instance with the given configuration.

**Features**:
- Forces local Playwright browser (not cloud)
- Configures window size
- Optionally sets allowed domains
- Handles Chrome profile management (copy mode, direct mode, auto mode)
- Falls back gracefully on permission errors
- Creates lightweight profile snapshots to avoid "Local State" permission issues

**Chrome Profile Modes**:
- `copy` - Creates a lightweight snapshot of the Chrome profile (safe)
- `direct` - Uses the profile in place (may have permission issues)
- `auto` - Attempts direct mode, falls back to copy mode on permission errors

**Example**:
```python
from src.extractor.config import ExtractorConfig
from src.extractor.agent import create_browser

config = ExtractorConfig(headless=True)
browser = create_browser(config)
```

#### `create_extraction_agent(url: str, browser: Browser, llm: LLM, config: ExtractorConfig) -> Agent`
Creates an extraction Agent with structured output schema.

**Parameters**:
- `url: str` - Job posting URL to extract from
- `browser: Browser` - Browser instance
- `llm: LLM` - LLM instance
- `config: ExtractorConfig` - Configuration settings

**Returns**:
- `Agent` - Configured Browser Use Agent with JobDescription schema

**Agent Configuration**:
- Task: Generated extraction prompt (see `get_extraction_prompt()`)
- Output schema: `JobDescription` model
- Vision mode: From config
- Max failures: From config
- Step timeout: From config

#### `get_extraction_prompt(url: str) -> str`
Generates the extraction task prompt for the agent.

**Prompt Template**:
```
Navigate to {url} and extract all job posting details.

Extract the following information:
- Company name
- Job title/role
- Location (city, state, country, or "Remote")
- Full job description text
- Key responsibilities (as a list)
- Required qualifications (as a list)
- Required skills/technologies
- Preferred/nice-to-have skills
- Years of experience required (min and max if specified)
- Education requirements
- Salary range (if disclosed)
- Work type (remote, hybrid, or onsite)
- Employment type (full-time, part-time, or contract)
- Direct application URL (if different from the job page URL)
- Job ID (if visible on the page)

Be thorough and extract as much information as possible from the job posting.
```

#### `get_llm(config: ExtractorConfig | None = None) -> LLM | None`
Gets the LLM instance for extraction with provider auto-detection.

**Provider Priority** (when provider="auto"):
1. OpenAI (if `base_url` is set or `OPENAI_API_KEY` / `LLM_API_KEY` is available)
2. Browser Use (if `BROWSER_USE_API_KEY` is available)
3. Anthropic (if `ANTHROPIC_API_KEY` / `LLM_API_KEY` is available)

**Explicit Providers**:
- `openai` - Uses `_create_openai_llm()`
- `anthropic` - Uses `_create_anthropic_llm()`
- `browser_use` - Uses `_create_browser_use_llm()`

**Environment Variables**:
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `BROWSER_USE_API_KEY` - Browser Use API key
- `LLM_API_KEY` - Fallback API key

**Default Models**:
- OpenAI: `gpt-4o`
- Anthropic: `claude-sonnet-4-20250514`
- Browser Use: `bu-latest`

#### `_create_chrome_profile_snapshot(chrome_user_data_dir: Path, profile_directory: str) -> Path`
Creates a lightweight temp user-data-dir containing the selected Chrome profile.

**Purpose**:
Browser Use's Chrome handling copies the selected profile AND "Local State" to a temp directory. On managed installs, "Local State" can be unreadable (often root-owned), which makes startup fail.

**Solution**:
- Copies only the selected profile directory (skipping large caches/extensions)
- Copies "Local State" only if readable (otherwise Chrome regenerates it)
- Uses path containing "browser-use-user-data-dir-" so Browser Use doesn't try to copy again

**Skipped Directories** (for performance):
- Extensions (can be hundreds of MB)
- Cache, Code Cache, GPUCache, GrShaderCache, ShaderCache
- DawnGraphiteCache, DawnWebGPUCache
- Service Worker

---

## Public API

The module exports the following public API via `__init__.py`:

```python
from src.extractor import (
    JobExtractor,           # Main service class
    JobDescription,         # Data model
    ExtractorConfig,        # Configuration class
    get_extractor_config,   # Config singleton getter
)
```

## Dependencies

### External Dependencies

From `pyproject.toml`:
- **browser-use >= 0.11.0** - AI-powered browser automation library
- **pydantic >= 2.0.0** - Data validation and settings management
- **pydantic-settings >= 2.0.0** - Settings management via environment variables

LLM Provider Dependencies (imported dynamically):
- **langchain-openai** - For OpenAI LLM support (via Browser Use)
- **langchain-anthropic** - For Anthropic LLM support (via Browser Use)

### Internal Dependencies

**From other modules**:
- `src.config.settings` - Global settings (`get_settings()`)
  - Used for Chrome profile configuration
  - Chrome user data directory settings
  - Chrome profile mode settings

- `src.tracker.fingerprint` - Job ID extraction (`extract_job_id()`)
  - Used as fallback when LLM doesn't extract job_id
  - Extracts platform-specific IDs from URLs

**Dependencies on extractor**:

The following modules depend on the extractor:

1. **src.scoring** - Uses `JobDescription` model for fit scoring
2. **src.tailoring** - Uses `JobDescription` model for resume/cover letter tailoring
3. **src.autonomous** - Uses `JobExtractor` service and `JobDescription` model
4. **src.runner** - Uses `get_llm()` and `_create_chrome_profile_snapshot()` from agent.py
5. **src.__main__** - CLI entry point uses `JobExtractor` service

## Integration with Other Modules

### Data Flow in Job-Easy Pipeline

```
extractor → scoring → tailoring → runner
    ↓           ↓          ↓           ↓
JobDescription  FitResult  Resume    Application
                           Cover Letter
```

### 1. Extractor → Scoring

The extractor provides `JobDescription` to the scoring module:

```python
from src.extractor.service import JobExtractor
from src.scoring.service import FitScoringService
from src.scoring.profile import ProfileService

# Extract job
extractor = JobExtractor()
job = await extractor.extract("https://example.com/jobs/123")

# Score fit
profile = ProfileService().load_profile("profiles/profile.yaml")
fit_result = FitScoringService().evaluate(job, profile)
```

### 2. Extractor → Tailoring

The tailoring module uses `JobDescription` to generate customized documents:

```python
from src.extractor.models import JobDescription
from src.tailoring.service import TailoringService

job = JobDescription.from_dict({"company": "...", "role_title": "..."})
service = TailoringService()
result = await service.tailor_all(job, profile)
# Generates tailored resume and cover letter
```

### 3. Extractor → Autonomous

The autonomous module uses `JobExtractor` for batch processing:

```python
from src.extractor.service import JobExtractor

extractor = JobExtractor()
for url in job_urls:
    job = await extractor.extract(url, save_artifact=True)
    # Process job (score, tailor, apply)
```

### 4. Extractor → Runner

The runner module reuses LLM and Chrome profile utilities from agent.py:

```python
from src.extractor.agent import get_llm, _create_chrome_profile_snapshot

# Get LLM for application agent
llm = get_llm(config)

# Create Chrome profile snapshot
snapshot_dir = _create_chrome_profile_snapshot(
    chrome_user_data_dir,
    profile_directory
)
```

### 5. Tracker Integration

The extractor uses tracker's `extract_job_id()` as a fallback:

```python
from src.tracker.fingerprint import extract_job_id

# If LLM didn't extract job_id, try pattern matching
if not result.job_id:
    result.job_id = extract_job_id(result.job_url or url)
```

## Usage Examples

### Basic Extraction

```python
import asyncio
from src.extractor import JobExtractor

async def main():
    extractor = JobExtractor()
    job = await extractor.extract("https://example.com/jobs/123")

    if job:
        print(f"Company: {job.company}")
        print(f"Role: {job.role_title}")
        print(f"Location: {job.location}")
        print(f"Required Skills: {', '.join(job.required_skills)}")

asyncio.run(main())
```

### Custom Configuration

```python
from src.extractor import JobExtractor, ExtractorConfig

config = ExtractorConfig(
    headless=False,           # Show browser
    llm_provider="anthropic", # Use Claude
    llm_model="claude-sonnet-4-20250514",
    step_timeout=120,         # 2 minute timeout
    output_dir="./my_output"
)

extractor = JobExtractor(config)
job = await extractor.extract(url, save_artifact=True)
```

### Environment Variable Configuration

```bash
# .env file
EXTRACTOR_HEADLESS=true
EXTRACTOR_LLM_PROVIDER=openai
EXTRACTOR_LLM_API_KEY=sk-...
EXTRACTOR_LLM_MODEL=gpt-4o
EXTRACTOR_STEP_TIMEOUT=90
EXTRACTOR_OUTPUT_DIR=./artifacts
```

```python
from src.extractor import JobExtractor, get_extractor_config

# Config automatically loaded from environment
config = get_extractor_config()
extractor = JobExtractor(config)
```

### Save and Load JobDescription

```python
from pathlib import Path
from src.extractor.models import JobDescription

# Save
job.save_json("artifacts/jd.json")

# Load
loaded_job = JobDescription.from_dict(
    json.loads(Path("artifacts/jd.json").read_text())
)
```

### CLI Usage

```bash
# Extract mode (command-line)
python -m src extract "https://example.com/jobs/123" --out-run-dir ./runs/run_001

# Output: ./runs/run_001/jd.json
```

### Using with Chrome Profile

```bash
# .env configuration
USE_EXISTING_CHROME_PROFILE=true
CHROME_USER_DATA_DIR=/Users/username/Library/Application Support/Google/Chrome
CHROME_PROFILE_DIR=Default
CHROME_PROFILE_MODE=auto
```

This allows the extractor to reuse your Chrome profile with existing logins and cookies.

### LLM Provider Configuration

**OpenAI**:
```bash
EXTRACTOR_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
EXTRACTOR_LLM_MODEL=gpt-4o
```

**Anthropic**:
```bash
EXTRACTOR_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
EXTRACTOR_LLM_MODEL=claude-sonnet-4-20250514
```

**Custom OpenAI-Compatible Endpoint** (Ollama, LM Studio, etc.):
```bash
EXTRACTOR_LLM_PROVIDER=openai
EXTRACTOR_LLM_BASE_URL=http://localhost:11434/v1
EXTRACTOR_LLM_MODEL=llama2
OPENAI_API_KEY=not-needed  # Dummy key for local servers
```

**Auto-Detection** (tries providers in order):
```bash
EXTRACTOR_LLM_PROVIDER=auto
# Set any of: OPENAI_API_KEY, ANTHROPIC_API_KEY, BROWSER_USE_API_KEY
```

## Input/Output Specifications

### Input

**JobExtractor.extract()**:
- **url**: `str` - Valid HTTP/HTTPS URL to a job posting
  - Supported platforms: Greenhouse, Lever, Workday, LinkedIn, Indeed, Glassdoor, generic sites
  - Example: `https://boards.greenhouse.io/company/jobs/12345`

- **save_artifact**: `bool` - Whether to save jd.json (default: False)

### Output

**JobDescription** (JSON Schema):

```json
{
  "company": "string (required)",
  "role_title": "string (required)",
  "job_url": "string (required)",
  "location": "string | null",
  "apply_url": "string | null",
  "job_id": "string | null",
  "description": "string | null",
  "responsibilities": ["string"],
  "qualifications": ["string"],
  "required_skills": ["string"],
  "preferred_skills": ["string"],
  "experience_years_min": "integer | null",
  "experience_years_max": "integer | null",
  "education": "string | null",
  "salary_min": "integer | null",
  "salary_max": "integer | null",
  "salary_currency": "string | null",
  "work_type": "remote | hybrid | onsite | null",
  "employment_type": "full-time | part-time | contract | null",
  "extracted_at": "ISO 8601 datetime string",
  "extraction_source": "string | null"
}
```

**Example Output**:

```json
{
  "company": "ExampleCo",
  "role_title": "Senior Software Engineer",
  "job_url": "https://boards.greenhouse.io/exampleco/jobs/12345",
  "location": "San Francisco, CA",
  "apply_url": "https://boards.greenhouse.io/exampleco/jobs/12345/apply",
  "job_id": "greenhouse:12345",
  "description": "We are looking for a Senior Software Engineer...",
  "responsibilities": [
    "Design and implement scalable backend services",
    "Mentor junior engineers",
    "Collaborate with product team"
  ],
  "qualifications": [
    "5+ years of software engineering experience",
    "Strong understanding of distributed systems",
    "Experience with Python and Go"
  ],
  "required_skills": [
    "Python",
    "PostgreSQL",
    "Docker",
    "Kubernetes"
  ],
  "preferred_skills": [
    "Go",
    "GraphQL",
    "Redis"
  ],
  "experience_years_min": 5,
  "experience_years_max": null,
  "education": "Bachelor's degree in Computer Science or related field",
  "salary_min": 150000,
  "salary_max": 200000,
  "salary_currency": "USD",
  "work_type": "hybrid",
  "employment_type": "full-time",
  "extracted_at": "2025-01-21T10:30:00.000Z",
  "extraction_source": "greenhouse"
}
```

### Artifact Files

When `save_artifact=True` or using CLI with `--out-run-dir`:

**Output Directory Structure**:
```
artifacts/runs/<run_id>/
└── jd.json              # Extracted JobDescription JSON
```

## Error Handling

### Common Errors

1. **No LLM Configured**:
```
Error: No LLM configured. Set EXTRACTOR_LLM_PROVIDER and credentials.
```
**Solution**: Set one of:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `BROWSER_USE_API_KEY`
- Or configure `EXTRACTOR_LLM_API_KEY` and `EXTRACTOR_LLM_PROVIDER`

2. **Chrome Profile Permission Denied**:
```
Warning: Failed to use Chrome profile (permission denied). Falling back to fresh profile.
```
**Solution**:
- Use `CHROME_PROFILE_MODE=auto` (recommended)
- Choose a different `CHROME_PROFILE_DIR` (e.g., "Profile 2")
- Fix file permissions on the Chrome profile directory

3. **Extraction Timeout**:
```
Error: Agent execution failed: Timeout
```
**Solution**: Increase `EXTRACTOR_STEP_TIMEOUT` (default: 60 seconds)

4. **Browser Launch Failure**:
```
Error: Failed to launch browser
```
**Solution**:
- Check Playwright installation: `playwright install chromium`
- Verify Chrome installation if using Chrome profile

### Return Values

- **Success**: Returns `JobDescription` object
- **Failure**: Returns `None` (logs error details)

### Logging

The module uses Python's standard logging:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

Log messages include:
- `INFO`: Extraction start/success, artifact saving
- `WARNING`: Extraction failures, profile fallbacks
- `ERROR`: Agent failures, configuration errors

## Configuration Reference

### Complete Configuration Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `headless` | bool | True | Run browser in headless mode |
| `window_width` | int | 1280 | Browser window width |
| `window_height` | int | 720 | Browser window height |
| `step_timeout` | int | 60 | Timeout per step (seconds) |
| `max_failures` | int | 3 | Maximum retry attempts |
| `use_vision` | str | "auto" | Vision mode ("auto", "true", "false") |
| `output_dir` | Path | "./artifacts" | Output directory |
| `allowed_domains` | list[str] | [] | Allowed navigation domains |
| `llm_provider` | str | "auto" | LLM provider |
| `llm_base_url` | str \| None | None | Custom LLM endpoint URL |
| `llm_api_key` | str \| None | None | LLM API key |
| `llm_model` | str \| None | None | LLM model ID |
| `llm_reasoning_effort` | str \| None | None | Reasoning effort level |
| `keep_browser_use_temp_dirs` | bool | False | Keep temp directories |

### Environment Variable Mapping

All settings use `EXTRACTOR_` prefix:

```bash
EXTRACTOR_HEADLESS=true
EXTRACTOR_WINDOW_WIDTH=1920
EXTRACTOR_WINDOW_HEIGHT=1080
EXTRACTOR_STEP_TIMEOUT=120
EXTRACTOR_MAX_FAILURES=5
EXTRACTOR_USE_VISION=auto
EXTRACTOR_OUTPUT_DIR=./my_artifacts
EXTRACTOR_ALLOWED_DOMAINS=["example.com","*.example.org"]
EXTRACTOR_LLM_PROVIDER=openai
EXTRACTOR_LLM_BASE_URL=http://localhost:11434/v1
EXTRACTOR_LLM_API_KEY=sk-...
EXTRACTOR_LLM_MODEL=gpt-4o
EXTRACTOR_LLM_REASONING_EFFORT=medium
EXTRACTOR_KEEP_BROWSER_USE_TEMP_DIRS=false
```

## Performance Considerations

### Extraction Speed

Typical extraction times:
- Simple job boards (Greenhouse, Lever): 15-30 seconds
- Complex job boards (Workday, LinkedIn): 30-60 seconds
- Depends on: page load time, LLM response time, network latency

### Resource Usage

**Browser**:
- Memory: ~200-500 MB per browser instance
- CPU: Low (mostly waiting for page loads)
- Disk: Temp directories cleaned up automatically (unless `keep_browser_use_temp_dirs=True`)

**LLM**:
- Token usage: ~2000-5000 tokens per extraction (varies by page complexity)
- Cost estimate (GPT-4o): ~$0.01-0.03 per extraction

### Optimization Tips

1. **Use headless mode** for production (`EXTRACTOR_HEADLESS=true`)
2. **Increase timeout** for slow job boards (`EXTRACTOR_STEP_TIMEOUT=120`)
3. **Use local LLM** for cost reduction (Ollama, LM Studio)
4. **Enable Chrome profile** for faster authenticated extractions
5. **Set allowed_domains** to restrict navigation (security)

## Testing

### Unit Tests

```python
import pytest
from src.extractor.models import JobDescription

def test_job_description_serialization():
    job = JobDescription(
        company="TestCo",
        role_title="Engineer",
        job_url="https://example.com/jobs/1"
    )
    data = job.to_dict()
    loaded = JobDescription.from_dict(data)
    assert loaded.company == "TestCo"
```

### Integration Tests

```python
import pytest
from src.extractor import JobExtractor

@pytest.mark.integration
async def test_extract_greenhouse_job():
    extractor = JobExtractor()
    job = await extractor.extract("https://boards.greenhouse.io/...")
    assert job is not None
    assert job.company
    assert job.role_title
    assert job.extraction_source == "greenhouse"
```

### Mock Testing

```python
from unittest.mock import AsyncMock, patch
from src.extractor.service import JobExtractor

async def test_extract_with_mock():
    with patch('src.extractor.agent.create_browser') as mock_browser:
        mock_browser.return_value = AsyncMock()
        extractor = JobExtractor()
        # Test extraction logic without actual browser
```

## Troubleshooting

### Issue: Extraction returns None

**Possible Causes**:
1. Invalid URL
2. Job posting no longer exists
3. LLM not configured
4. Browser launch failure
5. Network connectivity issues

**Debug Steps**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

extractor = JobExtractor()
job = await extractor.extract(url)
# Check logs for detailed error messages
```

### Issue: Missing job data fields

**Cause**: LLM couldn't extract all fields from the page

**Solution**:
- Check if page requires authentication (use Chrome profile)
- Try different LLM model (`EXTRACTOR_LLM_MODEL=gpt-4o`)
- Increase timeout (`EXTRACTOR_STEP_TIMEOUT=120`)
- Use vision mode (`EXTRACTOR_USE_VISION=true`)

### Issue: Chrome profile errors

**Symptoms**:
```
PermissionError: [Errno 13] Permission denied: '.../Local State'
```

**Solutions**:
1. Use `CHROME_PROFILE_MODE=auto` (automatic fallback)
2. Use `CHROME_PROFILE_MODE=copy` (always use snapshot)
3. Choose different profile: `CHROME_PROFILE_DIR=Profile 2`
4. Fix permissions: `chmod -R u+r ~/Library/Application\ Support/Google/Chrome/`

### Issue: High LLM costs

**Solutions**:
1. Use local LLM (Ollama):
```bash
EXTRACTOR_LLM_PROVIDER=openai
EXTRACTOR_LLM_BASE_URL=http://localhost:11434/v1
EXTRACTOR_LLM_MODEL=llama2
```

2. Use cheaper model:
```bash
EXTRACTOR_LLM_MODEL=gpt-4o-mini  # Cheaper than gpt-4o
```

## Future Enhancements

### Planned Features

1. **Caching**: Cache extracted job descriptions to avoid re-extraction
2. **Batch Extraction**: Extract multiple jobs in parallel
3. **Retry Logic**: Automatic retry with exponential backoff
4. **Job Board Plugins**: Extensible plugin system for custom extractors
5. **Validation**: Additional validation for extracted data quality
6. **Metrics**: Extraction success rate, performance metrics
7. **A/B Testing**: Compare different LLM providers/prompts

### Extension Points

The module is designed for extensibility:

1. **Custom Extraction Prompts**: Override `get_extraction_prompt()`
2. **Custom Job Models**: Extend `JobDescription` with additional fields
3. **Custom LLM Providers**: Implement new `_create_*_llm()` functions
4. **Custom Source Detection**: Extend `_detect_source()` with new patterns

## See Also

- [Project Brief](project-brief.md) - Overall system architecture
- [Workflow Diagram](workflow-diagram.md) - End-to-end process flow
- [Browser Use Documentation](https://github.com/browser-use/browser-use) - Browser Use library
- [Pydantic Documentation](https://docs.pydantic.dev/) - Data validation

## License

MIT License - See LICENSE file for details
