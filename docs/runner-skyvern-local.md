# Runner on Local Skyvern

## Scope

Runner execution is Skyvern-local only.

- Active backend: `RUNNER_BACKEND=skyvern_local`
- Local API default: `RUNNER_SKYVERN_BASE_URL=http://localhost:8000`
- Extractor, scoring, and tailoring modules keep their current Browser Use + LLM behavior.

This separation is intentional: only `runner` uses Skyvern directly.

## What Changed in the Latest Runner Refactor

The current runner track added reliability-focused behavior:

- Structured job context is always injected into runner prompts for better tailoring.
- Upload routing is explicit:
  - resume file only goes to Resume/CV upload controls
  - cover-letter PDF only goes to explicit cover-letter/supporting-document upload controls
- Cover-letter text fields are handled as text fields:
  - if the form asks for a written cover letter, runner writes tailored text
  - file upload is used only for actual file-upload controls
- Completion guardrails prevent early finish:
  - runner must sweep required fields across the full form before `complete/submit`
  - required dropdowns still showing `Select...` are treated as incomplete
- Default wait for long forms increased to:
  - `RUNNER_SKYVERN_MAX_WAIT_SECONDS=1800`

## Prerequisites

1. Project venv and dependencies installed.
2. `.env` populated (start from `.env.example`).
3. Profile created at `profiles/profile.yaml`.
4. Local Skyvern service available.

## Local Setup and Startup

### 1) Install and Configure

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
cp profiles/profile.example.yaml profiles/profile.yaml
```

### 2) Start Skyvern Server

Use the project script (recommended):

```bash
./scripts/start_skyvern_local.sh
```

What this script does:

- reads `RUNNER_LLM_*` from `.env` and maps to Skyvern-compatible env keys
- sets browser window size/position defaults
- launches `python -m skyvern run server` from `.venv`
- uses `DATABASE_STRING` if provided; otherwise defaults to:
  - `postgresql+psycopg://localhost/skyvern`

### 3) Verify Local API

```bash
curl -s http://localhost:8000/openapi.json >/dev/null && echo "skyvern up"
```

## Required Runner Environment

```dotenv
RUNNER_BACKEND=skyvern_local
RUNNER_SKYVERN_BASE_URL=http://localhost:8000
RUNNER_SKYVERN_ENFORCE_LOCAL=true
RUNNER_SKYVERN_VERIFY_HEALTH=true
RUNNER_SKYVERN_TIMEOUT_SECONDS=15
RUNNER_SKYVERN_POLL_INTERVAL_SECONDS=1.5
RUNNER_SKYVERN_MAX_WAIT_SECONDS=1800
```

## Optional Runtime Environment

### Browser profile/session reuse

```dotenv
RUNNER_SKYVERN_BROWSER_PROFILE_ID=
RUNNER_SKYVERN_BROWSER_SESSION_ID=
RUNNER_SKYVERN_BROWSER_ADDRESS=
RUNNER_SKYVERN_BROWSER_PATH=
RUNNER_SKYVERN_PERSIST_BROWSER_SESSION=false
RUNNER_SKYVERN_PROFILE_BOOTSTRAP_WORKFLOW_ID=
RUNNER_SKYVERN_PROFILE_NAME=job-easy-profile
RUNNER_SKYVERN_PROFILE_CREATE_RETRIES=10
RUNNER_SKYVERN_PROFILE_CREATE_RETRY_DELAY_SECONDS=1.0
```

### Explicit Skyvern env overrides

```dotenv
RUNNER_SKYVERN_ENV_OVERRIDES={"LLM_KEY":"OPENAI_GPT4O"}
```

### Legacy `RUNNER_LLM_*` compatibility

Runner still accepts legacy runner LLM vars and maps them at runtime.

