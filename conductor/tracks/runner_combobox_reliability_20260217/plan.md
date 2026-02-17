# Implementation Plan: runner_combobox_reliability_20260217

## Phase 1: Reproduce and Scope Failure Modes
- [x] Task: Confirm artifact-backed failure signatures for combobox flows
    - [x] Extract and document exact runner errors (`dropdown_options` + timeout + forced termination)
    - [x] Confirm affected control patterns (`input[role=combobox]`, dynamic listbox rendering)
- [x] Task: Define expected behavior for option discovery, selection, and preflight completeness
    - [x] Map desired behavior to generic dropdown/combobox patterns
    - [x] Enumerate non-goals and compatibility constraints

## Phase 2: Implement Runner/HITL Hardening
- [x] Task: Implement combobox-aware `dropdown_options` fallback behavior
    - [x] Expand collapsed combobox controls before option lookup
    - [x] Add visible-option extraction fallback when Browser Use event extraction fails
- [x] Task: Improve `select_dropdown` fallback for dynamic combobox controls
    - [x] Ensure combobox pre-open before selection attempts
    - [x] Add exact + partial visible-option click fallback path
- [x] Task: Improve preflight missing-field detection for selected combobox controls
    - [x] Detect selected-value UI states for React-select style fields
    - [x] Preserve existing required/invalid behavior for non-combobox fields
- [x] Task: Update runner prompt guidance for dropdown vs combobox handling
    - [x] Clarify native select flow
    - [x] Clarify combobox-first selection flow and fallback behavior

## Phase 3: Tests and Verification
- [x] Task: Add/adjust unit tests for new behavior contracts
    - [x] Ensure custom action registration includes combobox-safe dropdown tooling
    - [x] Ensure prompt includes combobox-specific guidance
- [x] Task: Run quality gates
    - [x] Run targeted unit tests for HITL and runner prompt modules
    - [x] Run lint checks on changed files
- [x] Task: Validate behavior on Canonical Greenhouse link with Playwright/manual checks
    - [x] Verify combobox options can be opened and selected
    - [x] Verify selected combobox state is treated as complete by preflight logic
