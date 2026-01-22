# Tracker Module Documentation

## Overview

The **tracker** module is Job-Easy's application tracking and duplicate detection system. It provides persistent storage and intelligent fingerprinting for job applications, preventing redundant submissions and maintaining a comprehensive history of all application attempts.

### Purpose

The tracker module serves three critical functions:

1. **Duplicate Detection**: Identifies previously encountered job postings to prevent redundant applications
2. **Application History**: Maintains a complete audit trail of all job application attempts with timestamps, statuses, and artifacts
3. **Progress Tracking**: Monitors the lifecycle of each application from initial discovery through final submission

### Core Responsibilities

- Generate unique fingerprints for job postings using multiple strategies
- Store and retrieve application records in a persistent SQLite database
- Track application status transitions (NEW → IN_PROGRESS → SUBMITTED/SKIPPED/FAILED)
- Manage application artifacts (resumes, cover letters, proof screenshots)
- Support both single-application and autonomous batch workflows
- Handle user overrides when duplicate detection requires manual intervention

## Architecture

### Module Structure

```
src/tracker/
├── __init__.py           # Public API exports
├── models.py            # Data models and enums
├── fingerprint.py       # URL normalization and fingerprint generation
├── repository.py        # Database layer (SQLite)
└── service.py           # Business logic layer
```

### Component Hierarchy

```
TrackerService (Business Logic)
       ↓
TrackerRepository (Data Access)
       ↓
SQLite Database (tracker.db)

fingerprint.py (Utility Functions)
       ↓
TrackerService (Fingerprint Consumer)
```

## Key Components

### 1. TrackerService

**File**: `/Users/shalom/Developer/Job-Easy/src/tracker/service.py`

The main business logic coordinator that provides high-level operations for duplicate detection and record management.

#### Class Definition

```python
class TrackerService:
    """Business logic service for tracking job applications."""

    def __init__(self, repository: TrackerRepository):
        self.repository = repository
```

#### Public Methods

##### check_duplicate()

```python
async def check_duplicate(
    self,
    url: str | None,
    company: str,
    role: str,
    location: str | None,
) -> TrackerRecord | None:
    """Check if a job application already exists.

    Returns:
        The existing TrackerRecord if duplicate found, None otherwise.
    """
```

**Algorithm**:
1. Extract job ID from URL using pattern matching (Greenhouse, Lever, Workday)
2. Compute fingerprint using cascading strategy (job_id → normalized_url → company|role|location)
3. Query database by fingerprint
4. Return existing record or None

**Usage**:
- Called at the beginning of every job application flow
- Used by autonomous queue builder to filter out duplicates
- Triggers human-in-the-loop prompts when SUBMITTED duplicates are found

##### create_record()

```python
async def create_record(
    self,
    url: str | None,
    company: str,
    role: str,
    location: str | None,
    source_mode: SourceMode,
) -> str:
    """Create a new tracker record.

    Returns:
        The fingerprint of the created record.
    """
```

**Workflow**:
1. Extract job ID from URL (if provided)
2. Compute unique fingerprint
3. Normalize URL to canonical form
4. Create TrackerRecord with status=NEW
5. Insert into database
6. Return fingerprint for subsequent operations

**Important**: The fingerprint serves as both the primary key and the run directory name for artifacts.

##### update_status()

```python
async def update_status(
    self,
    fingerprint: str,
    status: ApplicationStatus,
) -> None:
    """Update the status of a job application."""
```

**Status Lifecycle**:
- NEW → IN_PROGRESS: Application processing started
- IN_PROGRESS → SUBMITTED: Application successfully submitted
- IN_PROGRESS → FAILED: Application encountered an error
- IN_PROGRESS → SKIPPED: User or system decided to skip
- IN_PROGRESS → DUPLICATE_SKIPPED: Skipped due to duplicate detection

##### record_override()

```python
async def record_override(
    self,
    fingerprint: str,
    reason: str | None = None,
) -> None:
    """Record that a duplicate was overridden by the user."""
```

**Purpose**: When duplicate detection identifies a submitted application, users can choose to proceed anyway. This method records that decision along with their optional reason.

##### get_record()

```python
async def get_record(self, fingerprint: str) -> TrackerRecord | None:
    """Get a record by fingerprint."""
```

### 2. TrackerRepository

**File**: `/Users/shalom/Developer/Job-Easy/src/tracker/repository.py`

Async SQLite repository providing CRUD operations for tracker records.

#### Class Definition

