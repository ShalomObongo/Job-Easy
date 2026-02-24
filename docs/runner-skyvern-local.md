# Runner on Local Skyvern

## Summary

Runner execution is now Skyvern-backed and local-first.

- Active backend: `RUNNER_BACKEND=skyvern_local`
- Local API default: `RUNNER_SKYVERN_BASE_URL=http://localhost:8000`
- Extractor remains Browser Use-based.

## Required Local Setup

1. Start a local Skyvern service (API must be reachable from Job-Easy).
2. Ensure runner points at your local endpoint:
   - `RUNNER_SKYVERN_BASE_URL=http://localhost:8000`
   - `RUNNER_SKYVERN_ENFORCE_LOCAL=true`
3. Keep health checks enabled unless debugging startup issues:
   - `RUNNER_SKYVERN_VERIFY_HEALTH=true`

## Browser Profile Reuse

Skyvern supports two common local patterns.

### Managed Chrome by executable path

Use local CDP-connect mode with an installed Chrome executable:

- `RUNNER_SKYVERN_BROWSER_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- Skyvern-side browser env should use CDP-connect mode and Chrome executable path.

### Attached browser mode

Attach to an already-running debug Chrome instance:

- launch Chrome with remote debugging (example port `9222`)
- set `RUNNER_SKYVERN_BROWSER_ADDRESS=http://127.0.0.1:9222`

### Persisted profile bootstrap/reuse

- bootstrap workflow id: `RUNNER_SKYVERN_PROFILE_BOOTSTRAP_WORKFLOW_ID`
- created profile name: `RUNNER_SKYVERN_PROFILE_NAME`
- retry controls:
  - `RUNNER_SKYVERN_PROFILE_CREATE_RETRIES`
  - `RUNNER_SKYVERN_PROFILE_CREATE_RETRY_DELAY_SECONDS`
- direct reuse id: `RUNNER_SKYVERN_BROWSER_PROFILE_ID`

## Legacy `RUNNER_LLM_*` Compatibility

Runner accepts legacy runner env variables and maps them into Skyvern-compatible env keys at runtime.

| Legacy input | Skyvern mapping |
|---|---|
| `RUNNER_LLM_BASE_URL` set | `ENABLE_OPENAI_COMPATIBLE=true`, maps base/model/key, `LLM_KEY=OPENAI_COMPATIBLE` |
| `RUNNER_LLM_MODEL` with base URL | `OPENAI_COMPATIBLE_MODEL_NAME` |
| `RUNNER_LLM_API_KEY` with base URL | `OPENAI_COMPATIBLE_API_KEY` |
| `RUNNER_LLM_REASONING_EFFORT` with base URL | `OPENAI_COMPATIBLE_REASONING_EFFORT` |
| `RUNNER_LLM_PROVIDER=openai` | `ENABLE_OPENAI=true`, `OPENAI_API_KEY`, mapped `LLM_KEY` |
| `RUNNER_LLM_PROVIDER=anthropic` | `ENABLE_ANTHROPIC=true`, `ANTHROPIC_API_KEY`, mapped `LLM_KEY` |

Unsupported in Skyvern mode:

- `RUNNER_LLM_PROVIDER=browser_use` (fails fast)

Precedence:

1. `RUNNER_SKYVERN_ENV_OVERRIDES` (explicit JSON object)
2. mapped legacy `RUNNER_LLM_*`
3. Skyvern server defaults

## Key Runner Env Variables

```dotenv
RUNNER_BACKEND=skyvern_local
RUNNER_SKYVERN_BASE_URL=http://localhost:8000
RUNNER_SKYVERN_ENFORCE_LOCAL=true
RUNNER_SKYVERN_VERIFY_HEALTH=true
RUNNER_SKYVERN_TIMEOUT_SECONDS=15
RUNNER_SKYVERN_MAX_WAIT_SECONDS=900
RUNNER_SKYVERN_POLL_INTERVAL_SECONDS=1.5

# optional profile/session reuse
RUNNER_SKYVERN_BROWSER_PROFILE_ID=
RUNNER_SKYVERN_BROWSER_SESSION_ID=
RUNNER_SKYVERN_BROWSER_ADDRESS=
RUNNER_SKYVERN_BROWSER_PATH=
RUNNER_SKYVERN_PERSIST_BROWSER_SESSION=false
RUNNER_SKYVERN_PROFILE_BOOTSTRAP_WORKFLOW_ID=
RUNNER_SKYVERN_PROFILE_NAME=job-easy-profile
RUNNER_SKYVERN_PROFILE_CREATE_RETRIES=10
RUNNER_SKYVERN_PROFILE_CREATE_RETRY_DELAY_SECONDS=1.0

# optional explicit runtime env overrides for Skyvern
RUNNER_SKYVERN_ENV_OVERRIDES={"LLM_KEY":"OPENAI_GPT4O"}
```

## Troubleshooting

### Non-local endpoint rejected

Symptom:

- error says local enforcement rejected your Skyvern URL

Fix:

- use loopback URL (`localhost`, `127.0.0.1`, `::1`) or set `RUNNER_SKYVERN_ENFORCE_LOCAL=false` intentionally

### Health check failure

Symptom:

- error indicates `/health` probe failed

Fix:

- start local Skyvern API
- verify `RUNNER_SKYVERN_BASE_URL`
- confirm firewall/port access

### Browser profile creation fails right after bootstrap

Symptom:

- profile creation fails with persisted/archive-not-ready style errors

Fix:

- keep retry settings enabled/increase retries
- verify bootstrap workflow has `persist_browser_session: true`

### Provider mapping failure

Symptom:

- `RUNNER_LLM_PROVIDER=browser_use` or invalid combo errors

Fix:

- switch to `openai`, `anthropic`, or OpenAI-compatible (`RUNNER_LLM_BASE_URL`)

### Run times out

Symptom:

- run exits with timeout and no terminal status

Fix:

- increase `RUNNER_SKYVERN_MAX_WAIT_SECONDS`
- inspect `skyvern_execution.json` and `skyvern_artifacts.json` in run output
