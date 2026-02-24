# Runner Skyvern Design Contract

## Scope

This track replaces runner-time browser execution with **local Skyvern** while keeping other modules unchanged:

- `extractor` remains Browser Use-based.
- `scoring`, `tailoring`, `tracker`, and `autonomous` keep existing contracts.
- `runner` execution (`single`, `apply`, autonomous `SingleJobApplicationService`) now uses `src/runner/skyvern_*`.

## Runtime Boundaries

### Runner orchestration

- `src/runner/service.py` owns pipeline gating (duplicate checks, fit review, document approval, tracker updates).
- `src/runner/skyvern_runner.py` owns browser execution and artifact persistence.

### Skyvern adapter layer

- `src/runner/skyvern_config.py`: local-only config resolution + legacy `RUNNER_LLM_*` compatibility mapping.
- `src/runner/skyvern_sdk.py`: SDK wrapper and response normalization.
- `src/runner/skyvern_prompt.py`: prompt/schema/workflow payload builders.
- `src/runner/skyvern_profiles.py`: profile bootstrap/reuse/retry handling.

## Non-Negotiable Invariants

- Local-only guard: when `RUNNER_SKYVERN_ENFORCE_LOCAL=true`, non-loopback `RUNNER_SKYVERN_BASE_URL` is rejected.
- Runner must fail fast with actionable errors when local Skyvern health checks fail.
- Safety policy remains truthful and explicit:
  - no CAPTCHA/OTP bypass
  - no fabricated answers
  - no silent final submit unless auto-submit conditions are met
- Artifact contract remains compatible under `artifacts/runs/<fingerprint>/`.

## Result Mapping Contract

Skyvern terminal output is normalized to `ApplicationRunResult`:

- `completed` + `auto_submit=true` -> `submitted`
- `completed` + `auto_submit=false` -> `stopped_before_submit`
- `failed`/`terminated` -> `failed`
- `cancelled`/`canceled` -> `blocked`

`extracted_information.status` overrides SDK status when present.

## LLM Compatibility Contract

Legacy runner inputs are accepted and mapped for Skyvern mode:

- `RUNNER_LLM_BASE_URL` triggers OpenAI-compatible mapping (`ENABLE_OPENAI_COMPATIBLE=true`, base/model/key mapping, optional reasoning effort).
- `RUNNER_LLM_PROVIDER=openai` maps to OpenAI envs.
- `RUNNER_LLM_PROVIDER=anthropic` maps to Anthropic envs.
- `RUNNER_LLM_PROVIDER=browser_use` fails fast as unsupported in Skyvern mode.

Precedence:

1. explicit `RUNNER_SKYVERN_ENV_OVERRIDES`
2. mapped `RUNNER_LLM_*` values
3. Skyvern service defaults

## Browser Profile Contract

- If `RUNNER_SKYVERN_BROWSER_PROFILE_ID` is set, it is reused directly.
- If `RUNNER_SKYVERN_PROFILE_BOOTSTRAP_WORKFLOW_ID` is set, runner executes bootstrap workflow and retries profile creation for persisted-session archive lag.
- Profile creation retries are bounded by `RUNNER_SKYVERN_PROFILE_CREATE_RETRIES` and `RUNNER_SKYVERN_PROFILE_CREATE_RETRY_DELAY_SECONDS`.

## Explicitly Unsupported in Runner Path

- Skyvern cloud fallback in local mode.
- Browser Use provider selection for Skyvern runner backend.
- CAPTCHA/2FA automation bypass.
