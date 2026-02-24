"""Thin wrapper around Skyvern Python SDK with defensive compatibility helpers."""

from __future__ import annotations

import asyncio
import inspect
import json
from importlib import import_module
from types import ModuleType
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from src.runner.skyvern_config import SkyvernRunnerConfig


class SkyvernSDKError(RuntimeError):
    """Raised when Skyvern SDK calls fail or are unavailable."""


class SkyvernSDKClient:
    """SDK-backed client used by runner integrations."""

    def __init__(self, *, config: SkyvernRunnerConfig) -> None:
        self._config = config
        self._client = self._build_client(config)

    async def run_task(self, **kwargs: Any) -> Any:
        """Run a Skyvern task using supported SDK kwargs."""
        method = getattr(self._client, "run_task", None)
        if method is None:
            raise SkyvernSDKError("Skyvern SDK client has no run_task method.")
        return await _call_compatible(method, kwargs)

    async def run_workflow(self, *, workflow_id: str, data: dict[str, Any]) -> Any:
        """Run a Skyvern workflow through SDK workflow APIs."""
        workflows = getattr(self._client, "workflows", None)
        method = getattr(workflows, "run_workflow", None) if workflows else None
        if method is None:
            raise SkyvernSDKError("Skyvern SDK client has no workflows.run_workflow.")
        kwargs: dict[str, Any] = {
            "workflow_id": workflow_id,
            "data": data,
            "wait_for_completion": True,
        }
        return await _call_compatible(method, kwargs)

    async def get_workflow_run(self, *, workflow_run_id: str) -> Any:
        """Fetch a workflow run by ID if supported by current SDK."""
        workflows = getattr(self._client, "workflows", None)
        if workflows is None:
            raise SkyvernSDKError("Skyvern SDK workflows client is unavailable.")

        method = getattr(workflows, "get_workflow_run", None) or getattr(
            workflows, "get_workflow_run_by_id", None
        )
        if method is None:
            raise SkyvernSDKError(
                "Skyvern SDK workflows client has no workflow-run getter."
            )
        return await _call_compatible(method, {"workflow_run_id": workflow_run_id})

    async def create_browser_profile(
        self, *, name: str, workflow_run_id: str | None = None
    ) -> Any:
        """Create a browser profile from a workflow run/session archive."""
        browser_profiles = getattr(self._client, "browser_profiles", None)
        method = (
            getattr(browser_profiles, "create_browser_profile", None)
            if browser_profiles
            else None
        )
        if method is None:
            raise SkyvernSDKError(
                "Skyvern SDK client has no browser_profiles.create_browser_profile."
            )
        kwargs: dict[str, Any] = {"name": name}
        if workflow_run_id:
            kwargs["workflow_run_id"] = workflow_run_id
        return await _call_compatible(method, kwargs)

    async def check_health(self) -> None:
        """Probe local Skyvern HTTP health endpoints."""
        base_url = self._config.base_url.rstrip("/")
        paths = ("/health", "/api/v1/health", "/api/health")

        async def _probe(path: str) -> bool:
            target = urljoin(f"{base_url}/", path.lstrip("/"))
            request = Request(target, method="GET")
            try:

                def _request() -> bool:
                    with urlopen(request, timeout=self._config.timeout_seconds) as resp:
                        return 200 <= int(getattr(resp, "status", 500)) < 400

                return await asyncio.to_thread(_request)
            except Exception:
                return False

        for path in paths:
            if await _probe(path):
                return

        raise SkyvernSDKError(
            "Unable to reach local Skyvern service. "
            f"Checked {', '.join(paths)} at {base_url}. "
            "Start Skyvern locally and verify RUNNER_SKYVERN_BASE_URL."
        )

    @staticmethod
    def to_plain_data(value: Any) -> dict[str, Any]:
        """Convert SDK response objects into plain dictionaries."""
        if value is None:
            return {}
        if isinstance(value, dict):
            return value

        for attr in ("model_dump", "to_dict", "dict"):
            serializer = getattr(value, attr, None)
            if callable(serializer):
                try:
                    payload = serializer()
                    if isinstance(payload, dict):
                        return payload
                except Exception:
                    continue

        if hasattr(value, "__dict__"):
            candidate = {
                key: _plainify_json_value(val)
                for key, val in vars(value).items()
                if not key.startswith("_")
            }
            if candidate:
                return candidate

        return {"value": _plainify_json_value(value)}

    @staticmethod
    def to_json_text(value: Any) -> str:
        payload = SkyvernSDKClient.to_plain_data(value)
        return json.dumps(payload, indent=2, default=_plainify_json_value)

    @staticmethod
    def get_status(value: Any) -> str | None:
        payload = SkyvernSDKClient.to_plain_data(value)
        status = payload.get("status")
        return str(status).strip().lower() if status else None

    @staticmethod
    def get_errors(value: Any) -> list[str]:
        payload = SkyvernSDKClient.to_plain_data(value)
        errors: list[str] = []

        raw_errors = payload.get("errors")
        if isinstance(raw_errors, list):
            errors.extend(str(item) for item in raw_errors if str(item).strip())
        elif isinstance(raw_errors, str) and raw_errors.strip():
            errors.append(raw_errors.strip())

        failure_reason = payload.get("failure_reason")
        if failure_reason:
            errors.append(str(failure_reason))

        message = payload.get("message")
        if message:
            errors.append(str(message))

        deduped: list[str] = []
        seen: set[str] = set()
        for error in errors:
            if error in seen:
                continue
            seen.add(error)
            deduped.append(error)
        return deduped

    @staticmethod
    def get_extracted_information(value: Any) -> dict[str, Any]:
        payload = SkyvernSDKClient.to_plain_data(value)
        extracted = payload.get("extracted_information")
        if isinstance(extracted, dict):
            return extracted

        outputs = payload.get("outputs")
        if isinstance(outputs, dict):
            for output in outputs.values():
                if isinstance(output, dict):
                    info = output.get("extracted_information")
                    if isinstance(info, dict):
                        return info
        return {}

    @staticmethod
    def get_screenshot_urls(value: Any) -> list[str]:
        payload = SkyvernSDKClient.to_plain_data(value)
        raw = payload.get("screenshot_urls")
        if isinstance(raw, list):
            return [str(item) for item in raw if str(item).strip()]
        return []

    @staticmethod
    def get_recording_url(value: Any) -> str | None:
        payload = SkyvernSDKClient.to_plain_data(value)
        recording_url = payload.get("recording_url")
        if isinstance(recording_url, str) and recording_url.strip():
            return recording_url.strip()
        return None

    @staticmethod
    def get_workflow_run_id(value: Any) -> str | None:
        payload = SkyvernSDKClient.to_plain_data(value)
        workflow_run_id = payload.get("workflow_run_id")
        if workflow_run_id:
            return str(workflow_run_id)
        return None

    def _build_client(self, config: SkyvernRunnerConfig) -> Any:
        module = _import_skyvern_module()
        skyvern_cls = getattr(module, "Skyvern", None)
        if skyvern_cls is None:
            raise SkyvernSDKError(
                "Skyvern package is installed but Skyvern client class is missing."
            )

        kwargs = {
            "base_url": config.base_url,
            "api_key": config.api_key,
            "browser_path": config.browser_path,
        }
        filtered = _filter_kwargs(skyvern_cls, kwargs)
        try:
            return skyvern_cls(**filtered)
        except Exception as exc:
            raise SkyvernSDKError(
                f"Failed to initialize Skyvern client: {exc}"
            ) from exc


