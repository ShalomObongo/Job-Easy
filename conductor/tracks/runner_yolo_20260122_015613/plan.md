# Plan: Runner YOLO Mode (Auto-Answer With Job + Profile Context)

## Phase 1: Configuration + Context Plumbing
- [x] Task: Add `RUNNER_YOLO_MODE` setting (default false)
    - [x] Update `src/config/settings.py` with `runner_yolo_mode: bool`
    - [x] Update `.env.example` and `docs/config.md`
- [x] Task: Define a runner context payload for YOLO mode (hybrid)
    - [x] Create a small helper/module to build a JSON-serializable payload from `JobDescription` + `UserProfile`
    - [x] Include selected raw fields (notably full job description text) plus structured fields
- [x] Task: Pass job+profile context into the runner agent
    - [x] Extend `src/runner/agent.py#create_application_agent` to accept the context payload + yolo_mode flag
    - [x] Update `src/runner/agent.py#get_application_prompt` to embed the context and yolo rules when enabled
    - [x] Wire in `src/runner/service.py` (single pipeline) so the agent receives job/profile context
    - [x] Wire in autonomous execution to reuse queued job + loaded profile for yolo context

## Phase 2: Q&A Bank Scoping (Fix Wrong Reuse)
- [x] Task: Expand Q&A bank schema to support scoped entries (with backwards compatibility)
    - [x] Update `src/runner/qa_bank.py` to load old `{question, answer, context}` entries safely
    - [x] Add new entry fields (e.g., `scope_type`, `scope_key`, `source`, `category`)
- [x] Task: Implement lookup precedence by scope
    - [x] Prefer `job` scope (fingerprint/url) over `company` over `domain/ATS` over `global`
    - [x] Ensure motivation-type questions never reuse a global answer across companies
- [x] Task: Add unit tests for scoping + backwards compatibility
    - [x] New tests under `tests/unit/runner/test_qa_bank.py`

## Phase 3: YOLO Answer Flow In Runner
- [x] Task: Add question categorization utilities
    - [x] Implement a lightweight classifier (contact/eligibility/experience/compensation/motivation/eeo/other)
    - [x] Unit tests for classification
- [x] Task: Implement deterministic YOLO answer resolver
    - [x] Add a pure function that uses yolo_context + question + (optional) field metadata/options
    - [x] Choose safe defaults for select/radio/checkbox (prefer "Prefer not to say", else "Other")
    - [x] Generate a basic motivation answer from job+user context (truthful)
    - [x] Add unit tests for select/radio/checkbox safe defaults
- [x] Task: Update runner tools to use YOLO answer resolver
    - [x] In YOLO mode, `resolve_answer(...)` should not prompt and should return best-effort answers
    - [x] Persist auto-generated answers with appropriate scope/category
    - [x] Add unit test ensuring submit gate text is still present in prompt
- [x] Task: Wire scope inputs for the tools
    - [x] Provide the tools enough context (company name, start url domain, fingerprint/job id) to scope safely

## Phase 4: CLI + Autonomous Integration + Docs
- [x] Task: Ensure autonomous runs inherit YOLO mode
    - [x] Confirm `src/autonomous/service.py` -> single pipeline passes settings through unchanged
    - [x] Add/adjust tests to confirm autonomous uses queued job for yolo context
- [x] Task: Add CLI flag(s) to enable YOLO mode (in addition to env var)
    - [x] `job-easy single --yolo`
    - [x] `job-easy autonomous --yolo`
    - [x] (Optional) `job-easy apply --yolo` (and decide how to supply `jd.json` context in apply-only mode)
- [x] Task: Documentation updates
    - [x] Add a short section to `docs/runner.md` describing YOLO mode, scoping, and safety constraints
