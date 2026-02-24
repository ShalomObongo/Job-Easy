"""Skyvern runner configuration and compatibility mapping helpers."""

from __future__ import annotations

import ipaddress
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


class SkyvernConfigurationError(RuntimeError):
    """Raised when runner Skyvern configuration is invalid."""


@dataclass(frozen=True)
class SkyvernRunnerConfig:
    """Resolved runtime configuration for Skyvern-backed runner execution."""

    base_url: str
    api_key: str | None
    timeout_seconds: int
    poll_interval_seconds: float
    max_wait_seconds: int
    enforce_local: bool
    verify_health: bool
    workflow_id: str | None
    browser_profile_id: str | None
    browser_session_id: str | None
    browser_address: str | None
    browser_path: str | None
    persist_browser_session: bool
    profile_bootstrap_workflow_id: str | None
    profile_name: str
    profile_create_retries: int
    profile_create_retry_delay_seconds: float
    llm_env_overrides: dict[str, str]
    llm_mapping_notes: list[str]


def resolve_runner_skyvern_config(settings: Any) -> SkyvernRunnerConfig:
    """Resolve and validate Skyvern runtime settings from app settings."""
    base_url = str(
        getattr(settings, "runner_skyvern_base_url", "http://localhost:8000")
    ).strip()
    api_key = (
        _clean_optional(getattr(settings, "runner_skyvern_api_key", None))
        or _clean_optional(os.getenv("SKYVERN_API_KEY"))
        or "local-dev-key"
    )

    timeout_seconds = int(getattr(settings, "runner_skyvern_timeout_seconds", 15))
    poll_interval_seconds = float(
        getattr(settings, "runner_skyvern_poll_interval_seconds", 1.5)
    )
    max_wait_seconds = int(getattr(settings, "runner_skyvern_max_wait_seconds", 1800))

    enforce_local = bool(getattr(settings, "runner_skyvern_enforce_local", True))
    verify_health = bool(getattr(settings, "runner_skyvern_verify_health", True))

    workflow_id = _clean_optional(getattr(settings, "runner_skyvern_workflow_id", None))
    browser_profile_id = _clean_optional(
        getattr(settings, "runner_skyvern_browser_profile_id", None)
    )
    browser_session_id = _clean_optional(
        getattr(settings, "runner_skyvern_browser_session_id", None)
    )
    browser_address = _clean_optional(
        getattr(settings, "runner_skyvern_browser_address", None)
    )
    browser_path = _clean_optional(
        getattr(settings, "runner_skyvern_browser_path", None)
    )

    persist_browser_session = bool(
        getattr(settings, "runner_skyvern_persist_browser_session", False)
    )
    profile_bootstrap_workflow_id = _clean_optional(
        getattr(settings, "runner_skyvern_profile_bootstrap_workflow_id", None)
    )
    profile_name = str(
        getattr(settings, "runner_skyvern_profile_name", "job-easy-profile")
    ).strip()
    profile_create_retries = int(
        getattr(settings, "runner_skyvern_profile_create_retries", 10)
    )
    profile_create_retry_delay_seconds = float(
        getattr(settings, "runner_skyvern_profile_create_retry_delay_seconds", 1.0)
    )

    llm_env_overrides, llm_mapping_notes = map_legacy_runner_llm_env(settings)
    explicit_env_overrides = _parse_explicit_env_overrides(
        getattr(settings, "runner_skyvern_env_overrides", None)
    )
    if explicit_env_overrides:
        llm_env_overrides.update(explicit_env_overrides)
        llm_mapping_notes.append("runner_skyvern_env_overrides_applied")

    if timeout_seconds <= 0:
        raise SkyvernConfigurationError("RUNNER_SKYVERN_TIMEOUT_SECONDS must be > 0.")
    if poll_interval_seconds <= 0:
        raise SkyvernConfigurationError(
            "RUNNER_SKYVERN_POLL_INTERVAL_SECONDS must be > 0."
        )
    if max_wait_seconds <= 0:
        raise SkyvernConfigurationError("RUNNER_SKYVERN_MAX_WAIT_SECONDS must be > 0.")
    if profile_create_retries <= 0:
        raise SkyvernConfigurationError(
            "RUNNER_SKYVERN_PROFILE_CREATE_RETRIES must be > 0."
        )
    if profile_create_retry_delay_seconds <= 0:
        raise SkyvernConfigurationError(
            "RUNNER_SKYVERN_PROFILE_CREATE_RETRY_DELAY_SECONDS must be > 0."
        )
    if not profile_name:
        raise SkyvernConfigurationError(
            "RUNNER_SKYVERN_PROFILE_NAME must be non-empty."
        )

    if enforce_local and not is_local_skyvern_url(base_url):
        raise SkyvernConfigurationError(
            "Skyvern base URL must be local when RUNNER_SKYVERN_ENFORCE_LOCAL=true. "
            f"Got: {base_url}"
        )

    return SkyvernRunnerConfig(
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        max_wait_seconds=max_wait_seconds,
        enforce_local=enforce_local,
        verify_health=verify_health,
        workflow_id=workflow_id,
        browser_profile_id=browser_profile_id,
        browser_session_id=browser_session_id,
        browser_address=browser_address,
        browser_path=browser_path,
        persist_browser_session=persist_browser_session,
        profile_bootstrap_workflow_id=profile_bootstrap_workflow_id,
        profile_name=profile_name,
        profile_create_retries=profile_create_retries,
        profile_create_retry_delay_seconds=profile_create_retry_delay_seconds,
        llm_env_overrides=llm_env_overrides,
        llm_mapping_notes=llm_mapping_notes,
    )


