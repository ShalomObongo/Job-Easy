# Autonomous Module Documentation

## Overview

The **autonomous** module provides batch job application processing capabilities for the Job-Easy system. It enables users to process multiple job applications from a list of URLs (leads file), with automatic deduplication, fit scoring, ranking, and sequential execution. The module orchestrates the entire pipeline from lead ingestion to batch submission, while maintaining human oversight through confirmation prompts.

### Purpose

- **Batch Processing**: Process multiple job applications from a single leads file
- **Intelligent Filtering**: Automatically filter duplicates, low-scoring jobs, and previously submitted applications
- **Ranking**: Sort job opportunities by fit score to prioritize the best matches
- **Dry Run Mode**: Generate tailored documents without executing browser automation
- **Progress Tracking**: Monitor batch execution with real-time progress updates
- **Graceful Interruption**: Handle SIGINT/SIGTERM with proper cleanup and status reporting

## Architecture

### Module Structure

```
src/autonomous/
├── __init__.py          # Public API exports
├── models.py            # Data models and enums
├── leads.py             # Lead file parsing
├── queue.py             # Queue building and ranking
├── runner.py            # Batch execution engine
└── service.py           # High-level orchestration
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     AutonomousService                            │
│  (High-level orchestration and workflow coordination)           │
└────────────┬─────────────────────────────────────┬──────────────┘
             │                                     │
             ▼                                     ▼
┌────────────────────────┐            ┌──────────────────────────┐
│   LeadFileParser       │            │    QueueManager          │
│                        │            │                          │
│ - Parse leads.txt      │───────────▶│ - Duplicate detection    │
│ - Validate URLs        │            │ - Job extraction         │
│ - Line-by-line errors  │            │ - Fit scoring            │
└────────────────────────┘            │ - Filtering & ranking    │
                                      │ - Statistics tracking    │
                                      └────────────┬─────────────┘
                                                   │
                                                   ▼
                                      ┌──────────────────────────┐
                                      │    BatchRunner           │
                                      │                          │
                                      │ - Sequential execution   │
                                      │ - Progress callbacks     │
                                      │ - Signal handling        │
                                      │ - Dry-run support        │
                                      │ - Error aggregation      │
                                      └──────────────────────────┘
```

### Data Flow

```
1. Leads File (leads.txt)
        ↓
2. LeadFileParser → List[LeadItem]
        ↓
3. QueueManager.build_queue()
        ├─→ TrackerService (check duplicates)
        ├─→ JobExtractor (extract job descriptions)
        ├─→ FitScoringService (score jobs)
        └─→ Filter & Rank → List[QueuedJob]
        ↓
4. User Confirmation (optional)
        ↓
5. BatchRunner.run()
        ├─→ For each QueuedJob:
        │   ├─→ Dry Run: TailoringService
        │   └─→ Live Run: SingleJobApplicationService
        └─→ Aggregate Results → BatchResult
```

## Key Components

### 1. Models (`models.py`)

#### `LeadItem`
Represents a single line from a leads file.

**Attributes:**
- `url: str` - Job posting URL
- `line_number: int` - Line number in the leads file (1-indexed)
- `valid: bool` - Whether the URL passed validation
- `error: str | None` - Error message if validation failed

**Validation:**
- `line_number` must be >= 1
- If `valid=True`, `error` must be `None`
- If `valid=False`, `error` is required

**Example:**
```python
# Valid lead
LeadItem(
    url="https://example.com/jobs/123",
    line_number=1,
    valid=True
)

# Invalid lead
LeadItem(
    url="not-a-url",
    line_number=2,
    valid=False,
    error="Invalid URL: must start with http:// or https://"
)
```

#### `QueueStatus`
Enum representing the processing status of a queued job.

**Values:**
- `PENDING` - Not yet started
- `PROCESSING` - Currently being processed
- `COMPLETED` - Successfully completed
- `FAILED` - Processing failed
- `SKIPPED` - Skipped (e.g., user skipped, duplicate skipped)

#### `QueuedJob`
Represents a job ready for batch processing.

**Attributes:**
- `url: str` - Application URL (may be `apply_url` if different from `job_url`)
- `fingerprint: str` - Unique identifier for duplicate detection
- `job_description: JobDescription` - Extracted job data
- `fit_result: FitResult` - Fit scoring evaluation
- `status: QueueStatus` - Current processing status (default: `PENDING`)

