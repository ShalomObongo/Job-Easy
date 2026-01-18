from __future__ import annotations

from unittest.mock import AsyncMock

from src.autonomous.models import BatchResult
from src.runner.models import ApplicationRunResult, RunStatus


def test_cli_single_mode_calls_pipeline_service(monkeypatch) -> None:
    from src.__main__ import main

    mock = AsyncMock(
        return_value=ApplicationRunResult(success=True, status=RunStatus.SKIPPED)
    )
    monkeypatch.setattr("src.runner.service.run_single_job", mock, raising=False)

    exit_code = main(["single", "https://example.com/jobs/123"])

    assert exit_code == 0
    mock.assert_awaited_once()


def test_cli_single_mode_missing_url_errors_cleanly() -> None:
    from src.__main__ import main

    assert main(["single"]) == 1


def test_cli_autonomous_mode_calls_autonomous_service(monkeypatch, tmp_path) -> None:
    from src.__main__ import main

    leads_file = tmp_path / "leads.txt"
    leads_file.write_text("https://example.com/jobs/123\n", encoding="utf-8")

    mock = AsyncMock(
        return_value=BatchResult(
            processed=0,
            submitted=0,
            skipped=0,
            failed=0,
            duration_seconds=0.0,
            job_results=[],
        )
    )
    monkeypatch.setattr("src.autonomous.service.run_autonomous", mock, raising=False)

    exit_code = main(["autonomous", str(leads_file), "--yes"])

    assert exit_code == 0
    mock.assert_awaited_once()
