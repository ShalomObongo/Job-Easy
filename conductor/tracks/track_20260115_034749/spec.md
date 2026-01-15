# Track Specification: Application Tracker

> Track ID: track_20260115_034749
> Type: Feature
> Priority: High
> Status: Pending

---

## Overview

Implement the core Application Tracker system that prevents duplicate job applications by maintaining a SQLite database of all application attempts. The tracker uses a cascading fingerprint strategy to identify jobs and provides CRUD operations for managing application records.

---

## Functional Requirements

### 1. Database Schema & Models
- SQLite database with async operations (aiosqlite)
- TrackerRecord model with fields:
  - `fingerprint` (primary key, string)
  - `canonical_url` (string)
  - `source_mode` (enum: single/autonomous)
  - `company` (string)
  - `role_title` (string)
  - `location` (string, nullable)
  - `status` (enum: new, in_progress, skipped, duplicate_skipped, submitted, failed)
  - `first_seen_at` (datetime)
  - `last_attempt_at` (datetime, nullable)
  - `submitted_at` (datetime, nullable)
  - `resume_artifact_path` (string, nullable)
  - `cover_letter_artifact_path` (string, nullable)
  - `proof_text` (string, nullable)
  - `proof_screenshot_path` (string, nullable)
  - `override_duplicate` (boolean, default false)
  - `override_reason` (string, nullable)

### 2. Fingerprint Generation
- URL normalization: remove tracking params, normalize scheme
- Job ID extraction: detect IDs from Greenhouse, Lever, Workday URLs
- Cascading fingerprint strategy:
  1. If job_id available: `hash(job_id)`
  2. Else if canonical_url available: `hash(canonical_url)`
  3. Else: `hash(company|role_title|location)`
- Use SHA-256 for hashing

### 3. CRUD Operations
- `create_record(data)`: Insert new application record
- `get_by_fingerprint(fingerprint)`: Retrieve record by fingerprint
- `get_by_url(url)`: Retrieve record by URL (computes fingerprint)
- `update_status(fingerprint, status)`: Update application status
- `update_proof(fingerprint, proof_text, screenshot_path)`: Add submission proof
- `list_recent(limit, status_filter)`: List recent applications

### 4. Duplicate Detection
- `check_duplicate(url, company, role, location)`: Check if already applied
- Returns: `None` if no duplicate, or `TrackerRecord` if exists
- Supports override: record when user proceeds despite duplicate

---

## Non-Functional Requirements

- Async operations for non-blocking I/O
- Thread-safe database access
- Automatic database initialization on first use
- Database migrations support for schema changes
- Configurable database path via Settings

---

## Acceptance Criteria

- [ ] Database initializes automatically when tracker is first used
- [ ] Fingerprint is stable: same job produces same fingerprint
- [ ] URL normalization handles common tracking parameters
- [ ] Job ID extraction works for Greenhouse, Lever, Workday
- [ ] Duplicate detection returns existing record when fingerprint matches
- [ ] All CRUD operations work correctly with async/await
- [ ] Status transitions are logged with timestamps
- [ ] All operations have corresponding unit tests
- [ ] Integration test verifies SQLite persistence

---

## Out of Scope

- Web UI for viewing tracker records (v2)
- Export functionality (CSV, JSON) (v2)
- Statistics and analytics (v2)
- Multi-user support
