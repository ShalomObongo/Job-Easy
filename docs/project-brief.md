# Project Brief — Job Application Automation System (Browser Use)

> A Browser Use–powered system that helps you apply to jobs efficiently by extracting job descriptions, tailoring a resume, generating a cover letter, and completing applications in the browser—while preventing duplicate applications via a tracker and using human checkpoints for safety.

---

## 1) Summary

This project builds an end-to-end job application assistant with two operating modes:

- **Autonomous mode:** continuously collects job leads, deduplicates, ranks, and processes applications on a schedule.
- **Single-job mode:** user pastes a specific job URL and the system runs a single application attempt.

Core capabilities:
1. Open a job URL in a controlled browser session (optionally using an existing Chrome profile).
2. Extract the job description (JD) and metadata into structured JSON.
3. Score fit and decide apply/skip.
4. Tailor a resume + generate a cover letter based on the JD (truthful, evidence-based).
5. Upload the tailored resume/cover letter and fill the application form.
6. Require **human confirmation** before final submission (and for CAPTCHA/2FA/uncertainties).
7. Log everything into an **Application Tracker** so the system can detect “already applied” jobs and **prompt** whether to proceed.

---

## 2) Goals & Success Criteria

### Goals
- **Reduce time per application** without sacrificing quality.
- **Tailor documents** per job description using a reproducible pipeline.
- **Avoid duplicate applications** by maintaining a robust application log.
- **Use existing Chrome profile** to reuse sessions (e.g., logged-in job portals), with safety guidance.
- **Operate safely** with human-in-the-loop gates (doc review + submit confirmation).

### Success Criteria (measurable)
- ✅ 90%+ of runs correctly detect “already applied” when the tracker has a record (fingerprint match).
- ✅ Tailored resume/cover letter generated for every “apply” job and saved with deterministic naming.
- ✅ 80%+ of supported sites complete form fill + upload without manual intervention (excluding CAPTCHA/2FA).
- ✅ 100% of submissions require a positive user confirmation in the default configuration.
- ✅ Logs include proof artifacts (confirmation text and/or screenshot path) for every submission.

---

## 3) Non-Goals (for v1)
- Bypassing anti-bot systems (CAPTCHA solving, stealth automation). These trigger manual takeover.
- Mass “spray and pray” submissions at scale (v1 targets quality and control).
- Automatic claims fabrication or “experience invention.” Tailoring must remain truthful.

---

## 4) Users & Personas

- **Primary user (Applicant):** wants fast, targeted applications with minimal errors.
- **Power user:** comfortable configuring domains, schedules, and custom prompts.

---

## 5) Key Requirements

### Functional Requirements
1. **Mode selector**
   - Autonomous: gathers leads → queue → process repeatedly
   - Single URL: process one job end-to-end
2. **Job extraction**
   - Extract JD, company, role, location, apply method, and any job ID if present.
3. **Fit scoring**
   - Must-have matching, constraints (location/visa), seniority checks.
4. **Tailoring**
   - Keyword map + evidence map + bullet rewrites.
   - Produce tailored resume + tailored cover letter drafts.
5. **Document rendering**
   - Output PDF and/or DOCX with deterministic filenames.
6. **Application execution**
   - Navigate, fill, upload files, and reach review page.
7. **Human checkpoints**
   - Approve documents before upload.
   - Confirm before clicking the final submit button.
   - Prompt user if job already applied (duplicate detection).
8. **Application Tracker**
   - Read/write store to prevent reapplying.
   - If duplicate found: prompt “Proceed anyway?” and log override decision.
9. **Evidence capture**
   - Save submission proof (receipt ID / confirmation text / screenshots).
10. **Controlled browsing**
   - Domain allowlist and optional blocklist.

### Non-Functional Requirements
- Reliability: retries + graceful failure modes.
- Security: sensitive data handling, profile-safety guidance, minimal permissions.
- Auditability: run logs, conversation logs, and tracker entries.
- Portability: should run locally (recommended) and optionally via hosted components.

---

## 6) System Architecture

### High-level components
1. **UI / CLI**
   - Choose mode, provide job URL, confirm prompts, review drafts.
2. **Lead Collector (Autonomous mode)**
   - Sources: alerts/feeds/saved links/manual lists.
3. **Queue Manager**
   - Normalizes URLs, dedupes, ranks by fit/recency.
4. **Extractor**
   - Visits job page; extracts JD into structured JSON.
5. **Tailoring Engine**
   - Creates a tailoring plan and generates tailored resume + cover letter.
6. **Renderer**
   - Exports documents (PDF/DOCX), stores artifacts.
7. **Browser Runner (Browser Use Agent / CodeAgent)**
   - Executes the application steps using browser automation tools like `navigate`, `click`, `input`, `upload_file`, and `evaluate`.
