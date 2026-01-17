from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from src.runner.models import ApplicationRunResult, RunStatus, StepSummary


def test_application_run_result_schema_validates_required_fields() -> None:
    result = ApplicationRunResult(
        success=True,
        status=RunStatus.STOPPED_BEFORE_SUBMIT,
    )

    assert result.success is True
    assert result.status == RunStatus.STOPPED_BEFORE_SUBMIT
    assert result.visited_urls == []
    assert result.errors == []


def test_runner_step_summaries_serialize_to_json(tmp_path) -> None:
    result = ApplicationRunResult(
        success=False,
        status=RunStatus.FAILED,
        steps=[
            StepSummary(
                name="open",
                url="https://example.com/job/123",
                notes=["landed on page"],
            )
        ],
    )

    output_path = tmp_path / "result.json"
    result.save_json(output_path)

    loaded = json.loads(output_path.read_text())
    assert loaded["steps"][0]["name"] == "open"


def test_proof_capture_fields_are_optional_but_typed() -> None:
    result = ApplicationRunResult(
        success=True,
        status=RunStatus.SUBMITTED,
        proof_text=None,
        proof_screenshot_path=None,
    )

    assert result.proof_text is None
    assert result.proof_screenshot_path is None


def test_application_run_result_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        ApplicationRunResult(success=True, status="not-a-real-status")  # type: ignore[arg-type]