```python
class TrackerRepository:
    """Async SQLite repository for tracker records."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self._connection: aiosqlite.Connection | None = None
```

#### Database Schema

```sql
CREATE TABLE IF NOT EXISTS tracker (
    fingerprint TEXT PRIMARY KEY,
    canonical_url TEXT NOT NULL,
    source_mode TEXT NOT NULL,
    company TEXT NOT NULL,
    role_title TEXT NOT NULL,
    status TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    location TEXT,
    last_attempt_at TEXT,
    submitted_at TEXT,
    resume_artifact_path TEXT,
    cover_letter_artifact_path TEXT,
    proof_text TEXT,
    proof_screenshot_path TEXT,
    override_duplicate INTEGER DEFAULT 0,
    override_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_tracker_status ON tracker(status);
CREATE INDEX IF NOT EXISTS idx_tracker_first_seen ON tracker(first_seen_at);
```

#### Key Methods

##### initialize()

```python
async def initialize(self) -> None:
    """Initialize the database, creating tables if needed."""
```

**Workflow**:
1. Create parent directory if it doesn't exist
2. Create tables and indexes if they don't exist
3. No-op if database already exists

##### insert_record()

```python
async def insert_record(self, record: TrackerRecord) -> None:
    """Insert a new tracker record.

    Raises:
        sqlite3.IntegrityError: If a record with the same fingerprint exists.
    """
```

##### get_by_fingerprint()

```python
async def get_by_fingerprint(self, fingerprint: str) -> TrackerRecord | None:
    """Get a record by its fingerprint."""
```

##### get_by_url()

```python
async def get_by_url(self, url: str) -> TrackerRecord | None:
    """Get a record by its canonical URL."""
```

##### update_status()

```python
async def update_status(self, fingerprint: str, status: ApplicationStatus) -> None:
    """Update the status of a record.

    Also updates the last_attempt_at timestamp.
    """
```

**Special Behavior**: When status is SUBMITTED, also sets `submitted_at` timestamp.

##### update_proof()

```python
async def update_proof(
    self,
    fingerprint: str,
    proof_text: str | None = None,
    screenshot_path: str | None = None,
) -> None:
    """Update the proof fields for a record."""
```

**Usage**: Called after successful submission to store confirmation text and screenshot path.

##### update_artifacts()

```python
async def update_artifacts(
    self,
    fingerprint: str,
    resume_artifact_path: str | None = None,
    cover_letter_artifact_path: str | None = None,
) -> None:
    """Update resume/cover letter artifact paths for a record."""
```

##### get_status_counts()

```python
async def get_status_counts(self) -> dict[ApplicationStatus, int]:
    """Return record counts grouped by status."""
```

**Usage**: CLI stats command to show application statistics.

##### list_recent()

```python
async def list_recent(
    self,
    limit: int = 10,
    status_filter: ApplicationStatus | None = None,
) -> list[TrackerRecord]:
    """List recent tracker records, ordered by first_seen_at descending."""
```

**Usage**: CLI recent command to display recent applications.

##### close()

```python
async def close(self) -> None:
    """Close the database connection."""
```

**Important**: Always call this in a try/finally block or use as an async context manager.

### 3. Fingerprint Generation

**File**: `/Users/shalom/Developer/Job-Easy/src/tracker/fingerprint.py`

Provides URL normalization and fingerprint computation using a cascading strategy.

#### normalize_url()

```python
def normalize_url(url: str) -> str:
    """Normalize a URL for consistent fingerprinting."""
```

**Normalization Steps**:
1. Convert scheme to HTTPS
2. Remove tracking parameters (utm_*, ref, referrer, fbclid, gclid, etc.)
3. Remove trailing slashes from path
4. Sort remaining query parameters alphabetically
5. Rebuild URL in canonical form

**Example**:
```python
# Before
"http://example.com/job/?utm_source=linkedin&id=123&ref=twitter"

# After
"https://example.com/job?id=123"
```

#### extract_job_id()

```python
def extract_job_id(url: str) -> str | None:
    """Extract a job ID from known job board URL patterns."""
```

**Supported Platforms**:

| Platform | Pattern | Example | Result |
|----------|---------|---------|--------|
| Greenhouse | `boards.greenhouse.io/<company>/jobs/<id>` | `https://boards.greenhouse.io/company/jobs/12345` | `greenhouse:12345` |
| Lever | `jobs.lever.co/<company>/<uuid>` | `https://jobs.lever.co/company/abc-123-def` | `lever:abc-123-def` |
| Workday | `*.myworkdayjobs.com/.../<title>_<req-id>` | `https://company.wd5.myworkdayjobs.com/Jobs/Title_REQ-123456` | `workday:REQ-123456` |

