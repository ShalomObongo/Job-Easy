# Implementation Plan: Autonomous Mode (Queue + Scheduler)

> Track ID: track_20260118_011233
> Methodology: TDD (Test-Driven Development)

---

## Phase 1: Data Models

### [x] Task 1.1: Define autonomous mode models
- [x] Create `/src/autonomous/models.py`
- [x] Define `LeadItem` dataclass (url, line_number, valid, error)
- [x] Define `QueueStatus` enum (pending, processing, completed, failed, skipped)
- [x] Define `QueuedJob` dataclass (url, fingerprint, job_description, fit_result, status)
- [x] Define `JobResult` dataclass (url, fingerprint, status, error, duration)
- [x] Define `BatchResult` dataclass (counts, duration, job_results)
- [x] Write unit tests for model validation and serialization
- [x] Run tests and verify passing

### [x] Task 1.2: Update module exports
- [x] Update `/src/autonomous/__init__.py` with public exports
- [x] Verify imports work from parent module

---

## Phase 2: Lead File Parser

### [x] Task 2.1: Write lead parser tests
- [x] Create `/tests/unit/autonomous/test_leads.py`
- [x] Test: parse file with valid URLs returns LeadItems
- [x] Test: blank lines and comments are ignored
- [x] Test: invalid URLs are marked with valid=False and error message
- [x] Test: file not found raises appropriate error
- [x] Test: empty file returns empty list

### [x] Task 2.2: Implement lead parser
- [x] Create `/src/autonomous/leads.py`
- [x] Implement `LeadFileParser` class
- [x] Implement `parse(file_path: Path) -> list[LeadItem]` method
- [x] Add URL validation using urllib.parse
- [x] Run tests and verify passing

---

## Phase 3: Queue Manager

### [x] Task 3.1: Write queue manager tests
- [x] Create `/tests/unit/autonomous/test_queue.py`
- [x] Test: new URLs are added to queue
- [x] Test: submitted duplicates are filtered out
- [x] Test: failed/skipped duplicates are included
- [x] Test: queue is sorted by fit score descending
- [x] Test: min_score filter excludes low-scoring jobs
- [x] Test: include_skips flag behavior

### [x] Task 3.2: Implement queue manager
- [x] Create `/src/autonomous/queue.py`
- [x] Implement `QueueManager` class
- [x] Implement `async def build_queue(leads, tracker_service, extractor, scorer, profile, min_score, include_skips) -> list[QueuedJob]`
- [x] Integrate with `TrackerService.check_duplicate()`
- [x] Integrate with `JobExtractor.extract()`
- [x] Integrate with `FitScoringService.evaluate()`
- [x] Implement ranking logic
- [x] Run tests and verify passing

### [x] Task 3.3: Add queue statistics
- [x] Implement `QueueStats` dataclass (total, valid, duplicates, below_threshold, queued)
- [x] Implement `get_stats() -> QueueStats` method
- [x] Add tests for statistics accuracy
- [x] Run tests and verify passing

---

## Phase 4: Batch Runner

### [x] Task 4.1: Write batch runner tests
- [x] Create `/tests/unit/autonomous/test_runner.py`
- [x] Test: processes jobs sequentially
- [x] Test: updates job status after each run
- [x] Test: continues after individual job failure
- [x] Test: dry-run mode skips browser automation
- [x] Test: tracks progress counts correctly
- [x] Test: handles graceful shutdown

### [x] Task 4.2: Implement batch runner
- [x] Create `/src/autonomous/runner.py`
- [x] Implement `BatchRunner` class
- [x] Implement `async def run(queue: list[QueuedJob], dry_run: bool) -> BatchResult`
- [x] Integrate with `SingleJobApplicationService.run()`
- [x] Add progress callback mechanism
- [x] Implement error handling per job
- [x] Run tests and verify passing

### [x] Task 4.3: Implement dry-run mode
- [x] Create dry-run path that skips `SingleJobApplicationService.run()`
- [x] In dry-run: run extraction + scoring + tailoring only
- [x] Verify tailored documents are generated
- [x] Add tests for dry-run behavior
- [x] Run tests and verify passing

---

## Phase 5: Autonomous Service (Orchestrator)

### [x] Task 5.1: Write orchestrator tests
- [x] Create `/tests/unit/autonomous/test_service.py`
- [x] Test: full pipeline from file to BatchResult
- [x] Test: respects dry_run flag
- [x] Test: respects min_score filter
- [x] Test: handles empty queue gracefully
- [x] Test: handles all-duplicate queue

### [x] Task 5.2: Implement orchestrator
- [x] Create `/src/autonomous/service.py`
- [x] Implement `AutonomousService` class
- [x] Implement `async def run(leads_file, dry_run, min_score, include_skips) -> BatchResult`
- [x] Wire together: LeadFileParser → QueueManager → BatchRunner
- [x] Add pre-run summary display
- [x] Run tests and verify passing

---

## Phase 6: CLI Integration

### [x] Task 6.1: Update CLI parser
- [x] Update `/src/__main__.py` argument parser
- [x] Add `leads_file` positional argument to autonomous subcommand
- [x] Add `--dry-run` flag
- [x] Add `--min-score` option with float validation
- [x] Add `--include-skips` flag
- [x] Add `--yes` flag for skipping confirmation

### [x] Task 6.2: Implement autonomous mode handler
- [x] Replace placeholder with actual implementation
- [x] Load settings and initialize services
- [x] Call `AutonomousService.run()`
- [x] Display progress during execution
- [x] Display final summary report

### [x] Task 6.3: Add progress display
- [x] Implement progress bar or status line updates
- [x] Show per-job outcome (submitted, skipped, failed)
- [x] Show running totals
- [x] Format final summary table

---

## Phase 7: Integration Testing

### [x] Task 7.1: Create integration test fixtures
- [x] Create sample leads file with test URLs
- [x] Create mock job pages or use stable test URLs
- [x] Set up test profile and configuration

### [x] Task 7.2: Write integration tests
- [x] Create `/tests/integration/test_autonomous.py`
- [x] Test: end-to-end dry-run with sample leads
- [x] Test: queue building with real extraction
- [x] Test: duplicate detection across runs

### [x] Task 7.3: Manual verification
- [x] Run autonomous mode with real job URLs
- [x] Verify ranking matches expected order
- [x] Verify HITL gates work correctly in batch
- [x] Verify tracker records are created correctly

---

## Phase 8: Documentation and Cleanup

### [x] Task 8.1: Update configuration documentation
- [x] Document new CLI commands in README or docs
- [x] Add example leads file format
- [x] Document environment variables if any new ones

### [x] Task 8.2: Code cleanup
- [x] Run ruff format and ruff check
- [x] Ensure all tests pass
- [x] Remove any debug code or TODOs

---

## Dependencies

- **Internal**: tracker, extractor, scoring, tailoring, runner modules (all implemented)
- **External**: None new (uses existing dependencies)

## Estimated Scope

- New files: 6 (models.py, leads.py, queue.py, runner.py, service.py, tests)
- Modified files: 2 (__main__.py, autonomous/__init__.py)
- Test files: 4 (unit tests for each component + integration)
