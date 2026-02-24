# Runner Module Documentation

## Overview

The runner module executes job applications through **local Skyvern** and returns normalized
`ApplicationRunResult` artifacts to the rest of the system.

Runner orchestration remains in `SingleJobApplicationService` and includes:

- duplicate protection via tracker
- fit-based skip/review gates
- tailoring + document approval gate
- domain safety enforcement
- final application execution via Skyvern

For local setup and operations, see [runner-skyvern-local.md](./runner-skyvern-local.md).

## Module Structure

```text
src/runner/
├── __init__.py
├── domains.py
├── models.py
├── qa_bank.py
├── service.py                 # pipeline orchestration entrypoint
├── skyvern_config.py          # config + legacy RUNNER_LLM_* mapping
├── skyvern_sdk.py             # Skyvern SDK wrapper + normalization
├── skyvern_prompt.py          # prompt/schema/payload builders
├── skyvern_profiles.py        # browser profile bootstrap/reuse logic
├── skyvern_runner.py          # Skyvern execution + artifact persistence
├── yolo.py
└── yolo_answer.py
```

## Execution Flow

1. `SingleJobApplicationService.run(url)` starts pipeline.
2. Runner checks prohibited domains and duplicate tracker state.
3. If needed, extractor resolves canonical apply URL and job details.
4. Scoring recommendation gates user decision (`apply`, `review`, `skip`).
5. Tailoring generates upload artifacts.
6. Document-approval gate runs.
7. `_run_application_flow(...)` calls `run_application_with_skyvern(...)`.
8. Skyvern result is mapped to `ApplicationRunResult`.
9. Tracker gets proof/artifact updates when status is `submitted`.

## Skyvern Adapter Contracts

### Configuration (`skyvern_config.py`)

- local-only URL validation (`RUNNER_SKYVERN_ENFORCE_LOCAL`)
- timeout and polling validation
- legacy `RUNNER_LLM_*` compatibility mapping
- explicit JSON overrides via `RUNNER_SKYVERN_ENV_OVERRIDES`

### SDK wrapper (`skyvern_sdk.py`)

- wraps SDK methods:
  - `run_task`
  - `workflows.run_workflow`
  - `browser_profiles.create_browser_profile`
- probes health endpoints before run (optional)
- normalizes SDK payloads, status, errors, extracted information, and artifact URLs

### Profile lifecycle (`skyvern_profiles.py`)

- direct profile reuse via `RUNNER_SKYVERN_BROWSER_PROFILE_ID`
- optional bootstrap workflow run + bounded retry profile creation
- retry strategy handles persisted archive upload lag

### Run execution (`skyvern_runner.py`)

- builds prompt + extraction schema
- runs Skyvern workflow or task mode
- writes artifacts:
  - `application_result.json`
  - `conversation.jsonl`
  - `skyvern_execution.json`
  - `skyvern_artifacts.json`
- downloads first screenshot to `proof.png` when available
- applies prohibited-domain checks to visited URLs/final URL

## Status Mapping

Skyvern responses are normalized to runner statuses:

- `completed` + auto-submit enabled -> `submitted`
- `completed` + auto-submit disabled -> `stopped_before_submit`
- `failed` / `terminated` -> `failed`
- `cancelled` / `canceled` -> `blocked`

If extracted information includes explicit `status`, that value takes precedence.

## Integration With Other Modules

- `src/tracker`: duplicate checks, status updates, proof/artifact persistence.
- `src/extractor`: still Browser Use-based; supplies job details/canonical URLs.
- `src/scoring`: apply/skip/review recommendation before runner execution.
- `src/tailoring`: resume + cover letter generation before upload.
- `src/autonomous`: delegates per-job execution to `SingleJobApplicationService`.

## Safety Guarantees

- prohibited domains are blocked before and during execution
- no CAPTCHA/OTP bypass automation
- no fabricated information requirements in runner prompt policy
- auto-submit requires explicit runner conditions (`runner_yolo_mode` + `runner_assume_yes`)

## Notes on Legacy Browser Use Runner Internals

Legacy Browser Use runner construction utilities remain in the repository for historical
compatibility/reference, but production runner execution paths now use the Skyvern adapter.
