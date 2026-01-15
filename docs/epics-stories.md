# Epics & Stories — Job Application Automation System

> Date: 2026-01-15  
> This document breaks the project into **epics** and **user stories**, with acceptance criteria and sprint mapping.

---

## 0) Definition of Done (global)

A story is “Done” when:
- ✅ Feature works end-to-end on at least **one target job board** (or a mocked page when noted)
- ✅ Has basic error handling (clear failure reason + logged)
- ✅ Writes/reads required artifacts (tracker record, documents, proof as applicable)
- ✅ Includes a minimal test (unit test or integration test) where practical
- ✅ Does not violate system safety rules:
  - No automated submission without explicit confirmation (default)
  - No CAPTCHA/2FA bypass; must request user help instead

---

## 1) Epics overview

| Epic ID | Epic | Outcome | Depends on |
|---|---|---|---|
| E0 | Foundations & Architecture | Repo, config, CI, baseline “hello agent” run | — |
| E1 | Application Tracker & Duplicate Guard | Never reapply silently; prompt user on duplicates | E0 |
| E2 | Job Extraction & Fit Scoring | Structured JD JSON + apply/skip decision | E0 |
| E3 | Tailoring & Document Generation | Tailored resume + cover letter artifacts | E2 (schema), can start with mock |
| E4 | Application Runner (Browser Use) | Fill + upload + pre-submit checkpoint on 1 site | E0, E1 (log), E3 (docs) |
| E5 | Browser Session & Safety Rails | Chrome profile reuse, allowed/prohibited domains, downloads | E0 |
| E6 | Human-in-the-loop Tools & Audit Logs | Prompts, sensitive data handling, saved conversation logs | E0 |
| E7 | Autonomous Mode (Queue + Scheduler) | Continuous runs with caps + ranking | E1, E2 |
| E8 | Multi-site Support & Test Harness | Site adapters + regression tests | E4 baseline |
| E9 | Hardening & Performance | Vision tuning, extraction LLM split, scaling with CodeAgent | E2, E4, E6 |

---

## 2) Epics and stories (detailed)

### E0 — Foundations & Architecture
**Goal:** Create a runnable baseline and enforce project conventions.

- **E0-S1: Repo scaffold + environment**
  - Acceptance:
    - Project runs locally with a single command
    - Environment variables documented
    - Basic lint/test step runs in CI
  - Sprint: S0

- **E0-S2: Browser Use “hello world” harness**
  - Acceptance:
    - Can launch browser in non-headless mode
    - Can navigate to a URL and extract page title using Browser Use primitives
  - Sprint: S0

- **E0-S3: Config system**
  - Acceptance:
    - Single config file/env mapping for: allowed domains, output dirs, tracker path, chrome profile flags
  - Sprint: S0

---

### E1 — Application Tracker & Duplicate Guard
**Goal:** Maintain an application ledger so we prevent accidental reapplication.

- **E1-S1: URL canonicalization**
  - Acceptance:
    - Normalizes URLs consistently (removes known tracking params, resolves redirects when possible)
  - Sprint: S1

- **E1-S2: Fingerprinting**
  - Acceptance:
    - Computes fingerprint from job ID if present; else canonical URL; else company+title+location hash
    - Unit tests cover stable fingerprints for common cases
  - Sprint: S1

- **E1-S3: Tracker storage (SQLite preferred)**
  - Acceptance:
    - Create/read/update tracker entries
    - Supports statuses: new, in_progress, skipped, duplicate_skipped, submitted, failed
  - Sprint: S1

- **E1-S4: Duplicate prompt gate**
  - Acceptance:
    - If tracker indicates submitted: prompt user “Proceed anyway?”
    - Decision is stored (override flags + reason)
  - Sprint: S1 (uses E6 ask-human tool)

---

### E2 — Job Extraction & Fit Scoring
**Goal:** Extract JD and decide apply vs skip.

- **E2-S1: JD extraction schema**
  - Acceptance:
    - Schema includes company/title/location/apply_url/requirements/responsibilities/keywords/job_id (if found)
  - Sprint: S2

- **E2-S2: JD extractor (Browser Use)**
  - Acceptance:
    - Produces JD JSON for at least one real job posting page
    - Stores jd.json artifact linked to tracker record
  - Sprint: S2

- **E2-S3: Fit scoring rules**
  - Acceptance:
    - Computes a score + reasons list (must-have missing, constraint triggered, etc.)
    - Configurable thresholds (auto-skip vs apply)
  - Sprint: S2

- **E2-S4: Constraint checks**
  - Acceptance:
    - Flags location/visa/seniority mismatches if user sets constraints
  - Sprint: S2

---

### E3 — Tailoring & Document Generation
**Goal:** Tailor resume and cover letter per JD and render files.

- **E3-S1: Tailoring plan generator**
  - Acceptance:
    - Outputs keyword map + evidence mapping + bullet rewrite suggestions
    - Must not invent experience; adds “unsupported claim” warnings
  - Sprint: S3 (can start with mock JD)

- **E3-S2: Resume tailoring**
  - Acceptance:
    - Produces tailored resume text/structure and renders PDF/DOCX
    - Deterministic naming convention per job
  - Sprint: S3

