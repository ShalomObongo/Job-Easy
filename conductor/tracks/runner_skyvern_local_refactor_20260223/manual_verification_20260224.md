# Manual Verification — Runner Skyvern Local Refactor

Date: 2026-02-24
Branch: `codex/runner-skyvern-local-refactor`

## Scope

Manual checks were focused on the Skyvern-backed runner path and its local-only safeguards.

## Environment Checks

- Verified runner backend default and local-only configuration usage.
- Verified Skyvern dependency install and import path via project virtualenv.

## Manual Scenarios Executed

### 1) Non-local endpoint guard

Command pattern:

```bash
RUNNER_SKYVERN_BASE_URL=https://api.skyvern.com \
RUNNER_SKYVERN_ENFORCE_LOCAL=true \
python -m src apply "https://example.com/jobs/123" --resume ./resume.pdf
```

Observed:

- Run fails fast with a local-enforcement diagnostic.
- `application_result.json` is written.

### 2) Local health probe fail-fast

Command pattern:

```bash
RUNNER_SKYVERN_BASE_URL=http://127.0.0.1:65534 \
python -m src apply "https://example.com/jobs/123" --resume ./resume.pdf
```

Observed:

- Health check fails quickly with actionable endpoint guidance.
- No indefinite hang.
- `application_result.json` is written.

### 3) Successful runner-path artifact write (stubbed local SDK client)

Method:

- Replaced `SkyvernSDKClient` with a deterministic fake in a manual harness.

Observed artifacts in run directory:

- `application_result.json`
- `conversation.jsonl`
- `skyvern_execution.json`
- `skyvern_artifacts.json`

## Test Verification Executed

### Lint/format

- `ruff format .`
- `ruff check .`
- `ruff format --check .`

Result: pass.

### Runner-relevant tests

Command:

```bash
pytest tests/unit/runner \
  tests/unit/test_cli.py \
  tests/unit/config/test_settings.py \
  tests/unit/hitl/test_tools.py \
  tests/unit/autonomous \
  tests/unit/tracker \
  tests/integration/runner/test_runner_integration.py
```

Result:

- `168 passed, 1 skipped`.

### Scoring stability regression (due env isolation fixture)

Command:

```bash
pytest tests/unit/scoring
```

Result:

- `120 passed`.

## Notes

- Full live integration suites were not used for final verification because they are environment-dependent and long-running.
- Runner refactor verification focused on local Skyvern adapter behavior, compatibility mapping, artifacts, and orchestration contracts.