**Returns**: Prefixed job ID string (e.g., "greenhouse:12345") or None if pattern not recognized.

#### compute_fingerprint()

```python
def compute_fingerprint(
    url: str | None,
    job_id: str | None,
    company: str,
    role: str,
    location: str | None,
) -> str:
    """Compute a fingerprint for a job application.

    Uses a cascading strategy:
    1. If job_id is available, hash it
    2. Else if url is available, hash the normalized URL
    3. Else hash company|role|location

    Returns:
        A SHA-256 hash string representing the fingerprint.
    """
```

**Cascading Strategy Rationale**:

1. **Job ID (Most Reliable)**: If we can extract a platform-specific ID, use it. This handles URL variations and redirects.

2. **Normalized URL (Fallback)**: For platforms we don't have parsers for, use the cleaned URL. This handles different tracking parameters pointing to the same job.

3. **Metadata (Last Resort)**: When no URL is available, use company/role/location combination. This is the least reliable but necessary for job aggregator sites.

**Example**:
```python
# Scenario 1: Known platform (Greenhouse)
fingerprint = compute_fingerprint(
    url="https://boards.greenhouse.io/acme/jobs/42",
    job_id="greenhouse:42",  # Extracted
    company="Acme Corp",
    role="Engineer",
    location="NYC"
)
# Result: SHA-256 hash of "greenhouse:42"

# Scenario 2: Unknown platform with URL
fingerprint = compute_fingerprint(
    url="https://example.com/careers/engineer?source=linkedin",
    job_id=None,  # No pattern match
    company="Example Inc",
    role="Engineer",
    location="Remote"
)
# Result: SHA-256 hash of "https://example.com/careers/engineer"

# Scenario 3: No URL (job aggregator)
fingerprint = compute_fingerprint(
    url=None,
    job_id=None,
    company="Unknown Corp",
    role="Developer",
    location="SF"
)
# Result: SHA-256 hash of "Unknown Corp|Developer|SF"
```

### 4. Data Models

**File**: `/Users/shalom/Developer/Job-Easy/src/tracker/models.py`

#### ApplicationStatus Enum

```python
class ApplicationStatus(str, Enum):
    """Status of a job application."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    SKIPPED = "skipped"
    DUPLICATE_SKIPPED = "duplicate_skipped"
    SUBMITTED = "submitted"
    FAILED = "failed"
```

**Status Meanings**:

| Status | Meaning | When Set |
|--------|---------|----------|
| NEW | Record created, not yet processed | During `create_record()` |
| IN_PROGRESS | Application is being processed | When extraction/tailoring starts |
| SKIPPED | User or system decided to skip | When fit score recommends skip and user confirms |
| DUPLICATE_SKIPPED | Skipped due to duplicate detection | When user declines to override duplicate |
| SUBMITTED | Application successfully submitted | After browser agent confirms submission |
| FAILED | Application encountered an error | When extraction, tailoring, or submission fails |

#### SourceMode Enum

```python
class SourceMode(str, Enum):
    """Mode in which the application was initiated."""

    SINGLE = "single"
    AUTONOMOUS = "autonomous"
```

**Usage**:
- SINGLE: Manual application via `job-easy apply <url>`
- AUTONOMOUS: Batch processing via `job-easy auto <leads-file>`

**Purpose**: Analytics and auditing to understand which workflow generated applications.

#### TrackerRecord Dataclass

```python
@dataclass
class TrackerRecord:
    """A record of a job application attempt."""

    # Required fields
    fingerprint: str
    canonical_url: str
    source_mode: SourceMode
    company: str
    role_title: str
    status: ApplicationStatus
    first_seen_at: datetime

    # Optional fields
    location: str | None = None
    last_attempt_at: datetime | None = None
    submitted_at: datetime | None = None
    resume_artifact_path: str | None = None
    cover_letter_artifact_path: str | None = None
    proof_text: str | None = None
    proof_screenshot_path: str | None = None
    override_duplicate: bool = field(default=False)
    override_reason: str | None = None
```

##### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| fingerprint | str | SHA-256 hash serving as primary key |
| canonical_url | str | Normalized URL (or empty string if no URL) |
| source_mode | SourceMode | How application was initiated (SINGLE/AUTONOMOUS) |
| company | str | Company name |
| role_title | str | Job title/role |
| status | ApplicationStatus | Current status |
| first_seen_at | datetime | When job was first encountered |
| location | str \| None | Job location (e.g., "NYC", "Remote") |
| last_attempt_at | datetime \| None | Last time application was attempted |
| submitted_at | datetime \| None | When application was successfully submitted |
| resume_artifact_path | str \| None | Path to tailored resume file |
| cover_letter_artifact_path | str \| None | Path to tailored cover letter file |
| proof_text | str \| None | Text confirmation of submission |
| proof_screenshot_path | str \| None | Path to screenshot proof |
| override_duplicate | bool | Whether user overrode duplicate warning |
| override_reason | str \| None | User's reason for override |

##### Serialization Methods

```python
def to_dict(self) -> dict:
    """Serialize the record to a dictionary."""

@classmethod
def from_dict(cls, data: dict) -> "TrackerRecord":
    """Deserialize a record from a dictionary."""
```

**Usage**: CLI output, API responses, debugging.

## Integration with Other Modules

### Runner Module

**File**: `/Users/shalom/Developer/Job-Easy/src/runner/service.py`

The runner module (SingleJobApplicationService) integrates tracker at multiple checkpoints:

#### Duplicate Detection Flow

```python
# 1. Initial URL-based check (before extraction)
duplicate = await self.tracker_service.check_duplicate(
    url=url,
    company="",
    role="",
    location=None,
)

if duplicate is not None and duplicate.status == ApplicationStatus.SUBMITTED:
    proceed = hitl.prompt_yes_no(
        f"Tracker indicates this job was already submitted. Proceed anyway?\n{url}"
    )
    if not proceed:
        return ApplicationRunResult(
            success=True,
            status=RunStatus.DUPLICATE_SKIPPED,
            notes=["duplicate_detected"],
        )

    reason = hitl.prompt_free_text("Optional override reason")
    await self.tracker_service.record_override(
        fingerprint=duplicate.fingerprint,
        reason=reason or None,
    )
```

#### Second-Pass Duplicate Check

After job extraction, runner performs a more accurate duplicate check:

```python
# 2. Canonical check with extracted details (handles redirects/aggregators)
if duplicate is None:
    canonical_duplicate = await self.tracker_service.check_duplicate(
        url=start_url,  # May differ from original URL
        company=job.company,
        role=job.role_title,
        location=job.location,
    )
    # ... same duplicate handling as above
```

**Rationale**: Job aggregator sites (Indeed, LinkedIn) redirect to canonical URLs. The second check catches duplicates that the first check missed.

#### Record Creation

```python
# 3. Create record if not a duplicate
if fingerprint is None:
    fingerprint = await self.tracker_service.create_record(
        url=start_url,
        company=job.company,
        role=job.role_title,
        location=job.location,
        source_mode=self.source_mode,
    )

# 4. Use fingerprint as run directory name
run_dir = (
    Path(settings.output_dir)
    / "runs"
    / fingerprint
)
run_dir.mkdir(parents=True, exist_ok=True)
```

#### Status Updates Throughout Lifecycle

```python
# 5. Update on failure
if job is None:
    if fingerprint:
        await self.tracker_service.update_status(
            fingerprint, ApplicationStatus.FAILED
        )

# 6. Update on skip
if fit.recommendation == "skip" and not proceed:
    await self.tracker_service.update_status(
        fingerprint, ApplicationStatus.SKIPPED
    )

# 7. Update on successful submission
if result.status == RunStatus.SUBMITTED:
    await self.tracker_repository.update_proof(
        fingerprint,
        proof_text=result.proof_text,
        screenshot_path=result.proof_screenshot_path,
    )
    await self.tracker_repository.update_artifacts(
        fingerprint,
        resume_artifact_path=resume_path,
        cover_letter_artifact_path=cover_letter_path,
    )
    await self.tracker_service.update_status(
        fingerprint, ApplicationStatus.SUBMITTED
    )
```

### Autonomous Module

**File**: `/Users/shalom/Developer/Job-Easy/src/autonomous/queue.py`

The autonomous queue builder uses tracker to filter out duplicates during batch processing:

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
    queued: list[QueuedJob] = []
    duplicates = 0

    for lead in valid_leads:
        # Check if already submitted
        duplicate = await tracker_service.check_duplicate(
            url=lead.url,
            company="",
            role="",
            location=None,
        )

        if (
            duplicate is not None
            and duplicate.status == ApplicationStatus.SUBMITTED
        ):
            duplicates += 1
            continue  # Skip this lead

        # ... extract, score, and queue if passes thresholds
