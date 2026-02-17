# Track Spec: Runner YOLO Reliability Hardening (Preflight + Robust Fill)

## Overview
Recent runs show YOLO-mode application automation can reach a state where it *looks* like
fields were filled, but they did not persist (e.g., textareas not “sticking”, dropdowns not
actually selected, uploads not attached). This leads to:
- Manual-submit runs stopping before the form is truly complete.
- Auto-submit runs using “submit → validation errors” as the primary way to discover
  missing fields.

This track hardens the runner so the agent verifies completeness *before* attempting to
submit (in both manual and auto-submit modes), improves deterministic filling/selection
behavior, and improves handling of blocking gates (OTP/CAPTCHA) without violating safety
constraints.

## Goals
- Make YOLO runs complete required fields reliably without depending on submit-triggered
  validation errors.
- Make manual-submit runs behave like auto-submit runs in terms of “fill completeness”
  (the only difference should be the final YES gate).
- Improve robustness across common ATS patterns: Ashby, Greenhouse (including iframe
  embeds), BambooHR, LinkedIn Easy Apply.
- Preserve non-negotiable safety: no automated CAPTCHA/2FA bypass; no fabrication; no
  auto-submit without explicit opt-in.

## Research Notes (Browser Use Docs MCP)
Browser Use docs mention “stealth”/anti-bot related capabilities:
- Cloud browsers + country proxies are described as helping with CAPTCHAs/Cloudflare/geo
  restrictions (the docs explicitly use language like “bypass captchas / Cloudflare”).
  - `https://docs.browser-use.com/production`
  - `https://docs.browser-use.com/customize/sandbox/quickstart`
  - `https://docs.browser-use.com/customize/browser/remote`
- For 2FA/OTP, the prompting guide recommends a dedicated action/tool to obtain the code
  and explicitly says not to extract codes from the page manually.
  - `https://docs.browser-use.com/customize/agent/prompting-guide`
- Custom tool/action docs include examples for “get 2FA codes” and HITL patterns.
  - `https://docs.browser-use.com/customize/tools/add`

Policy alignment for Job-Easy:
- We will **not** implement CAPTCHA solving, stealth automation, or bypass of bot
  protections/2FA.
- We will implement **detection + pause + human-in-the-loop** handling when these gates
  block progress, and proceed normally when they do not block.

## Functional Requirements

### FR1: Preflight Form Validation (No “Submit as Validator”)
Add a preflight validation step that runs before:
- asking the user for YES in manual-submit mode, and
- clicking submit in auto-submit mode.

Preflight must identify *high-confidence* missing/invalid required fields without
submitting, including:
- Empty required text inputs / textareas.
- Required comboboxes/selects still at placeholder values (e.g., “Select…”, empty).
- Required radio/checkbox groups with no selection.
- Required file uploads (resume/cover) not attached.
- Invalid states (`aria-invalid=true`, `:invalid`, common inline error text).
- Must traverse open shadow roots and same-origin iframes where possible.

Preflight must **not** block submission for intentionally empty *optional* fields.

### FR2: Intentional-Blank Safety
Preflight must not prevent submission when a field is left empty intentionally due to
specific instructions (e.g., optional fields, voluntary EEO sections, “leave blank”).

Implementation guidance:
- Only treat a field as “missing” when it is required or explicitly invalid.
- Optionally support an explicit “intentionally blank” marker the agent can set for
  specific fields to suppress non-required heuristics.

### FR3: Deterministic Fill + Verify + Fallback
For all filled fields, the runner must verify the post-condition and retry with a more
robust strategy when it fails:
- Inputs/textareas: focus → clear → type (not just set value) → verify value.
- Dropdowns: open → select by exact visible option → verify selection.
- File uploads: ensure an actual file is attached; handle hidden inputs and iframe-based
  “Attach” patterns without overwriting Resume/CV with cover letter.

### FR4: OTP/CAPTCHA Handling (Blocking vs Non-Blocking)
If OTP/2FA or CAPTCHA appears:
- If it **blocks** progress (cannot continue/submit), pause and request human help:
  - OTP: ask for the code via HITL and continue once entered.
  - CAPTCHA: prompt the user to complete it manually, then continue.
- If it does **not** block progress (e.g., reCAPTCHA badge present but no challenge),
  continue normally.

### FR5: Proof Artifacts (Screenshot Always)
Ensure each run captures a final proof screenshot (submitted/blocked/stopped) and writes
`proof_screenshot_path` in `application_result.json`.

## Non-Functional Requirements
- Safety:
  - No automated CAPTCHA solving or 2FA bypass.
  - Preserve the YES-to-submit gate unless auto-submit is explicitly enabled with all
    required prerequisites.
  - Maintain truthfulness; do not fabricate claims or personal facts.
- Reliability:
  - Avoid infinite retry loops; cap retries per field/action.
  - Avoid repeated submit attempts that increase bot-detection risk.
- Observability:
  - Always write `application_result.json` even on runner exceptions.
  - Log concise “what was missing and why” diagnostics from preflight.

## Acceptance Criteria
- Manual-submit mode:
  - The agent does not stop at the submit gate until preflight passes.
  - If preflight fails, the agent continues filling missing required fields.
- Auto-submit mode:
  - The agent does not click submit until preflight passes.
  - Missing-field discovery should not rely primarily on submit-triggered validation.
- Blocking OTP/CAPTCHA:
  - The runner pauses only when it cannot proceed, requests human intervention, then
    continues.
  - If the gate is non-blocking, the runner proceeds without unnecessary pauses.
- Proof:
  - Each run ends with `proof_screenshot_path` populated when a visible confirmation/error
    state exists.

## Out of Scope
- CAPTCHA solving / stealth automation / bypassing bot protections.
- Automatic retrieval of OTP codes from email/SMS/inbox.
