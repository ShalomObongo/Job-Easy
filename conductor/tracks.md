# Conductor Tracks

> All features, bugs, and chores for the Job-Easy project

---

## Active Tracks

### [track_20260115_190146] Fit Scoring
- **Type**: Feature
- **Priority**: High
- **Status**: Pending
- **Created**: 2026-01-15
- **Epic Reference**: E2-S3, E2-S4
- **Spec**: [spec.md](./tracks/track_20260115_190146/spec.md)
- **Plan**: [plan.md](./tracks/track_20260115_190146/plan.md)

Implement fit scoring system with user profile management, weighted scoring algorithm, and constraint checking (location, visa, experience, salary) for apply/skip/review recommendations.

**Deliverables:**
- `/src/scoring/models.py` - UserProfile, FitScore, ConstraintResult, FitResult models
- `/src/scoring/config.py` - ScoringConfig settings
- `/src/scoring/profile.py` - ProfileService for loading profiles
- `/src/scoring/service.py` - FitScoringService main class
- `/src/scoring/matchers.py` - Skill matching utilities
- `/profiles/profile.example.yaml` - Example profile template
- Unit tests + integration tests

---

## Completed Tracks

### [track_20260115_044908] Job Extractor ✅
- **Type**: Feature
- **Priority**: High
- **Status**: Completed
- **Completed**: 2026-01-15
- **Epic Reference**: E2-S1, E2-S2
- **Spec**: [spec.md](./tracks/track_20260115_044908/spec.md)
- **Plan**: [plan.md](./tracks/track_20260115_044908/plan.md)

Extract structured job description data from job posting URLs using Browser Use with LLM-based extraction and Pydantic schema validation.

**Deliverables:**
- `/src/extractor/models.py` - JobDescription Pydantic model
- `/src/extractor/config.py` - ExtractorConfig settings
- `/src/extractor/service.py` - JobExtractor service
- `/src/extractor/agent.py` - Browser Use agent factory
- `/src/extractor/__init__.py` - Public API exports
- 40 unit tests + 5 integration test stubs (100 total tests passing)

### [track_20260115_034749] Application Tracker ✅
- **Type**: Feature
- **Priority**: High
- **Status**: Completed
- **Completed**: 2026-01-15
- **Spec**: [spec.md](./tracks/track_20260115_034749/spec.md)
- **Plan**: [plan.md](./tracks/track_20260115_034749/plan.md)

Implement the core Application Tracker system with SQLite storage, fingerprinting, and duplicate detection.

**Deliverables:**
- `/src/tracker/models.py` - Data models (TrackerRecord, ApplicationStatus, SourceMode)
- `/src/tracker/fingerprint.py` - URL normalization and fingerprint generation
- `/src/tracker/repository.py` - Async SQLite database layer
- `/src/tracker/service.py` - Business logic for duplicate detection
- 44 unit tests + 4 integration tests (60 total tests passing)

### [track_20260115_032209] Project Scaffolding ✅
- **Type**: Feature
- **Priority**: High
- **Status**: Completed
- **Completed**: 2026-01-15
- **Spec**: [spec.md](./tracks/track_20260115_032209/spec.md)
- **Plan**: [plan.md](./tracks/track_20260115_032209/plan.md)

Set up the foundational project structure including directory layout, Python package configuration, development tooling, and configuration system.

**Deliverables:**
- Complete `/src/` directory structure with all modules
- Complete `/tests/` directory with unit test framework
- `pyproject.toml` with dependencies and tool configuration
- Configuration system with pydantic-settings
- Logging utility with configurable levels
- CLI entry point with mode selection

---

## Archived Tracks

*No archived tracks.*
