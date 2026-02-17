# Manual Verification - 2026-02-17

## Scope

Phase 7 checklist verification for:

1. Ashby required textarea/buttons flow
2. Greenhouse dropdown/upload/OTP flow
3. Iframe embed upload/selection behavior
4. Manual vs auto-submit parity before submit

## Evidence Sources

- Historical high-signal runs (from `artifacts/runs/`):
  - `3ee5cc7c51a2993d35c7c2a1c5e6802f6496d43276a5ca2f1293c913124fb628/application_result.json`
  - `91634f3cfba79ebe3ed8c0ea5bf0b4235deeed35956e026603ce610a37336b9e/application_result.json`
  - `9d2c3450b8280420952adc60d3514ed4d70156253ba59dfee2962e727b902686/application_result.json`
- Fresh regression attempts (2026-02-17):
  - `artifacts/runs/manual_verify_ashby_manual/`
  - `artifacts/runs/manual_verify_greenhouse_manual/`
  - `artifacts/runs/manual_verify_iframe_manual/`
  - `artifacts/runs/manual_verify_iframe_auto/`

## Results

### 1) Ashby - Required textarea + required buttons

- Verified historical run shows resume + identity + location completion and explicit blocker on required motivation textarea:
  - `artifacts/runs/3ee5cc7c51a2993d35c7c2a1c5e6802f6496d43276a5ca2f1293c913124fb628/application_result.json`
  - Error confirms required textarea remained incomplete; submit gate not reached.
- Fresh run confirmed original Capi URL now redirects to "Job not found" and then to active role listing, but still blocks before submit when required upload/fields are incomplete.

Conclusion: required-field gating behavior is enforced; run does not submit while required textarea/fields remain incomplete.

### 2) Greenhouse - Dropdowns + uploads + OTP path

- Verified historical Greenhouse run captures OTP/security-code blocking behavior and invalid-code handling:
  - `artifacts/runs/91634f3cfba79ebe3ed8c0ea5bf0b4235deeed35956e026603ce610a37336b9e/application_result.json`
  - Includes "Invalid security code" and required location blocker before submission.
- Fresh run confirmed dropdown fallback interactions continue to work (custom combobox handling), but upload remained a blocker in this environment before reaching final submit.

Conclusion: OTP blocking path and dropdown handling are observable; upload remains a practical blocker in fresh live runs.

### 3) Iframe embed - Upload/selection paths

- Verified historical iframe embed run successfully submitted with fallback behavior:
  - `artifacts/runs/9d2c3450b8280420952adc60d3514ed4d70156253ba59dfee2962e727b902686/application_result.json`
  - Notes include repeated upload tool failures and manual resume-entry fallback; final status is `submitted`.
- Fresh iframe run confirms robust cross-frame field selection and combobox selection, with blocking on resume upload when dedicated upload path is not successfully used.

Conclusion: iframe paths can complete; when upload cannot be attached, submission remains blocked.

### 4) Manual vs auto-submit parity

- Fresh manual and auto-submit runs on DT One iframe target both blocked before submission due unresolved required blockers (resume upload + required combobox completion).
- Auto-submit mode did not bypass required-field completeness; no unsafe submit occurred.

Conclusion: parity holds for pre-submit completeness behavior; auto-submit does not bypass missing required fields.

## Additional Finding (Resolved)

- `apply` mode previously crashed when Browser Use appended judge commentary after JSON output (`ValidationError: trailing characters`).
- Resolution implemented in `src/__main__.py`: fall back to first JSON object extraction when `structured_output` is unavailable and continue result persistence.
- Regression coverage added in `tests/unit/test_cli.py`:
  - `test_extract_first_json_object_ignores_trailing_commentary`
  - `test_cli_apply_mode_parses_json_with_trailing_text`
- Current status: parser fallback works and `application_result.json` persists in the covered apply-mode path.
