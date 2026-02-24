from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from src.runner.skyvern_config import (
    SkyvernConfigurationError,
    is_local_skyvern_url,
    map_legacy_runner_llm_env,
    resolve_runner_skyvern_config,
    temporary_env_overrides,
)


def _settings(**overrides):
    base = {
        "runner_skyvern_base_url": "http://localhost:8000",
        "runner_skyvern_api_key": None,
        "runner_skyvern_timeout_seconds": 15,
        "runner_skyvern_poll_interval_seconds": 1.5,
        "runner_skyvern_max_wait_seconds": 900,
        "runner_skyvern_enforce_local": True,
        "runner_skyvern_verify_health": True,
        "runner_skyvern_workflow_id": None,
        "runner_skyvern_browser_profile_id": None,
        "runner_skyvern_browser_session_id": None,
        "runner_skyvern_browser_address": None,
        "runner_skyvern_browser_path": None,
        "runner_skyvern_persist_browser_session": False,
        "runner_skyvern_profile_bootstrap_workflow_id": None,
        "runner_skyvern_profile_name": "job-easy-profile",
        "runner_skyvern_profile_create_retries": 10,
        "runner_skyvern_profile_create_retry_delay_seconds": 1.0,
        "runner_llm_provider": None,
        "runner_llm_api_key": None,
        "runner_llm_base_url": None,
        "runner_llm_model": None,
        "runner_llm_reasoning_effort": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_is_local_skyvern_url_accepts_loopback_hosts() -> None:
    assert is_local_skyvern_url("http://localhost:8000") is True
    assert is_local_skyvern_url("http://127.0.0.1:8000") is True
    assert is_local_skyvern_url("http://[::1]:8000") is True


def test_is_local_skyvern_url_rejects_remote_hosts() -> None:
    assert is_local_skyvern_url("https://api.skyvern.com") is False
    assert is_local_skyvern_url("https://example.com") is False


def test_map_legacy_runner_llm_env_base_url_uses_openai_compatible() -> None:
    env, notes = map_legacy_runner_llm_env(
        _settings(
            runner_llm_base_url="http://localhost:4000/v1",
            runner_llm_api_key="sk-test",
            runner_llm_model="llama3.1",
            runner_llm_reasoning_effort="low",
        )
    )
    assert env["ENABLE_OPENAI_COMPATIBLE"] == "true"
    assert env["OPENAI_COMPATIBLE_API_BASE"] == "http://localhost:4000/v1"
    assert env["OPENAI_COMPATIBLE_API_KEY"] == "sk-test"
    assert env["OPENAI_COMPATIBLE_MODEL_NAME"] == "llama3.1"
    assert env["OPENAI_COMPATIBLE_REASONING_EFFORT"] == "low"
    assert env["LLM_KEY"] == "OPENAI_COMPATIBLE"
    assert "runner_llm_mapped_openai_compatible" in notes


def test_map_legacy_runner_llm_env_rejects_browser_use_provider() -> None:
    with pytest.raises(SkyvernConfigurationError):
        map_legacy_runner_llm_env(_settings(runner_llm_provider="browser_use"))


def test_resolve_runner_skyvern_config_rejects_non_local_when_enforced() -> None:
    with pytest.raises(SkyvernConfigurationError):
        resolve_runner_skyvern_config(
            _settings(
                runner_skyvern_base_url="https://api.skyvern.com",
                runner_skyvern_enforce_local=True,
            )
        )


def test_temporary_env_overrides_restores_original_values(monkeypatch) -> None:
    monkeypatch.setenv("LLM_KEY", "ORIGINAL")

    with temporary_env_overrides({"LLM_KEY": "OPENAI_COMPATIBLE", "FOO": "BAR"}):
        assert os.getenv("LLM_KEY") == "OPENAI_COMPATIBLE"
        assert os.getenv("FOO") == "BAR"

    assert os.getenv("LLM_KEY") == "ORIGINAL"
    assert os.getenv("FOO") is None


def test_explicit_skyvern_env_overrides_take_precedence_over_mapped_values() -> None:
    config = resolve_runner_skyvern_config(
        _settings(
            runner_llm_provider="openai",
            runner_llm_model="gpt-4o",
            runner_skyvern_env_overrides='{"LLM_KEY":"OPENAI_GPT5"}',
        )
    )
    assert config.llm_env_overrides["LLM_KEY"] == "OPENAI_GPT5"
    assert "runner_skyvern_env_overrides_applied" in config.llm_mapping_notes