- **E3-S3: Cover letter generator**
  - Acceptance:
    - Generates 1-2 page cover letter aligned to JD top themes
    - Renders PDF/DOCX
  - Sprint: S3

- **E3-S4: Doc review packet**
  - Acceptance:
    - Produces a “review summary” (key changes + keywords + files)
    - Ready to show user before upload
  - Sprint: S3

---

### E4 — Application Runner (Browser Use)
**Goal:** Complete applications in the browser with checkpoints.

- **E4-S1: Site adapter v1 (choose 1: Greenhouse/Lever/Workday)**
  - Acceptance:
    - Reaches apply form, fills at least core fields, and uploads docs
  - Sprint: S4

- **E4-S2: Q&A bank integration**
  - Acceptance:
    - Screening questions are answered from a stored Q&A bank
    - Unknown questions trigger ask-human prompt
  - Sprint: S4

- **E4-S3: Pre-submit checkpoint (default required)**
  - Acceptance:
    - Agent stops before final submit, shows summary, requires “YES” to submit
  - Sprint: S4 (uses E6 tools)

- **E4-S4: Proof capture**
  - Acceptance:
    - Captures confirmation text and optionally screenshot path
    - Updates tracker to submitted with proof fields
  - Sprint: S4/S6

---

### E5 — Browser Session & Safety Rails
**Goal:** Safe browser operation with real profiles and navigation guards.

- **E5-S1: Existing Chrome profile support**
  - Acceptance:
    - Supports `user_data_dir` + `profile_directory` config
    - Detects/handles “profile locked” scenario with clear user message
  - Sprint: S5

- **E5-S2: Domain allowlist/blocklist**
  - Acceptance:
    - `allowed_domains` restricts navigation; `prohibited_domains` blocks risky domains
    - Tests validate pattern matching rules
  - Sprint: S5

- **E5-S3: Download handling**
  - Acceptance:
    - Configures downloads_path per job run
    - Handles PDF download behavior (if job portal emits PDFs)
  - Sprint: S5

---

### E6 — Human-in-the-loop Tools & Audit Logs
**Goal:** Prompting, sensitive handling, and audit trails.

- **E6-S1: Ask-human tool library**
  - Acceptance:
    - Shared tool supports: yes/no prompts, free text, OTP code entry
  - Sprint: S6

- **E6-S2: Sensitive data vault integration**
  - Acceptance:
    - PII kept in `sensitive_data` (not scattered in prompts/logs)
  - Sprint: S6

- **E6-S3: File access constraints**
  - Acceptance:
    - Only generated resume/cover letter paths appear in `available_file_paths`
    - Agent cannot upload arbitrary files
  - Sprint: S6

- **E6-S4: Run log saving**
  - Acceptance:
    - Saves conversation/run logs per job using configured path
  - Sprint: S6

---

### E7 — Autonomous Mode (Queue + Scheduler)
**Goal:** Run continuously with safety caps.

- **E7-S1: Lead intake adapters**
  - Acceptance:
    - At least one source supported (manual list file, RSS, etc.)
  - Sprint: S7

- **E7-S2: Queue manager**
  - Acceptance:
    - Dedupe by fingerprint/canonical URL, prioritize by score/recency
    - Respects max applications per day
  - Sprint: S7

- **E7-S3: Scheduler**
  - Acceptance:
    - Runs at configured cadence; supports “dry run” mode
  - Sprint: S7

---

### E8 — Multi-site Support & Test Harness
**Goal:** Scale beyond one job board safely.

- **E8-S1: Second site adapter**
  - Acceptance:
    - Successfully applies through second job site with same checkpoints
  - Sprint: S8

- **E8-S2: Integration test harness**
  - Acceptance:
    - Record/replay flows or use stable test pages
    - Regression tests for extractor + runner
  - Sprint: S8

- **E8-S3: “Layout changed” fallback improvements**
  - Acceptance:
    - Recovery playbook: re-extract, try alternative selectors, then ask user
  - Sprint: S8/S9

---

### E9 — Hardening & Performance
**Goal:** Make it robust and efficient in autonomous mode.

- **E9-S1: Vision/extraction tuning**
  - Acceptance:
    - Proper defaults for `use_vision` and detail level
    - Separate `page_extraction_llm` configured for extraction-heavy runs
  - Sprint: S9

- **E9-S2: CodeAgent scaling for lead processing**
  - Acceptance:
    - Can process 100+ job links reliably with reusable code functions
  - Sprint: S9

- **E9-S3: Fast mode experiments**
  - Acceptance:
    - Optional `flash_mode` configuration gated by stability tests
  - Sprint: S9

---

## 3) Sprint mapping (summary)

| Sprint | Focus | Epics covered |
|---|---|---|
| S0 | Foundations | E0 |
| S1 | Tracker + duplicate gate | E1 (+E6-S1 stub) |
| S2 | JD extraction + fit scoring | E2 |
| S3 | Tailoring + doc generation | E3 |
| S4 | Application runner v1 + proof | E4 |
| S5 | Chrome profile + safety rails | E5 |
| S6 | HITL tools + audit logs + sensitive data | E6 |
| S7 | Autonomous mode queue + scheduler | E7 |
| S8 | Multi-site + tests | E8 |
| S9 | Hardening + performance | E9 |