#### `JobResult`
Result of processing a single queued job.

**Attributes:**
- `url: str` - Job URL
- `fingerprint: str` - Job fingerprint
- `status: QueueStatus` - Final status
- `error: str | None` - Error message if failed
- `duration_seconds: float` - Processing time (must be >= 0)

#### `BatchResult`
Summary of an entire batch run.

**Attributes:**
- `processed: int` - Total jobs processed
- `submitted: int` - Successfully submitted applications
- `skipped: int` - Jobs skipped during execution
- `failed: int` - Jobs that failed
- `duration_seconds: float` - Total batch execution time
- `job_results: list[JobResult]` - Individual job results

**Validation:**
- All counts must be >= 0
- `duration_seconds` must be >= 0

### 2. Lead File Parser (`leads.py`)

#### `LeadFileParser`
Parses a leads file containing job URLs (one per line).

**Format:**
- One URL per line
- Blank lines are ignored
- Lines starting with `#` are treated as comments and ignored
- Invalid URLs are returned with `valid=False` and an error message

**Example leads file:**
```
# High priority jobs
https://example.com/jobs/senior-engineer
https://example.com/jobs/staff-engineer

# Medium priority
https://careers.company.com/position/123

# Invalid URL (will be marked as invalid)
not-a-valid-url
```

**API:**

```python
def parse(self, file_path: Path) -> list[LeadItem]:
    """Parse a leads file into LeadItem entries.

    Args:
        file_path: Path to the leads file

    Returns:
        List of LeadItem objects (both valid and invalid)
    """
```

**URL Validation:**
- Must start with `http://` or `https://`
- Must have a valid hostname

**Usage Example:**
```python
parser = LeadFileParser()
leads = parser.parse(Path("leads.txt"))

valid_leads = [lead for lead in leads if lead.valid]
invalid_leads = [lead for lead in leads if not lead.valid]

print(f"Valid: {len(valid_leads)}, Invalid: {len(invalid_leads)}")
for lead in invalid_leads:
    print(f"Line {lead.line_number}: {lead.error}")
```

### 3. Queue Manager (`queue.py`)

#### `QueueStats`
Immutable statistics from queue building.

**Attributes:**
- `total: int` - Total leads in file
- `valid: int` - Valid URLs
- `duplicates: int` - Already submitted duplicates filtered out
- `below_threshold: int` - Jobs filtered by min_score
- `queued: int` - Final queue size

#### `QueueManager`
Builds and ranks the job application queue.

**API:**

```python
async def build_queue(
    self,
    leads: list[LeadItem],
    *,
    tracker_service: Any,
    extractor: Any,
    scorer: Any,
    profile: Any,
    min_score: float | None,
    include_skips: bool,
) -> list[QueuedJob]:
    """Build a ranked queue from leads.

    Args:
        leads: Parsed lead items
        tracker_service: TrackerService for duplicate detection
        extractor: JobExtractor for extracting job descriptions
        scorer: FitScoringService for evaluating fit
        profile: User profile for scoring
        min_score: Minimum total_score threshold (0.0-1.0), None to disable
        include_skips: Whether to include jobs with recommendation="skip"

    Returns:
        List of QueuedJob, sorted by fit score (highest first)
    """

def get_stats(self) -> QueueStats:
    """Get statistics from the last build_queue call.

    Returns:
        QueueStats object

    Raises:
        RuntimeError: If build_queue hasn't been called yet
    """
```

**Processing Logic:**

1. **Filter Valid Leads**: Only process leads where `valid=True`

2. **Duplicate Detection**:
   - Call `tracker_service.check_duplicate()` for each URL
   - Skip jobs with status `ApplicationStatus.SUBMITTED`
   - Include jobs with other statuses (FAILED, SKIPPED, etc.)

3. **Job Extraction**:
   - Call `extractor.extract(url)` for each lead
   - Cache results to avoid re-extraction if same URL appears multiple times
   - Skip leads that fail extraction (return `None`)

4. **Fit Scoring**:
   - Call `scorer.evaluate(job, profile)` for each extracted job
   - Cache results with extraction results
   - Handles both sync and async scorers

5. **Filtering**:
   - **Skip Recommendation**: If `include_skips=False`, exclude jobs with `recommendation="skip"`
   - **Min Score**: If `min_score` is set, exclude jobs with `total_score < min_score`
   - Extracts score from `fit_result.fit_score.total_score` or `fit_result.total_score`

