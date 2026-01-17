from __future__ import annotations

import os

import pytest

from src.config.settings import Settings
from src.runner.models import RunStatus
from src.runner.service import run_single_job


@pytest.mark.integration
@pytest.mark.asyncio
async def test_runner_single_job_smoke() -> None:
    """Optional smoke test.

    This requires:
    - a reachable job/application URL
    - configured LLM credentials for Browser Use
    """
    url = os.getenv("RUNNER_INTEGRATION_URL")
    if not url:
        pytest.skip("Set RUNNER_INTEGRATION_URL to run this test")

    settings = Settings()
    result = await run_single_job(url, settings=settings)

    assert result.status in {
        RunStatus.SUBMITTED,
        RunStatus.STOPPED_BEFORE_SUBMIT,
        RunStatus.SKIPPED,
        RunStatus.DUPLICATE_SKIPPED,
        RunStatus.FAILED,
        RunStatus.BLOCKED,
    }
