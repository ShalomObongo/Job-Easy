from __future__ import annotations

from urllib.parse import urlparse

import pytest

from src.runner.skyvern_config import SkyvernRunnerConfig
from src.runner.skyvern_sdk import SkyvernSDKClient


def _config() -> SkyvernRunnerConfig:
    return SkyvernRunnerConfig(
        base_url="http://localhost:8000",
        api_key="old-key",
        timeout_seconds=2,
        poll_interval_seconds=0.1,
        max_wait_seconds=30,
        enforce_local=True,
        verify_health=True,
        workflow_id=None,
        browser_profile_id=None,
        browser_session_id=None,
        browser_address=None,
        browser_path=None,
        persist_browser_session=False,
        profile_bootstrap_workflow_id=None,
        profile_name="job-easy-profile",
        profile_create_retries=2,
        profile_create_retry_delay_seconds=0.1,
        llm_env_overrides={},
        llm_mapping_notes=[],
    )


class _FakeResponse:
    def __init__(self, status: int, body: bytes = b"") -> None:
        self.status = status
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        _ = (exc_type, exc, tb)
        return False

    def read(self) -> bytes:
        return self._body


@pytest.mark.asyncio
async def test_skyvern_sdk_check_health_openapi_fallback_succeeds(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SkyvernSDKClient,
        "_build_client",
        lambda _self, _config: object(),
    )

    def fake_urlopen(request, timeout):
        _ = timeout
        path = urlparse(request.full_url).path
        if path == "/openapi.json":
            return _FakeResponse(200)
        return _FakeResponse(404)

    monkeypatch.setattr("src.runner.skyvern_sdk.urlopen", fake_urlopen)

    client = SkyvernSDKClient(config=_config())
    await client.check_health()


@pytest.mark.asyncio
async def test_skyvern_sdk_run_task_repairs_local_auth_and_retries(
    monkeypatch,
) -> None:
    seen_api_keys: list[str | None] = []

    def fake_build_client(_self, config):
        class _FakeClient:
            async def run_task(_self, **kwargs):
                _ = kwargs
                seen_api_keys.append(config.api_key)
                if config.api_key != "new-key":
                    raise RuntimeError(
                        "status_code: 403 detail: Could not validate credentials"
                    )
                return {"status": "completed"}

        return _FakeClient()

    async def fake_repair(_self):
        return "new-key"

    monkeypatch.setattr(SkyvernSDKClient, "_build_client", fake_build_client)
    monkeypatch.setattr(SkyvernSDKClient, "_repair_local_auth", fake_repair)

    client = SkyvernSDKClient(config=_config())
    result = await client.run_task(prompt="hello")

    assert result == {"status": "completed"}
    assert seen_api_keys == ["old-key", "new-key"]