6. **Ranking**:
   - Sort by `fit_result.fit_score.total_score` in descending order (highest first)

7. **Fingerprinting**:
   - Use existing fingerprint from duplicate record if available
   - Otherwise compute fingerprint from URL and job_id

**Usage Example:**
```python
manager = QueueManager()

queue = await manager.build_queue(
    leads=parsed_leads,
    tracker_service=tracker_service,
    extractor=job_extractor,
    scorer=fit_scorer,
    profile=user_profile,
    min_score=0.6,
    include_skips=False
)

stats = manager.get_stats()
print(f"Queued {stats.queued} out of {stats.valid} valid leads")
print(f"Filtered: {stats.duplicates} duplicates, {stats.below_threshold} below threshold")

# Queue is already sorted by score
for job in queue[:5]:
    print(f"{job.url} - Score: {job.fit_result.fit_score.total_score}")
```

### 4. Batch Runner (`runner.py`)

#### `BatchProgressEvent`
Immutable event emitted during batch processing.

**Attributes:**
- `index: int` - Current job index (1-based)
- `total: int` - Total jobs in queue
- `url: str` - Current job URL
- `status: QueueStatus` - Current job status
- `processed: int` - Jobs processed so far
- `submitted: int` - Jobs submitted so far
- `skipped: int` - Jobs skipped so far
- `failed: int` - Jobs failed so far

#### `BatchRunner`
Processes queued jobs sequentially with progress tracking.

**Constructor:**
```python
def __init__(
    self,
    *,
    single_job_service: Any,
    tailoring_service: Any | None,
    profile: Any,
    output_dir: Path,
    progress_callback: Callable[[BatchProgressEvent], None] | None = None,
) -> None:
    """Initialize the batch runner.

    Args:
        single_job_service: SingleJobApplicationService for live runs
        tailoring_service: TailoringService for dry runs (optional)
        profile: User profile for tailoring
        output_dir: Base output directory
        progress_callback: Optional callback for progress events
    """
```

**API:**

```python
async def run(
    self,
    queue: list[QueuedJob],
    *,
    dry_run: bool
) -> BatchResult:
    """Execute the batch job queue.

    Args:
        queue: List of QueuedJob to process
        dry_run: If True, only generate tailored documents (no browser automation)

    Returns:
        BatchResult with statistics and individual job results

    Notes:
        - Processes jobs sequentially (not in parallel)
        - Handles SIGINT/SIGTERM gracefully
        - Emits progress events after each job
        - In dry-run mode, creates tailored documents without browser automation
    """
```

**Processing Behavior:**

1. **Sequential Execution**: Jobs are processed one at a time (not parallel)

2. **Progress Updates**: Emits `BatchProgressEvent` before and after each job

3. **Dry Run Mode** (`dry_run=True`):
   - Creates run directory: `output_dir/runs/{fingerprint}`
   - Calls `tailoring_service.tailor(profile, job_description)`
   - Marks as `COMPLETED` on success
   - No browser automation

4. **Live Mode** (`dry_run=False`):
   - Calls `single_job_service.run(url)`
   - Maps `RunStatus` to `QueueStatus`:
     - `SUBMITTED` → `COMPLETED`
     - `SKIPPED`, `DUPLICATE_SKIPPED`, `STOPPED_BEFORE_SUBMIT` → `SKIPPED`
     - Others → `FAILED`
   - Captures first error message from `run_result.errors`

5. **Signal Handling**:
   - Registers handlers for `SIGINT` and `SIGTERM`
   - Sets stop event and cancels current task
   - Marks interrupted job as `FAILED` with error "interrupted"
   - Cleans up signal handlers in finally block

6. **Error Handling**:
   - `asyncio.CancelledError`: Mark as failed, break loop
   - `Exception`: Log exception, mark as failed, continue to next job
   - All errors are captured in `JobResult.error`

7. **Timing**: Tracks duration for each job and the entire batch

**Usage Example:**
```python
def on_progress(event: BatchProgressEvent):
    print(f"[{event.index}/{event.total}] {event.url} - {event.status}")
    print(f"  Submitted: {event.submitted}, Skipped: {event.skipped}, Failed: {event.failed}")

runner = BatchRunner(
    single_job_service=job_service,
    tailoring_service=tailoring_service,
    profile=user_profile,
    output_dir=Path("./artifacts"),
    progress_callback=on_progress
)

result = await runner.run(queue, dry_run=False)

print(f"Batch completed in {result.duration_seconds:.2f}s")
print(f"Processed: {result.processed}, Submitted: {result.submitted}")
print(f"Failed: {result.failed}, Skipped: {result.skipped}")
```