```

**Key Difference from Runner**: Autonomous mode automatically skips duplicates without user prompts, making batch processing fully automated.

### Extractor Module

**File**: `/Users/shalom/Developer/Job-Easy/src/extractor/service.py`

The extractor uses tracker's job ID extraction to populate job descriptions:

```python
# If the model didn't extract a job_id, try deriving it from the URL
if not result.job_id:
    with contextlib.suppress(Exception):
        from src.tracker.fingerprint import extract_job_id

        result.job_id = extract_job_id(result.job_url or url)
```

**Purpose**: Provides a canonical identifier for debugging and analytics.

### Config Module

**File**: `/Users/shalom/Developer/Job-Easy/src/config/settings.py`

Configuration setting for tracker database path:

```python
tracker_db_path: Path = Field(
    default=Path("./data/tracker.db"),
    description="Path to the SQLite tracker database",
)
```

**Default Location**: `./data/tracker.db`

**Environment Override**: `TRACKER_DB_PATH=/custom/path/tracker.db`

## CLI Commands

The tracker module exposes several CLI commands for inspecting and managing application records.

### Stats Command

```bash
job-easy tracker stats [--db PATH]
```

**Output**:
```
new: 5
in_progress: 2
skipped: 8
duplicate_skipped: 3
submitted: 42
failed: 1
```

**Implementation**: Calls `repository.get_status_counts()`

### Lookup Command

```bash
# By fingerprint
job-easy tracker lookup --fingerprint <HASH>

# By URL
job-easy tracker lookup --url <URL>
```

**Output**: JSON representation of the TrackerRecord

```json
{
  "fingerprint": "a3b2c1...",
  "canonical_url": "https://boards.greenhouse.io/acme/jobs/42",
  "source_mode": "single",
  "company": "Acme Corp",
  "role_title": "Senior Engineer",
  "status": "submitted",
  "first_seen_at": "2025-01-15T10:30:00",
  "location": "NYC",
  "last_attempt_at": "2025-01-15T10:45:00",
  "submitted_at": "2025-01-15T11:00:00",
  "resume_artifact_path": "./artifacts/runs/a3b2c1.../resume.pdf",
  "cover_letter_artifact_path": "./artifacts/runs/a3b2c1.../cover_letter.pdf",
  "proof_text": "Application submitted successfully",
  "proof_screenshot_path": "./artifacts/runs/a3b2c1.../proof.png",
  "override_duplicate": false,
  "override_reason": null
}
```

### Recent Command

```bash
# List 10 most recent applications
job-easy tracker recent

# List 20 most recent
job-easy tracker recent --limit 20

# Filter by status
job-easy tracker recent --status submitted --limit 5
```

**Output**:
```
2025-01-21T14:30:00 submitted abc123... TechCorp Senior Developer
2025-01-21T13:15:00 skipped def456... StartupInc Junior Engineer
2025-01-21T12:00:00 submitted ghi789... BigCo Staff Engineer
```

**Implementation**: Calls `repository.list_recent(limit, status_filter)`

### Mark Command

```bash
# Update status
job-easy tracker mark --fingerprint <HASH> --status submitted

# Add proof
job-easy tracker mark --fingerprint <HASH> --status submitted \
  --proof-text "Application confirmed via email" \
  --proof-screenshot ./proof.png
```

**Purpose**: Manual status updates for debugging or correcting incorrect states.

## Data Persistence

### Database File

**Default Path**: `./data/tracker.db`

**Format**: SQLite 3

**Encoding**: UTF-8

**Persistence**: All data persists across application restarts. The database file is the single source of truth.

### Connection Management

The repository uses a single persistent connection per instance:

```python
@asynccontextmanager
async def _get_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
    if self._connection is None:
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
    yield self._connection
```

**Important**: Always call `repository.close()` to properly close the connection:

```python
repo = TrackerRepository(settings.tracker_db_path)
await repo.initialize()

try:
    # ... use repository
finally:
    await repo.close()
