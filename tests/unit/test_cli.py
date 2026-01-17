from __future__ import annotations

from unittest.mock import AsyncMock

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
