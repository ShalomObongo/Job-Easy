# Implementation Plan: runner_skyvern_local_refactor_20260223

## Phase 1: Design and Migration Contract
- [x] Task: Finalize runner-to-Skyvern architecture and invariants
    - [x] Define explicit module boundaries (`src/runner/skyvern_*` adapter layer)
    - [x] Define unsupported paths and migration constraints (runner-only replacement)
    - [x] Define status and error mapping contract to `ApplicationRunResult`
- [x] Task: Map current runner capabilities to Skyvern equivalents
    - [x] Prompting/safety gates mapping
    - [x] File upload and artifact mapping
    - [x] Task/workflow lifecycle and terminal-state handling
- [x] Task: Specify Q&A bank and YOLO compatibility strategy
    - [x] Preserve behavior where possible
    - [x] Define explicit transition behavior where parity is not feasible

## Phase 2: Local Skyvern Runtime and Configuration Integration
- [x] Task: Add Skyvern runner configuration surface in Job-Easy settings
    - [x] Local Skyvern API base URL and auth settings
    - [x] Local-only guardrails (reject cloud endpoints by default)
    - [x] Timeout/retry/polling controls
- [x] Task: Add browser profile reuse compatibility guidance
    - [x] Document required Skyvern env vars (`BROWSER_TYPE=cdp-connect`, `CHROME_EXECUTABLE_PATH`)
    - [x] Document optional attached-browser mode (`browser_address`) and required remote-debugging launch args
    - [x] Document profile-copy behavior and first-run expectations
    - [x] Align with existing `CHROME_USER_DATA_DIR` / `CHROME_PROFILE_DIR` operational flow
- [x] Task: Standardize API integration on Skyvern Python SDK
    - [x] Avoid direct hard-coded REST endpoint strings in runner
    - [x] Add notes for endpoint-version drift seen in docs (`/v1/run/tasks` vs `/api/v1/tasks`)
    - [x] Ensure local base_url wiring is explicit and test-covered
- [x] Task: Implement legacy `RUNNER_LLM_*` compatibility mapping
    - [x] Add adapter to map:
      - [x] `RUNNER_LLM_PROVIDER`
      - [x] `RUNNER_LLM_API_KEY`
      - [x] `RUNNER_LLM_BASE_URL`
      - [x] `RUNNER_LLM_MODEL`
      - [x] `RUNNER_LLM_REASONING_EFFORT`
      into Skyvern provider env/config inputs
    - [x] Prefer OpenAI-compatible bridge when `RUNNER_LLM_BASE_URL` is set
    - [x] Add strict validation for unsupported combinations (e.g. `browser_use` provider in Skyvern mode)
    - [x] Define precedence between explicit Skyvern config, compatibility mapping, and service defaults
- [x] Task: Add startup/health diagnostics for local Skyvern dependency
    - [x] Fast-fail checks with actionable error messages
    - [x] Optional health probe helper for CLI and tests

## Phase 3: Implement Skyvern Runner Adapter
- [x] Task: Implement typed Skyvern client wrapper for runner module
    - [x] Task creation API integration
    - [x] Task status polling and terminal-state normalization
    - [x] Retrieval/mapping of execution artifacts (proof text/screenshot/logs)
- [x] Task: Implement prompt/payload builder for application tasks
    - [x] Include URL, applicant context, and upload artifact references
    - [x] Encode safety instructions and submission semantics
    - [x] Encode extraction schema for structured completion signals
- [x] Task: Implement robust error and timeout handling
    - [x] Network failures and retries
    - [x] Non-terminal polling timeout behavior
    - [x] Structured error mapping to runner result model
- [x] Task: Implement browser profile bootstrap/reuse manager
    - [x] Bootstrap run path with `persist_browser_session: true`
    - [x] Post-completion profile creation with bounded retry/backoff for async archive readiness
    - [x] Reuse persisted `browser_profile_id` in follow-up runs
    - [x] Re-bootstrap/fail-fast fallback semantics when profile restore fails

## Phase 4: Replace Runner Service and CLI Execution Paths
- [x] Task: Refactor `SingleJobApplicationService._run_application_flow` to Skyvern backend
    - [x] Remove Browser Use runner-agent dependency in this path
    - [x] Preserve tracker persistence and run artifact contracts
    - [x] Preserve domain/duplicate/scoring/tailoring gates upstream
