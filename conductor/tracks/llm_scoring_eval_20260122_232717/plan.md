# Plan: LLM-Based Fit Scoring + Evaluation Harness

## Phase 1: Design + Models + Config
- [x] Task: Define LLM score output schema for runtime scoring
    - [x] Add Pydantic model(s) for LLM scoring output
    - [x] Add unit tests validating ranges and required fields
- [x] Task: Extend `ScoringConfig` for LLM mode + LLM provider settings
    - [x] Add tests for new config fields and env overrides
    - [x] Implement config changes (defaults + validation)
- [x] Task: Decide and document FitResult/FitScore shape changes for "LLM primary + deterministic fallback"
    - [x] Audit existing call sites (`src/__main__.py`, `src/autonomous/queue.py`, `src/runner/service.py`)
    - [x] Add/update unit tests to lock expected public surface area
- [x] Task: Conductor - User Manual Verification 'Phase 1: Design + Models + Config' (Protocol in workflow.md)

---

## Phase 2: LLM Scoring Client (LiteLLM)
- [x] Task: Implement a scoring LLM client with structured output
    - [x] Reuse patterns from `src/tailoring/llm.py` (timeouts, retries, JSON extraction)
    - [x] Add unit tests that mock LiteLLM responses
- [x] Task: Create prompt(s) for LLM scoring
    - [x] Ensure the prompt forbids candidate-skill fabrication
    - [x] Include guidance for producing matched/missing items and risk flags
- [x] Task: Conductor - User Manual Verification 'Phase 2: LLM Scoring Client (LiteLLM)' (Protocol in workflow.md)

---

## Phase 3: FitScoringService Integration (LLM Primary)
- [x] Task: Add LLM scoring mode to `FitScoringService.evaluate()`
    - [x] Write tests: LLM mode uses LLM score/recommendation
    - [x] Write tests: LLM failure falls back to deterministic
    - [x] Write tests: hard constraints force skip regardless of LLM recommendation
    - [x] Implement logic + result fields indicating score source
- [x] Task: Update CLI output formatting and JSON artifact writing
    - [x] Ensure `job-easy score` prints primary LLM result and preserves deterministic baseline visibility
    - [x] Ensure `fit_result.json` contains primary LLM result plus baseline fields needed for diffing
- [x] Task: Conductor - User Manual Verification 'Phase 3: FitScoringService Integration (LLM Primary)' (Protocol in workflow.md)

---

## Phase 4: Benchmark / Evaluation Harness
- [x] Task: Design the evaluation entry point based on scoring call sites
    - [x] Decide CLI shape and inputs (jd.json file/dir and/or queue.json)
    - [x] Define report schema (per-job + summary)
- [x] Task: Implement `job-easy score-eval`
    - [x] Run deterministic + LLM scoring for each input JD
    - [x] Produce a JSON report under `artifacts/`
    - [x] Support resuming/incremental runs via existing report file
- [x] Task: Add tests for the evaluation harness
    - [x] Use fake JD fixtures + stubbed scorer outputs
- [x] Task: Conductor - User Manual Verification 'Phase 4: Benchmark / Evaluation Harness' (Protocol in workflow.md)

---

## Phase 5: Docs + Quality Gates
- [x] Task: Document new scoring mode + env vars
    - [x] Update `.env.example` with `SCORING_SCORING_MODE` and `SCORING_LLM_*`
    - [x] Add a short usage section in `README.md` / `docs/`
- [x] Task: Run quality gates
    - [x] `ruff check .`
    - [x] `ruff format --check .`
    - [x] `pytest tests/unit/scoring/`
- [x] Task: Conductor - User Manual Verification 'Phase 5: Docs + Quality Gates' (Protocol in workflow.md)
