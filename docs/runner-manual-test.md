# Runner Manual Test Checklist (Skyvern Local)

This checklist validates the Skyvern-backed runner flow on local infrastructure.

## Preconditions

- Local Skyvern service is running and reachable.
- `.env` configured with at least:
  - `RUNNER_BACKEND=skyvern_local`
  - `RUNNER_SKYVERN_BASE_URL=http://localhost:8000`
  - `RUNNER_SKYVERN_ENFORCE_LOCAL=true`
- Resume file exists for upload tests.
- Optional:
  - `RUNNER_SKYVERN_BROWSER_PROFILE_ID` for persisted login reuse
  - `RUNNER_SKYVERN_PROFILE_BOOTSTRAP_WORKFLOW_ID` for profile bootstrap flow

## Test 1: Local enforcement guard

1. Set:
   - `RUNNER_SKYVERN_BASE_URL=https://api.skyvern.com`
   - `RUNNER_SKYVERN_ENFORCE_LOCAL=true`
2. Run:
   - `python -m src apply "https://example.com/jobs/123" --resume ./resume.pdf`
3. Expect:
   - immediate failure with local-enforcement diagnostic
   - `application_result.json` created

## Test 2: Health-check fail-fast

1. Set:
   - `RUNNER_SKYVERN_BASE_URL=http://127.0.0.1:65534`
2. Run:
   - `python -m src apply "https://example.com/jobs/123" --resume ./resume.pdf`
3. Expect:
   - failure with health endpoint diagnostic
   - no indefinite hang
   - `application_result.json` created

## Test 3: Runner-only smoke (local Skyvern)

1. Set valid local Skyvern base URL.
2. Run:
   - `python -m src apply "<APPLICATION_URL>" --resume ./resume.pdf`
3. Expect:
   - runner executes via Skyvern
   - artifacts written under run directory:
     - `application_result.json`
     - `conversation.jsonl`
     - `skyvern_execution.json`
     - `skyvern_artifacts.json` (if screenshot/recording metadata available)

## Test 4: End-to-end single mode

1. Run:
   - `python -m src single "<JOB_POSTING_URL>"`
2. Expect:
   - tracker duplicate checks still enforced
   - fit scoring and document approval gates still enforced
   - runner execution delegated to Skyvern backend

## Safety Checks

- No CAPTCHA/OTP bypass automation.
- No submission without required runner safety conditions.
- Prohibited domains remain blocked (`PROHIBITED_DOMAINS`).
- Allowed domains appended to `ALLOWLIST_LOG_PATH`.
