# Track Spec: Runner Rewrite on Local Skyvern (Profile-Reuse First)

## Overview
The current Browser Use-based runner path is fragile in production usage, especially around dynamic forms, retries, and action/tool orchestration. Multiple reliability workarounds were added, but the flow remains finicky.

This track replaces the `runner` module execution backend with **Skyvern running locally** while preserving the rest of the pipeline:
- Keep `extractor`, `scoring`, `tailoring`, `tracker`, and `autonomous` modules as-is.
- Replace only runner-time browser execution (`single`, `apply`, and autonomous-runner call paths) with Skyvern task/workflow execution.

Context7 research findings that drive this refactor:
- Skyvern supports local service execution with CLI and Docker Compose (`skyvern run ...`, `docker compose up -d`).
- Skyvern supports local browser control via `BROWSER_TYPE=cdp-connect` and `CHROME_EXECUTABLE_PATH`.
- Recent Chrome behavior requires profile-copy behavior for CDP connectivity; Skyvern handles this by copying user data to a local temp directory on first connect.
- Skyvern exposes task/workflow APIs suitable for replacing Browser Use agent orchestration, and Browser Profiles for persisted login/session reuse.
- Skyvern docs currently show multiple API surfaces/versions; this refactor should rely on the Python SDK to reduce endpoint/version drift risk.

## Skyvern Research Notes (Context7)

### R1: Local Runtime Topology
- Skyvern local operation expects a running API service (and UI optionally), with PostgreSQL configured via `DATABASE_STRING`.
- Skyvern CLI supports local bootstrap and runtime control (`skyvern quickstart`, `skyvern run server`, `skyvern run ui`, `skyvern run all`).
- Docker Compose is a first-class local/prod-like path.

### R2: Task and Workflow Execution Surface
- Task execution is available via `/v1/run/tasks` with prompt, URL, engine, and optional extraction schema payload.
- Workflow execution is available via workflow APIs and YAML-defined block pipelines.
- Python SDK supports local service targeting via `Skyvern(base_url=\"http://localhost:8000\", api_key=\"...\")`.
- Docs also reference `/api/v1/tasks` in advanced examples, indicating endpoint/version drift across docs generations.
- Design implication: prefer SDK wrapper calls over direct hard-coded REST paths in runner code.

### R3: Browser Control and Profile Reuse
- Skyvern browser mode is configurable by env (e.g., `BROWSER_TYPE=chromium-headless` or `BROWSER_TYPE=cdp-connect`).
- Local Chrome control requires `CHROME_EXECUTABLE_PATH` with `BROWSER_TYPE=cdp-connect`.
- For recent Chrome versions, Skyvern documents a local profile-copy behavior for CDP connectivity, which is relevant to preserving logged-in session workflows.
- Skyvern can also control an already-running browser via `browser_address` when Chrome is launched with remote debugging enabled.
- In default control mode, Skyvern opens/closes its own browser per run; with `browser_address` mode, the external browser lifecycle remains user-managed.

### R4: Browser Profiles Lifecycle (Critical Reliability Detail)
- Browser Profiles are generated from persisted browser state and are intended for login/session reuse.
- For workflow-derived profiles, `persist_browser_session: true` must be enabled at the workflow level.
- Profile creation is asynchronous relative to workflow completion because the session archive upload happens after run completion.
- Immediate profile creation calls can fail with a 400-level \"no persisted session yet\" condition; retry with bounded backoff is explicitly recommended.
- Reuse path: pass `browser_profile_id` to future workflow runs to restore cookies/storage/files before step 1.

### R5: Refactor Direction Chosen
- Use Skyvern local task/workflow execution as the runner backend.
- Keep all Browser Use functionality outside runner execution paths unchanged (notably extractor).
- Preserve existing pipeline orchestration semantics while replacing only runner-time browser automation primitives.

## Functional Requirements