```

### Schema Migrations

**Current Version**: 1 (initial schema)

**Migration Strategy**: Not yet implemented. Future migrations will use Alembic or custom migration scripts.

**Backward Compatibility**: Adding new nullable columns is safe. Changing existing columns requires migration.

## Query and Retrieval Patterns

### Primary Key Lookup (Fastest)

```python
record = await repository.get_by_fingerprint(fingerprint)
```

**Performance**: O(1) - Direct primary key lookup

**Index**: Primary key index on `fingerprint`

### URL Lookup

```python
record = await repository.get_by_url(canonical_url)
```

**Performance**: O(n) - Full table scan (no index on canonical_url)

**Recommendation**: If URL lookups become frequent, add an index:
```sql
CREATE INDEX idx_tracker_canonical_url ON tracker(canonical_url);
```

### Status Filtering

```python
records = await repository.list_recent(limit=10, status_filter=ApplicationStatus.SUBMITTED)
```

**Performance**: O(n) with index optimization

**Index**: `idx_tracker_status` speeds up status filtering

### Timestamp-Based Queries

```python
records = await repository.list_recent(limit=10)
```

**Performance**: O(n log n) with index optimization

**Index**: `idx_tracker_first_seen` speeds up ORDER BY first_seen_at

### Aggregation Queries

```python
counts = await repository.get_status_counts()
```

**Performance**: O(n) - Full table scan with GROUP BY

**Index**: `idx_tracker_status` speeds up grouping

## Dependencies

### Internal Dependencies

| Module | Usage |
|--------|-------|
| config | Database path configuration (`settings.tracker_db_path`) |
| hitl | User prompts for duplicate override decisions |
| runner | Duplicate checks, status updates, artifact recording |
| autonomous | Duplicate filtering during queue building |
| extractor | Job ID extraction for job descriptions |

### External Dependencies

| Package | Purpose | Version |
|---------|---------|---------|
| aiosqlite | Async SQLite database access | ^0.17.0 |
| hashlib | SHA-256 fingerprint generation | stdlib |
| urllib.parse | URL normalization | stdlib |
| dataclasses | TrackerRecord model | stdlib |
| datetime | Timestamp management | stdlib |
| pathlib | File path handling | stdlib |

### Dependency Graph

```
TrackerService
    ├─ TrackerRepository
    │   └─ aiosqlite
    └─ fingerprint
        ├─ hashlib
        └─ urllib.parse

Runner (Consumer)
    ├─ TrackerService
    └─ hitl

Autonomous (Consumer)
    └─ TrackerService

Extractor (Consumer)
    └─ fingerprint.extract_job_id
```

## Testing

### Test Coverage

**Location**: `/Users/shalom/Developer/Job-Easy/tests/integration/tracker/test_tracker_integration.py`

### Test Suites

#### 1. Full Workflow Tests

```python
class TestFullWorkflow:
    """Test the full tracker workflow end-to-end."""

    async def test_full_workflow_create_check_update(self, service):
        """Test: create → check duplicate → update status → verify persistence"""
```

**Coverage**:
- Record creation with fingerprint generation
- Duplicate detection with exact URL match
- Status transitions (NEW → IN_PROGRESS → SUBMITTED)
- Timestamp updates (submitted_at set on SUBMITTED)

#### 2. Database Persistence Tests

```python
class TestDatabasePersistence:
    """Test that database persists between sessions."""

    async def test_database_persists_between_sessions(self, tmp_path):
        """Test: create → close → reopen → verify"""
```

**Coverage**:
- Database file creation
- Connection closure and reopening
- Data persistence across sessions
- Enum serialization/deserialization

#### 3. Concurrent Access Tests

```python
class TestConcurrentAccess:
    """Test concurrent access handling."""

    async def test_concurrent_reads_succeed(self, tmp_path):
        """Test multiple concurrent reads"""

    async def test_concurrent_duplicate_checks_succeed(self, tmp_path):
        """Test multiple concurrent duplicate checks"""
```

**Coverage**:
- Thread-safe database access
- Concurrent reads without locking issues
- Consistent results from parallel queries

### Running Tests

```bash
# Run all tracker tests
pytest tests/integration/tracker/

# Run with verbose output
pytest tests/integration/tracker/ -v

# Run specific test
pytest tests/integration/tracker/test_tracker_integration.py::TestFullWorkflow::test_full_workflow_create_check_update
```

## Error Handling

### Common Errors and Solutions

#### 1. Duplicate Primary Key

**Error**:
```
sqlite3.IntegrityError: UNIQUE constraint failed: tracker.fingerprint
```

**Cause**: Attempting to insert a record with an existing fingerprint.

**Solution**: Always check for duplicates before creating:
```python
duplicate = await tracker_service.check_duplicate(...)
if duplicate is None:
    fingerprint = await tracker_service.create_record(...)
