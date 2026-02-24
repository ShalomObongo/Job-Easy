from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from urllib.request import urlopen

import pytest

from src.runner.models import RunStatus
from src.runner.skyvern_config import SkyvernRunnerConfig
from src.runner.skyvern_profiles import BrowserProfileResolution
from src.runner.skyvern_sdk import SkyvernSDKError


def _settings(tmp_path: Path, prohibited_domains: list[str] | None = None):
    return SimpleNamespace(
        prohibited_domains=prohibited_domains or [],
        allowlist_log_path=tmp_path / "allowlist.log",
        qa_bank_path=tmp_path / "qa.json",
        runner_max_actions_per_step=4,
    )


def _config() -> SkyvernRunnerConfig:
    return SkyvernRunnerConfig(
        base_url="http://localhost:8000",
        api_key=None,
        timeout_seconds=3,
        poll_interval_seconds=1.0,
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
        profile_create_retry_delay_seconds=0.01,
        llm_env_overrides={},
        llm_mapping_notes=[],
    )


class _HealthyClient:
    def __init__(self, *, config):
        _ = config

    async def check_health(self) -> None:
        return None

    async def run_task(self, **kwargs):
        _ = kwargs
        return {
            "status": "completed",
            "extracted_information": {
                "final_url": "https://example.com/apply",
                "visited_urls": ["https://example.com/apply"],
                "notes": ["task-complete"],
            },
            "errors": [],
        }

    @staticmethod
    def to_plain_data(value):
        return value

    @staticmethod
    def get_status(value):
        return value.get("status")

    @staticmethod
    def get_extracted_information(value):
        return value.get("extracted_information", {})

    @staticmethod
    def get_errors(value):
        return value.get("errors", [])

    @staticmethod
    def get_screenshot_urls(value):
        return value.get("screenshot_urls", [])

    @staticmethod
    def get_recording_url(value):
        return value.get("recording_url")

    @staticmethod
    def get_workflow_run_id(value):
        return value.get("workflow_run_id")


@pytest.mark.asyncio
async def test_run_application_with_skyvern_defaults_to_stopped_before_submit(
    monkeypatch, tmp_path: Path
) -> None:
    from src.runner.skyvern_runner import run_application_with_skyvern

    monkeypatch.setattr(
        "src.runner.skyvern_runner.resolve_runner_skyvern_config",
        lambda _settings: _config(),
    )
    monkeypatch.setattr("src.runner.skyvern_runner.SkyvernSDKClient", _HealthyClient)
    monkeypatch.setattr(
        "src.runner.skyvern_runner.resolve_browser_profile",
        _fake_profile_resolution,
    )

    run_dir = tmp_path / "run"
    result = await run_application_with_skyvern(
        settings=_settings(tmp_path),
        job_url="https://example.com/apply",
        run_dir=run_dir,
        profile=None,
        resume_path=None,
        cover_letter_path=None,
        auto_submit=False,
    )

    assert result.status == RunStatus.STOPPED_BEFORE_SUBMIT
    assert result.success is True
    assert (run_dir / "application_result.json").exists()
    assert (run_dir / "conversation.jsonl").exists()
    assert (run_dir / "skyvern_execution.json").exists()


@pytest.mark.asyncio
async def test_run_application_with_skyvern_auto_submit_maps_to_submitted(
    monkeypatch, tmp_path: Path
) -> None:
    from src.runner.skyvern_runner import run_application_with_skyvern

    monkeypatch.setattr(
        "src.runner.skyvern_runner.resolve_runner_skyvern_config",
        lambda _settings: _config(),
    )
    monkeypatch.setattr("src.runner.skyvern_runner.SkyvernSDKClient", _HealthyClient)
    monkeypatch.setattr(
        "src.runner.skyvern_runner.resolve_browser_profile",
        _fake_profile_resolution,
    )

    result = await run_application_with_skyvern(
        settings=_settings(tmp_path),
        job_url="https://example.com/apply",
        run_dir=tmp_path / "run2",
        profile=None,
        resume_path=None,
        cover_letter_path=None,
        auto_submit=True,
    )

    assert result.status == RunStatus.SUBMITTED
    assert result.success is True


@pytest.mark.asyncio
async def test_run_application_with_skyvern_fails_fast_on_health_error(
    monkeypatch, tmp_path: Path
) -> None:
    from src.runner.skyvern_runner import run_application_with_skyvern

    class _UnhealthyClient(_HealthyClient):
        async def check_health(self) -> None:
            raise SkyvernSDKError("health failed")

    monkeypatch.setattr(
        "src.runner.skyvern_runner.resolve_runner_skyvern_config",
        lambda _settings: _config(),
    )
    monkeypatch.setattr("src.runner.skyvern_runner.SkyvernSDKClient", _UnhealthyClient)

    result = await run_application_with_skyvern(
        settings=_settings(tmp_path),
        job_url="https://example.com/apply",
        run_dir=tmp_path / "run3",
        profile=None,
        resume_path=None,
        cover_letter_path=None,
        auto_submit=False,
    )

    assert result.status == RunStatus.FAILED
    assert any("health failed" in err for err in result.errors)