### FR1: Runner Backend Swap (Runner Module Only)
- The runner execution path must no longer depend on Browser Use Agent APIs.
- `src/runner/service.py` and runner-only CLI mode (`apply`) must execute applications through a Skyvern client adapter.
- Extractor module remains Browser Use-based and must not be rewritten in this track.

### FR2: Local-Only Skyvern Execution
- Runner must target a local Skyvern service endpoint by default (e.g., `http://localhost:8000`).
- Configuration must explicitly prevent accidental fallback to Skyvern Cloud.
- Runner must fail fast with actionable diagnostics when local Skyvern is unavailable.

### FR3: Browser Profile Reuse Parity
- The runner integration must support local Chrome/profile reuse expectations from existing `.env` usage.
- Runner configuration and docs must define the Skyvern-local browser settings needed for profile reuse (`BROWSER_TYPE=cdp-connect`, `CHROME_EXECUTABLE_PATH`, and profile-copy behavior notes).
- Runner configuration must support both:
  - managed local Chrome mode (Skyvern launches browser from executable path), and
  - attached browser mode (`browser_address`) when user keeps a debug-enabled browser instance alive.
- Existing user operational flow for logged-in sessions must remain viable.

### FR4: Skyvern Task Contract for Job Apply Flows
- Implement a typed runner-to-Skyvern adapter that builds task payloads from:
  - job/apply URL
  - user/profile context
  - resume/cover-letter artifact paths
  - run-level safety flags (`assume_yes`, `yolo_mode`, `auto_submit`)
- Poll task/workflow state to terminal status and map outcomes into `ApplicationRunResult`.
- Use Skyvern SDK calls (not hard-coded REST endpoint strings) to avoid doc/API-version inconsistencies.

### FR5: Safety and HITL Semantics Preservation
- Existing pre-run safety gates must stay intact:
  - prohibited-domain gate
  - duplicate checks and override prompts
  - fit scoring skip/review prompts
  - document approval prompt
- Final submission safety semantics must remain explicit and truthful (no CAPTCHA/2FA bypass, no fabricated answers).

### FR6: Artifact and Tracker Compatibility
- Runner must continue producing canonical run artifacts under `artifacts/runs/<fingerprint>/`:
  - `jd.json` (unchanged upstream behavior)
  - `application_result.json`
  - conversation/execution trace artifact (Skyvern equivalent)
  - proof screenshot artifact where available
- Tracker updates (`proof_text`, artifact paths, status updates) must remain behaviorally compatible.

### FR7: Autonomous and CLI Compatibility
- Autonomous mode must continue using `SingleJobApplicationService` and preserve status mapping logic in batch results.
- `single` and `apply` CLI modes must continue to work with minimal argument-surface changes.

### FR8: QA Bank and YOLO Context Strategy
- Define explicit compatibility strategy for Q&A memory and YOLO context under Skyvern:
  - preserve where feasible
  - otherwise define scoped transitional behavior and migration notes
- Avoid hidden regressions in question-answering behavior.

### FR9: Profile Bootstrap and Rotation Contract
- Implement a deterministic profile bootstrap flow:
  - run designated auth/bootstrap workflow with `persist_browser_session: true`,
  - wait for terminal run status,
  - attempt browser profile creation with bounded retry/backoff until archive is available.
- Store and reuse `browser_profile_id` for runner workflows that need authenticated session state.
- Define fallback behavior when profile restore fails (e.g., re-bootstrap path and explicit user-facing diagnostics).

### FR10: Legacy Runner LLM Env Compatibility Layer
- The Skyvern-backed runner must accept legacy runner LLM inputs:
  - `RUNNER_LLM_PROVIDER`
  - `RUNNER_LLM_API_KEY`
  - `RUNNER_LLM_BASE_URL`
  - `RUNNER_LLM_MODEL`
  - `RUNNER_LLM_REASONING_EFFORT`