8. **Tracker + Storage**
   - Stores application fingerprints, statuses, proof, artifact versions.
9. **Human-in-the-loop Prompter**
   - Ask user questions (duplicate override, submit confirmation, 2FA codes).

### Browser Use integration (doc-backed capabilities)
- Browser control functions available to agents include `navigate`, `click`, `input`, `upload_file`, `evaluate`, and `done`.  
  Docs: https://docs.browser-use.com/customize/code-agent/basics
- Built-in tool for page content extraction: `extract` (LLM-based extraction).  
  Docs: https://docs.browser-use.com/customize/tools/available
- Custom tools can be added via `@tools.action(...)`, including “ask human” prompts.  
  Docs: https://docs.browser-use.com/customize/tools/add
- Agent parameters support log saving and controlling file access:
  - `save_conversation_path`, `available_file_paths`, `sensitive_data`  
  Docs: https://docs.browser-use.com/customize/agent/all-parameters
- Browser parameters support using existing Chrome profiles:
  - `user_data_dir`, `profile_directory`, `storage_state`  
  Docs: https://docs.browser-use.com/customize/browser/all-parameters

---

## 7) Workflow Overview (Operational)

### A) Mode Selection
- **Autonomous mode** → collect leads → queue → process repeatedly
- **Single-job mode** → validate URL → process once

### B) Pre-flight Checks
1. Normalize URL (remove tracking params where possible).
2. Compute fingerprint (see section 8).
3. Query Tracker:
   - If found: prompt user “Already applied—proceed anyway?”
   - If not found: create tracker entry `status=in_progress`

### C) Process Job
1. Open job page.
2. Extract structured JD.
3. Fit scoring:
   - low fit → log skip
   - good fit → tailor documents
4. Generate + render tailored resume/cover letter.
5. Human review checkpoint: approve docs.

### D) Apply in Browser
1. Prepare browser session (use existing Chrome profile if enabled).
2. Fill form fields using applicant profile + Q&A bank.
3. Upload tailored files.
4. Pre-submit checkpoint: show summary; require user confirmation.
5. Submit and capture proof.
6. Update tracker status to `submitted`.

### E) Exceptions
- CAPTCHA / 2FA → pause and ask user; manual takeover if needed.
- Layout changes / element not found → fallback (re-extract, conservative actions).

---

## 8) Application Tracker & Fingerprinting

### Purpose
Prevent duplicate applications and keep an audit trail.

### Recommended store (v1)
- **SQLite** (preferred) or CSV (simpler to start)

### Fingerprint strategy
A fingerprint should survive minor URL changes:
- `canonical_url` (normalized)
- plus **job ID** if available (Greenhouse/Lever/Workday often include an ID)
- plus fallback: `(company, role title, location)` hashed

Suggested fingerprint:
- `fingerprint = hash(job_id or canonical_url or (company|title|location))`

### Tracker fields (minimum)
- `fingerprint` (primary key)
- `canonical_url`
- `source_mode` (autonomous/single)
- `company`, `role_title`, `location`
- `status` (new, in_progress, skipped, duplicate_skipped, submitted, failed)
- `first_seen_at`, `last_attempt_at`, `submitted_at`
- `resume_artifact_path`, `cover_letter_artifact_path`
- `proof_text`, `proof_screenshot_path`
- `override_duplicate` (bool) + `override_reason` (string)

### Duplicate handling requirement
If `fingerprint` exists with `status=submitted` (or equivalent):
- prompt user: **Proceed anyway?**
- record decision in tracker (`override_duplicate=true/false`)

---

## 9) Resume Tailoring & Cover Letter Generation

### Inputs
- Extracted JD JSON
- Base resume (structured or text)
- Applicant profile (skills, projects, achievements)
- Constraints: “no invented claims”, max length rules

### Tailoring Plan output
- Top keywords (10–15)
- Must-have mapping to evidence
- Bullet rewrite suggestions (2–8 bullets)
- Recommended reorder of sections (optional)
- Risk notes (anything that cannot be supported by evidence)

### Outputs
- Tailored resume (PDF/DOCX)
- Tailored cover letter (PDF/DOCX)

### Naming convention
- `Resume__{Company}__{Role}__{YYYY-MM-DD}.pdf`
- `CoverLetter__{Company}__{Role}__{YYYY-MM-DD}.pdf`

---

## 10) Using Existing Chrome Profile (Safety + Setup)

### Why
Reuses logged-in sessions, cookies, and job portal state.

### How (Browser Use parameters)
- `user_data_dir`: Chrome user data directory
- `profile_directory`: profile folder name (e.g., `Default`, `Profile 1`)
- alternative: `storage_state` for cookie/localStorage snapshot

Docs: https://docs.browser-use.com/customize/browser/all-parameters