### 5. Autonomous Service (`service.py`)

#### `AutonomousService`
High-level orchestration service that coordinates the entire batch processing workflow.

**Constructor:**
```python
def __init__(
    self,
    *,
    settings: Any,
    tracker_service: Any,
    extractor: Any,
    scoring_service: Any,
    profile_service: Any,
    single_job_service: Any,
    tailoring_service: Any | None = None,
    confirm_callback: ConfirmCallback | None = None,
    progress_callback: ProgressCallback | None = None,
) -> None:
    """Initialize the autonomous service.

    Args:
        settings: Application settings (must have output_dir, max_applications_per_day)
        tracker_service: TrackerService instance
        extractor: JobExtractor instance
        scoring_service: FitScoringService instance
        profile_service: ProfileService instance
        single_job_service: SingleJobApplicationService instance
        tailoring_service: Optional TailoringService for dry runs
        confirm_callback: Optional async/sync callback for user confirmation
        progress_callback: Optional callback for batch progress events
    """
```

**API:**

```python
async def run(
    self,
    *,
    leads_file: Path,
    dry_run: bool = False,
    min_score: float | None = None,
    include_skips: bool = False,
    assume_yes: bool = False,
) -> BatchResult:
    """Execute the autonomous batch processing workflow.

    Args:
        leads_file: Path to leads file (one URL per line)
        dry_run: If True, only generate documents (no browser automation)
        min_score: Minimum fit score threshold (0.0-1.0)
        include_skips: Include jobs even if scorer recommends "skip"
        assume_yes: Skip confirmation prompt

    Returns:
        BatchResult with execution statistics

    Workflow:
        1. Parse leads file
        2. Load user profile
        3. Build and rank queue
        4. Apply max_applications_per_day limit
        5. Prompt for confirmation (unless assume_yes=True)
        6. Execute batch via BatchRunner
    """
```

**Workflow Details:**

1. **Lead Parsing**: Uses `LeadFileParser` to parse the leads file

2. **Profile Loading**: Loads user profile via `profile_service.load_profile()`

3. **Queue Building**:
   - Calls `QueueManager.build_queue()` with all dependencies
   - Applies `min_score` and `include_skips` filters

4. **Daily Limit**:
   - If `settings.max_applications_per_day` is set, truncates queue to that limit
   - Queue is already sorted by score, so highest-scoring jobs are kept

5. **Empty Queue Handling**:
   - Returns empty `BatchResult` immediately if queue is empty
   - No confirmation prompt shown

6. **User Confirmation** (unless `assume_yes=True`):
   - Formats summary with queue stats and leads file path
   - Uses `confirm_callback` if provided (supports sync/async)
   - Falls back to `hitl.prompt_yes_no()` if no callback
   - Returns empty `BatchResult` if user declines

7. **Batch Execution**:
   - Creates `BatchRunner` with all dependencies
   - Passes `progress_callback` if provided
   - Returns `BatchResult` from runner

**Confirmation Summary Format:**
```
Leads: total=50 valid=48 duplicates_skipped=5 below_threshold=10
Queue size: 33
Leads file: /path/to/leads.txt
Proceed with batch processing? (This will still prompt before any submit)
```

**Usage Example:**
```python
service = AutonomousService(
    settings=settings,
    tracker_service=tracker_service,
    extractor=job_extractor,
    scoring_service=fit_scorer,
    profile_service=profile_service,
    single_job_service=job_service,
    tailoring_service=tailoring_service,
    confirm_callback=lambda msg: input(f"{msg} [y/N]: ").lower() == 'y',
    progress_callback=lambda e: print(f"[{e.index}/{e.total}] {e.status}")
)

result = await service.run(
    leads_file=Path("leads.txt"),
    dry_run=False,
    min_score=0.6,
    include_skips=False,
    assume_yes=False
)
```

#### `run_autonomous()` Function
Convenience entry point for CLI usage that constructs all dependencies.