```

#### 2. Connection Not Initialized

**Error**:
```
AttributeError: 'NoneType' object has no attribute 'execute'
```

**Cause**: Calling repository methods before `initialize()`.

**Solution**: Always initialize before use:
```python
repo = TrackerRepository(db_path)
await repo.initialize()  # REQUIRED
```

#### 3. Connection Not Closed

**Symptom**: Database locks, file handle leaks

**Solution**: Always close in finally block:
```python
try:
    # ... use repository
finally:
    await repo.close()
```

#### 4. Invalid Status Value

**Error**:
```
ValueError: 'invalid' is not a valid ApplicationStatus
```

**Cause**: Attempting to create ApplicationStatus with invalid string.

**Solution**: Use enum members directly:
```python
# Good
status = ApplicationStatus.SUBMITTED

# Bad
status = ApplicationStatus("submitted")  # Works but fragile

# Very Bad
status = "submitted"  # Type error, use enum!
```

## Best Practices

### 1. Always Use TrackerService, Not Repository Directly

**Good**:
```python
service = TrackerService(repository)
duplicate = await service.check_duplicate(url, company, role, location)
```

**Bad**:
```python
# Don't compute fingerprints manually
fingerprint = compute_fingerprint(...)
duplicate = await repository.get_by_fingerprint(fingerprint)
```

**Rationale**: TrackerService encapsulates fingerprint logic and may add additional business rules in the future.

### 2. Initialize Repository Once, Reuse Across Operations

**Good**:
```python
repo = TrackerRepository(settings.tracker_db_path)
await repo.initialize()

service = TrackerService(repo)
# ... many operations
await repo.close()
```

**Bad**:
```python
# Don't create new repo instances for each operation
for url in urls:
    repo = TrackerRepository(settings.tracker_db_path)
    await repo.initialize()
    # ... operation
    await repo.close()  # Inefficient!
```

### 3. Use Context Managers for Automatic Cleanup

**Best**:
```python
# Future enhancement: Add context manager support
async with TrackerRepository(db_path) as repo:
    await repo.initialize()
    service = TrackerService(repo)
    # ... operations
    # Auto-closes on exit
```

**Current**:
```python
repo = TrackerRepository(db_path)
await repo.initialize()
try:
    # ... operations
finally:
    await repo.close()
```

### 4. Handle Duplicate Overrides Properly

**Good**:
```python
duplicate = await service.check_duplicate(...)
if duplicate and duplicate.status == ApplicationStatus.SUBMITTED:
    proceed = hitl.prompt_yes_no("Already submitted. Proceed?")
    if proceed:
        reason = hitl.prompt_free_text("Reason for override?")
        await service.record_override(duplicate.fingerprint, reason)
    else:
        return  # Respect user's decision
```

**Bad**:
```python
# Don't silently ignore duplicates
duplicate = await service.check_duplicate(...)
if duplicate:
    pass  # Oops! User might apply twice
```

### 5. Update Status at Appropriate Lifecycle Points

**Status Update Timeline**:
```
create_record() → NEW
    ↓
extraction starts → (no status change yet)
    ↓
tailoring starts → (no status change yet)
    ↓
submission starts → (no status change yet)
    ↓
submission succeeds → SUBMITTED
    OR
submission fails → FAILED
    OR
