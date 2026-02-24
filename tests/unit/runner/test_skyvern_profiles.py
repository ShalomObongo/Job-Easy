from __future__ import annotations

from dataclasses import replace

import pytest

from src.runner.skyvern_config import SkyvernRunnerConfig
from src.runner.skyvern_profiles import (
    SkyvernProfileError,
    resolve_browser_profile,
)


def _config() -> SkyvernRunnerConfig:
    return SkyvernRunnerConfig(
        base_url="http://localhost:8000",
        api_key=None,
        timeout_seconds=15,
        poll_interval_seconds=1.0,
        max_wait_seconds=120,
        enforce_local=True,
        verify_health=True,
        workflow_id=None,
        browser_profile_id=None,
        browser_session_id=None,
        browser_address=None,
        browser_path=None,
        persist_browser_session=False,
        profile_bootstrap_workflow_id="wf_bootstrap",
        profile_name="job-easy-profile",
        profile_create_retries=3,
        profile_create_retry_delay_seconds=0.001,
        llm_env_overrides={},
        llm_mapping_notes=[],
    )


@pytest.mark.asyncio
async def test_resolve_browser_profile_reuses_existing_profile_id() -> None:
    config = replace(_config(), browser_profile_id="bp_existing")
    client = _FakeClient()

    result = await resolve_browser_profile(
        config=config,
        client=client,
        bootstrap_data={"prompt": "x"},
    )

    assert result.browser_profile_id == "bp_existing"
    assert "browser_profile_reused_from_settings" in result.notes


@pytest.mark.asyncio
async def test_resolve_browser_profile_retries_until_archive_is_ready() -> None:
    client = _FakeClient(retry_on_create=True)

    result = await resolve_browser_profile(
        config=_config(),
        client=client,
        bootstrap_data={"prompt": "x"},
    )

    assert result.browser_profile_id == "bp_created"
    assert client.create_attempts == 2
    assert any(
        note.startswith("profile_bootstrap_workflow_run_id=") for note in result.notes
    )
    assert any(note.startswith("browser_profile_created=") for note in result.notes)


@pytest.mark.asyncio
async def test_resolve_browser_profile_raises_when_bootstrap_fails() -> None:
    client = _FakeClient(workflow_status="failed")
    with pytest.raises(SkyvernProfileError):
        await resolve_browser_profile(
            config=_config(),
            client=client,
            bootstrap_data={"prompt": "x"},
        )


class _FakeClient:
    def __init__(
        self, *, retry_on_create: bool = False, workflow_status: str = "completed"
    ):
        self.retry_on_create = retry_on_create
        self.workflow_status = workflow_status
        self.create_attempts = 0

    async def run_workflow(self, *, workflow_id: str, data: dict):
        _ = workflow_id, data
        return {
            "status": self.workflow_status,
            "workflow_run_id": "wr_123",
            "errors": [],
        }

    @staticmethod
    def get_status(value):
        return value.get("status")

    @staticmethod
    def get_workflow_run_id(value):
        return value.get("workflow_run_id")

    @staticmethod
    def get_errors(value):
        return value.get("errors", [])

    async def create_browser_profile(
        self, *, name: str, workflow_run_id: str | None = None
    ):
        _ = name, workflow_run_id
        self.create_attempts += 1
        if self.retry_on_create and self.create_attempts == 1:
            raise RuntimeError("browser session has no persisted archive yet")
        return {"browser_profile_id": "bp_created"}

    @staticmethod
    def to_plain_data(value):
        return value