| Legacy input | Skyvern mapping |
|---|---|
| `RUNNER_LLM_BASE_URL` set | `ENABLE_OPENAI_COMPATIBLE=true`, maps base/model/key, `LLM_KEY=OPENAI_COMPATIBLE` |
| `RUNNER_LLM_MODEL` + base URL | `OPENAI_COMPATIBLE_MODEL_NAME` |
| `RUNNER_LLM_API_KEY` + base URL | `OPENAI_COMPATIBLE_API_KEY` |
| `RUNNER_LLM_REASONING_EFFORT` + base URL | `OPENAI_COMPATIBLE_REASONING_EFFORT` |
| `RUNNER_LLM_PROVIDER=openai` | `ENABLE_OPENAI=true`, `OPENAI_API_KEY`, mapped `LLM_KEY` |
| `RUNNER_LLM_PROVIDER=anthropic` | `ENABLE_ANTHROPIC=true`, `ANTHROPIC_API_KEY`, mapped `LLM_KEY` |

Unsupported:

- `RUNNER_LLM_PROVIDER=browser_use` (fails fast for runner)

Precedence:

1. `RUNNER_SKYVERN_ENV_OVERRIDES`
2. mapped `RUNNER_LLM_*`
3. Skyvern server defaults

## Running the System

### Full pipeline (recommended)

```bash
python -m src single "<JOB_URL>"
python -m src single "<JOB_URL>" --yolo
python -m src single "<JOB_URL>" --yolo --yes
python -m src single "<JOB_URL>" --yolo --yes --auto-submit
```

### Runner-only execution

```bash
python -m src apply "<APPLICATION_URL>" --resume ./resume.pdf --cover-letter ./cover.pdf
```

With YOLO context (recommended for harder forms):

```bash
python -m src apply "<APPLICATION_URL>" \
  --resume ./resume.pdf \
  --cover-letter ./cover.pdf \
  --profile profiles/profile.yaml \
  --jd artifacts/runs/<RUN_ID>/jd.json \
  --yolo
```

## Expected Runtime Behavior

During apply runs, expect this order:

1. identity + contact fields
2. resume upload
3. cover-letter upload (only if explicit cover upload control exists)
4. required question sweep (dropdowns/comboboxes/consents/demographics where required)
5. submit/finalize

For unknown required questions:

- non-YOLO mode: blocked with explicit error
- YOLO mode: best-effort truthful answer from profile + job context, then blocked only if still unresolved

## Runner Artifacts

Each run directory should include:

- `application_result.json`
- `conversation.jsonl`
- `skyvern_execution.json`
- `skyvern_artifacts.json` (when screenshot/recording metadata exists)
- `proof.png` (when screenshot download succeeds)

## Troubleshooting

### Non-local endpoint rejected

Symptom:

- runner fails with local-enforcement error

Fix:

- use loopback URL (`localhost`, `127.0.0.1`, `::1`)
- or intentionally set `RUNNER_SKYVERN_ENFORCE_LOCAL=false`

### Health check failure

Symptom:

- runner fails before execution with health probe errors

Fix:

- ensure Skyvern server is running
- verify `RUNNER_SKYVERN_BASE_URL`
- check local firewall/port access

### Run appears stalled on large forms

Symptom:

- same step persists for a while with low/slow action count changes

Fix:

- allow more time; long embedded Greenhouse flows can be slow
- inspect `skyvern_execution.json` and timeline in local Skyvern UI
- increase `RUNNER_SKYVERN_MAX_WAIT_SECONDS` beyond `1800` if needed

### Browser profile bootstrap fails

Symptom:

- profile creation fails after bootstrap workflow

Fix:

- keep retry settings enabled/increase retries
- ensure bootstrap workflow persists browser session (`persist_browser_session=true`)

### Wrong provider mapping

Symptom:

- invalid provider/mapping errors for runner

Fix:

- use `RUNNER_LLM_PROVIDER=openai|anthropic` or OpenAI-compatible base URL
- avoid `RUNNER_LLM_PROVIDER=browser_use` for runner