def is_local_skyvern_url(url: str) -> bool:
    """Return True if url points to a loopback/local interface."""
    parsed = urlparse(str(url).strip())
    if not parsed.scheme or not parsed.hostname:
        return False

    hostname = parsed.hostname.strip().lower()
    if hostname == "localhost":
        return True

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return False

    return ip.is_loopback or ip.is_unspecified


def map_legacy_runner_llm_env(settings: Any) -> tuple[dict[str, str], list[str]]:
    """Map legacy RUNNER_LLM_* settings into Skyvern-compatible env values."""
    provider_raw = _clean_optional(getattr(settings, "runner_llm_provider", None))
    provider = provider_raw.lower() if provider_raw else None
    api_key = _clean_optional(getattr(settings, "runner_llm_api_key", None))
    base_url = _clean_optional(getattr(settings, "runner_llm_base_url", None))
    model = _clean_optional(getattr(settings, "runner_llm_model", None))
    reasoning_effort = _clean_optional(
        getattr(settings, "runner_llm_reasoning_effort", None)
    )

    if provider == "browser_use":
        raise SkyvernConfigurationError(
            "RUNNER_LLM_PROVIDER=browser_use is not supported by Skyvern runner backend."
        )

    env: dict[str, str] = {}
    notes: list[str] = []

    if base_url:
        env["ENABLE_OPENAI_COMPATIBLE"] = "true"
        env["OPENAI_COMPATIBLE_API_BASE"] = base_url
        env["OPENAI_COMPATIBLE_MODEL_NAME"] = model or "gpt-4o"
        env["LLM_KEY"] = "OPENAI_COMPATIBLE"
        if api_key:
            env["OPENAI_COMPATIBLE_API_KEY"] = api_key
        if reasoning_effort:
            env["OPENAI_COMPATIBLE_REASONING_EFFORT"] = reasoning_effort
        notes.append("runner_llm_mapped_openai_compatible")
        return env, notes

    if provider == "openai":
        env["ENABLE_OPENAI"] = "true"
        if api_key:
            env["OPENAI_API_KEY"] = api_key
        env["LLM_KEY"] = _map_openai_model_to_llm_key(model)
        if reasoning_effort and env["LLM_KEY"].startswith("OPENAI_GPT5"):
            env["GPT5_REASONING_EFFORT"] = reasoning_effort
        notes.append("runner_llm_mapped_openai")
        return env, notes

    if provider == "anthropic":
        env["ENABLE_ANTHROPIC"] = "true"
        if api_key:
            env["ANTHROPIC_API_KEY"] = api_key
        env["LLM_KEY"] = _map_anthropic_model_to_llm_key(model)
        notes.append("runner_llm_mapped_anthropic")
        return env, notes

    # `auto` / unset: map only when concrete values exist.
    if api_key or model or reasoning_effort:
        env["ENABLE_OPENAI"] = "true"
        if api_key:
            env["OPENAI_API_KEY"] = api_key
        env["LLM_KEY"] = _map_openai_model_to_llm_key(model)
        if reasoning_effort and env["LLM_KEY"].startswith("OPENAI_GPT5"):
            env["GPT5_REASONING_EFFORT"] = reasoning_effort
        notes.append("runner_llm_auto_mapped_openai")

    return env, notes


