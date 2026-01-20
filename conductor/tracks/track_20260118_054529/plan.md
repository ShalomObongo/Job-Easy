# Implementation Plan: Component CLI Commands + Documentation Refresh

> Methodology: TDD (Test-Driven Development)

---

## Phase 1: CLI Foundations (Shared Helpers + Run Dirs)

- [x] Task: Define run directory + artifact conventions
    - [x] Decide a run_id strategy for non-fingerprint flows (timestamp-based)
    - [x] Ensure all commands can write into `artifacts/runs/<run_id>/` by default
    - [x] Define standard artifact filenames per command:
        - [x] `jd.json` (extract)
        - [x] `fit_result.json` (score)
        - [x] `tailoring_plan.json` + PDFs + `review_packet.json` (tailor)
        - [x] `application_result.json` + `conversation.jsonl` (apply)
        - [x] `queue.json` (queue)
- [x] Task: Add file-first input helpers
    - [x] Helper to load profile from `--profile` (YAML/JSON per existing ProfileService behavior)
    - [x] Helper to load JD from `--jd` path
    - [x] Helper to validate resume/cover-letter file paths for `apply`
- [x] Task: Wire CLI subcommand skeletons
    - [x] Add argparse subparsers for: `extract`, `score`, `tailor`, `apply`, `queue`, `tracker`
    - [x] Keep existing `single` and `autonomous` behavior unchanged
- [ ] Task: Conductor - User Manual Verification 'Phase 1: CLI Foundations' (Protocol in workflow.md)

---

## Phase 2: `job-easy extract` (URL -> jd.json)

- [x] Task: Write tests for `extract` CLI wiring
    - [x] `job-easy extract <url>` calls extractor service
    - [x] Writes `jd.json` into a run dir by default
    - [x] Prints a concise summary (company/title/location)
- [x] Task: Implement `extract` command
    - [x] Create run dir
    - [x] Call `JobExtractor.extract(url)` and persist `jd.json`
    - [x] Exit non-zero on extraction failure
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Extract Command' (Protocol in workflow.md)

---

## Phase 3: `job-easy score` (jd.json + profile -> fit_result.json)

- [x] Task: Write tests for `score` CLI wiring
    - [x] Requires `--jd` and `--profile`
    - [x] Prints formatted FitResult
    - [x] Writes `fit_result.json` into run dir
- [x] Task: Implement `score` command
    - [x] Load JD + profile
    - [x] Run `FitScoringService.evaluate()` and persist result
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Score Command' (Protocol in workflow.md)

---

## Phase 4: `job-easy tailor` (jd.json + profile -> PDFs)

- [x] Task: Write tests for `tailor` CLI wiring
    - [x] Requires `--jd` and `--profile`
    - [x] Supports `--no-cover-letter`
    - [x] Writes artifacts into run dir and prints file paths
- [x] Task: Implement `tailor` command
    - [x] Create TailoringService with output_dir=run_dir
    - [x] Run tailoring and persist key artifacts (plan/review packet + PDFs)
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Tailor Command' (Protocol in workflow.md)

---

## Phase 5: `job-easy apply` (runner only)

- [x] Task: Write tests for `apply` CLI wiring
    - [x] Requires `--resume`; optional `--cover-letter`
    - [x] Ensures `available_file_paths` is restricted to provided docs
    - [x] Writes `application_result.json` + conversation log
- [x] Task: Implement `apply` command
    - [x] Create run dir
    - [x] Run runner agent starting at URL with provided docs
    - [x] Preserve existing HITL submit gate + CAPTCHA/2FA behavior
- [ ] Task: Conductor - User Manual Verification 'Phase 5: Apply Command' (Protocol in workflow.md)

---

## Phase 6: `job-easy queue` (leads -> ranked queue)

- [x] Task: Write tests for `queue` CLI wiring
    - [x] Requires leads file + `--profile`
    - [x] Supports `--min-score`, `--include-skips`, `--limit`
    - [x] Writes `queue.json` and prints summary/stats
- [x] Task: Implement `queue` command
    - [x] Parse leads, build queue using QueueManager
    - [x] Apply limit and output stats + top-N preview
- [ ] Task: Conductor - User Manual Verification 'Phase 6: Queue Command' (Protocol in workflow.md)

---

## Phase 7: `job-easy tracker` Utilities

- [x] Task: Write tests for tracker subcommands
    - [x] `tracker lookup` by fingerprint and by URL
    - [x] `tracker recent` with limit and optional status filter
    - [x] `tracker stats` counts by status
    - [x] `tracker mark` updates status and optional proof fields
- [x] Task: Implement tracker subcommands
    - [x] Add argparse structure: `tracker {lookup,recent,stats,mark}`
    - [x] Implement DB reads/writes via TrackerRepository/TrackerService where appropriate
    - [x] Ensure these commands run without LLM configuration
- [ ] Task: Conductor - User Manual Verification 'Phase 7: Tracker Command' (Protocol in workflow.md)

---

## Phase 8: Documentation Refresh (README + docs)

- [x] Task: Update `README.md` (full quickstart + command reference)
    - [x] Install + venv + dev deps
    - [x] Required env vars + `.env` guidance
    - [x] Profile setup
    - [x] Command reference for: single/autonomous/extract/score/tailor/apply/queue/tracker
    - [x] Artifact layout explanation
    - [x] Safety guarantees section
- [x] Task: Update supporting docs
    - [x] Update `docs/dev.md` to include new commands for dev workflows
    - [x] Update `docs/runner-manual-test.md` to reference `apply` and offline reruns
- [ ] Task: Conductor - User Manual Verification 'Phase 8: Documentation' (Protocol in workflow.md)

---

## Phase 9: Quality Gates

- [x] Task: Run unit tests (non-integration)
- [x] Task: Run ruff lint + format check
- [x] Task: Smoke-check CLI help output
- [ ] Task: Conductor - User Manual Verification 'Phase 9: Verification' (Protocol in workflow.md)
