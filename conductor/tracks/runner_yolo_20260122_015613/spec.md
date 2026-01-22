# Track Spec: Runner YOLO Mode (Auto-Answer With Job + Profile Context)

## Overview
Add an opt-in "yolo mode" used by the application runner in both single-job and autonomous modes. The goal is for the runner agent to automatically answer application questions using only the available job details (`jd.json`) and user details (`profile.yaml`), without prompting the user for normal questions.

In yolo mode, when the system is not confident, it should still answer best-effort.

This system must remain truthful: it can rephrase, infer from explicit inputs, and choose safe defaults, but must not fabricate experience, credentials, or personal facts.

## Goals
- Reduce/near-eliminate interactive prompts during application runs (except safety gates like final submit, OTP/CAPTCHA handling).
- Improve answer quality by providing the agent full job + user context rather than only small `sensitive_data`.
- Prevent brittle reuse of saved answers across different companies/roles by making persistence context-aware.

## Functional Requirements

### FR1: Provide Runner Agent With Job + User Context
When yolo mode is enabled, the runner agent must receive:
- A "hybrid" context payload derived from:
  - `jd.json` (job/company/role/location/apply_url, requirements, responsibilities, plus full JD text when available).
  - `profile.yaml` (full user profile details used elsewhere in the pipeline).
- The payload should include both:
  - Compact structured fields for retrieval (skills, work history, preferences).
  - Selected raw fields for generation (notably full job description text).

Notes:
- In single mode, this context comes from the extracted JobDescription + loaded profile.
- In autonomous mode, this context comes from the queued job + loaded profile.
- The runner should still receive `available_file_paths` (documents) and `sensitive_data` (PII fields), but yolo mode should not be limited to those.

### FR2: YOLO Answer Resolver
Implement a yolo answer resolver used by the runner when it needs to fill a form question. It must:
- Accept the question prompt and any field metadata available at runtime:
  - label/prompt text, field type (text/select/radio/checkbox/textarea), and options list (when present).
- Produce a best-effort answer derived from job + user context, including:
  - Basic contact info
  - Eligibility (work auth, sponsorship, relocation, start date)
  - Experience & skills (years, tools, projects)
  - Compensation (salary expectations) using profile preferences when present
  - Motivation prompts (company/role-specific responses grounded in JD + user experience)
  - EEO/demographics (select safe defaults like "Prefer not to say" when available)

Truthfulness constraints:
- Must not invent employers, titles, dates, degrees, certifications, immigration status, or achievements not present in the profile.
- If a question cannot be answered from context, it should still respond best-effort using safe placeholders/options (e.g., "Prefer not to say", "N/A", "Other", "0") depending on field type and available choices.

### FR3: Integration With Existing Q&A Bank
Update the runner question-answer flow to support:
- Using existing Q&A bank answers when they are safe and context-appropriate.
- Falling back to yolo answer generation when no safe saved answer exists.

### FR4: Context-Aware Persistence (Avoid Wrong Reuse)
The system must solve the "saved answer reused in the wrong company" problem by changing persistence semantics:
- Store Q&A entries with scoping metadata, e.g.:
  - global: safe across companies (e.g., name, phone, sponsorship)
  - company-scoped: only reusable for the same company
  - job-scoped: only reusable for the same job fingerprint / URL
  - domain/ATS-scoped: reusable within the same job board/ATS when appropriate
- Motivation prompts (e.g., "Why do you want to work here?") must not be saved as a single global raw answer. Instead:
  - Either do not reuse them across companies by default (company/job-scoped), OR
  - Persist a "generation strategy" marker (regenerate per job) rather than the literal answer.

### FR5: Configuration / Enablement
- Yolo mode must be opt-in via a configuration flag (env and/or CLI), default off.
- When disabled, current behavior remains (Q&A bank + interactive prompt fallback).

## Non-Functional Requirements
- Deterministic + auditable: saved answers should record provenance (auto-generated vs user-provided) and scope.
- Safety: preserve existing "YES to submit" requirement; do not reduce safety gates.
- Maintainable: keep runner module boundaries; add tests for core logic.

## Acceptance Criteria
- When enabled, runner can answer common questions without prompting the user in both `single` and `autonomous` flows.
- Runner agent receives job + user context payload (hybrid) and uses it when answering questions.
- Motivation prompts are generated in a company/job-specific way (not reused incorrectly across companies).
- Q&A bank persistence prevents cross-company leakage of company-specific answers.
- Unit tests cover:
  - scoping rules and lookup precedence
  - persistence rules for motivation questions
  - answer selection for select/radio/checkbox with "Prefer not to say"/"Other"
- No change removes the final-submit confirmation gate.

## Out of Scope
- CAPTCHA solving / 2FA bypass.
- Building a large retrieval database beyond `profile.yaml` + `jd.json`.
- Perfect correctness for every custom employer form; this is best-effort automation.
