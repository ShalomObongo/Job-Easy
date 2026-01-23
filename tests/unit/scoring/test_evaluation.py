"""Unit tests for scoring evaluation harness."""

from __future__ import annotations

import json


class _DummyScorer:
    def __init__(self, results_by_url: dict[str, object]):
        self._results_by_url = results_by_url

    def evaluate(self, job, profile):  # noqa: ARG002
        return self._results_by_url[job.job_url]


class TestLoadJobDescriptions:
    def test_loads_from_single_jd_json(self, tmp_path) -> None:
        from src.scoring.evaluation import load_job_descriptions

        path = tmp_path / "jd.json"
        path.write_text(
            json.dumps(
                {
                    "company": "Acme",
                    "role_title": "Engineer",
                    "job_url": "https://example.com/jobs/1",
                }
            ),
            encoding="utf-8",
        )

        jobs = load_job_descriptions(path)

        assert len(jobs) == 1
        assert jobs[0].job_url == "https://example.com/jobs/1"

    def test_loads_from_directory_recursive(self, tmp_path) -> None:
        from src.scoring.evaluation import load_job_descriptions

        (tmp_path / "a").mkdir()
        (tmp_path / "b" / "c").mkdir(parents=True)

        (tmp_path / "a" / "jd.json").write_text(
            json.dumps(
                {
                    "company": "Acme",
                    "role_title": "Engineer",
                    "job_url": "https://example.com/jobs/1",
                }
            ),
            encoding="utf-8",
        )
        (tmp_path / "b" / "c" / "jd.json").write_text(
            json.dumps(
                {
                    "company": "Acme",
                    "role_title": "Engineer 2",
                    "job_url": "https://example.com/jobs/2",
                }
            ),
            encoding="utf-8",
        )

        jobs = load_job_descriptions(tmp_path)

        assert {job.job_url for job in jobs} == {
            "https://example.com/jobs/1",
            "https://example.com/jobs/2",
        }

    def test_loads_from_queue_json(self, tmp_path) -> None:
        from src.scoring.evaluation import load_job_descriptions

        path = tmp_path / "queue.json"
        path.write_text(
            json.dumps(
                {
                    "stats": {"total": 2},
                    "items": [
                        {
                            "job_description": {
                                "company": "Acme",
                                "role_title": "Engineer",
                                "job_url": "https://example.com/jobs/1",
                            }
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        jobs = load_job_descriptions(path)

        assert len(jobs) == 1
        assert jobs[0].company == "Acme"


class TestBuildScoreEvalReport:
    def test_builds_report_with_summary_metrics(self) -> None:
        from src.extractor.models import JobDescription
        from src.scoring.evaluation import build_score_eval_report
        from src.scoring.models import ConstraintResult, FitResult, FitScore

        job1 = JobDescription(company="Acme", role_title="Eng", job_url="https://x/1")
        job2 = JobDescription(company="Acme", role_title="Eng", job_url="https://x/2")

        det1 = FitResult(
            job_url=job1.job_url,
            job_title=job1.role_title,
            company=job1.company,
            fit_score=FitScore(total_score=0.8, must_have_score=1.0),
            constraints=ConstraintResult(passed=True),
            recommendation="apply",
            reasoning="det",
        )
        det2 = FitResult(
            job_url=job2.job_url,
            job_title=job2.role_title,
            company=job2.company,
            fit_score=FitScore(total_score=0.4, must_have_score=1.0),
            constraints=ConstraintResult(passed=True),
            recommendation="skip",
            reasoning="det",
        )

        llm1 = FitResult(
            job_url=job1.job_url,
            job_title=job1.role_title,
            company=job1.company,
            fit_score=FitScore(total_score=0.7, must_have_score=1.0),
            constraints=ConstraintResult(passed=True),
            recommendation="review",
            reasoning="llm",
            score_source="llm",
        )
        llm2 = FitResult(
            job_url=job2.job_url,
            job_title=job2.role_title,
            company=job2.company,
            fit_score=FitScore(total_score=0.4, must_have_score=1.0),
            constraints=ConstraintResult(passed=True),
            recommendation="skip",
            reasoning="llm",
            score_source="fallback_deterministic",
        )

        report = build_score_eval_report(
            jobs=[job1, job2],
            profile=object(),
            deterministic_scorer=_DummyScorer({job1.job_url: det1, job2.job_url: det2}),
            llm_scorer=_DummyScorer({job1.job_url: llm1, job2.job_url: llm2}),
        )

        assert report["summary"]["evaluated"] == 2
        assert report["summary"]["disagreements"] == 1
        assert report["summary"]["disagreement_rate"] == 0.5
        assert report["summary"]["llm_failures"] == 1
        assert report["items"][0]["job_url"]
