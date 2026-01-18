# Implementation Plan: Component CLI Commands + Documentation Refresh

> Methodology: TDD (Test-Driven Development)

---

## Phase 1: CLI Foundations (Shared Helpers + Run Dirs)

- [ ] Task: Define run directory + artifact conventions
    - [ ] Decide a run_id strategy for non-fingerprint flows (timestamp-based)
    - [ ] Ensure all commands can write into `artifacts/runs/<run_id>/` by default
    - [ ] Define standard artifact filenames per command:
        - [ ] `jd.json` (extract)
        - [ ] `fit_result.json` (score)
        - [ ] `tailoring_plan.json` + PDFs + `review_packet.json` (tailor)
        - [ ] `application_result.json` + `conversation.jsonl` (apply)
        - [ ] `queue.json` (queue)
- [ ] Task: Add file-first input helpers
    - [ ] Helper to load profile from `--profile` (YAML/JSON per existing ProfileService behavior)
    - [ ] Helper to load JD from `--jd` path
    - [ ] Helper to validate resume/cover-letter file paths for `apply`
- [ ] Task: Wire CLI subcommand skeletons
    - [ ] Add argparse subparsers for: `extract`, `score`, `tailor`, `apply`, `queue`, `tracker`
    - [ ] Keep existing `single` and `autonomous` behavior unchanged
- [ ] Task: Conductor - User Manual Verification 'Phase 1: CLI Foundations' (Protocol in workflow.md)

---

## Phase 2: `job-easy extract` (URL -> jd.json)

- [ ] Task: Write tests for `extract` CLI wiring
    - [ ] `job-easy extract <url>` calls extractor service
    - [ ] Writes `jd.json` into a run dir by default
    - [ ] Prints a concise summary (company/title/location)
- [ ] Task: Implement `extract` command
    - [ ] Create run dir
    - [ ] Call `JobExtractor.extract(url)` and persist `jd.json`
    - [ ] Exit non-zero on extraction failure
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Extract Command' (Protocol in workflow.md)

---

## Phase 3: `job-easy score` (jd.json + profile -> fit_result.json)

- [ ] Task: Write tests for `score` CLI wiring
    - [ ] Requires `--jd` and `--profile`
    - [ ] Prints formatted FitResult
    - [ ] Writes `fit_result.json` into run dir
- [ ] Task: Implement `score` command
    - [ ] Load JD + profile
    - [ ] Run `FitScoringService.evaluate()` and persist result
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Score Command' (Protocol in workflow.md)

---

## Phase 4: `job-easy tailor` (jd.json + profile -> PDFs)

- [ ] Task: Write tests for `tailor` CLI wiring
    - [ ] Requires `--jd` and `--profile`
    - [ ] Supports `--no-cover-letter`
    - [ ] Writes artifacts into run dir and prints file paths
- [ ] Task: Implement `tailor` command
    - [ ] Create TailoringService with output_dir=run_dir
    - [ ] Run tailoring and persist key artifacts (plan/review packet + PDFs)
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Tailor Command' (Protocol in workflow.md)

---

## Phase 5: `job-easy apply` (runner only)

- [ ] Task: Write tests for `apply` CLI wiring
    - [ ] Requires `--resume`; optional `--cover-letter`
    - [ ] Ensures `available_file_paths` is restricted to provided docs
    - [ ] Writes `application_result.json` + conversation log
- [ ] Task: Implement `apply` command
    - [ ] Create run dir
    - [ ] Run runner agent starting at URL with provided docs
    - [ ] Preserve existing HITL submit gate + CAPTCHA/2FA behavior
- [ ] Task: Conductor - User Manual Verification 'Phase 5: Apply Command' (Protocol in workflow.md)

---

## Phase 6: `job-easy queue` (leads -> ranked queue)

- [ ] Task: Write tests for `queue` CLI wiring
    - [ ] Requires leads file + `--profile`
    - [ ] Supports `--min-score`, `--include-skips`, `--limit`
    - [ ] Writes `queue.json` and prints summary/stats
- [ ] Task: Implement `queue` command
    - [ ] Parse leads, build queue using QueueManager
    - [ ] Apply limit and output stats + top-N preview
- [ ] Task: Conductor - User Manual Verification 'Phase 6: Queue Command' (Protocol in workflow.md)

---

## Phase 7: `job-easy tracker` Utilities

- [ ] Task: Write tests for tracker subcommands
    - [ ] `tracker lookup` by fingerprint and by URL
    - [ ] `tracker recent` with limit and optional status filter
    - [ ] `tracker stats` counts by status
    - [ ] `tracker mark` updates status and optional proof fields
- [ ] Task: Implement tracker subcommands
    - [ ] Add argparse structure: `tracker {lookup,recent,stats,mark}`
    - [ ] Implement DB reads/writes via TrackerRepository/TrackerService where appropriate
    - [ ] Ensure these commands run without LLM configuration
- [ ] Task: Conductor - User Manual Verification 'Phase 7: Tracker Command' (Protocol in workflow.md)

---

## Phase 8: Documentation Refresh (README + docs)

- [ ] Task: Update `README.md` (full quickstart + command reference)
    - [ ] Install + venv + dev deps
    - [ ] Required env vars + `.env` guidance
    - [ ] Profile setup
    - [ ] Command reference for: single/autonomous/extract/score/tailor/apply/queue/tracker
    - [ ] Artifact layout explanation
    - [ ] Safety guarantees section
- [ ] Task: Update supporting docs
    - [ ] Update `docs/dev.md` to include new commands for dev workflows
    - [ ] Update `docs/runner-manual-test.md` to reference `apply` and offline reruns
- [ ] Task: Conductor - User Manual Verification 'Phase 8: Documentation' (Protocol in workflow.md)

---

## Phase 9: Quality Gates

- [ ] Task: Run unit tests (non-integration)
- [ ] Task: Run ruff lint + format check
- [ ] Task: Smoke-check CLI help output
- [ ] Task: Conductor - User Manual Verification 'Phase 9: Verification' (Protocol in workflow.md)
