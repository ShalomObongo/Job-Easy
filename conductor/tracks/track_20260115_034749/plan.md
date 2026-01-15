# Implementation Plan: Application Tracker

> Track ID: track_20260115_034749
> Last Updated: 2026-01-15

---

## Overview

Implement the Application Tracker system with SQLite storage and cascading fingerprint strategy. Following TDD methodology, tests are written before implementation for each component.

---

## Phase 1: Data Models & Schema ✅

### Task 1.1: Write Model Tests
- [x] Test: TrackerRecord dataclass has all required fields
- [x] Test: ApplicationStatus enum has correct values
- [x] Test: SourceMode enum has correct values
- [x] Test: TrackerRecord serializes to dict correctly

### Task 1.2: Implement Data Models
- [x] Create `/src/tracker/models.py`
- [x] Define ApplicationStatus enum
- [x] Define SourceMode enum
- [x] Define TrackerRecord dataclass with all fields
- [x] Add serialization/deserialization methods

---

## Phase 2: Fingerprint Generation ✅

### Task 2.1: Write URL Normalization Tests
- [x] Test: Removes tracking parameters (utm_*, ref, etc.)
- [x] Test: Normalizes scheme to https
- [x] Test: Handles trailing slashes consistently
- [x] Test: Handles query parameter ordering

### Task 2.2: Implement URL Normalization
- [x] Create `/src/tracker/fingerprint.py`
- [x] Implement `normalize_url(url)` function
- [x] Handle common tracking parameter patterns

### Task 2.3: Write Job ID Extraction Tests
- [x] Test: Extracts ID from Greenhouse URLs
- [x] Test: Extracts ID from Lever URLs
- [x] Test: Extracts ID from Workday URLs
- [x] Test: Returns None for unknown URL patterns

### Task 2.4: Implement Job ID Extraction
- [x] Implement `extract_job_id(url)` function
- [x] Add regex patterns for Greenhouse, Lever, Workday

### Task 2.5: Write Fingerprint Computation Tests
- [x] Test: Uses job_id when available
- [x] Test: Falls back to canonical_url
- [x] Test: Falls back to company|role|location hash
- [x] Test: Fingerprint is deterministic (same input = same output)

### Task 2.6: Implement Fingerprint Computation
- [x] Implement `compute_fingerprint(url, job_id, company, role, location)` function
- [x] Use SHA-256 for hashing
- [x] Implement cascading strategy

---

## Phase 3: Database Layer ✅

### Task 3.1: Write Database Initialization Tests
- [x] Test: Creates database file if not exists
- [x] Test: Creates tracker table with correct schema
- [x] Test: Handles existing database gracefully

### Task 3.2: Implement Database Initialization
- [x] Create `/src/tracker/repository.py`
- [x] Implement `TrackerRepository` class
- [x] Implement async `initialize()` method
- [x] Define SQL schema for tracker table

### Task 3.3: Write CRUD Operation Tests
- [x] Test: insert_record creates new record
- [x] Test: insert_record fails on duplicate fingerprint
- [x] Test: get_by_fingerprint returns correct record
- [x] Test: get_by_fingerprint returns None if not found
- [x] Test: update_status changes status and updates timestamp
- [x] Test: update_proof sets proof fields

### Task 3.4: Implement CRUD Operations
- [x] Implement `insert_record(record: TrackerRecord)` method
- [x] Implement `get_by_fingerprint(fingerprint: str)` method
- [x] Implement `get_by_url(url: str)` method
- [x] Implement `update_status(fingerprint, status)` method
- [x] Implement `update_proof(fingerprint, proof_text, screenshot_path)` method
- [x] Implement `list_recent(limit, status_filter)` method

---

## Phase 4: Duplicate Detection Service ✅

### Task 4.1: Write Duplicate Detection Tests
- [x] Test: Returns None when no duplicate exists
- [x] Test: Returns TrackerRecord when duplicate found
- [x] Test: Detects duplicates by URL
- [x] Test: Detects duplicates by company+role+location

### Task 4.2: Implement Duplicate Detection
- [x] Create `/src/tracker/service.py`
- [x] Implement `TrackerService` class
- [x] Implement `check_duplicate(url, company, role, location)` method
- [x] Integrate fingerprint computation with repository lookup

### Task 4.3: Write Override Recording Tests
- [x] Test: Records override decision correctly
- [x] Test: Stores override reason

### Task 4.4: Implement Override Recording
- [x] Implement `record_override(fingerprint, reason)` method

---

## Phase 5: Integration & Module Export ✅

### Task 5.1: Integration Tests
- [x] Test: Full workflow - create, check duplicate, update status
- [x] Test: Database persists between sessions
- [x] Test: Concurrent access handling

### Task 5.2: Module Export
- [x] Update `/src/tracker/__init__.py` with public API
- [x] Export TrackerService, TrackerRecord, ApplicationStatus

---

## Phase 6: Verification ✅

### Task 6.1: Code Quality Checks
- [x] Run `ruff check .` - all passes
- [x] Run `ruff format --check .` - all formatted
- [x] Run `pytest` - all tests pass (60 tests)
- [x] Run `pytest --cov` - coverage 78% (tracker module 90%+, main entry point excluded)

### Task 6.2: Manual Verification
- [x] Tracker initializes database correctly
- [x] Fingerprints are consistent
- [x] Duplicate detection works as expected

---

## Dependencies

- Project Scaffolding (track_20260115_032209) ✅

---

## Artifacts

After completion:
- `/src/tracker/models.py` - Data models
- `/src/tracker/fingerprint.py` - URL normalization and fingerprint generation
- `/src/tracker/repository.py` - Database layer
- `/src/tracker/service.py` - Business logic
- `/tests/unit/tracker/` - Unit tests
- `/tests/integration/tracker/` - Integration tests
