# Specification: Autonomous Mode (Queue + Scheduler)

> Track Type: Feature
> Epic Reference: E7

---

## Overview

Implement autonomous mode for Job-Easy that processes multiple job applications from a user-provided list file. The system leverages the existing `SingleJobApplicationService.run(url)` pipeline, adding queue management, fit-score ranking, and batch orchestration on top.

---

## Current State Analysis

### Existing Infrastructure (Ready to Use)
- `SingleJobApplicationService.run(url)` - Full pipeline: extract → score → tailor → apply
- `JobExtractor.extract(url)` - Browser Use-powered JD extraction
- `FitScoringService.evaluate(job, profile)` - Scoring with recommendation
- `TrackerService` - Fingerprint-based duplicate detection
- `ProfileService.load_profile()` - User profile loading
- `Settings.max_applications_per_day` - Exists but unused
- `SourceMode.AUTONOMOUS` enum - Exists in tracker models
- CLI stub: `python -m src autonomous` - Prints "not yet implemented"

### To Be Implemented
- `/src/autonomous/` module (currently empty placeholder)
- Lead file parser
- Queue management service
- Batch orchestration service
- CLI argument handling for autonomous mode

---

## Functional Requirements

### FR1: Lead File Parser

Location: `/src/autonomous/leads.py`

- Parse text file with one job URL per line
- Ignore blank lines and comments (lines starting with `#`)
- Validate URLs (must be valid HTTP/HTTPS URLs)
- Return list of `LeadItem` dataclass:
  ```python
  @dataclass
  class LeadItem:
      url: str
      line_number: int
      valid: bool
      error: str | None = None
  ```
- Report parsing results: total lines, valid URLs, invalid URLs

### FR2: Queue Manager

Location: `/src/autonomous/queue.py`

**QueueManager class with:**

1. **Deduplication** (reuse existing `TrackerService`):
   - Check each lead against tracker fingerprints
   - Classify as: `new`, `duplicate_submitted`, `duplicate_failed`, `duplicate_skipped`
   - New and failed jobs are eligible for processing
   - Submitted jobs are skipped (no override in batch mode)

2. **Pre-scoring** (reuse existing services):
   - For eligible leads, run extraction + fit scoring
   - Use `JobExtractor.extract()` for JD
   - Use `FitScoringService.evaluate()` for fit result
   - Cache `JobDescription` and `FitResult` to avoid re-extraction

3. **Ranking**:
   - Sort queue by `FitResult.score.overall` descending
   - Filter out jobs below `--min-score` threshold
   - Filter out jobs with `recommendation == "skip"` (unless `--include-skips`)

4. **Queue State Model**:
   ```python
   @dataclass
   class QueuedJob:
       url: str
       fingerprint: str
       job_description: JobDescription
       fit_result: FitResult
       status: QueueStatus  # pending, processing, completed, failed, skipped
   ```

### FR3: Batch Runner

Location: `/src/autonomous/runner.py`

**BatchRunner class with:**

1. **Sequential Processing**:
   - Process jobs one-by-one using `SingleJobApplicationService.run(url)`
   - Update queue status after each job
   - Continue on individual failures (log and move to next)

2. **Progress Tracking**:
   - Track: processed, submitted, skipped, failed counts
   - Emit progress events for CLI display
   - Checkpoint to tracker after each job (already done by SingleJobApplicationService)

3. **Dry-Run Mode**:
   - Run extraction + scoring + tailoring
   - Skip browser automation (don't call runner agent)
   - Still produce tailored documents for review

4. **Interruption Handling**:
   - Graceful shutdown on SIGINT/SIGTERM
   - Mark current job as interrupted
   - Resume capability via tracker status queries

### FR4: Batch Orchestration Service

Location: `/src/autonomous/service.py`

**AutonomousService class that orchestrates:**

```python
class AutonomousService:
    async def run(
        leads_file: Path,
        dry_run: bool = False,
        min_score: float | None = None,
        include_skips: bool = False,
    ) -> BatchResult
```

Pipeline:
1. Parse leads file → `LeadItem[]`
2. Initialize queue with deduplication → `QueuedJob[]`
3. Pre-score and rank queue
4. Display queue summary, await user confirmation
5. Run batch processor
6. Generate and return `BatchResult`

### FR5: CLI Integration

Location: Update `/src/__main__.py`

**Command**: `job-easy autonomous <leads-file>`

**Arguments**:
- `leads_file` (positional): Path to text file with job URLs

**Flags**:
- `--dry-run`: Score and generate documents without applying
- `--min-score <float>`: Skip jobs below this overall score (0.0-1.0)
- `--include-skips`: Process jobs even if fit scoring recommends skip
- `--yes`: Skip confirmation prompt before processing

**Output**:
- Queue summary before processing
- Per-job progress updates
- Final summary report

### FR6: Result Reporting

**BatchResult dataclass**:
```python
@dataclass
class BatchResult:
    total_leads: int
    valid_leads: int
    duplicates_skipped: int
    below_threshold: int
    queued: int
    processed: int
    submitted: int
    failed: int
    skipped: int
    interrupted: bool
    duration_seconds: float
    job_results: list[JobResult]
```

**Console Output**:
- Progress bar during batch run
- Per-job status line (URL, score, outcome)
- Final summary table

---

## Non-Functional Requirements

### NFR1: Reliability
- Individual job failures don't stop the batch
- All state changes persisted to tracker immediately
- Clean shutdown on interrupt signals

### NFR2: Performance
- Extraction + scoring can be parallelized (future optimization)
- Browser automation remains sequential (Browser Use constraint)

### NFR3: Consistency with Single Mode
- Reuse existing services without modification
- Same HITL gates apply (submit confirmation, duplicate override, etc.)
- Same artifact naming and storage

---

## Acceptance Criteria

1. **Lead parsing**: File with 10 URLs (including 2 invalid) correctly parses 8 valid leads
2. **Deduplication**: Previously submitted job is identified and skipped
3. **Ranking**: Jobs are processed in descending fit score order
4. **Dry-run**: `--dry-run` produces scored queue and tailored docs without browser automation
5. **Progress**: User sees real-time progress during batch run
6. **Graceful failure**: One failed job doesn't stop remaining jobs
7. **Summary**: Final report shows accurate counts for all outcomes
8. **Integration**: Full batch run successfully applies to multiple jobs

---

## Out of Scope

- Email/RSS feed parsing (future enhancement)
- LinkedIn saved jobs integration (future enhancement)
- Job board scraping (future enhancement)
- Background daemon mode
- Parallel browser sessions
- Automatic rate limiting (user controls input file size)

---

## File Structure

```
/src/autonomous/
├── __init__.py      # Public exports
├── models.py        # LeadItem, QueuedJob, QueueStatus, BatchResult
├── leads.py         # LeadFileParser
├── queue.py         # QueueManager
├── runner.py        # BatchRunner
└── service.py       # AutonomousService (orchestrator)
```
