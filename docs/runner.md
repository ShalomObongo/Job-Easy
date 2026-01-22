# Runner Module Documentation

## Overview

The **runner** module is the browser automation engine for the Job-Easy application. It orchestrates the entire job application submission process using Browser Use agents, handling form filling, file uploads, screening questions, and final submission with human-in-the-loop (HITL) confirmation gates. The runner provides intelligent navigation, persistent question answering, domain safety controls, and structured output tracking.

### Purpose

- **Browser Automation**: Automate job application form filling and submission using AI-powered browser agents
- **Intelligent Form Handling**: Navigate multi-step forms, handle dropdowns, upload documents, and respond to screening questions
- **Safety Gates**: Enforce human confirmation before final submission and prevent prohibited domain access
- **Persistent Learning**: Store and reuse answers to common application questions via Q&A bank
- **Structured Output**: Return standardized results with proof of submission, errors, and execution traces
- **Profile Integration**: Automatically fill applicant information from user profile (name, email, phone, LinkedIn)

## Architecture

### Module Structure

```
src/runner/
├── __init__.py          # Module docstring and public API
├── models.py            # Result models (ApplicationRunResult, RunStatus, StepSummary)
├── domains.py           # Domain safety policies (blocklist, allowlist logging)
├── qa_bank.py           # Persistent Q&A storage for screening questions
├── agent.py             # Browser Use agent factory and configuration
└── service.py           # Single-job orchestration service
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                   SingleJobApplicationService                        │
│  (End-to-end orchestration: tracker → extractor → scoring →         │
│   tailoring → runner agent)                                          │
└────────────┬────────────────────────────────────────┬────────────────┘
             │                                        │
             ▼                                        ▼
┌────────────────────────┐              ┌─────────────────────────────┐
│   Domain Safety Layer  │              │    Browser Use Agent        │
│                        │              │                             │
│ - Prohibited domains   │              │ - Form navigation           │
│ - Allowlist logging    │──────────────│ - Field population          │
│ - Pre-run validation   │              │ - File uploads              │
└────────────────────────┘              │ - Multi-step flows          │
                                        │ - Submit confirmation       │
                                        └──────────┬──────────────────┘
                                                   │
                                                   ▼
                                        ┌─────────────────────────────┐
                                        │    Q&A Bank + HITL Tools    │
                                        │                             │
                                        │ - Persistent Q&A storage    │
                                        │ - Human prompts             │
                                        │ - Submit confirmation       │
                                        │ - OTP/2FA handling          │
                                        └─────────────────────────────┘
```

### Integration with Other Modules

The runner module integrates with:

1. **tracker** (`src/tracker`):
   - Checks for duplicate applications before running
   - Updates application status (SUBMITTED, FAILED, SKIPPED)
   - Records proof artifacts and file paths

2. **extractor** (`src/extractor`):
   - Receives job description and canonical URLs
   - Inherits LLM configuration for agent execution

3. **scoring** (`src/scoring`):
   - Receives fit evaluation results
   - Enforces skip/review recommendations with HITL prompts

4. **tailoring** (`src/tailoring`):
   - Receives tailored resume and cover letter paths
   - Provides documents for upload during application

5. **hitl** (`src/hitl`):
   - Uses HITL tools for yes/no prompts, free text input, submit confirmation
   - Integrates confirm_submit, ask_yes_no, ask_free_text, ask_otp_code tools

6. **config** (`src/config`):
   - Reads runner configuration (LLM settings, browser options, safety controls)
   - Configures prohibited domains, Q&A bank path, allowlist log path

7. **autonomous** (`src/autonomous`):
   - Used by BatchRunner for sequential job processing
   - Returns ApplicationRunResult for each job in the batch

## Execution Flow

### Single Job Application Flow

```
1. URL Validation
   ├── Check prohibited domains → BLOCKED if matched
   └── Proceed to duplicate check

2. Duplicate Detection (First Pass)
   ├── Check tracker by URL only
   ├── If duplicate + SUBMITTED → Prompt "Proceed anyway?"
   │   ├── User says NO → Return DUPLICATE_SKIPPED
   │   └── User says YES → Record override and continue
   └── No duplicate → Continue

3. Job Extraction
   ├── Extract job description via extractor module
   ├── Save jd.json to run directory
   └── Determine canonical start URL (apply_url or job_url)

4. Duplicate Detection (Second Pass - with job details)
   ├── Check tracker by canonical URL + company + role + location
   ├── If duplicate + SUBMITTED → Prompt "Proceed anyway?"
   │   ├── User says NO → Return DUPLICATE_SKIPPED
   │   └── User says YES → Record override and continue
   └── No duplicate → Continue or link to existing fingerprint

5. Tracker Initialization
   ├── Create tracker record with fingerprint
   └── Use fingerprint for run directory (artifacts/runs/<fingerprint>)

6. Fit Scoring
   ├── Load user profile
   ├── Evaluate job fit
   ├── If recommendation = "skip" → Prompt "Proceed anyway?"
   │   ├── User says NO → Update tracker to SKIPPED, return SKIPPED
   │   └── User says YES → Add override note, continue
   └── If recommendation = "review" → Prompt "Proceed?"
       ├── User says NO → Update tracker to SKIPPED, return SKIPPED
       └── User says YES → Continue

7. Document Tailoring
   ├── Generate tailored resume and cover letter
   ├── Save to run directory
   └── If tailoring fails → Update tracker to FAILED, return FAILED

8. Document Approval
   ├── Prompt: "Approve resume/cover letter for upload?"
   ├── User says NO → Return STOPPED_BEFORE_SUBMIT
   └── User says YES → Continue to browser automation

9. Browser Automation (via _run_application_flow)
   ├── Initialize Browser Use browser with safety controls
   ├── Create application agent with:
   │   ├── LLM from get_runner_llm()
   │   ├── HITL tools (confirm_submit, ask_yes_no, ask_free_text, ask_otp_code)
   │   ├── Q&A bank tool (resolve_answer)
   │   ├── Sensitive data placeholders (first_name, last_name, email, phone, etc.)
   │   └── Available file paths (resume, cover letter)
   ├── Execute agent.run()
   ├── Track visited URLs and final URL
   ├── Log allowed domains to allowlist log
   └── Return ApplicationRunResult

10. Post-Submission Processing
    ├── If status = SUBMITTED:
    │   ├── Update tracker with proof text and screenshot
    │   ├── Update tracker with resume/cover letter artifact paths
    │   └── Update tracker status to SUBMITTED
    └── Return result with notes, errors, proof
```

