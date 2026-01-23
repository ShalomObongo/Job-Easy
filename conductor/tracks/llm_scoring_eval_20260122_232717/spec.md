# Spec: LLM-Based Fit Scoring + Evaluation Harness

## Overview
The current fit scoring system is fully deterministic and relies heavily on the extractor to populate structured fields like `required_skills`, `preferred_skills`, and `experience_years_min/max`.

This track introduces an LLM-primary scoring mode that evaluates job fit using the full extracted job content (including `description`, `qualifications`, and `responsibilities`) and the full `UserProfile`. The LLM output becomes the primary `FitResult` score/recommendation, while the existing deterministic scorer remains available as a fallback and as a benchmark target.

In addition, this track adds a benchmarking harness that runs both scorers across a dataset of jobs and produces a comparison report to help tune prompts, thresholds, and constraints.

## Goals
- Improve scoring robustness when structured JD fields are missing or incomplete.
- Make LLM scoring the primary signal (when enabled), while preserving deterministic constraints and a deterministic fallback.
- Provide transparent scoring outputs: score/recommendation, matched/missing items, and structured risk flags.
- Provide a repeatable evaluation harness to compare LLM vs deterministic outcomes across many jobs.

## Functional Requirements

### FR-1: LLM Scoring Output Schema
Implement a structured output schema (Pydantic model) for the runtime LLM scorer.

Required fields:
- `total_score: float` in the range 0.0-1.0
- `recommendation: Literal["apply", "review", "skip"]`
- `reasoning: str` (short, user-readable)
- `must_have_matched: list[str]`
- `must_have_missing: list[str]`
- `preferred_matched: list[str]`
- `risk_flags: list[str]` (e.g., unknown visa policy, missing salary, unclear location, missing must-haves)

Notes:
- The LLM must base matched/missing items strictly on the provided `UserProfile` and extracted JD content (no fabricated skills/experience).

### FR-2: LLM Scoring Configuration
Extend scoring configuration to support LLM scoring mode and LLM provider settings.

New/updated configuration fields (env prefix `SCORING_`):
- `scoring_mode: Literal["deterministic", "llm"]` (default: `deterministic`)
- LLM client settings:
  - `llm_provider: str`
  - `llm_model: str`
  - `llm_api_key: str | None`
  - `llm_base_url: str | None`
  - `llm_timeout: float`
  - `llm_max_retries: int`
  - `llm_reasoning_effort: str | None`

Desired behavior:
- When `SCORING_SCORING_MODE=llm`, the scoring service uses the LLM output as the primary score/recommendation.
- If LLM config is missing or the LLM call fails, the service falls back to deterministic scoring and records that fallback in the result.

### FR-3: LLM Scoring Client
Implement a scoring-focused LLM client with:
- structured output parsing (Pydantic)
- retries/backoff
- timeouts
- helpful error messages

It should follow the patterns already used in `src/tailoring/llm.py` (LiteLLM `acompletion`, `response_format`, JSON extraction).

### FR-4: FitScoringService Integration (LLM Primary)
Update `FitScoringService` to support LLM-primary scoring when enabled.

Behavior:
- Always run deterministic constraint checks (location/work type, visa, experience tolerance, salary minimum) and force `skip` on hard violations.
- In `llm` scoring mode:
  - Call the LLM scorer to obtain score + recommendation + matched/missing + risk flags.
  - Use the LLM score as the `FitResult.fit_score.total_score` and the LLM recommendation as the primary recommendation (subject to constraints).
  - If the LLM scorer fails, compute deterministic scoring and proceed.

Output:
- The returned `FitResult` must indicate which scoring mode/source was used (LLM vs deterministic fallback).
- CLI formatting should show both the primary LLM result and (when available) the deterministic breakdown for comparison.

### FR-5: Benchmark / Evaluation Harness
Add a harness that compares deterministic vs LLM scoring over a dataset.

Design:
- Implement as a new CLI command (recommended: `job-easy score-eval`) because scoring is used by multiple flows (single runs, autonomous queue ranking, runner gating) and the harness should be runnable independently of runner/browser automation.
- Inputs should be file-first:
  - a directory of `jd.json` files, or
  - a single `jd.json` file, or
  - a queue artifact (`queue.json`) where available
- Output a machine-readable report under `artifacts/` (JSON), including:
  - per-job: URL/company/title, deterministic score/recommendation, LLM score/recommendation, differences, and short reasoning
  - summary metrics: counts by recommendation bucket, disagreement rate, average score delta

## Non-Functional Requirements
- Safety: constraints remain deterministic and must override any LLM recommendation.
- Deterministic fallback: a failed LLM call must not break scoring.
- Cost control: the harness must be opt-in and should support incremental runs via an output report file.
- Testability: unit tests for config, schema validation, and LLM integration points using mocks.

## Acceptance Criteria
- When `SCORING_SCORING_MODE=llm`, `FitScoringService.evaluate()` produces a `FitResult` driven by the LLM score/recommendation, unless constraints fail.
- When the LLM call fails, `FitScoringService.evaluate()` falls back to deterministic scoring and records that fallback.
- LLM output includes matched/missing items and risk flags.
- `job-easy score` output and `fit_result.json` include enough data to inspect the LLM result and the deterministic baseline.
- `job-easy score-eval` produces a comparison report for a directory of `jd.json` files.
- Unit tests cover critical logic paths, and `ruff check .` + unit tests pass.

## Out of Scope
- Changing extractor behavior or schemas (beyond what is required to pass richer JD text into the scorer).
- Replacing deterministic constraint checks with LLM inference.
- Long-term analytics dashboards.
