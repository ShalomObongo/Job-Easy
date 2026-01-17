# Implementation Plan: Dynamic Application Runner (Any Job Link)

> Track ID: track_20260116_174354
> Methodology: Test-Driven Development (TDD)

---

## Overview

Implement a best-effort, dynamic application runner that can start from arbitrary job-related URLs
and progress through application flows with strict human checkpoints and audit logging.

This track focuses on:
- a generic runner Agent using `output_model_schema` → `history.structured_output`
- a reusable HITL tool library (yes/no, free text, YES-to-submit, OTP)
- Q&A bank persistence for unknown questions
- blocklist-first domain policy (stop only on prohibited domains)
- wiring into the existing CLI and pipeline modules (tracker/extractor/scoring/tailoring)

---

## Phase 1: Runner Contracts (Models + Result Schema)

### Task 1.1: Write tests - runner result models
- [x] Test: ApplicationRunResult schema validates required fields
- [x] Test: Runner step summaries serialize to JSON
- [x] Test: Proof capture fields are optional but typed

### Task 1.2: Implement runner result models
- [x] Create `/src/runner/models.py` (Pydantic models)
- [x] Define `ApplicationRunResult` with status, urls visited, proof fields, and errors
- [x] Add `to_dict()` / `save_json()` helpers for artifacts

### [x] Task 1.3: Conductor - User Manual Verification 'Phase 1: Runner Contracts' (Protocol in workflow.md)

---

## Phase 2: HITL Tools (Prompts + Confirmation Gates)

### Task 2.1: Write tests - HITL prompt helpers
- [x] Test: yes/no prompt parsing (case/whitespace tolerant)
- [x] Test: YES-to-submit requires exact confirmation string
- [x] Test: OTP prompt returns raw string without logging secrets

### Task 2.2: Implement HITL tool library
- [x] Create `/src/hitl/tools.py`
- [x] Implement Browser Use custom tools via `@tools.action`:
  - [x] ask_yes_no(question) -> str ("yes" | "no")
  - [x] ask_free_text(question) -> str
  - [x] confirm_submit(prompt) -> str ("confirmed" | "cancelled") (requires "YES")
  - [x] ask_otp_code(prompt) -> str
- [x] Ensure tools are reusable by runner and tracker duplicate gates

### [x] Task 2.3: Conductor - User Manual Verification 'Phase 2: HITL Tools' (Protocol in workflow.md)

---

## Phase 3: Q&A Bank (Learning Unknown Questions)

### Task 3.1: Write tests - Q&A bank storage
- [x] Test: loads empty bank when file missing
- [x] Test: persists new Q&A entries deterministically
- [x] Test: question normalization and lookup

### Task 3.2: Implement Q&A bank
- [x] Create `/src/runner/qa_bank.py`
- [x] Implement `QABank` load/save (JSON)
- [x] Implement `get_answer(question, context)` with normalization
- [x] Implement `record_answer(question, answer, context)` for persistence

### [x] Task 3.3: Conductor - User Manual Verification 'Phase 3: Q&A Bank' (Protocol in workflow.md)

---

## Phase 4: Domain Policy (Blocklist-First + Allowlist Log)

### Task 4.1: Write tests - prohibited domain enforcement
- [x] Test: navigation is blocked when domain matches prohibited list
- [x] Test: non-prohibited domains are permitted
- [x] Test: allowlist log is appended when encountering new domains

### Task 4.2: Implement domain policy utilities
- [x] Create `/src/runner/domains.py`
- [x] Implement `is_prohibited(url, prohibited_domains)` and pattern handling
- [x] Implement allowlist log writer (append-only) for domains seen
- [x] Ensure runner uses browser `prohibited_domains` and does not set `allowed_domains` by default

### [x] Task 4.3: Conductor - User Manual Verification 'Phase 4: Domain Policy' (Protocol in workflow.md)

---

## Phase 5: Runner Agent (Generic Form-Filling + Uploads)

### Task 5.1: Write tests - agent factory wiring (mocked)
- [x] Test: creates Agent with tools registry and `output_model_schema`
- [x] Test: agent is configured for batching (`max_actions_per_step`) and retries (`max_failures`)
- [x] Test: passes `available_file_paths` limited to generated artifacts
- [x] Test: sets `save_conversation_path` per run

### Task 5.2: Implement runner agent factory
- [x] Create `/src/runner/agent.py`
- [x] Implement `create_browser(settings)` honoring Chrome profile reuse
- [x] Implement `create_application_agent(context, browser, llm, settings)`
- [x] Task prompt includes:
  - detect flow type (apply button vs direct form)
  - iterate through steps/modals
  - ask-human for unknown questions, then persist to Q&A bank
  - stop at final submit and call confirmation tool
  - capture proof after submit

### [x] Task 5.3: Conductor - User Manual Verification 'Phase 5: Runner Agent' (Protocol in workflow.md)

---

## Phase 6: Orchestration (Tracker → Extract → Score → Tailor → Apply)

### Task 6.1: Write tests - single-job pipeline (mocked components)
- [x] Test: duplicate found triggers prompt and override logging
- [x] Test: skip decision updates tracker and exits before applying
- [x] Test: apply decision generates artifacts then calls runner
- [x] Test: submission updates tracker with proof + artifact paths

### Task 6.2: Implement single-job pipeline service
- [x] Create `/src/runner/service.py`
- [x] Wire: TrackerService, JobExtractor, FitScoringService, TailoringService
- [x] Construct per-run artifact folder under `artifacts/runs/<fingerprint>/`
- [x] Configure agent with:
  - `available_file_paths` = [resume_pdf, cover_letter_pdf]
  - `save_conversation_path` in run folder
- [x] Handle CAPTCHA/2FA by pausing and requesting manual action (no bypass)

### [x] Task 6.3: Conductor - User Manual Verification 'Phase 6: Orchestration' (Protocol in workflow.md)

---

## Phase 7: CLI Wiring + Integration Test Stubs

### Task 7.1: Write tests - CLI single mode wiring
- [x] Test: `python -m src single <url>` calls pipeline service
- [x] Test: missing URL errors cleanly

### Task 7.2: Implement CLI wiring
- [x] Update `/src/__main__.py` to call the pipeline service for `single`
- [x] Print concise summary from structured output

### Task 7.3: Add integration test stubs (non-network)
- [x] Add `/tests/integration/runner/` with stubs and safety assertions
- [x] Provide manual test checklist doc (links + expected outcomes)

### [x] Task 7.4: Conductor - User Manual Verification 'Phase 7: CLI + Stubs' (Protocol in workflow.md)

---

## Phase 8: Verification

### Task 8.1: Code quality checks
- [x] Run `ruff check .`
- [x] Run `ruff format --check .`
- [x] Run `pytest -m "not integration"`

### Task 8.2: Manual verification
- [x] Run against at least 2 distinct flows (apply button → multi-step, direct form)
- [x] Verify explicit "YES" gate prevents accidental submission
- [x] Verify prohibited domain blocks navigation
- [x] Verify artifacts and logs saved under `artifacts/runs/<fingerprint>/`

### [x] Task 8.3: Conductor - User Manual Verification 'Phase 8: Verification' (Protocol in workflow.md)