**API:**
```python
async def run_autonomous(
    leads_file: Path,
    *,
    settings: Any,
    dry_run: bool = False,
    min_score: float | None = None,
    include_skips: bool = False,
    assume_yes: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> BatchResult:
    """Convenience entry point for CLI usage.

    Creates all required services and executes autonomous batch processing.
    Handles tracker repository initialization and cleanup.

    Args:
        leads_file: Path to leads file
        settings: Application settings
        dry_run: Only generate documents, no browser automation
        min_score: Minimum fit score threshold
        include_skips: Include jobs with "skip" recommendation
        assume_yes: Skip confirmation prompt
        progress_callback: Optional progress callback

    Returns:
        BatchResult
    """
```

**Created Services:**
- `TrackerRepository` (initialized and closed automatically)
- `TrackerService`
- `JobExtractor`
- `FitScoringService`
- `ProfileService`
- `SingleJobApplicationService` (with `SourceMode.AUTONOMOUS`)
- `AutonomousService`

## Dependencies

### Internal Module Dependencies

#### Extractor Module (`src.extractor`)
- **Purpose**: Extract structured job data from URLs
- **Usage**: `JobExtractor.extract(url)` returns `JobDescription`
- **Models**: `JobDescription`

#### Scoring Module (`src.scoring`)
- **Purpose**: Evaluate job fit against user profile
- **Usage**: `FitScoringService.evaluate(job, profile)` returns `FitResult`
- **Models**: `FitResult`, `FitScore`, `ConstraintResult`
- **Services**: `ProfileService.load_profile()`

#### Tracker Module (`src.tracker`)
- **Purpose**: Track applications and detect duplicates
- **Usage**:
  - `TrackerService.check_duplicate()` returns `TrackerRecord | None`
  - Fingerprinting via `compute_fingerprint()`, `extract_job_id()`
- **Models**: `TrackerRecord`, `ApplicationStatus`, `SourceMode`
- **Repository**: `TrackerRepository` for database access

#### Runner Module (`src.runner`)
- **Purpose**: Execute single job applications with browser automation
- **Usage**: `SingleJobApplicationService.run(url)` returns `ApplicationRunResult`
- **Models**: `RunStatus`, `ApplicationRunResult`

#### Tailoring Module (`src.tailoring`)
- **Purpose**: Generate tailored resumes and cover letters
- **Usage**: `TailoringService.tailor(profile, job)` for dry-run mode
- **Config**: `TailoringConfig` for output directory

#### HITL Module (`src.hitl`)
- **Purpose**: Human-in-the-loop interactions
- **Usage**: `hitl.prompt_yes_no(message)` for confirmation prompts

#### Config Module (`src.config`)
- **Purpose**: Application settings
- **Usage**: Settings object with `output_dir`, `max_applications_per_day`, `tracker_db_path`

### External Dependencies

- **asyncio**: Async I/O and task management
- **signal**: SIGINT/SIGTERM handling for graceful shutdown
- **pathlib**: Path manipulation
- **urllib.parse**: URL validation and parsing
- **dataclasses**: Data model definitions
- **enum**: Status enumerations
- **logging**: Error and debug logging
- **time**: Duration tracking

## Integration with Other Modules

### Workflow Integration

```
CLI (src.__main__.py)
    ↓
run_autonomous() or AutonomousService.run()
    ↓
┌─────────────────────────────────────────────┐
│ Autonomous Module Orchestration             │
├─────────────────────────────────────────────┤
│                                             │
│  1. Parse Leads                             │
│     └─→ LeadFileParser                      │
│                                             │
│  2. Build Queue                             │
│     ├─→ Tracker: check_duplicate()          │
│     ├─→ Extractor: extract()                │
│     ├─→ Scoring: evaluate()                 │
│     └─→ QueueManager: filter & rank         │
│                                             │
│  3. User Confirmation                       │
│     └─→ HITL: prompt_yes_no()               │
│                                             │
│  4. Execute Batch                           │
│     ├─→ Dry Run: Tailoring.tailor()         │
│     └─→ Live: Runner.run()                  │
│         ├─→ Extractor (again if needed)     │
│         ├─→ Scoring (again if needed)       │
│         ├─→ Tailoring (generate docs)       │
│         ├─→ Browser automation              │
│         └─→ Tracker: create/update records  │
└─────────────────────────────────────────────┘
```

### Key Integration Points

#### 1. CLI Integration (`src.__main__.py`)

The autonomous mode is invoked via the CLI:

