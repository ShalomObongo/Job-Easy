# Track Spec: Runner Combobox/Dropdown Reliability Hardening

## Overview
Runner application attempts are failing on Greenhouse forms that use React-style combobox controls (`input[role="combobox"]`) for required questions.

Observed failure pattern:
- `dropdown_options` is called on a collapsed combobox input.
- Browser automation reports `not recognizable dropdown types`.
- Agent retries and times out.
- Run is terminated before submission.

This track hardens runner behavior so combobox/dropdown fields can be completed reliably and validated correctly by preflight.

## Functional Requirements

### FR1: Combobox-Aware Option Discovery
- Runner must support retrieving options for collapsed combobox fields by expanding the control before option extraction.
- If default dropdown extraction fails, runner must provide a fallback option list from visible listbox/option elements.

### FR2: Combobox-Aware Option Selection
- Runner must support selecting combobox options even when default dropdown selection fails.
- Selection flow must include fallback behavior that works with dynamic listboxes and visible option text.

### FR3: Accurate Preflight for React-Select Style Controls
- Preflight must not falsely report required combobox fields as missing when a value is visibly selected.
- Preflight must continue to report truly missing required dropdown/combobox fields.

### FR4: Prompt/Strategy Alignment
- Runner instructions must distinguish native selects from combobox controls.
- Guidance must avoid forcing `dropdown_options` as a prerequisite on combobox fields.

### FR5: Regression Coverage
- Unit tests must cover action registration and prompt guidance changes.
- Existing runner/HITL tests must remain green.

## Non-Functional Requirements
- Keep compatibility with current Browser Use APIs and event model.
- Avoid domain-specific hardcoding beyond generic combobox/listbox patterns.
- Maintain clear error messages to support debugging in artifacts.

## Acceptance Criteria
- On the Canonical Greenhouse form (`job-boards.greenhouse.io/canonical/jobs/7522509`), attestation combobox options can be discovered and selected without `dropdown_options` hard-failing the run.
- Required combobox fields with visible selected values are not flagged missing by preflight.
- Prompt guidance explicitly differentiates combobox vs native select handling.
- Targeted unit tests and lint checks pass.

## Out of Scope
- CAPTCHA or 2FA bypass automation.
- Site-specific hardcoding for a single company/job.
- End-to-end auto-submit for this track.