### Browser Agent Flow (within agent.run)

```
1. Navigate to Job URL
   ├── If job posting page → Find and click "Apply" button
   └── If application form page → Start filling

2. Form Filling Loop
   ├── Identify required fields
   ├── Fill from sensitive_data placeholders (first_name, last_name, email, phone, etc.)
   ├── For unknown questions → Call resolve_answer tool:
   │   ├── Check Q&A bank for existing answer
   │   ├── If found → Return cached answer
   │   └── If not found → Prompt user, save to Q&A bank, return answer
   ├── For dropdowns → Use dropdown_options + select_dropdown (never type with input)
   ├── For file uploads → Use available_file_paths (resume, cover letter)
   └── Handle multi-step flows (Next/Continue buttons, modals, page transitions)

3. Submit Gate (confirm_submit tool)
   ├── Check for required field errors → If present, return "blocked_missing_fields"
   ├── Prompt user: "Type YES to submit this application"
   ├── If user confirms:
   │   ├── Click submit button (via index or CSS selector fallback)
   │   ├── Wait for page transition
   │   ├── Check for success text → Return "submitted"
   │   ├── Check for required field errors → Return "blocked_missing_fields"
   │   └── Otherwise → Return "confirmed"
   └── If user cancels → Return "cancelled"

4. Verify Submission
   ├── Check for confirmation text ("thank you for applying", etc.)
   ├── Take screenshot if proof_screenshot_path configured
   ├── Extract proof_text from page
   └── Return ApplicationRunResult with status=SUBMITTED

5. Error Handling
   ├── Max failures exceeded → Return FAILED with errors
   ├── Step timeout exceeded → Return FAILED with errors
   ├── CAPTCHA/2FA detected → Ask user for manual help
   ├── Prohibited domain navigation → Browser blocks, return BLOCKED
   └── Exception during agent.run → Return FAILED with exception message
```

## Key Components

### 1. SingleJobApplicationService (`service.py`)

**Purpose**: End-to-end orchestration for a single job application attempt.

**Responsibilities**:
- Coordinate tracker, extractor, scoring, tailoring, and runner modules
- Enforce safety checks (prohibited domains, duplicate detection, fit scoring)
- Manage HITL prompts for skip overrides and document approval
- Initialize browser automation and return structured results

**Key Methods**:

```python
async def run(self, url: str) -> ApplicationRunResult:
    """
    Run a single job application flow from URL.

    Flow:
    1. Validate URL against prohibited domains
    2. Check for duplicates (URL-only, then canonical with job details)
    3. Extract job description
    4. Evaluate fit score
    5. Tailor resume and cover letter
    6. Prompt for document approval
    7. Execute browser automation
    8. Update tracker with results

    Returns:
        ApplicationRunResult with status, proof, errors, and notes
    """
```

```python
async def _run_application_flow(
    self,
    *,
    job_url: str,
    run_dir: Path,
    profile: Any,
    resume_path: str | None,
    cover_letter_path: str | None,
) -> ApplicationRunResult:
    """
    Run the Browser Use application agent and persist artifacts.

    Steps:
    1. Create browser with safety controls (prohibited domains)
    2. Initialize LLM from get_runner_llm()
    3. Build sensitive_data dict from profile (name, email, phone, etc.)
    4. Create Browser Use agent with HITL tools and Q&A bank
    5. Execute agent.run() and capture structured output
    6. Save conversation.jsonl, application_result.json
    7. Log allowed domains to allowlist log
    8. Close browser

    Returns:
        ApplicationRunResult with visited URLs, proof, and errors
    """
```

**Constructor Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `settings` | Any | Global settings (LLM config, paths, safety controls) |
| `tracker_repository` | Any | Tracker database repository |
| `tracker_service` | Any | Tracker service for duplicate checks and status updates |
| `extractor` | Any | Job description extractor service |
| `scoring_service` | Any | Fit scoring service |
| `profile_service` | Any | User profile loader |
| `tailoring_service` | Any \| None | Document tailoring service (creates default if None) |
| `source_mode` | SourceMode | Single or autonomous mode (for tracker metadata) |

**Convenience Entry Point**:

```python
async def run_single_job(url: str, *, settings: Any) -> ApplicationRunResult:
    """
    Convenience entry point for CLI usage.

    Initializes tracker repository, creates service with default
    extractor/scoring/profile services, and runs the application.

    Usage:
        from src.runner.service import run_single_job
        from src.config.settings import Settings

        settings = Settings()
        result = await run_single_job("https://example.com/jobs/123", settings=settings)
    """
```

