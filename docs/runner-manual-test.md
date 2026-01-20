# Runner Manual Test Checklist

This checklist validates the **dynamic application runner** end-to-end on real job/application links.

## Preconditions

- LLM credentials configured (see `.env.example`), typically:
  - `EXTRACTOR_LLM_API_KEY=...` (used by extractor and runner by default)
  - `TAILORING_LLM_API_KEY=...` (optional; falls back to extractor key)
  - `RUNNER_LLM_API_KEY=...` (optional; overrides runner only)
- `profiles/profile.yaml` exists (copy from `profiles/profile.example.yaml`)
- Optional but recommended:
  - `QA_BANK_PATH=./data/qa_bank.json` (default) to persist answers to screening questions
  - `ALLOWLIST_LOG_PATH=./data/allowlist.log` (default) to record encountered domains
- Chrome profile reuse configured if desired:
  - `USE_EXISTING_CHROME_PROFILE=true`
  - `CHROME_USER_DATA_DIR=...`
  - `CHROME_PROFILE_DIR=...`

## Test 1: Job posting → “Apply” → multi-step flow

Option A (end-to-end):
1. Run:
   - `python -m src single "<JOB_POSTING_URL>"`
2. Expect:
   - If tracker says already submitted → prompted “Proceed anyway?”
   - Fit scoring decision is printed (skip/review/apply)
   - Tailored resume/cover letter are generated
   - Prompt: “Approve resume/cover letter for upload?”
   - Final submit gate requires typing **YES**
3. Artifacts:
   - `artifacts/runs/<fingerprint>/jd.json`
   - `artifacts/runs/<fingerprint>/conversation.jsonl`
   - `artifacts/runs/<fingerprint>/application_result.json`

Option B (runner-only):
1. Prepare:
   - Have `resume.pdf` (and optionally `cover.pdf`) ready
2. Run:
   - `python -m src apply "<JOB_POSTING_OR_APPLICATION_URL>" --resume resume.pdf --cover-letter cover.pdf`
3. Expect:
   - Runner fills required fields best-effort
   - Unknown questions trigger a prompt and are saved to the Q&A bank
   - Final submit gate requires typing **YES**

## Test 2: Direct application form (single page)

Option A (end-to-end):
1. Run:
   - `python -m src single "<APPLICATION_FORM_URL>"`

Option B (runner-only):
1. Run:
   - `python -m src apply "<APPLICATION_FORM_URL>" --resume resume.pdf`

Expect:
- Runner fills required fields best-effort
- Unknown questions trigger a prompt and are saved to the Q&A bank
- Final submit gate requires typing **YES**

## Safety checks

- Confirm no submission occurs without explicit “YES”.
- Confirm CAPTCHA/2FA prompts request manual help (no bypass).
- Confirm prohibited domains are blocked (set `PROHIBITED_DOMAINS` in `.env`).
- Confirm allowed domains are appended to `ALLOWLIST_LOG_PATH` (default `./data/allowlist.log`).