@contextmanager
def temporary_env_overrides(
    overrides: dict[str, str],
) -> Iterator[
    None
]:  # pragma: no cover - simple context manager exercised via integration points.
    """Temporarily apply environment variable overrides."""
    original: dict[str, str | None] = {}
    for key, value in overrides.items():
        original[key] = os.getenv(key)
        os.environ[key] = value
    try:
        yield
    finally:
        for key, previous in original.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous


def _map_openai_model_to_llm_key(model: str | None) -> str:
    if not model:
        return "OPENAI_GPT4O"

    normalized = model.strip().lower()
    mapping = {
        "gpt-5": "OPENAI_GPT5",
        "gpt-5.2": "OPENAI_GPT5_2",
        "gpt-4.1": "OPENAI_GPT4_1",
        "gpt-4o": "OPENAI_GPT4O",
        "gpt-4o-mini": "OPENAI_GPT4O_MINI",
        "o3": "OPENAI_O3",
        "o4-mini": "OPENAI_O4_MINI",
    }
    return mapping.get(normalized, "OPENAI_GPT4O")


def _map_anthropic_model_to_llm_key(model: str | None) -> str:
    if not model:
        return "ANTHROPIC_CLAUDE4_SONNET"

    normalized = model.strip().lower()
    if normalized.startswith("claude-opus-4.5") or normalized.startswith(
        "claude-4.5-opus"
    ):
        return "ANTHROPIC_CLAUDE4.5_OPUS"
    if normalized.startswith("claude-sonnet-4.5") or normalized.startswith(
        "claude-4.5-sonnet"
    ):
        return "ANTHROPIC_CLAUDE4.5_SONNET"
    if normalized.startswith("claude-opus-4") or normalized.startswith("claude-4-opus"):
        return "ANTHROPIC_CLAUDE4_OPUS"
    if normalized.startswith("claude-sonnet-4") or normalized.startswith(
        "claude-4-sonnet"
    ):
        return "ANTHROPIC_CLAUDE4_SONNET"
    return "ANTHROPIC_CLAUDE4_SONNET"


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_explicit_env_overrides(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if isinstance(value, dict):
        candidate = value
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SkyvernConfigurationError(
                "RUNNER_SKYVERN_ENV_OVERRIDES must be valid JSON object."
            ) from exc
        if not isinstance(parsed, dict):
            raise SkyvernConfigurationError(
                "RUNNER_SKYVERN_ENV_OVERRIDES must be a JSON object."
            )
        candidate = parsed
    else:
        raise SkyvernConfigurationError(
            "RUNNER_SKYVERN_ENV_OVERRIDES must be a JSON object string."
        )

    overrides: dict[str, str] = {}
    for key, val in candidate.items():
        key_str = str(key).strip()
        if not key_str:
            continue
        value_str = str(val).strip()
        if not value_str:
            continue
        overrides[key_str] = value_str
    return overrides