```bash
python -m src autonomous leads.txt \
    --dry-run \
    --min-score 0.6 \
    --include-skips \
    --yes
```

CLI calls `run_autonomous()` which handles all service initialization.

#### 2. Tracker Integration

- **Duplicate Detection**: Before queue building
- **Record Creation**: During SingleJobApplicationService execution
- **Status Updates**: After each job completion
- **Fingerprinting**: Consistent fingerprint calculation for deduplication

#### 3. Scoring Integration

- **Queue Building**: Score each job for filtering and ranking
- **Single Job Execution**: May re-score if needed by SingleJobApplicationService

#### 4. Tailoring Integration

- **Dry Run Mode**: Explicitly calls tailoring service
- **Live Mode**: SingleJobApplicationService handles tailoring internally

#### 5. Runner Integration

- **Live Execution**: Delegates to SingleJobApplicationService for each queued job
- **Source Mode**: Passes `SourceMode.AUTONOMOUS` to distinguish from single-job mode

## Usage Examples

### Basic Usage (CLI)

```bash
# Simple autonomous run
python -m src autonomous leads.txt

# Dry run (no browser automation)
python -m src autonomous leads.txt --dry-run

# Filter by minimum score
python -m src autonomous leads.txt --min-score 0.7

# Include jobs even if scorer recommends "skip"
python -m src autonomous leads.txt --include-skips

# Skip confirmation prompt
python -m src autonomous leads.txt --yes
```

### Programmatic Usage

#### Example 1: Basic Programmatic Usage

```python
from pathlib import Path
from src.autonomous.service import run_autonomous
from src.config.settings import Settings

settings = Settings()

result = await run_autonomous(
    leads_file=Path("leads.txt"),
    settings=settings,
    dry_run=False,
    min_score=0.6,
    include_skips=False,
    assume_yes=False
)

print(f"Processed: {result.processed}")
print(f"Submitted: {result.submitted}")
print(f"Failed: {result.failed}")
```

#### Example 2: Custom Service with Callbacks

```python
from pathlib import Path
from src.autonomous.service import AutonomousService
from src.autonomous.runner import BatchProgressEvent

def on_progress(event: BatchProgressEvent):
    percent = (event.index / event.total) * 100
    print(f"[{percent:.1f}%] Processing job {event.index}/{event.total}")
    print(f"  URL: {event.url}")
    print(f"  Status: {event.status.value}")
    print(f"  Results: {event.submitted} submitted, {event.failed} failed")

async def confirm(message: str) -> bool:
    print(message)
    return input("Continue? [y/N]: ").lower() == 'y'

# Initialize all services (tracker, extractor, scoring, etc.)
# ... service initialization code ...

service = AutonomousService(
    settings=settings,
    tracker_service=tracker_service,
    extractor=extractor,
    scoring_service=scoring_service,
    profile_service=profile_service,
    single_job_service=single_job_service,
    tailoring_service=tailoring_service,
    confirm_callback=confirm,
    progress_callback=on_progress
)

result = await service.run(
    leads_file=Path("leads.txt"),
    dry_run=False,
    min_score=0.7,
    include_skips=False,
    assume_yes=False
)
```

#### Example 3: Queue Building Only

```python
from src.autonomous.leads import LeadFileParser
from src.autonomous.queue import QueueManager

# Parse leads
parser = LeadFileParser()
leads = parser.parse(Path("leads.txt"))

print(f"Parsed {len(leads)} leads")
valid = [l for l in leads if l.valid]
invalid = [l for l in leads if not l.valid]
print(f"  Valid: {len(valid)}, Invalid: {len(invalid)}")

# Build queue
manager = QueueManager()
queue = await manager.build_queue(
    leads=leads,
    tracker_service=tracker_service,
    extractor=extractor,
    scorer=scoring_service,
    profile=profile,
    min_score=0.6,
    include_skips=False
)

# Get statistics
stats = manager.get_stats()
print(f"\nQueue Statistics:")
print(f"  Total leads: {stats.total}")
print(f"  Valid URLs: {stats.valid}")
print(f"  Duplicates filtered: {stats.duplicates}")
print(f"  Below threshold: {stats.below_threshold}")
print(f"  Final queue size: {stats.queued}")

# Inspect top jobs
print(f"\nTop 5 jobs:")
for i, job in enumerate(queue[:5], 1):
    score = job.fit_result.fit_score.total_score
    print(f"  {i}. {job.job_description.role_title} at {job.job_description.company}")
    print(f"     Score: {score:.2f}")
    print(f"     URL: {job.url}")
```