- Compatibility mapping contract (adapter-owned, deterministic, test-covered):
  - `RUNNER_LLM_BASE_URL` set:
    - enable OpenAI-compatible path in Skyvern (`ENABLE_OPENAI_COMPATIBLE=true`)
    - map base URL -> `OPENAI_COMPATIBLE_API_BASE`
    - map model -> `OPENAI_COMPATIBLE_MODEL_NAME`
    - map key -> `OPENAI_COMPATIBLE_API_KEY`
    - map reasoning effort -> `OPENAI_COMPATIBLE_REASONING_EFFORT` when non-empty
    - set `LLM_KEY=OPENAI_COMPATIBLE` unless an explicit supported override is provided
  - `RUNNER_LLM_PROVIDER=openai` without custom base URL:
    - enable OpenAI provider (`ENABLE_OPENAI=true`)
    - map key -> `OPENAI_API_KEY`
    - use `LLM_KEY` mapped from `RUNNER_LLM_MODEL` (fallback to project default if unset)
  - `RUNNER_LLM_PROVIDER=anthropic` without custom base URL:
    - enable Anthropic provider (`ENABLE_ANTHROPIC=true`)
    - map key -> `ANTHROPIC_API_KEY`
    - use `LLM_KEY` mapped from `RUNNER_LLM_MODEL` (fallback to project default if unset)
- Unsupported/ambiguous values (for example `RUNNER_LLM_PROVIDER=browser_use` in Skyvern mode) must fail fast with actionable diagnostics.
- Compatibility precedence for runner path:
  1) explicit Skyvern runner config (new settings)
  2) mapped `RUNNER_LLM_*` compatibility values
  3) existing Skyvern service defaults

## Non-Functional Requirements
- Reliability-first implementation with clear timeout/retry policies and deterministic failure messages.
- Keep module boundaries clean: runner-specific Skyvern integration code remains inside `src/runner/*`.
- Maintain or improve existing unit/integration coverage for runner orchestration contracts.
- No breaking changes to extractor/scoring/tailoring public contracts.
- Explicitly test asynchronous profile-archive lag and retry behavior to prevent flaky first-run failures.
- Legacy env compatibility behavior must be deterministic and matrix-tested across provider/base-url/model combinations.

## Acceptance Criteria
- `single` mode executes full pipeline and uses Skyvern (local) for application execution.
- `apply` mode executes via Skyvern (local) without Browser Use runner agent usage.
- Autonomous mode continues to process queue items with unchanged high-level semantics.
- Local Skyvern connectivity failures produce clear errors and do not hang indefinitely.
- Existing tracker-side persistence behavior remains intact for submitted runs.
- Tests pass for new adapter logic, service orchestration behavior, and CLI integration for runner paths.
- Documentation includes a verified local Skyvern setup path and browser-profile reuse instructions.
- Browser profile bootstrap/reuse flow is validated, including delayed-archive retry behavior and failure diagnostics.
- `RUNNER_LLM_*` values are accepted and correctly mapped for Skyvern local execution, with clear failure messages for unsupported mappings.

## Source Notes (Research Refresh 2026-02-23)
- Skyvern Quickstart (local server/UI options, CLI and Docker setup)
  - https://docs.skyvern.com/getting-started/quickstart
- Run Tasks (control own browser via `BROWSER_TYPE=cdp-connect`, `CHROME_EXECUTABLE_PATH`; attached browser via `browser_address`)
  - https://docs.skyvern.com/running-tasks/run-tasks
- Browser Configuration (browser mode selection and profile-copy behavior notes)
  - https://docs.skyvern.com/self-hosted/browser-configuration
- Browser Sessions and Browser Profiles lifecycle (persistence and reuse model)
  - https://docs.skyvern.com/browser-sessions/introduction
  - https://docs.skyvern.com/browser-sessions/browser-profiles
- Skyvern open-source docs mirrored in repository (SDK examples and persistence caveats)
  - https://github.com/skyvern-ai/skyvern

## Out of Scope
- Rewriting extractor to Skyvern.
- Skyvern Cloud rollout.
- CAPTCHA/2FA bypass automation.
- Product behavior changes unrelated to runner backend replacement.