### 2. Browser Use Agent Factory (`agent.py`)

**Purpose**: Create and configure Browser Use browser and agent instances for application automation.

**Key Functions**:

#### `create_browser`

```python
def create_browser(settings: Any, prohibited_domains: list[str] | None = None) -> Any:
    """
    Create a Browser instance for application runs.

    Configuration:
    - Headless: settings.runner_headless (default: False)
    - Window size: settings.runner_window_width x settings.runner_window_height
    - Prohibited domains: Blocklist-first policy (only specified domains blocked)
    - Chrome profile: settings.use_existing_chrome_profile, chrome_user_data_dir, chrome_profile_dir
    - Profile mode: auto (copy first, fallback to direct), copy (safe), direct (risky)

    Fallback behavior:
    - If permission denied on profile, retries with snapshot copy
    - If snapshot fails, falls back to fresh browser profile

    Returns:
        Browser instance from browser_use library
    """
```

#### `create_application_agent`

```python
def create_application_agent(
    *,
    job_url: str,
    browser: Any,
    llm: Any,
    tools: Any | None = None,
    available_file_paths: list[str] | None = None,
    save_conversation_path: str | Path | None = None,
    qa_bank_path: str | Path | None = None,
    sensitive_data: dict[str, str] | None = None,
    max_failures: int = 3,
    max_actions_per_step: int = 4,
    step_timeout: int = 120,
    use_vision: bool | str = "auto",
) -> Any:
    """
    Create a Browser Use Agent configured for generic application flows.

    Parameters:
    - job_url: Starting URL (job posting or application form)
    - browser: Browser instance from create_browser()
    - llm: LLM instance from get_runner_llm()
    - tools: Custom tools (default: create_hitl_tools())
    - available_file_paths: List of file paths for upload (resume, cover letter)
    - save_conversation_path: Path to save conversation.jsonl
    - qa_bank_path: Path to Q&A bank JSON file
    - sensitive_data: Dict of placeholders (first_name, last_name, email, phone, etc.)
    - max_failures: Maximum retry attempts (default: 3)
    - max_actions_per_step: Actions per step (default: 4)
    - step_timeout: Timeout per step in seconds (default: 120)
    - use_vision: Vision mode (auto, true, false) (default: auto)

    Agent Configuration:
    - task: Application prompt from get_application_prompt()
    - output_model_schema: ApplicationRunResult (structured output)
    - tools: HITL tools + resolve_answer (Q&A bank integration)

    Returns:
        Browser Use Agent instance
    """
```

#### `get_application_prompt`

```python
def get_application_prompt(job_url: str) -> str:
    """
    Build the task prompt for a generic job application flow.

    Prompt includes:
    1. Goal: Reach final submit step, then STOP and ask for explicit confirmation
    2. Applicant info: Sensitive placeholders (first_name, last_name, email, etc.)
    3. Form filling rules:
       - Never guess answers; use resolve_answer for unknowns
       - Use dropdown_options + select_dropdown for dropdowns (never type with input)
       - Check for required field errors before considering submit-ready
       - Only upload cover letter if dedicated field exists (never overwrite resume)
       - Generate text cover letter if text-only field
    4. Flow handling:
       - Navigate from job posting to application form
       - Handle multi-step flows, modals, page transitions
       - Upload files from available_file_paths
       - Use resolve_answer for unknown questions
       - Stop and ask for help on CAPTCHA/2FA
    5. Submit gate:
       - Call confirm_submit when ready (all required fields complete)
       - Pass submit_button_index for final submit button
       - Handle "submitted", "confirmed", "blocked_missing_fields", "cancelled" responses
    6. Structured output:
       - Return ApplicationRunResult with success, status, proof_text, errors, notes

    Returns:
        Formatted task prompt string
    """
```

#### `get_runner_llm`

```python
def get_runner_llm(settings: Any | None = None) -> Any | None:
    """
    Get an LLM instance for the runner.

    Priority order:
    1. RUNNER_LLM_* (settings.runner_llm_provider, runner_llm_api_key, etc.)
    2. EXTRACTOR_LLM_* (extractor config fallback)
    3. Provider defaults (OPENAI_API_KEY, ANTHROPIC_API_KEY, BROWSER_USE_API_KEY)

    Configuration:
    - provider: auto, openai, anthropic, browser_use
    - api_key: Runner-specific or extractor fallback
    - base_url: Custom endpoint (Azure, local LLM server, etc.)
    - model: Model ID (gpt-4o, claude-sonnet-4-20250514, etc.)
    - reasoning_effort: Effort level (none, minimal, low, medium, high, xhigh)

    Returns:
        LLM instance from extractor.agent.get_llm() or None if unconfigured
    """
```

### 3. Result Models (`models.py`)

#### `RunStatus` (Enum)

High-level status for a single application run.

| Status | Description |
|--------|-------------|
| `SUBMITTED` | Application successfully submitted |
| `STOPPED_BEFORE_SUBMIT` | User cancelled before final submission |
| `SKIPPED` | Skipped due to fit scoring or user decision |
| `DUPLICATE_SKIPPED` | Skipped due to duplicate detection |
| `FAILED` | Failed due to error or exception |
| `BLOCKED` | Blocked by prohibited domain or safety control |

#### `StepSummary` (Model)

Structured summary of an important runner step.

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Step name (e.g., "Filled personal info") |
| `url` | str \| None | URL where step occurred |
| `notes` | list[str] | Additional notes or observations |

