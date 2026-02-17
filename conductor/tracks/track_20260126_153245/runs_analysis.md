# Runs Analysis (artifacts/runs)

Reviewed recent runner outputs (most recent first) to identify recurring YOLO-mode failure points.

## Key recurring issues

1) **Shadow DOM textarea/value visibility**
- Some ATS pages (notably Ashby) render key fields in shadow DOM and Browser Use’s `browser_state` output may not show the textarea’s current value even after a successful `input(...)`.
- This can cause the agent to repeatedly “re-fill” a field and eventually time out / terminate even though the field may already be filled.
- Mitigation implemented in this track: `preflight_check(browser_session)` + submit preflight gating (required/invalid only) so the agent has a source-of-truth completeness signal before submit.

2) **Combobox/dropdown selection mismatch**
- Some Greenhouse forms expose visible options but `dropdown_options(...)` returns empty and/or `select_dropdown(...)` can’t find the menu item text.
- Mitigation implemented in this track: `click_visible_option(option_text, browser_session)` fallback that clicks visible `role=option` (and `<option>`) items across open shadow roots / same-origin iframes.

3) **Blocking gates: OTP + bot protection**
- Greenhouse can require an 8-character email verification “security code” before submission.
- Ashby can hard-block automation with “flagged as possible spam” (reCAPTCHA/bot protection).
- Mitigation implemented in this track: detect OTP/bot-protection blocking states and pause for HITL (no bypass).

## Runs (high-signal subset)

### `3ee5cc7c51a2...` (2026-01-26) — Ashby (Capi Money)
- Final URL: `https://jobs.ashbyhq.com/capimoney/ee995bea-22fe-4948-9bfb-deb819909c2c/application`
- Outcome: `stopped_before_submit`
- Observed failure: required motivation textarea appeared “empty” in `browser_state` after multiple fill attempts.
- Likely root cause: textarea value not represented reliably in DOM snapshot, leading to “false missing” perception.
- Track mitigations: `preflight_check` completeness signal + submit preflight gating (required/invalid only).

### `0b47306faa35...` (2026-01-26) — Ashby (Capi Money) reCAPTCHA spam block
- Final URL: `https://jobs.ashbyhq.com/capimoney/ee995bea-22fe-4948-9bfb-deb819909c2c/application`
- Outcome: `blocked`
- Observed failure: “We couldn’t submit… flagged as possible spam… reCAPTCHA”.
- Track mitigations: detect bot-protection block state and request manual intervention; avoid repeated submit attempts.

### `91634f3cfba7...` (2026-01-23) — Greenhouse (Canonical)
- Final URL: `https://job-boards.greenhouse.io/canonicaljobs/jobs/7455578?gh_src=hovfsw5l1us`
- Outcome: `blocked`
- Observed failures:
  - OTP/security code rejected (“Invalid security code”)
  - Required “current location” dropdown not completed
  - Education fields with “No options” during search
  - Phone field intermittently not persisting
- Track mitigations: OTP block detection + HITL flow; required-field preflight; dropdown fallback click helper.

### `7d44db4b1526...` (2026-01-17) — Greenhouse (GiveDirectly)
- Final URL: `https://job-boards.greenhouse.io/givedirectly/jobs/4642859005`
- Outcome: `stopped_before_submit`
- Observed failure: combobox toggles opened visible listbox, but `dropdown_options` and `select_dropdown` could not enumerate/select items.
- Track mitigations: `click_visible_option` fallback + prompt guidance to use it.

### `9d2c3450b828...` (2026-01-23) — Greenhouse embed (DT One careers page)
- Final URL: `https://www.dtone.com/careers/apply?gh_jid=7469829003&gh_src=7d96b2cc3us&source=LinkedIn`
- Outcome: `submitted`
- Observed quirk: file upload tool failed (“Node is not a file input element”) but the flow provided a manual resume-entry fallback; submission still succeeded.
- Track note: robust upload handling for “hidden input behind button” and embedded iframes is still an open item (Phase 4).

