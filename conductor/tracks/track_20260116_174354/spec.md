# Track Specification: Dynamic Application Runner (Any Job Link)

> Track ID: track_20260116_174354
> Type: Feature
> Priority: High
> Epic Reference: E4 (Runner) + E6 (HITL) + E5 (Domain policy)

---

## Overview

Build a **dynamic, best-effort application runner** that can start from **any job-related link**:
- a job posting page with an “Apply” button leading to multi-step flows (pages/modals), or
- a direct application form page with a submit button at the bottom, or
- other common variants (external redirects, embedded iframes, etc.).

The runner uses a **Browser Use `Agent`** (similar to the JD extractor pattern) and returns a
structured result via `output_model_schema` (`history.structured_output`).

Safety rules are non-negotiable:
- **Never submit without explicit user “YES”.**
- **No CAPTCHA/2FA bypass**; request manual takeover.

---

## Functional Requirements

### FR-1: Single-job orchestration (CLI entry)
`python -m src single <url>` runs an end-to-end pipeline:
1. Tracker duplicate check (prompt + override logging if previously submitted)
2. Navigate + infer flow type (posting vs direct form vs other)
3. Extract required context needed for application (company/title where possible)
4. Fit scoring (apply/skip/review)
5. Tailoring (resume + cover letter artifacts)
6. Doc review prompt (approve/edit loop)
7. Application runner executes browser flow up to final submit gate
8. If user types “YES”, submit and capture proof
9. Update tracker with status + proof + artifact paths

### FR-2: Dynamic flow handling (multi-step forms)
Runner must be able to:
- click “Apply” when present (or detect “Continue/Next/Submit” flow on direct forms)
- iterate across multi-page/multi-modal flows
- fill detected required fields
- upload tailored files
- handle unknown questions via ask-human prompt and persist answers to a Q&A bank

### FR-3: HITL tool library
Provide reusable prompts via Browser Use custom tools (`@tools.action`) backed by `input()`:
- yes/no prompts
- free-text prompts
- “Type YES to confirm submit”
- OTP/2FA code prompt (manual only; no extraction)

### FR-4: Q&A bank (learning)
- Store Q&A entries in a local file (JSON/YAML).
- On new question: ask human, then persist mapping for reuse.
- Include minimal normalization for question matching (text cleanup + optional page context hints).

### FR-5: Domain policy (blocklist-first)
- Runner must **stop only** if navigation target domain matches `prohibited_domains`.
- If the domain is not prohibited, it is allowed, and should be **auto-added to a persisted allowlist
  log** for future reference (not used to block by default).

### FR-6: Upload constraints + sensitive data
- Use `available_file_paths` so the agent can only upload the generated resume/cover letter
  artifacts.
- Use `sensitive_data` for applicant PII (avoid scattering in prompts/logs).

### FR-7: Audit logs + proof capture
- Save agent conversation history to a per-run path (`save_conversation_path`).
- Capture proof after submit: confirmation text and optional screenshot path.

---

## Non-Functional Requirements

- Reliability: configure retries (`max_failures`), step timeouts, and batching
  (`max_actions_per_step`) for form filling.
- Transparency: produce a structured run summary for the CLI.
- Safety: explicit “YES” gate; no CAPTCHA/2FA bypass; truthful documents only.

---

## Acceptance Criteria

- Works on a variety of application flows in best-effort mode:
  - job posting → apply → multi-step forms
  - direct form → submit gate
- Unknown questions trigger ask-human and are saved to Q&A bank.
- Submission requires user to type “YES” (always).
- Prohibited domains are blocked; non-prohibited domains proceed and are logged into allowlist file.
- Tracker updated with status + artifacts + proof fields.
- Unit tests for orchestration logic and Q&A bank; integration test stubs for runner.