user skips → SKIPPED
```

**Rationale**: Only update status when the application's state definitively changes, not for internal processing steps.

### 6. Store Artifact Paths Relative to Output Directory

**Good**:
```python
# Store relative paths
resume_path = "./artifacts/runs/abc123.../resume.pdf"
await repository.update_artifacts(
    fingerprint,
    resume_artifact_path=str(resume_path),
)
```

**Better**:
```python
# Store paths relative to run directory
resume_path = "resume.pdf"
cover_letter_path = "cover_letter.pdf"
await repository.update_artifacts(
    fingerprint,
    resume_artifact_path=resume_path,
    cover_letter_artifact_path=cover_letter_path,
)
```

**Rationale**: Relative paths are portable across environments and don't leak absolute path information.

## Performance Considerations

### Database Size

**Current**: Single-table design scales to ~100,000 records without performance degradation.

**Indexes**: Two indexes (status, first_seen_at) keep queries fast.

**Growth Rate**: Typical usage generates 10-50 records/day, reaching 1,000-5,000 records/year.

**Vacuum**: Periodically run `VACUUM` to reclaim space from deleted records (if implementing deletion).

### Query Performance

| Operation | Complexity | Index | Performance |
|-----------|------------|-------|-------------|
| get_by_fingerprint() | O(1) | Primary Key | <1ms |
| get_by_url() | O(n) | None | 1-10ms (1K records) |
| list_recent() | O(n log n) | first_seen_at | 2-20ms (1K records) |
| get_status_counts() | O(n) | status | 5-50ms (1K records) |

### Connection Pooling

**Current**: Single connection per repository instance.

**Future**: For high-concurrency scenarios, consider connection pooling with `aiosqlite.pool`.

### Fingerprint Computation

**Performance**: SHA-256 hashing is very fast (<0.1ms per fingerprint).

**Caching**: Not necessary given the low computational cost.

## Future Enhancements

### 1. Full-Text Search

**Goal**: Search applications by company, role, or location.

**Implementation**:
```sql
CREATE VIRTUAL TABLE tracker_fts USING fts5(company, role_title, location);
```

### 2. Application History Timeline

**Goal**: Track all status transitions with timestamps.

**Implementation**: Separate `tracker_history` table with foreign key to `tracker.fingerprint`.

### 3. Deduplication Report

**Goal**: Show near-duplicates that might be the same job.

**Implementation**: Fuzzy matching on company+role using Levenshtein distance.

### 4. Application Metrics

**Goal**: Dashboard showing success rates, time-to-submission, etc.

**Implementation**: Aggregate queries with date bucketing.

### 5. Archive Old Applications

**Goal**: Move old applications to separate archive table.

**Implementation**: `tracker_archive` table with periodic migration of records older than 1 year.

### 6. External ID Support

**Goal**: Link tracker records to external ATS systems.

**Implementation**: Add `external_id` and `external_system` columns.

### 7. Webhook Notifications

**Goal**: Send webhook when application status changes.

**Implementation**: Trigger async webhook on status update.

## Troubleshooting

### Database Corruption

**Symptoms**: `sqlite3.DatabaseError: database disk image is malformed`

**Solution**:
1. Stop the application
2. Backup the database: `cp tracker.db tracker.db.backup`
3. Run integrity check: `sqlite3 tracker.db "PRAGMA integrity_check;"`
4. If corrupted, restore from backup or rebuild from artifacts

### Missing Indexes

**Symptoms**: Slow queries on large databases

**Solution**:
```bash
sqlite3 data/tracker.db <<EOF
CREATE INDEX IF NOT EXISTS idx_tracker_status ON tracker(status);
CREATE INDEX IF NOT EXISTS idx_tracker_first_seen ON tracker(first_seen_at);
EOF
```

### Duplicate Detection Not Working

**Checklist**:
1. Verify URL normalization: `normalize_url(url1) == normalize_url(url2)`
2. Check job ID extraction: `extract_job_id(url)` returns expected value
3. Verify fingerprint computation: Same inputs produce same fingerprint
4. Check database: `sqlite3 tracker.db "SELECT * FROM tracker WHERE fingerprint = '<hash>';"`

### Connection Leaks

**Symptoms**: `Too many open files` error

**Solution**: Ensure all repository instances are properly closed:
```bash
# Find unclosed connections
lsof -p $(pgrep -f job-easy) | grep tracker.db
```

## Summary

The tracker module is a critical component of Job-Easy, providing:

1. **Reliable Duplicate Detection**: Multi-strategy fingerprinting prevents redundant applications
2. **Comprehensive History**: Complete audit trail of all application attempts
3. **Artifact Management**: Links tailored resumes, cover letters, and proof screenshots to applications
4. **Status Tracking**: Monitors application lifecycle from discovery to submission
5. **CLI Tools**: Convenient commands for inspecting and managing application records

**Key Architectural Decisions**:
- SQLite for simplicity and portability (no separate database server)
- Async I/O for non-blocking operations
- Cascading fingerprint strategy for robustness across different job platforms
- Separation of concerns (service layer, repository layer, fingerprint utilities)
- Human-in-the-loop integration for duplicate override decisions

**Integration Points**:
- Runner: Duplicate checks, status updates, artifact recording
- Autonomous: Batch duplicate filtering
- Extractor: Job ID population
- Config: Database path configuration
- HITL: User confirmation for duplicate overrides

The tracker module successfully balances simplicity, performance, and reliability, forming the foundation for Job-Easy's duplicate detection and application management capabilities.
