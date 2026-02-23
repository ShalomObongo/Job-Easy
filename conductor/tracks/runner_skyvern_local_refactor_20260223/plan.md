# Implementation Plan: runner_skyvern_local_refactor_20260223

## Phase 1: Design and Migration Contract
- [ ] Task: Finalize runner-to-Skyvern architecture and invariants
    - [ ] Define explicit module boundaries (`src/runner/skyvern_*` adapter layer)
    - [ ] Define unsupported paths and migration constraints (runner-only replacement)
    - [ ] Define status and error mapping contract to `ApplicationRunResult`
- [ ] Task: Map current runner capabilities to Skyvern equivalents
    - [ ] Prompting/safety gates mapping
    - [ ] File upload and artifact mapping
    - [ ] Task/workflow lifecycle and terminal-state handling
- [ ] Task: Specify Q&A bank and YOLO compatibility strategy
    - [ ] Preserve behavior where possible
    - [ ] Define explicit transition behavior where parity is not feasible

## Phase 2: Local Skyvern Runtime and Configuration Integration
- [ ] Task: Add Skyvern runner configuration surface in Job-Easy settings
    - [ ] Local Skyvern API base URL and auth settings
    - [ ] Local-only guardrails (reject cloud endpoints by default)
    - [ ] Timeout/retry/polling controls
- [ ] Task: Add browser profile reuse compatibility guidance
    - [ ] Document required Skyvern env vars (`BROWSER_TYPE=cdp-connect`, `CHROME_EXECUTABLE_PATH`)
    - [ ] Document optional attached-browser mode (`browser_address`) and required remote-debugging launch args
    - [ ] Document profile-copy behavior and first-run expectations
    - [ ] Align with existing `CHROME_USER_DATA_DIR` / `CHROME_PROFILE_DIR` operational flow
- [ ] Task: Standardize API integration on Skyvern Python SDK
    - [ ] Avoid direct hard-coded REST endpoint strings in runner
    - [ ] Add notes for endpoint-version drift seen in docs (`/v1/run/tasks` vs `/api/v1/tasks`)
    - [ ] Ensure local base_url wiring is explicit and test-covered
- [ ] Task: Implement legacy `RUNNER_LLM_*` compatibility mapping
    - [ ] Add adapter to map:
      - [ ] `RUNNER_LLM_PROVIDER`
      - [ ] `RUNNER_LLM_API_KEY`
      - [ ] `RUNNER_LLM_BASE_URL`
      - [ ] `RUNNER_LLM_MODEL`
      - [ ] `RUNNER_LLM_REASONING_EFFORT`
      into Skyvern provider env/config inputs
    - [ ] Prefer OpenAI-compatible bridge when `RUNNER_LLM_BASE_URL` is set
    - [ ] Add strict validation for unsupported combinations (e.g. `browser_use` provider in Skyvern mode)
    - [ ] Define precedence between explicit Skyvern config, compatibility mapping, and service defaults
- [ ] Task: Add startup/health diagnostics for local Skyvern dependency
    - [ ] Fast-fail checks with actionable error messages
    - [ ] Optional health probe helper for CLI and tests

## Phase 3: Implement Skyvern Runner Adapter
- [ ] Task: Implement typed Skyvern client wrapper for runner module
    - [ ] Task creation API integration
    - [ ] Task status polling and terminal-state normalization
    - [ ] Retrieval/mapping of execution artifacts (proof text/screenshot/logs)
- [ ] Task: Implement prompt/payload builder for application tasks
    - [ ] Include URL, applicant context, and upload artifact references
    - [ ] Encode safety instructions and submission semantics
    - [ ] Encode extraction schema for structured completion signals
- [ ] Task: Implement robust error and timeout handling
    - [ ] Network failures and retries
    - [ ] Non-terminal polling timeout behavior
    - [ ] Structured error mapping to runner result model
- [ ] Task: Implement browser profile bootstrap/reuse manager
    - [ ] Bootstrap run path with `persist_browser_session: true`
    - [ ] Post-completion profile creation with bounded retry/backoff for async archive readiness
    - [ ] Reuse persisted `browser_profile_id` in follow-up runs
    - [ ] Re-bootstrap/fail-fast fallback semantics when profile restore fails

## Phase 4: Replace Runner Service and CLI Execution Paths
- [ ] Task: Refactor `SingleJobApplicationService._run_application_flow` to Skyvern backend
    - [ ] Remove Browser Use runner-agent dependency in this path
    - [ ] Preserve tracker persistence and run artifact contracts
    - [ ] Preserve domain/duplicate/scoring/tailoring gates upstream
- [ ] Task: Refactor CLI `apply` mode to Skyvern backend
    - [ ] Preserve existing CLI UX and return-code behavior
    - [ ] Keep `application_result.json` and proof artifact output behavior
    - [ ] Keep runner-specific flags behaviorally consistent where supported
- [ ] Task: Ensure autonomous mode compatibility
    - [ ] Validate status mapping and batch accounting unchanged
    - [ ] Validate dry-run mode remains tailoring-only

## Phase 5: Tests and Reliability Verification
- [ ] Task: Add/refresh unit tests for new runner architecture
    - [ ] Skyvern client request/response mapping tests
    - [ ] Service orchestration tests for success/skip/failure/blocked cases
    - [ ] CLI runner mode tests (`single`, `apply`) for Skyvern path
    - [ ] Legacy env compatibility tests for `RUNNER_LLM_*` -> Skyvern config mapping
- [ ] Task: Add integration tests with controllable Skyvern endpoint stubs
    - [ ] Task lifecycle polling behavior
    - [ ] Artifact persistence behavior
    - [ ] Failure-mode diagnostics
    - [ ] Delayed browser-profile archive upload (400 persisted-not-ready) retry behavior
    - [ ] Browser profile restore failure fallback path
    - [ ] End-to-end smoke with `RUNNER_LLM_BASE_URL` + `RUNNER_LLM_MODEL` OpenAI-compatible local backend
- [ ] Task: Run quality gates
    - [ ] `ruff check .`
    - [ ] targeted `pytest` for runner/autonomous/cli modules
    - [ ] expanded regression run for related modules

## Phase 6: Rollout, Documentation, and Cleanup
- [ ] Task: Update docs for local Skyvern runner operations
    - [ ] Setup and env examples
    - [ ] Browser profile reuse instructions
    - [ ] `RUNNER_LLM_*` compatibility mapping table and migration examples
    - [ ] Troubleshooting playbook
- [ ] Task: Deprecate/clean obsolete Browser Use runner internals
    - [ ] Remove dead code paths that are no longer used by runner execution
    - [ ] Keep extractor Browser Use paths untouched
    - [ ] Ensure imports and dependencies remain coherent
- [ ] Task: Manual verification checkpoint
    - [ ] Validate at least one real application-form smoke path in local environment
    - [ ] Capture artifacts and final migration notes in track folder