#### Example 4: Dry Run with Custom Output

```python
from pathlib import Path
from src.autonomous.service import AutonomousService
from src.tailoring.service import TailoringService
from src.tailoring.config import TailoringConfig

# Custom tailoring service with specific output directory
custom_output = Path("./custom-artifacts")
tailoring_service = TailoringService(
    config=TailoringConfig(output_dir=custom_output)
)

service = AutonomousService(
    settings=settings,
    tracker_service=tracker_service,
    extractor=extractor,
    scoring_service=scoring_service,
    profile_service=profile_service,
    single_job_service=single_job_service,
    tailoring_service=tailoring_service,
    confirm_callback=None,
    progress_callback=None
)

result = await service.run(
    leads_file=Path("leads.txt"),
    dry_run=True,  # Only generate documents
    min_score=0.7,
    include_skips=False,
    assume_yes=True
)

print(f"Generated documents for {result.processed} jobs")
print(f"Output directory: {custom_output}")
```

## Design Patterns and Decisions

### 1. Sequential Processing (Not Parallel)

**Decision**: Process jobs one at a time in `BatchRunner`

**Rationale**:
- Browser automation is resource-intensive
- Prevents rate limiting and bot detection
- Easier to debug and monitor progress
- Simplifies error handling and cancellation
- Maintains deterministic execution order

### 2. Immutable Data Models

**Decision**: Use frozen dataclasses for events and stats

**Rationale**:
- `BatchProgressEvent` is frozen to prevent accidental modification by callbacks
- `QueueStats` is frozen as it's a snapshot in time
- Prevents bugs from shared mutable state

### 3. Flexible Service Injection

**Decision**: Accept `Any` type for services instead of concrete types

**Rationale**:
- Supports both real and mock implementations
- Enables duck typing for testing
- Reduces coupling between modules
- Simplifies test setup with `SimpleNamespace` or `AsyncMock`

### 4. Two-Phase Queue Building

**Decision**: Separate queue building from execution

**Rationale**:
- Allows queue inspection before execution
- Enables user confirmation with full statistics
- Supports "queue only" mode for analysis
- Facilitates testing of queue logic independently

### 5. Graceful Interrupt Handling

**Decision**: Handle SIGINT/SIGTERM with cleanup

**Rationale**:
- Users can safely Ctrl+C during batch processing
- Current job is marked as failed (not lost)
- Signal handlers are cleaned up properly
- Batch result includes all jobs processed up to interruption

### 6. Dual-Mode Execution (Dry Run / Live)

**Decision**: Support both dry-run and live modes in same runner

**Rationale**:
- Dry run validates leads and generates documents without browser automation
- Useful for testing, previewing, or preparing documents offline
- Shares same queue building and filtering logic
- Reduces code duplication

### 7. Progressive Filtering

**Decision**: Apply filters in QueueManager, not in LeadFileParser

**Rationale**:
- Parser focuses on syntax validation only
- Semantic filtering (duplicates, scores) happens during queue building
- Allows same parsed leads to be queued with different filters
- Separation of concerns

### 8. Fingerprint Reuse

**Decision**: Reuse fingerprint from tracker if job already exists

**Rationale**:
- Maintains consistent fingerprinting even if job details change slightly
- Enables tracking across multiple autonomous runs
- Prevents duplicate records in tracker database

### 9. Callback-Based Progress Reporting

**Decision**: Use optional callbacks instead of events/queues

**Rationale**:
- Simple interface for CLI and programmatic usage
- No need for complex event loop management
- Callback can be synchronous or asynchronous
- Easy to test with mock callbacks

### 10. Statistics Tracking

**Decision**: Track comprehensive statistics in `QueueManager` and `BatchResult`

**Rationale**:
- Provides visibility into filtering decisions
- Helps users understand why jobs were excluded
- Useful for debugging and optimization
- Enables data-driven improvements to filtering logic

## Testing

The autonomous module has comprehensive test coverage:

### Unit Tests (`tests/unit/autonomous/`)

- `test_models.py`: Data model validation
- `test_leads.py`: Lead file parsing
- `test_queue.py`: Queue building, filtering, ranking
- `test_runner.py`: Batch execution logic
- `test_service.py`: Service orchestration

