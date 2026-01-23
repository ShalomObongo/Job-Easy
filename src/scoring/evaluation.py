"""Evaluation harness for comparing deterministic vs LLM fit scoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.extractor.models import JobDescription


def load_job_descriptions(path: Path) -> list[JobDescription]:
    """Load JobDescription objects from a file or directory.

    Supported inputs:
    - A single jd.json file
    - A queue.json file produced by `job-easy queue`
    - A directory containing one or more jd.json files (searched recursively)
    """
    if path.is_dir():
        jobs: list[JobDescription] = []
        for jd_path in sorted(path.rglob("jd.json")):
            jobs.extend(load_job_descriptions(jd_path))
        return jobs

    data = json.loads(path.read_text(encoding="utf-8"))

    # queue.json payload
    if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
        jobs = []
        for item in data["items"]:
            if not isinstance(item, dict):
                continue
            job_payload = item.get("job_description")
            if isinstance(job_payload, dict):
                jobs.append(JobDescription.from_dict(job_payload))
        return jobs

    # assume jd.json payload
    if not isinstance(data, dict):
        raise ValueError(f"Invalid job description payload: {path}")
    return [JobDescription.from_dict(data)]


def build_score_eval_report(
    *,
    jobs: list[JobDescription],
    profile: Any,
    deterministic_scorer: Any,
    llm_scorer: Any,
    limit: int | None = None,
) -> dict[str, Any]:
    """Run both scorers over jobs and build a JSON-serializable report."""
    items: list[dict[str, Any]] = []

    for idx, job in enumerate(jobs):
        if limit is not None and idx >= limit:
            break

        det = deterministic_scorer.evaluate(job, profile)
        llm = llm_scorer.evaluate(job, profile)

        det_rec = getattr(det, "recommendation", None)
        llm_rec = getattr(llm, "recommendation", None)

        det_score = getattr(getattr(det, "fit_score", None), "total_score", None)
        llm_score = getattr(getattr(llm, "fit_score", None), "total_score", None)

        llm_source = getattr(llm, "score_source", None)

        items.append(
            {
                "job_url": getattr(job, "job_url", None),
                "company": getattr(job, "company", None),
                "job_title": getattr(job, "role_title", None),
                "deterministic": {
                    "score": det_score,
                    "recommendation": det_rec,
                    "reasoning": getattr(det, "reasoning", None),
                },
                "llm": {
                    "score": llm_score,
                    "recommendation": llm_rec,
                    "reasoning": getattr(llm, "reasoning", None),
                    "score_source": llm_source,
                    "risk_flags": getattr(
                        getattr(llm, "fit_score", None), "risk_flags", []
                    ),
                },
                "delta_score": (float(llm_score) - float(det_score))
                if isinstance(det_score, (int, float))
                and isinstance(llm_score, (int, float))
                else None,
                "recommendation_changed": det_rec != llm_rec,
            }
        )

    return {
        "summary": summarize_score_eval_items(total_jobs=len(jobs), items=items),
        "items": items,
    }


def summarize_score_eval_items(
    *, total_jobs: int, items: list[dict[str, Any]]
) -> dict[str, Any]:
    det_counts: dict[str, int] = {"apply": 0, "review": 0, "skip": 0}
    llm_counts: dict[str, int] = {"apply": 0, "review": 0, "skip": 0}

    disagreements = 0
    llm_failures = 0
    score_deltas: list[float] = []

    for item in items:
        det = item.get("deterministic") if isinstance(item, dict) else None
        llm = item.get("llm") if isinstance(item, dict) else None

        det_rec = det.get("recommendation") if isinstance(det, dict) else None
        llm_rec = llm.get("recommendation") if isinstance(llm, dict) else None

        det_counts[str(det_rec)] = det_counts.get(str(det_rec), 0) + 1
        llm_counts[str(llm_rec)] = llm_counts.get(str(llm_rec), 0) + 1

        if det_rec != llm_rec:
            disagreements += 1

        llm_source = llm.get("score_source") if isinstance(llm, dict) else None
        if llm_source == "fallback_deterministic":
            llm_failures += 1

        delta = item.get("delta_score") if isinstance(item, dict) else None
        if isinstance(delta, (int, float)):
            score_deltas.append(float(delta))

    avg_delta = sum(score_deltas) / len(score_deltas) if score_deltas else 0.0

    return {
        "total_jobs": total_jobs,
        "evaluated": len(items),
        "disagreements": disagreements,
        "disagreement_rate": (disagreements / len(items)) if items else 0.0,
        "agreement_rate": (1.0 - (disagreements / len(items))) if items else 1.0,
        "avg_score_delta": avg_delta,
        "llm_failures": llm_failures,
        "deterministic_counts": det_counts,
        "llm_counts": llm_counts,
    }