#### `ApplicationRunResult` (Model)

Structured result for a single application run.

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | Whether the run was successful |
| `status` | RunStatus | High-level status enum |
| `final_url` | str \| None | Last URL visited |
| `visited_urls` | list[str] | All URLs visited during run |
| `steps` | list[StepSummary] | Important steps executed |
| `proof_text` | str \| None | Confirmation text from page |
| `proof_screenshot_path` | str \| None | Path to proof screenshot |
| `errors` | list[str] | Error messages encountered |
| `notes` | list[str] | Additional notes (overrides, canonical URL, etc.) |

**Methods**:

```python
def to_dict(self) -> dict:
    """Return a JSON-serializable representation."""

def save_json(self, path: str | Path) -> None:
    """Save the result as JSON on disk."""
```

### 4. Domain Safety (`domains.py`)

**Purpose**: Implement blocklist-first domain policy and track allowed domains.

**Policy**: Only URLs matching `prohibited_domains` are blocked. All other domains are permitted and logged to an allowlist log for visibility.

**Key Functions**:

```python
def is_prohibited(url: str, prohibited_domains: list[str]) -> bool:
    """
    Return True when the URL matches any prohibited domain pattern.

    Supports patterns:
    - example.com (matches example.com and subdomains)
    - *.example.com (matches subdomains only)
    - http*://example.com (matches http/https)

    Uses browser_use.utils.match_url_with_domain_pattern for matching.
    """
```

```python
def extract_hostname(url: str) -> str | None:
    """Extract hostname from a URL (best-effort)."""
```

```python
def record_allowed_domain(url: str, allowlist_log_path: str | Path) -> str | None:
    """
    Append the hostname to an allowlist log file, if not already present.

    Logic:
    1. Extract hostname from URL
    2. Read existing allowlist log (if exists)
    3. If hostname already in log → Return hostname (no-op)
    4. If hostname not in log → Append to file and return hostname

    Returns:
        Hostname if recorded, None if extraction failed
    """
```

### 5. Q&A Bank (`qa_bank.py`)

**Purpose**: Store previously answered application questions so future runs can reuse answers without prompting the user again.

**Storage Format**: JSON file with entries array:

```json
{
  "entries": [
    {
      "question": "What is your desired salary?",
      "answer": "$120,000",
      "context": "optional context"
    }
  ]
}
```

**Question Normalization**: Questions are normalized for stable lookup:
- Lowercase
- Collapse whitespace
- Strip trailing punctuation (?, !, ., :)

**Key Methods**:

```python
class QABank:
    def __init__(self, path: str | Path) -> None:
        """Initialize Q&A bank with file path."""

    def load(self) -> None:
        """Load the Q&A bank from disk (no-op if missing)."""

    def save(self) -> None:
        """Persist the Q&A bank to disk deterministically."""

    def get_answer(self, question: str, _context: str | None = None) -> str | None:
        """Get a saved answer for a question (best-effort)."""

    def record_answer(
        self, question: str, answer: str, context: str | None = None
    ) -> None:
        """Record an answer and persist to disk."""
```

**Integration with Browser Use Agent**:

The Q&A bank is exposed as a custom tool (`resolve_answer`) in the Browser Use agent:

```python
@tools.action(description="Resolve an answer for an application question from the saved Q&A bank.")
def resolve_answer(question: str, context: str | None = None) -> str:
    """
    Resolve an answer for an application question.

    Flow:
    1. Check Q&A bank for existing answer
    2. If found → Return cached answer
    3. If not found:
       - Prompt user for answer
       - Validate answer (not blank, not "make it up", not "invent")
       - Save to Q&A bank
       - Return answer

    Returns:
        Answer string (from cache or user input)
    """
```

## API / Interface Documentation

### Public Entry Points

#### CLI Usage (via `src/__main__.py`)

**Single Job Mode**:

```bash
python -m src single "https://example.com/jobs/123"
```

This runs the full pipeline:
1. Extract job description
2. Evaluate fit score
3. Tailor resume and cover letter
4. Prompt for document approval
5. Execute browser automation
6. Update tracker

**Runner-Only Mode** (Component Mode):

```bash
python -m src apply "https://example.com/jobs/123" \
  --resume /path/to/resume.pdf \
  --cover-letter /path/to/cover.pdf \
  --profile profiles/profile.yaml
```

This runs only the browser automation step (no extraction, scoring, or tailoring).

#### Programmatic Usage

```python
from src.runner.service import run_single_job
from src.config.settings import Settings

# Load settings from environment
settings = Settings()

# Run application
result = await run_single_job("https://example.com/jobs/123", settings=settings)

# Check result
if result.success and result.status == RunStatus.SUBMITTED:
    print(f"Submitted! Proof: {result.proof_text}")
else:
    print(f"Failed: {result.errors}")
```

**Advanced Usage** (custom service):

```python
from src.runner.service import SingleJobApplicationService
from src.tracker.repository import TrackerRepository
from src.tracker.service import TrackerService
from src.extractor.service import JobExtractor
from src.scoring.service import FitScoringService
from src.scoring.profile import ProfileService
from src.config.settings import Settings

settings = Settings()

# Initialize dependencies
tracker_repository = TrackerRepository(settings.tracker_db_path)
await tracker_repository.initialize()

service = SingleJobApplicationService(
    settings=settings,
    tracker_repository=tracker_repository,
    tracker_service=TrackerService(tracker_repository),
    extractor=JobExtractor(),
    scoring_service=FitScoringService(),
    profile_service=ProfileService(),
    tailoring_service=None,  # Uses default
)

# Run application
result = await service.run("https://example.com/jobs/123")

# Cleanup
await tracker_repository.close()
```