- [x] Task: Refactor CLI `apply` mode to Skyvern backend
    - [x] Preserve existing CLI UX and return-code behavior
    - [x] Keep `application_result.json` and proof artifact output behavior
    - [x] Keep runner-specific flags behaviorally consistent where supported
- [x] Task: Ensure autonomous mode compatibility
    - [x] Validate status mapping and batch accounting unchanged
    - [x] Validate dry-run mode remains tailoring-only

## Phase 5: Tests and Reliability Verification
- [x] Task: Add/refresh unit tests for new runner architecture
    - [x] Skyvern client request/response mapping tests
    - [x] Service orchestration tests for success/skip/failure/blocked cases
    - [x] CLI runner mode tests (`single`, `apply`) for Skyvern path
    - [x] Legacy env compatibility tests for `RUNNER_LLM_*` -> Skyvern config mapping
- [x] Task: Add integration tests with controllable Skyvern endpoint stubs
    - [x] Task lifecycle polling behavior
    - [x] Artifact persistence behavior
    - [x] Failure-mode diagnostics
    - [x] Delayed browser-profile archive upload (400 persisted-not-ready) retry behavior
    - [x] Browser profile restore failure fallback path
    - [x] End-to-end smoke with `RUNNER_LLM_BASE_URL` + `RUNNER_LLM_MODEL` OpenAI-compatible local backend
- [x] Task: Run quality gates
    - [x] `ruff check .`
    - [x] targeted `pytest` for runner/autonomous/cli modules
    - [x] expanded regression run for related modules

## Phase 6: Rollout, Documentation, and Cleanup
- [x] Task: Update docs for local Skyvern runner operations
    - [x] Setup and env examples
    - [x] Browser profile reuse instructions
    - [x] `RUNNER_LLM_*` compatibility mapping table and migration examples
    - [x] Troubleshooting playbook
- [x] Task: Deprecate/clean obsolete Browser Use runner internals
    - [x] Remove dead code paths that are no longer used by runner execution
    - [x] Keep extractor Browser Use paths untouched
    - [x] Ensure imports and dependencies remain coherent
- [x] Task: Manual verification checkpoint
    - [x] Validate at least one real application-form smoke path in local environment
    - [x] Capture artifacts and final migration notes in track folder

## Phase 7: Upload Reliability Hotfix (Post-Cutover)
- [x] Task: Research Skyvern upload transport contract and constraints
    - [x] Validate docs/context references for task/workflow upload behavior
    - [x] Validate local installed Skyvern source for `file_url` handling
- [x] Task: Implement local upload URL bridge for Skyvern runner
    - [x] Serve whitelisted resume/cover files from a loopback HTTP endpoint during run execution
    - [x] Route prompt/workflow file references to served URLs instead of raw filesystem paths
    - [x] Preserve fallback behavior when no local files are provided
- [x] Task: Add focused tests for upload reliability
    - [x] Unit test local upload server references and payload retrieval
    - [x] Unit test prompt formatting preserves HTTP upload references
    - [x] Unit test runner prompt uses served upload URL pathing
- [ ] Task: Re-verify end-to-end Canonical application smoke in YOLO + auto-submit mode
    - [ ] Confirm no `InvalidUrlClientError` during resume/cover upload
    - [ ] Capture run artifacts and logs

## Phase 8: Browser Stability and Alternate E2E Verification
- [x] Task: Stabilize local Skyvern headful browser window geometry
    - [x] Add local startup wrapper to detect laptop screen bounds and set `BROWSER_WIDTH` / `BROWSER_HEIGHT`
    - [x] Inject explicit browser args (`--window-position`, `--window-size`, `--force-device-scale-factor`)
    - [x] Verify launched Skyvern Chromium process includes explicit sizing args
    - [x] Verify live window bounds match laptop display size class
- [x] Task: Prevent missing-dropdown value loops in runner prompt
    - [x] Add explicit fallback rule for required dropdown/combobox values when exact option is unavailable
    - [x] Instruct Skyvern to continue after one truthful fallback instead of retry looping
- [x] Task: Validate alternate full E2E application flow with tailored docs
    - [x] Generate Turaco-specific tailored resume and cover letter
    - [x] Execute Turaco YOLO + auto-submit run using tailored docs
    - [x] Confirm terminal `submitted` status with no action errors
    - [x] Confirm resume and cover-letter uploads include non-null `file_url` references
