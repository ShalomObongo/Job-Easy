# Spec: Component CLI Commands + Documentation Refresh

## Overview
Job-Easy currently supports end-to-end flows via `job-easy single <url>` and `job-easy autonomous <leads_file>`.
This track adds first-class CLI subcommands to run each major component independently (extract, score, tailor, apply, queue, tracker) to support debugging, reruns, and partial workflows. It also refreshes `README.md` and supporting `docs/` content to document setup and proper usage for each component.

## Goals
- Make each component runnable in isolation with a consistent artifact layout.
- Keep the CLI "file-first": prefer explicit `--profile` / `--jd` / `--resume` inputs.
- Default to writing artifacts under `artifacts/runs/<run_id>/...` while also printing concise summaries to stdout.
- Provide a clear, copy-pasteable setup + usage guide in `README.md`, with deeper detail in `docs/`.

## New CLI Surface Area

### 1) `job-easy extract`
Purpose: Extract a JobDescription from a URL and write `jd.json`.

Proposed interface:
- `job-easy extract <url> [--out-run-dir <path>]`

Outputs:
- `jd.json`

Behavior:
- Creates a run directory (default under `artifacts/runs/<run_id>/`).
- Writes `jd.json` by default.
- Prints a short summary (company/title/location/source/apply_url if present).

### 2) `job-easy score`
Purpose: Compute fit scoring without running tailoring or applying.

Proposed interface:
- `job-easy score --jd <path> --profile <path> [--out-run-dir <path>]`

Behavior:
- Loads JD from `--jd`.
- Loads profile from `--profile`.
- Prints formatted FitResult and writes a JSON artifact (e.g. `fit_result.json`) into the run dir.

### 3) `job-easy tailor`
Purpose: Run tailoring + rendering (resume + cover letter) without applying.

Proposed interface:
- `job-easy tailor --jd <path> --profile <path> [--out-run-dir <path>] [--no-cover-letter]`

Behavior:
- Uses existing TailoringService to produce PDFs and review packet artifacts in the run dir.
- Prints the generated file paths and any warnings.

### 4) `job-easy apply`
Purpose: Run the browser runner only (form fill + uploads + submit gate), without extraction/scoring/tailoring.

Proposed interface:
- `job-easy apply <url> --resume <path> [--cover-letter <path>] [--out-run-dir <path>]`

Behavior:
- Uses the existing runner agent factory and HITL tools.
- Enforces `available_file_paths` to ONLY the provided resume/cover letter.
- Always requires the existing explicit YES gate (no behavior change to safety).
- Writes `application_result.json` + conversation log into the run dir.

### 5) `job-easy queue`
Purpose: Build the autonomous queue (parse leads, dedupe, extract, score, rank) without running applications.

Proposed interface:
- `job-easy queue <leads_file> --profile <path> [--min-score <0..1>] [--include-skips] [--limit <n>] [--out <path>]`

Behavior:
- Reuses existing QueueManager logic.
- Prints queue stats and the top N ranked items.
- Writes a machine-readable artifact (e.g. `queue.json`) by default.

### 6) `job-easy tracker`
Purpose: Operational utilities for the tracker database.

Proposed subcommands:
- `job-easy tracker lookup --fingerprint <fp>` OR `--url <url>`
- `job-easy tracker recent [--limit <n>] [--status <status>]`
- `job-easy tracker stats`
- `job-easy tracker mark --fingerprint <fp> --status <status> [--proof-text <text>] [--proof-screenshot <path>]`

Behavior:
- Must not require any Browser Use / LLM configuration for basic tracker operations.

## Documentation Changes

### README.md (top-level)
Must include:
- Install / setup (venv, `pip install -e ".[dev]"`, `.env` guidance)
- Required configuration variables (LLM provider & keys, profile path)
- Command quickstart for:
  - `single`, `autonomous`
  - `extract`, `score`, `tailor`, `apply`, `queue`, `tracker`
- Artifact layout explanation (`artifacts/runs/<run_id>/...`)
- Safety model (no auto-submit by default; no CAPTCHA/2FA bypass; duplicate prompts)

### docs/
Update relevant existing docs to match the new CLI:
- `docs/dev.md` (developer usage + testing commands)
- `docs/runner-manual-test.md` to reference `apply` and offline reruns

## Non-Functional Requirements
- Maintain current safety guarantees:
  - no submission without explicit confirmation
  - no CAPTCHA/2FA bypass
  - no fabricated answers (runner Q&A bank flow must keep current protections)
- Provide unit tests for the CLI parsing/wiring for the new subcommands.
- Keep implementation consistent with existing architecture (reuse existing services).

## Acceptance Criteria
- `job-easy --help` lists the new subcommands.
- Each new command works end-to-end for its scope (with mocks where network/LLM is required).
- Artifacts are written by default for each command in a predictable run directory.
- `README.md` is updated with setup + a command reference covering all modes/subcommands.
- Existing `single` and `autonomous` behavior remains backward compatible.
- `ruff check .`, `ruff format --check .`, and unit tests pass.

## Out of Scope
- Adding new site adapters (multi-site work).
- Changing the underlying extraction/scoring/tailoring algorithms.
- Changing safety policy defaults (e.g., enabling auto-submit).