### Configuration

All runner configuration is managed via environment variables (see `.env.example`).

#### Runner Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `PROHIBITED_DOMAINS` | list[str] | [] | Blocklist-first: only these domains are blocked |
| `ALLOWLIST_LOG_PATH` | Path | ./data/allowlist.log | Append-only log of encountered non-prohibited domains |
| `QA_BANK_PATH` | Path | ./data/qa_bank.json | Persistent Q&A bank for application questions |
| `RUNNER_HEADLESS` | bool | False | Run browser headless (not recommended for debugging) |
| `RUNNER_WINDOW_WIDTH` | int | 1280 | Browser window width |
| `RUNNER_WINDOW_HEIGHT` | int | 720 | Browser window height |
| `RUNNER_MAX_FAILURES` | int | 3 | Maximum retry attempts for failed steps |
| `RUNNER_MAX_ACTIONS_PER_STEP` | int | 4 | Max actions per agent step (form fill batching) |
| `RUNNER_STEP_TIMEOUT` | int | 120 | Timeout per step in seconds |
| `RUNNER_USE_VISION` | str | auto | Vision mode: auto, true, false |

#### Runner LLM Settings (Optional)

Runner inherits from `EXTRACTOR_LLM_*` by default. Override only if you want a different LLM for runner.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `RUNNER_LLM_PROVIDER` | str \| None | None | Provider: auto, openai, anthropic, browser_use |
| `RUNNER_LLM_BASE_URL` | str \| None | None | Base URL for OpenAI-compatible endpoints |
| `RUNNER_LLM_API_KEY` | str \| None | None | API key (overrides extractor key for runner only) |
| `RUNNER_LLM_MODEL` | str \| None | None | Model ID (e.g., gpt-4o, claude-sonnet-4-20250514) |
| `RUNNER_LLM_REASONING_EFFORT` | str \| None | None | Reasoning effort (none, minimal, low, medium, high, xhigh) |

#### Chrome Profile Settings (Optional)

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `USE_EXISTING_CHROME_PROFILE` | bool | False | Use an existing Chrome profile for sessions |
| `CHROME_USER_DATA_DIR` | Path \| None | None | Chrome user data directory path |
| `CHROME_PROFILE_DIR` | str | Default | Chrome profile directory name |
| `CHROME_PROFILE_MODE` | str | auto | Profile mode: copy (safe), direct (risky), auto |

**Profile Mode Behavior**:
- `copy`: Browser Use copies profile to temp dir (safest)
- `direct`: Use profile in place (riskier; close Chrome first)
- `auto`: Try copy first, fallback to direct on permission errors

## Dependencies

### Internal Dependencies

| Module | Usage |
|--------|-------|
| `src.tracker` | Duplicate detection, status updates, proof recording |
| `src.extractor` | Job description extraction, LLM configuration |
| `src.scoring` | Fit evaluation, skip/review decisions |
| `src.tailoring` | Resume and cover letter generation |
| `src.hitl` | HITL tools (confirm_submit, ask_yes_no, ask_free_text, ask_otp_code) |
| `src.config` | Settings and environment configuration |

### External Dependencies

| Package | Purpose |
|---------|---------|
| `browser_use` | Browser automation library (Browser, Agent, BrowserSession, Tools) |
| `pydantic` | Data models (BaseModel, Field) |
| `pathlib` | Path manipulation |
| `json` | Q&A bank persistence |
| `re` | Question normalization (whitespace, punctuation) |
| `logging` | Structured logging |
| `asyncio` | Async execution |

### Browser Use Integration