@pytest.mark.asyncio
async def test_run_application_with_skyvern_marks_prohibited_domain_blocked(
    monkeypatch, tmp_path: Path
) -> None:
    from src.runner.skyvern_runner import run_application_with_skyvern

    class _RedirectClient(_HealthyClient):
        async def run_task(self, **kwargs):
            _ = kwargs
            return {
                "status": "completed",
                "extracted_information": {
                    "status": "submitted",
                    "final_url": "https://evil.com/submit",
                    "visited_urls": ["https://evil.com/submit"],
                },
                "errors": [],
            }

    monkeypatch.setattr(
        "src.runner.skyvern_runner.resolve_runner_skyvern_config",
        lambda _settings: _config(),
    )
    monkeypatch.setattr("src.runner.skyvern_runner.SkyvernSDKClient", _RedirectClient)
    monkeypatch.setattr(
        "src.runner.skyvern_runner.resolve_browser_profile",
        _fake_profile_resolution,
    )

    result = await run_application_with_skyvern(
        settings=_settings(tmp_path, prohibited_domains=["evil.com"]),
        job_url="https://example.com/apply",
        run_dir=tmp_path / "run4",
        profile=None,
        resume_path=None,
        cover_letter_path=None,
        auto_submit=True,
    )

    assert result.status == RunStatus.BLOCKED
    assert result.success is False
    assert any("Prohibited domain encountered" in err for err in result.errors)


@pytest.mark.asyncio
async def test_run_application_with_skyvern_handles_timeout(
    monkeypatch, tmp_path: Path
) -> None:
    from src.runner.skyvern_runner import run_application_with_skyvern

    class _SlowClient(_HealthyClient):
        async def run_task(self, **kwargs):
            _ = kwargs
            await asyncio.sleep(0.02)
            return {"status": "completed", "extracted_information": {}}

    config = _config()
    config = SkyvernRunnerConfig(
        **{**config.__dict__, "max_wait_seconds": 0.001},
    )

    monkeypatch.setattr(
        "src.runner.skyvern_runner.resolve_runner_skyvern_config",
        lambda _settings: config,
    )
    monkeypatch.setattr("src.runner.skyvern_runner.SkyvernSDKClient", _SlowClient)
    monkeypatch.setattr(
        "src.runner.skyvern_runner.resolve_browser_profile",
        _fake_profile_resolution,
    )

    result = await run_application_with_skyvern(
        settings=_settings(tmp_path),
        job_url="https://example.com/apply",
        run_dir=tmp_path / "run5",
        profile=None,
        resume_path=None,
        cover_letter_path=None,
        auto_submit=False,
    )

    assert result.status == RunStatus.FAILED
    assert any("timed out" in err for err in result.errors)


def test_prepare_upload_references_serves_local_files(tmp_path: Path) -> None:
    from src.runner.skyvern_runner import _prepare_upload_references

    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"%PDF-1.4\\nresume\\n")

    with _prepare_upload_references(
        resume_path=str(resume),
        cover_letter_path=None,
    ) as refs:
        assert refs.resume_path is not None
        assert refs.resume_path.startswith("http://127.0.0.1:")
        assert refs.available_file_paths == [refs.resume_path]
        with urlopen(refs.resume_path, timeout=2) as response:
            assert response.read() == b"%PDF-1.4\\nresume\\n"


@pytest.mark.asyncio
async def test_run_application_with_skyvern_uses_served_upload_url_in_prompt(
    monkeypatch, tmp_path: Path
) -> None:
    from src.runner.skyvern_runner import run_application_with_skyvern

    captured: dict[str, object] = {}

    class _CaptureClient(_HealthyClient):
        async def run_task(self, **kwargs):
            captured.update(kwargs)
            return await super().run_task(**kwargs)

    monkeypatch.setattr(
        "src.runner.skyvern_runner.resolve_runner_skyvern_config",
        lambda _settings: _config(),
    )
    monkeypatch.setattr("src.runner.skyvern_runner.SkyvernSDKClient", _CaptureClient)
    monkeypatch.setattr(
        "src.runner.skyvern_runner.resolve_browser_profile",
        _fake_profile_resolution,
    )

    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"%PDF-1.4\\nresume\\n")

    result = await run_application_with_skyvern(
        settings=_settings(tmp_path),
        job_url="https://example.com/apply",
        run_dir=tmp_path / "run6",
        profile=None,
        resume_path=str(resume),
        cover_letter_path=None,
        auto_submit=False,
    )

    assert result.status == RunStatus.STOPPED_BEFORE_SUBMIT
    prompt = str(captured.get("prompt", ""))
    assert "Available files:" in prompt
    assert "- Resume: http://127.0.0.1:" in prompt
    assert str(resume) not in prompt


async def _fake_profile_resolution(**kwargs):
    _ = kwargs
    return BrowserProfileResolution(browser_profile_id=None, notes=[])