### Safety guidance
- Close Chrome before running automation to avoid profile locks/corruption.
- Prefer copying your profile to a dedicated “automation profile” folder.
- Do not run unknown scripts on a profile containing sensitive sessions.

---

## 11) Human-in-the-loop Prompts

### Required prompts
1. Duplicate detected → “Already applied. Proceed anyway? (yes/no)”
2. Docs review → “Approve tailored resume + cover letter? (approve/edit)”
3. Final submit → “Confirm submit? (YES to submit)”
4. 2FA / email code needed → ask user for code

Implementation can use custom tools via `@tools.action(...)` and `input()` prompts.  
Docs: https://docs.browser-use.com/customize/tools/add

---

## 12) Configuration & Settings (v1)

- `MODE`: `autonomous` | `single`
- `AUTO_SUBMIT`: default `false`
- `MAX_APPLICATIONS_PER_DAY`
- `ALLOWED_DOMAINS` (allowlist)
- `PROHIBITED_DOMAINS` (blocklist)
- `USE_EXISTING_CHROME_PROFILE`: true/false
- `CHROME_USER_DATA_DIR`, `CHROME_PROFILE_DIR`
- `OUTPUT_DIR` (artifacts)
- `TRACKER_DB_PATH`
- `SAVE_CONVERSATION_PATH` (audit log)
- `AVAILABLE_FILE_PATHS` (what can be uploaded)
- `SENSITIVE_DATA` (name/email/phone, etc.)

Agent parameters supporting file/log controls are documented here:  
https://docs.browser-use.com/customize/agent/all-parameters

---

## 13) Risks, Compliance, and Ethics

- **Site Terms:** some platforms restrict automation. Default to human confirmation before submitting.
- **Anti-bot defenses:** do not attempt to bypass. Treat CAPTCHA/2FA as a manual step.
- **Privacy:** avoid storing sensitive data in plain text; limit file access to necessary artifacts only.
- **Truthfulness:** tailoring must not fabricate experience; only rephrase/reorder supported content.

---

## 14) Testing Strategy

### Unit tests
- URL normalization and fingerprinting
- Tracker read/write + duplicate detection
- Document generation templates

### Integration tests (per site family)
- Greenhouse flow
- Lever flow
- Workday flow
- “Company custom careers page” flow

### Regression tests
- DOM changes: validate extractor robustness
- Upload reliability: different file inputs
- Prompt gating: ensure auto-submit cannot happen accidentally

---

## 15) Milestones & Deliverables

### Milestone 1 — Foundations
- Tracker (SQLite) + fingerprinting + duplicate prompt
- Single-job mode end-to-end on 1 target site
- Artifact folder + naming conventions

### Milestone 2 — Tailoring
- JD extraction schema
- Tailoring plan + resume/cover letter generation
- Human review checkpoint

### Milestone 3 — Autonomous mode
- Lead collector + queue + scheduler
- Dedupe/rank + daily cap

### Milestone 4 — Hardening
- Multi-site support
- Better fallbacks (re-extract, conservative actions)
- Proof capture improvements

---

## 16) Open Questions (Decide Early)
- Tracker backend: CSV vs SQLite (recommended: SQLite)
- Supported sites for v1 (choose 1–3 to start)
- Resume format: base DOCX template vs structured JSON resume
- Auto-submit policy: always off? per-domain allowlist? per-user toggle?
- Proof capture: screenshots only, or also parse confirmation IDs?

---

## 17) Appendix — Suggested Data Schemas

### JD JSON (example)
```json
{
  "company": "ExampleCo",
  "role_title": "Frontend Intern",
  "location": "Remote",
  "employment_type": "Internship",
  "requirements_must": ["React", "JavaScript", "Git"],
  "requirements_nice": ["TypeScript", "Figma"],
  "responsibilities": ["Build UI components", "Write tests"],
  "keywords": ["React", "UI", "accessibility", "performance"],
  "apply_url": "https://..."
}
```

### Tracker record (example)
```json
{
  "fingerprint": "sha256:...",
  "canonical_url": "https://...",
  "company": "ExampleCo",
  "role_title": "Frontend Intern",
  "status": "submitted",
  "first_seen_at": "2026-01-15T10:00:00+03:00",
  "submitted_at": "2026-01-15T10:35:00+03:00",
  "resume_artifact_path": "./artifacts/Resume__ExampleCo__Frontend_Intern__2026-01-15.pdf",
  "cover_letter_artifact_path": "./artifacts/CoverLetter__ExampleCo__Frontend_Intern__2026-01-15.pdf",
  "proof_text": "Application received. Confirmation #ABC123",
  "proof_screenshot_path": "./artifacts/proof__ABC123.png",
  "override_duplicate": false,
  "override_reason": ""
}
```
