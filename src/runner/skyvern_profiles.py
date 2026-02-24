"""Browser profile lifecycle helpers for Skyvern runner integrations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from src.runner.skyvern_config import SkyvernRunnerConfig
from src.runner.skyvern_sdk import SkyvernSDKClient, SkyvernSDKError


class SkyvernProfileError(RuntimeError):
    """Raised when browser profile bootstrap/reuse handling fails."""


@dataclass(frozen=True)
class BrowserProfileResolution:
    """Resolved browser profile information for an application run."""

    browser_profile_id: str | None
    notes: list[str]


async def resolve_browser_profile(
    *,
    config: SkyvernRunnerConfig,
    client: SkyvernSDKClient,
    bootstrap_data: dict[str, Any],
) -> BrowserProfileResolution:
    """Resolve browser profile via direct ID or bootstrap workflow."""
    notes: list[str] = []

    if config.browser_profile_id:
        notes.append("browser_profile_reused_from_settings")
        return BrowserProfileResolution(
            browser_profile_id=config.browser_profile_id,
            notes=notes,
        )

    workflow_id = config.profile_bootstrap_workflow_id
    if not workflow_id:
        return BrowserProfileResolution(browser_profile_id=None, notes=notes)

    run = await client.run_workflow(workflow_id=workflow_id, data=bootstrap_data)
    status = client.get_status(run)
    workflow_run_id = client.get_workflow_run_id(run)
    if status != "completed" or not workflow_run_id:
        errors = client.get_errors(run)
        message = (
            "Skyvern profile bootstrap workflow did not complete successfully. "
            f"status={status or 'unknown'}"
        )
        if errors:
            message += f" errors={'; '.join(errors)}"
        raise SkyvernProfileError(message)

    notes.append(f"profile_bootstrap_workflow_run_id={workflow_run_id}")
    profile_id = await _create_browser_profile_with_retry(
        client=client,
        workflow_run_id=workflow_run_id,
        profile_name=config.profile_name,
        retries=config.profile_create_retries,
        retry_delay_seconds=config.profile_create_retry_delay_seconds,
    )
    notes.append(f"browser_profile_created={profile_id}")
    return BrowserProfileResolution(browser_profile_id=profile_id, notes=notes)


async def _create_browser_profile_with_retry(
    *,
    client: SkyvernSDKClient,
    workflow_run_id: str,
    profile_name: str,
    retries: int,
    retry_delay_seconds: float,
) -> str:
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            profile = await client.create_browser_profile(
                name=profile_name,
                workflow_run_id=workflow_run_id,
            )
            payload = client.to_plain_data(profile)
            for key in ("browser_profile_id", "id", "profile_id"):
                value = payload.get(key)
                if value:
                    return str(value)
            raise SkyvernProfileError(
                "Skyvern profile create response did not include browser_profile_id."
            )
        except Exception as exc:
            last_error = exc
            message = str(exc).lower()
            # Skyvern docs describe a transient persisted-session upload lag.
            retryable = "persist" in message or "archive" in message
            if not retryable or attempt == retries:
                break
            await asyncio.sleep(retry_delay_seconds)

    if isinstance(last_error, SkyvernSDKError):
        raise SkyvernProfileError(str(last_error)) from last_error
    if last_error is not None:
        raise SkyvernProfileError(
            f"Failed to create browser profile after retries: {last_error}"
        ) from last_error
    raise SkyvernProfileError("Failed to create browser profile for unknown reason.")
