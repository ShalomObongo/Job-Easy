# Plan: Runner YOLO Reliability Hardening (Preflight + Robust Fill)

## Phase 1: Research + Policy Alignment
- [x] Task: Add Browser Use docs research to track notes
  - [x] Capture relevant doc links and summarize “stealth/proxy/cloud browser” guidance
  - [x] Explicitly document Job-Easy safety policy (no CAPTCHA/2FA bypass)
- [x] Task: Define “blocking vs non-blocking” gate behavior
  - [x] OTP/2FA: pause only if it blocks progress; otherwise continue
  - [x] CAPTCHA/bot protection: pause only if it blocks progress; otherwise continue

## Phase 2: Preflight Form Validation (Required/Invalid Only)
- [x] Task: Implement preflight validation helper (no submit attempt)
  - [x] Detect missing required inputs/textareas/comboboxes (incl. placeholder values)
  - [x] Detect missing required radios/checkboxes
  - [x] Detect missing required uploads (file inputs / attached filenames)
  - [x] Detect invalid states (`aria-invalid`, `:invalid`, inline error text)
  - [x] Traverse open shadow roots and same-origin iframes where possible
- [x] Task: Add “intentional blank” safety
  - [x] Ensure preflight only blocks on required/invalid signals (never optional empties)
  - [x] (Optional) Add a mechanism for the agent to mark a field as intentionally blank
- [x] Task: Add tests
  - [x] Unit tests for pure detection logic using HTML fixtures when feasible
  - [x] Targeted integration test stubs for shadow/iframe cases (best-effort)

## Phase 3: Submit Gate Integration (Manual + Auto)
- [x] Task: Update submit gating to use preflight
  - [x] Manual-submit: do not ask for YES until preflight passes
  - [x] Auto-submit: do not click submit until preflight passes
  - [x] Keep existing “blocked_missing_fields” behavior for post-click fallbacks
- [x] Task: Update runner prompt to require preflight before confirm_submit

## Phase 4: Robust Fill/Select/Upload (Verify + Fallback)
- [x] Task: Add robust input/textarea filling utilities
  - [x] Focus/scroll-into-view/clear/type/verify with retries
  - [x] Handle shadow DOM-backed fields reliably
- [x] Task: Add robust dropdown/combobox selection utilities
  - [x] Prefer select-by-visible-option + verify selection
  - [x] Fallback: click visible `role=option` items when tool-based selection fails
- [x] Task: Add robust upload utilities
  - [x] Handle hidden `<input type=file>` patterns behind “Attach/Upload” buttons
  - [x] Handle same-origin iframe embeds
  - [x] Enforce “never overwrite Resume/CV with cover letter”
- [x] Task: Best-effort cookie banner dismissal helper

## Phase 5: Blocking Gate Handling (OTP/CAPTCHA)
- [x] Task: OTP/2FA detection + HITL
  - [x] Detect blocking OTP steps (e.g., security code required before submit)
  - [x] Use HITL `ask_otp_code` only when blocked; proceed otherwise
  - [x] Add retry guidance when a code is rejected as invalid
- [x] Task: CAPTCHA/bot-protection detection + HITL
  - [x] Detect blocking CAPTCHA/spam/bot protection states
  - [x] Pause and request manual completion; proceed after user confirmation
  - [x] Avoid repeated submit attempts that increase bot detection risk

## Phase 6: Proof Artifacts + Failure Persistence
- [x] Task: Always save `application_result.json` (including on exceptions)
- [x] Task: Capture a final screenshot and populate `proof_screenshot_path`

## Phase 7: Manual Verification Checklist (No Auto-Submit Unless Explicitly Enabled)
- [x] Task: Verify Ashby: required textarea + required buttons are filled and verified
- [x] Task: Verify Greenhouse: dropdowns + uploads + OTP path triggers HITL correctly
- [x] Task: Verify iframe embed: upload/selection paths work (or degrade gracefully)
- [x] Task: Verify manual vs auto-submit parity (same completeness before submit)
  - [x] Evidence captured in `manual_verification_20260217.md`