The runner module is built on top of the [Browser Use](https://github.com/browser-use/browser-use) library, which provides:

- **Browser**: Playwright-based browser controller with Chrome profile support
- **Agent**: LLM-powered browser agent for autonomous web navigation
- **Tools**: Custom tool registry for agent actions
- **BrowserSession**: Current page context for tool operations

**Browser Use Configuration**:

```python
from browser_use import Browser, Agent, Tools

# Create browser
browser = Browser(
    is_local=True,
    use_cloud=False,
    headless=False,
    window_size={"width": 1280, "height": 720},
    prohibited_domains=["example.com", "*.evil.com"],
    channel="chrome",  # Optional: Use Chrome profile
    user_data_dir="/path/to/Chrome/User Data",
    profile_directory="Default",
)

# Create agent
agent = Agent(
    task="Apply to this job: https://example.com/jobs/123",
    browser=browser,
    llm=llm,
    tools=tools,
    output_model_schema=ApplicationRunResult,
    available_file_paths=["/path/to/resume.pdf"],
    save_conversation_path="conversation.jsonl",
    sensitive_data={"first_name": "John", "email": "john@example.com"},
    max_failures=3,
    max_actions_per_step=4,
    step_timeout=120,
    use_vision="auto",
)

# Run agent
history = await agent.run()
result = history.structured_output  # ApplicationRunResult instance
```

## Error Handling and Retry Logic

### Error Categories

1. **Validation Errors** (Pre-execution):
   - Prohibited domain → Return `BLOCKED` immediately
   - Duplicate detection → Prompt user, possibly return `DUPLICATE_SKIPPED`
   - Missing LLM configuration → Return `FAILED` with error message

2. **Extraction Errors**:
   - Job extraction failed → Update tracker to `FAILED`, return `FAILED`

3. **Tailoring Errors**:
   - Document generation failed → Update tracker to `FAILED`, return `FAILED` with error message

4. **Browser Errors**:
   - Browser creation failed → Retry with profile snapshot, fallback to fresh profile
   - Permission denied on Chrome profile → Automatic fallback to copy mode

5. **Agent Execution Errors**:
   - Step timeout → Retry up to `max_failures` times
   - Action failure → Retry up to `max_failures` times
   - Max failures exceeded → Return `FAILED` with errors
   - Exception during `agent.run()` → Log exception, return `FAILED` with exception message

### Retry Logic

**Browser Use Agent Retries**:
- Configured via `max_failures` (default: 3)
- Retries on step timeout or action failure
- Does NOT retry on user cancellation or blocked domains

**Browser Profile Retries**:
- If permission denied on Chrome profile:
  1. First retry: Use profile snapshot copy
  2. Second retry: Fallback to fresh browser profile
  3. Log warnings for user visibility

**No Retries**:
- User cancellation (STOPPED_BEFORE_SUBMIT)
- Duplicate detection (DUPLICATE_SKIPPED)
- Fit scoring skip (SKIPPED)
- Prohibited domain (BLOCKED)

### Error Propagation

All errors are captured in `ApplicationRunResult.errors` and logged:

```python
result = ApplicationRunResult(
    success=False,
    status=RunStatus.FAILED,
    errors=["Job extraction failed", "HTTP 404: Not Found"],
    notes=["canonical_start_url=https://example.com/apply"],
)
```

**Tracker Integration**:
- On FAILED → Tracker status set to `ApplicationStatus.FAILED`
- On SUBMITTED → Tracker status set to `ApplicationStatus.SUBMITTED`
- On SKIPPED → Tracker status set to `ApplicationStatus.SKIPPED`

### Browser Cleanup

Browsers are always closed in a `finally` block to prevent resource leaks:

```python
browser = None
try:
    browser = create_browser(settings, prohibited_domains=prohibited_domains)
    # ... agent execution ...
finally:
    if browser is not None:
        with contextlib.suppress(Exception):
            await browser.close()
```

## Human-in-the-Loop (HITL) Integration

The runner enforces multiple HITL safety gates to ensure user oversight.

### HITL Gates

1. **Duplicate Override Prompt**:
   - Triggered when tracker indicates job already submitted
   - Prompt: "Tracker indicates this job was already submitted. Proceed anyway?"
   - Options: yes (continue with override), no (return DUPLICATE_SKIPPED)
   - Records override reason in tracker if yes

2. **Fit Skip Override Prompt**:
   - Triggered when fit scoring recommends "skip"
   - Prompt: "Fit scoring recommends SKIP. Proceed with application anyway? {reasoning}"
   - Options: yes (continue with override note), no (return SKIPPED)

3. **Fit Review Prompt**:
   - Triggered when fit scoring recommends "review"
   - Prompt: "Fit score recommends REVIEW. Proceed with application? {reasoning}"
   - Options: yes (continue), no (return SKIPPED)

4. **Document Approval Prompt**:
   - Triggered after tailoring completes
   - Prompt: "Documents are ready. Approve resume/cover letter for upload?"
   - Options: yes (continue to browser automation), no (return STOPPED_BEFORE_SUBMIT)

5. **Submit Confirmation Gate** (Most Critical):
   - Triggered when agent reaches final submit step
   - Prompt: "Type YES to submit this application"
   - Options: YES (submit), anything else (cancel)
   - Tool: `confirm_submit` from HITL tools
   - Behavior:
     - If required fields missing → Returns "blocked_missing_fields" (no prompt)
     - If user confirms → Clicks submit button, returns "submitted" or "confirmed"
     - If user cancels → Returns "cancelled"

### HITL Tools (from `src.hitl.tools`)

The runner uses these HITL tools via Browser Use custom tools:

```python
@tools.action(description="Ask the human a yes/no question.")
def ask_yes_no(question: str) -> str:
    """Returns 'yes' or 'no'."""

@tools.action(description="Ask the human for free text input.")
def ask_free_text(question: str) -> str:
    """Returns user's text input."""

@tools.action(description="Before final submit, require the human to type YES to confirm.")
async def confirm_submit(
    prompt: str,
    browser_session: BrowserSession,
    submit_button_index: int | None = None,
) -> str:
    """
    Returns:
    - "submitted": user confirmed and we clicked a submit button
    - "confirmed": user confirmed but we could not click automatically
    - "blocked_missing_fields": form has required field errors (no prompt shown)
    - "cancelled": user did not confirm
    """

@tools.action(description="Ask the human for an OTP/2FA code.")
def ask_otp_code(prompt: str) -> str:
    """Returns OTP code entered by user."""
```

### Submit Confirmation Flow

```
1. Agent reaches final submit step (all required fields filled)
   ↓
2. Agent calls confirm_submit(prompt="Type YES to submit", submit_button_index=42)
   ↓
3. Tool checks for required field errors:
   - If errors present → Return "blocked_missing_fields" (agent must fix fields)
   - If no errors → Continue to step 4
   ↓
4. Tool prompts user: "Type YES to submit this application >"
   - User types "YES" or "yes" → Continue to step 5
   - User types anything else → Return "cancelled" (agent stops with STOPPED_BEFORE_SUBMIT)
   ↓
5. Tool clicks submit button:
   - If submit_button_index provided → Click element by index
   - If index fails or not provided → Fallback to CSS selector (button[type="submit"])
   - If no button found → Return "confirmed" (agent must click manually)
   ↓
6. Tool waits 0.75s for page transition
   ↓
7. Tool checks for submission success:
   - If success text detected ("thank you for applying", etc.) → Return "submitted"
   - If required field errors detected → Return "blocked_missing_fields"
   - Otherwise → Return "confirmed"
   ↓
8. Agent interprets response:
   - "submitted" → Verify submission, extract proof, finish with SUBMITTED
   - "confirmed" → Agent must click submit button manually
   - "blocked_missing_fields" → Agent must fix missing fields, call confirm_submit again
   - "cancelled" → Finish with STOPPED_BEFORE_SUBMIT
```

## Testing

### Unit Tests

Location: `/Users/shalom/Developer/Job-Easy/tests/unit/autonomous/test_runner.py`

Tests for `BatchRunner` (autonomous mode):
- Sequential job processing
- Error handling and continuation
- Dry run mode (tailoring only, no browser automation)
- Progress tracking and status counts
- Graceful shutdown on cancellation

### Integration Tests

Location: `/Users/shalom/Developer/Job-Easy/tests/integration/runner/test_runner_integration.py`

End-to-end tests with real browser automation (not included in this documentation; see file for details).

### Manual Testing

See `/Users/shalom/Developer/Job-Easy/docs/runner-manual-test.md` for manual test checklist:

**Test 1: Job posting → "Apply" → multi-step flow**
- End-to-end mode: `python -m src single "<JOB_URL>"`
- Runner-only mode: `python -m src apply "<JOB_URL>" --resume resume.pdf`

**Test 2: Direct application form (single page)**
- Same commands as Test 1, but with direct application form URL

**Safety checks**:
- Confirm no submission without explicit "YES"
- Confirm CAPTCHA/2FA prompts request manual help
- Confirm prohibited domains are blocked
- Confirm allowed domains are logged to allowlist

## Artifacts and Output

### Artifact Structure

All runner artifacts are saved under `artifacts/runs/<fingerprint>/`:

```
artifacts/runs/<fingerprint>/
├── jd.json                      # Job description (from extractor)
├── resume.pdf                   # Tailored resume (from tailoring)
├── cover_letter.pdf             # Tailored cover letter (from tailoring)
├── conversation.jsonl           # Browser Use conversation log
└── application_result.json      # ApplicationRunResult (structured output)
```

### Conversation Log (conversation.jsonl)

JSON Lines format with one entry per agent step:

```jsonl
{"role": "system", "content": "You are applying to a job...", "timestamp": "2026-01-21T12:00:00Z"}
{"role": "user", "content": "Navigate to https://example.com/jobs/123", "timestamp": "2026-01-21T12:00:01Z"}
{"role": "assistant", "content": "Clicked Apply button", "actions": [...], "timestamp": "2026-01-21T12:00:05Z"}
```

### Application Result (application_result.json)

Structured JSON representation of `ApplicationRunResult`:

```json
{
  "success": true,
  "status": "submitted",
  "final_url": "https://example.com/application/confirmation",
  "visited_urls": [
    "https://example.com/jobs/123",
    "https://example.com/apply",
    "https://example.com/application/step1",
    "https://example.com/application/step2",
    "https://example.com/application/confirmation"
  ],
  "steps": [
    {
      "name": "Filled personal information",
      "url": "https://example.com/application/step1",
      "notes": ["first_name", "last_name", "email", "phone"]
    },
    {
      "name": "Uploaded resume",
      "url": "https://example.com/application/step2",
      "notes": ["resume.pdf"]
    }
  ],
  "proof_text": "Thank you for applying! Your application has been submitted.",
  "proof_screenshot_path": null,
  "errors": [],
  "notes": [
    "canonical_start_url=https://example.com/apply"
  ]
}
```

### Tracker Integration

The runner updates the tracker database with proof and artifact paths:

```python
await tracker_repository.update_proof(
    fingerprint,
    proof_text=result.proof_text,
    screenshot_path=result.proof_screenshot_path,
)

await tracker_repository.update_artifacts(
    fingerprint,
    resume_artifact_path=resume_path,
    cover_letter_artifact_path=cover_letter_path,
)

await tracker_service.update_status(
    fingerprint,
    ApplicationStatus.SUBMITTED,
)
```

## Best Practices

### 1. Use Prohibited Domains for Safety

Always configure `PROHIBITED_DOMAINS` to prevent accidental navigation to dangerous sites:

```bash
# .env
PROHIBITED_DOMAINS=["example.com", "*.phishing-site.com", "http*://malware.com"]
```

### 2. Review Allowlist Log Regularly

Check `ALLOWLIST_LOG_PATH` (default: `./data/allowlist.log`) to see all domains visited:

```bash
cat data/allowlist.log
```

This helps identify unexpected third-party domains or trackers.

### 3. Use Q&A Bank for Common Questions

Build up the Q&A bank (`QA_BANK_PATH`, default: `./data/qa_bank.json`) over time:

```json
{
  "entries": [
    {"question": "What is your desired salary?", "answer": "$120,000"},
    {"question": "Why do you want to work here?", "answer": "I am passionate about..."},
    {"question": "Are you authorized to work in the US?", "answer": "Yes"}
  ]
}
```

Future applications will reuse these answers without prompting.

### 4. Use Chrome Profile for Logged-In Sessions

Configure `USE_EXISTING_CHROME_PROFILE=true` to reuse logged-in sessions (LinkedIn, Indeed, etc.):

```bash
# .env
USE_EXISTING_CHROME_PROFILE=true
CHROME_USER_DATA_DIR=/Users/shalom/Library/Application Support/Google/Chrome
CHROME_PROFILE_DIR=Default
CHROME_PROFILE_MODE=auto
```

**Warning**: Always use `CHROME_PROFILE_MODE=copy` or `auto` to avoid profile corruption.

### 5. Monitor Conversation Logs

Review `conversation.jsonl` to debug agent behavior:

```bash
cat artifacts/runs/<fingerprint>/conversation.jsonl | jq
```

Look for:
- Actions taken (clicks, inputs, uploads)
- Errors or warnings
- Tool calls (resolve_answer, confirm_submit)

### 6. Tune Agent Parameters

Adjust runner parameters for different job sites:

| Site Type | Recommended Settings |
|-----------|---------------------|
| Simple forms | `RUNNER_MAX_ACTIONS_PER_STEP=4`, `RUNNER_STEP_TIMEOUT=60` |
| Complex multi-step | `RUNNER_MAX_ACTIONS_PER_STEP=6`, `RUNNER_STEP_TIMEOUT=180` |
| Slow-loading pages | `RUNNER_STEP_TIMEOUT=240` |

### 7. Use Dry Run for Testing

In autonomous mode, use `--dry-run` to test tailoring without browser automation:

```bash
python -m src autonomous leads.txt --dry-run
```

This generates resumes and cover letters but skips the runner entirely.

## Troubleshooting

### Common Issues

#### Issue: "No LLM configured for runner"

**Cause**: Neither `RUNNER_LLM_*` nor `EXTRACTOR_LLM_*` settings are configured.

**Solution**:
```bash
# .env
EXTRACTOR_LLM_PROVIDER=openai
EXTRACTOR_LLM_API_KEY=sk-...
```

#### Issue: "Permission denied" on Chrome profile

**Cause**: Chrome profile contains unreadable files (often root-owned).

**Solution**:
1. Use `CHROME_PROFILE_MODE=auto` (recommended)
2. Or choose a different profile: `CHROME_PROFILE_DIR=Profile 1`
3. Or fix file permissions: `sudo chown -R $USER ~/Library/Application\ Support/Google/Chrome/Default`

#### Issue: "blocked_missing_fields" returned repeatedly

**Cause**: Agent is calling `confirm_submit` before all required fields are filled.

**Solution**:
- Check conversation.jsonl for missing fields
- Manually fill fields in browser (agent will resume)
- Adjust agent prompt to emphasize required field validation

#### Issue: Agent never reaches submit step

**Cause**: Multi-step flow navigation failed or infinite loop.

**Solution**:
- Check conversation.jsonl for repeated actions
- Increase `RUNNER_STEP_TIMEOUT` if pages are slow-loading
- Increase `RUNNER_MAX_ACTIONS_PER_STEP` for complex forms
- Manually guide agent by clicking Next/Continue buttons

#### Issue: Cover letter uploaded to resume field

**Cause**: Agent misidentified upload fields.

**Solution**:
- Check conversation.jsonl for field labels
- Ensure prompt emphasizes: "Only upload cover letter if there is a dedicated Cover Letter upload field"
- Manually correct upload and retry

#### Issue: Domain blocked but should be allowed

**Cause**: Overly broad prohibited domain pattern.

**Solution**:
- Review `PROHIBITED_DOMAINS` patterns
- Use specific patterns: `malware.example.com` instead of `*.example.com`
- Remove or narrow blocklist entry

## Future Enhancements

Potential improvements for the runner module:

1. **Screenshot Proof Capture**: Automatically take screenshots after successful submission
2. **Resume Upload Verification**: Verify resume parsing/upload by reading back displayed text
3. **Multi-Language Support**: Support application forms in non-English languages
4. **Form Field Detection**: Improve required field detection via aria-required, HTML5 validation
5. **CAPTCHA Detection**: Detect CAPTCHA/2FA earlier and pause agent proactively
6. **Rate Limiting**: Add configurable delays between actions to avoid bot detection
7. **Headless Mode Improvements**: Better headless support for production environments
8. **Advanced Q&A Bank**: Support fuzzy matching for similar questions
9. **Profile-Specific Q&A Banks**: Separate Q&A banks per profile/role
10. **Telemetry**: Track success rates, failure reasons, and performance metrics

## See Also

- [Autonomous Module Documentation](autonomous.md) - Batch processing with runner
- [Extractor Module Documentation](extractor.md) - Job description extraction
- [Config Module Documentation](config.md) - Settings and environment configuration
- [Manual Test Checklist](runner-manual-test.md) - Manual testing procedures
- [Browser Use Documentation](https://github.com/browser-use/browser-use) - Browser automation library

## Conclusion

The runner module is the core browser automation engine for Job-Easy, orchestrating intelligent form filling, file uploads, and submission with robust safety controls. It integrates seamlessly with the tracker, extractor, scoring, tailoring, and HITL modules to provide a complete end-to-end application experience.

Key features:
- AI-powered browser automation via Browser Use
- Multiple HITL safety gates (duplicate detection, fit scoring, document approval, submit confirmation)
- Persistent Q&A bank for common screening questions
- Domain safety controls (blocklist + allowlist logging)
- Structured output tracking (proof, errors, visited URLs)
- Chrome profile reuse for logged-in sessions
- Comprehensive error handling and retry logic

For production use, always configure prohibited domains, review allowlist logs, and monitor conversation artifacts for debugging and compliance.