### Integration Tests (`tests/integration/`)

- `test_autonomous.py`: End-to-end workflows
  - Dry run execution with stubs
  - Duplicate detection integration
  - Live extraction smoke test (optional, requires API keys)

### Key Test Scenarios

1. **Queue Building**:
   - New URLs added to queue
   - Submitted duplicates filtered out
   - Failed/skipped duplicates included
   - Min score filtering
   - Include/exclude skip recommendations
   - Statistics accuracy

2. **Batch Execution**:
   - Sequential processing
   - Status mapping (RunStatus → QueueStatus)
   - Error handling and aggregation
   - Dry run vs live execution
   - Progress callback invocation

3. **Service Orchestration**:
   - Full pipeline from file to result
   - Empty queue handling
   - User confirmation flow
   - Min score filtering
   - Daily limit application

## Error Handling

### Lead Parsing Errors

Invalid URLs are returned as `LeadItem` with `valid=False` and a descriptive error message. They are filtered out during queue building.

### Queue Building Errors

- **Extraction failure**: Jobs that fail extraction are skipped (logged but not added to queue)
- **Scoring failure**: Caught and logged, job excluded from queue
- **Tracker errors**: Propagated as exceptions (fail-fast)

### Batch Execution Errors

- **Job failures**: Captured in `JobResult.error`, batch continues
- **Cancellation**: Marks current job as failed, stops batch gracefully
- **Tailoring failure**: In dry-run mode, raises `RuntimeError` and marks job as failed
- **Signal interruption**: Sets stop event, cancels current task, cleans up

### Error Propagation

- Parse errors: Returned as invalid LeadItem
- Queue building errors: Logged and excluded from queue
- Execution errors: Captured in JobResult, batch continues
- Fatal errors: Propagated to caller (e.g., file not found, tracker initialization failure)

## Performance Considerations

### Sequential Execution

Jobs are processed one at a time to:
- Avoid overwhelming browser automation
- Prevent rate limiting
- Reduce memory footprint
- Simplify error tracking

**Trade-off**: Slower than parallel execution, but more reliable and controllable.

### Caching in QueueManager

- Jobs from duplicate URLs are extracted and scored only once
- Cache stored in dict during single `build_queue()` call
- Reduces redundant API calls if same URL appears multiple times

### Database Queries

- One `check_duplicate()` call per valid lead
- Batch inserts/updates handled by TrackerRepository
- No N+1 query issues

### Memory Usage

- All queue items loaded into memory (acceptable for typical lead file sizes)
- Job results accumulated in list (freed after batch completion)
- No streaming/chunking (not needed for expected workload)

## Security Considerations

1. **URL Validation**: Only `http://` and `https://` URLs accepted
2. **File Path Safety**: Uses `pathlib.Path` for safe path handling
3. **SQL Injection**: TrackerRepository uses parameterized queries
4. **Credential Handling**: Browser automation reuses existing Chrome profile (managed by runner module)
5. **Human Confirmation**: Default behavior requires user confirmation before batch execution

## Future Enhancements

Potential improvements documented in tests and code comments:

1. **Parallel Queue Building**: Extract and score multiple jobs concurrently
2. **Resume/Retry**: Save queue state and resume interrupted batches
3. **Adaptive Rate Limiting**: Dynamically adjust execution speed based on site responses
4. **Queue Prioritization**: Allow manual reordering or priority boosting
5. **Scheduling**: Cron-like scheduling for automated runs
6. **Lead Source Integration**: Auto-fetch leads from job boards/RSS feeds
7. **Notification System**: Email/Slack notifications on batch completion
8. **Analytics Dashboard**: Track success rates, average scores, etc.

---

## Appendix: File Locations

- **Source**: `/Users/shalom/Developer/Job-Easy/src/autonomous/`
- **Tests**: `/Users/shalom/Developer/Job-Easy/tests/unit/autonomous/`
- **Integration Tests**: `/Users/shalom/Developer/Job-Easy/tests/integration/test_autonomous.py`
- **CLI Entry Point**: `/Users/shalom/Developer/Job-Easy/src/__main__.py` (autonomous mode)

## Appendix: Related Documentation

- Project Brief: `docs/project-brief.md`
- Development Guide: `docs/dev.md`
- Runner Manual Test: `docs/runner-manual-test.md`
- Workflow Diagram: `docs/workflow-diagram.md`