def _import_skyvern_module() -> ModuleType:
    try:
        return import_module("skyvern")
    except Exception as exc:  # pragma: no cover - exercised via integration.
        raise SkyvernSDKError(
            "Skyvern SDK is not available. Install project dependencies with "
            '`pip install -e ".[dev]"` after adding Skyvern to dependencies.'
        ) from exc


def _filter_kwargs(callable_obj: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    signature = inspect.signature(callable_obj)
    if any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()
    ):
        return {k: v for k, v in kwargs.items() if v is not None}

    supported = set(signature.parameters.keys())
    filtered: dict[str, Any] = {}
    for key, value in kwargs.items():
        if key in supported and value is not None:
            filtered[key] = value
    return filtered


async def _call_compatible(method: Any, kwargs: dict[str, Any]) -> Any:
    filtered = _filter_kwargs(method, kwargs)
    value = method(**filtered)
    if inspect.isawaitable(value):
        return await value
    return value


def _plainify_json_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _plainify_json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plainify_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_plainify_json_value(item) for item in value]
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return _plainify_json_value(value.model_dump())
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _plainify_json_value(value.to_dict())
    if hasattr(value, "__dict__"):
        return {
            key: _plainify_json_value(val)
            for key, val in vars(value).items()
            if not key.startswith("_")
        }
    return str(value)
