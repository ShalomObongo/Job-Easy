"""Skyvern-backed application runner implementation."""

from __future__ import annotations

import asyncio
import contextlib
import json
import mimetypes
import secrets
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from src.extractor.models import JobDescription
from src.runner.domains import is_prohibited, record_allowed_domain
from src.runner.models import ApplicationRunResult, RunStatus
from src.runner.qa_bank import ScopeHint
from src.runner.skyvern_config import (
    SkyvernConfigurationError,
    resolve_runner_skyvern_config,
    temporary_env_overrides,
)
from src.runner.skyvern_profiles import SkyvernProfileError, resolve_browser_profile
from src.runner.skyvern_prompt import (
    build_data_extraction_schema,
    build_runner_prompt,
    build_workflow_data,
)
from src.runner.skyvern_sdk import SkyvernSDKClient, SkyvernSDKError
from src.runner.yolo import build_yolo_context
from src.tracker.fingerprint import compute_fingerprint, extract_job_id


def build_skyvern_apply_scope_hints(
    *,
    url: str,
    job: JobDescription | None = None,
) -> list[ScopeHint]:
    """Build scope hints for compatibility notes and prompt context."""
    domain = urlparse(url).netloc.strip().lower()
    hints: list[ScopeHint] = []

    if job is not None:
        job_id = job.job_id or extract_job_id(job.apply_url or job.job_url or url)
        fingerprint = compute_fingerprint(
            url=job.apply_url or job.job_url or url,
            job_id=job_id,
            company=job.company,
            role=job.role_title,
            location=job.location,
        )
        hints.append(("job", fingerprint))
        company_key = str(job.company or "").strip().lower()
        if company_key:
            hints.append(("company", company_key))

    if domain:
        hints.append(("domain", domain))
    hints.append(("global", None))
    return hints


def expand_upload_paths(paths: list[str | Path | None]) -> list[str]:
    """Return unique original + absolute upload file paths."""
    expanded: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        if raw is None:
            continue
        raw_str = str(raw).strip()
        if not raw_str:
            continue
        for candidate in (raw_str, str(Path(raw_str).expanduser().resolve())):
            if candidate in seen:
                continue
            seen.add(candidate)
            expanded.append(candidate)
    return expanded


@dataclass
class _UploadReferences:
    resume_path: str | None
    cover_letter_path: str | None
    available_file_paths: list[str]
    notes: list[str]


class _LocalUploadFileServer:
    """Serve local upload artifacts over loopback HTTP for Skyvern file fetching."""

    def __init__(self, files: list[Path]) -> None:
        unique_files: list[Path] = []
        seen: set[Path] = set()
        for path in files:
            resolved = path.expanduser().resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            unique_files.append(resolved)

        self._files = unique_files
        self._token_to_path = {secrets.token_urlsafe(16): path for path in self._files}
        self._url_by_path: dict[Path, str] = {}
        self._server: ThreadingHTTPServer | None = None
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._server is not None:
            return

        handler_cls = self._build_handler()
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        server.daemon_threads = True
        thread = Thread(
            target=server.serve_forever,
            name="skyvern-upload-file-server",
            daemon=True,
        )
        thread.start()

        self._server = server
        self._thread = thread

        host, port = server.server_address[:2]
        for token, path in self._token_to_path.items():
            self._url_by_path[path] = f"http://{host}:{port}/files/{token}/{path.name}"

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def url_for(self, path: Path) -> str | None:
        resolved = path.expanduser().resolve()
        return self._url_by_path.get(resolved)

    def _build_handler(self) -> type[BaseHTTPRequestHandler]:
        token_to_path = dict(self._token_to_path)

        class UploadHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parts = urlparse(self.path).path.split("/")
                if len(parts) < 4 or parts[1] != "files":
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return

                token = parts[2]
                file_path = token_to_path.get(token)
                if file_path is None or not file_path.exists():
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return

                try:
                    payload = file_path.read_bytes()
                except OSError:
                    self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
                    return

                content_type = (
                    mimetypes.guess_type(file_path.name)[0]
                    or "application/octet-stream"
                )
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, fmt: str, *args: Any) -> None:
                _ = (fmt, args)

        return UploadHandler


def _resolve_existing_file_path(raw: str | None) -> Path | None:
    if raw is None:
        return None
    raw_str = str(raw).strip()
    if not raw_str:
        return None
    candidate = Path(raw_str).expanduser()
    with contextlib.suppress(Exception):
        candidate = candidate.resolve()
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate


@contextlib.contextmanager
def _prepare_upload_references(
    *,
    resume_path: str | None,
    cover_letter_path: str | None,
) -> Any:
    resolved_resume = _resolve_existing_file_path(resume_path)
    resolved_cover = _resolve_existing_file_path(cover_letter_path)
    server_files = [
        path for path in (resolved_resume, resolved_cover) if path is not None
    ]

    if not server_files:
        yield _UploadReferences(
            resume_path=resume_path,
            cover_letter_path=cover_letter_path,
            available_file_paths=expand_upload_paths([resume_path, cover_letter_path]),
            notes=[],
        )
        return

    server = _LocalUploadFileServer(server_files)
    server.start()
    try:
        served_resume = (
            server.url_for(resolved_resume)
            if resolved_resume is not None
            else resume_path
        )
        served_cover = (
            server.url_for(resolved_cover)
            if resolved_cover is not None
            else cover_letter_path
        )
        available_paths = [
            candidate
            for candidate in (served_resume, served_cover)
            if isinstance(candidate, str) and candidate.strip()
        ]
        server_origin = None
        for value in available_paths:
            parsed = urlparse(value)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                server_origin = f"{parsed.scheme}://{parsed.netloc}"
                break
        notes = [f"skyvern_upload_server={server_origin}"] if server_origin else []
        yield _UploadReferences(
            resume_path=served_resume,
            cover_letter_path=served_cover,
            available_file_paths=available_paths,
            notes=notes,
        )
    finally:
        server.stop()


async def run_application_with_skyvern(
    *,
    settings: Any,
    job_url: str,
    run_dir: Path,
    profile: Any | None,
    resume_path: str | None,
    cover_letter_path: str | None,
    qa_scope_hints: list[ScopeHint] | None = None,
    yolo_mode: bool = False,
    yolo_context: dict[str, Any] | None = None,
    auto_submit: bool = False,
    job: JobDescription | None = None,
) -> ApplicationRunResult:
    """Run job application execution through Skyvern and persist artifacts."""
    run_dir.mkdir(parents=True, exist_ok=True)
    conversation_path = run_dir / "conversation.jsonl"
    execution_path = run_dir / "skyvern_execution.json"
    artifacts_path = run_dir / "skyvern_artifacts.json"
    result_path = run_dir / "application_result.json"

    prohibited_domains = list(getattr(settings, "prohibited_domains", []))
    allowlist_log_path = getattr(
        settings,
        "allowlist_log_path",
        Path("./data/allowlist.log"),
    )

    try:
        config = resolve_runner_skyvern_config(settings)
    except SkyvernConfigurationError as exc:
        result = ApplicationRunResult(
            success=False,
            status=RunStatus.FAILED,
            errors=[str(exc)],
        )
        with contextlib.suppress(Exception):
            result.save_json(result_path)
        return result

    if prohibited_domains and is_prohibited(job_url, prohibited_domains):
        result = ApplicationRunResult(
            success=False,
            status=RunStatus.BLOCKED,
            errors=["Domain is prohibited by configuration"],
        )
        with contextlib.suppress(Exception):
            result.save_json(result_path)
        return result

    if yolo_mode and yolo_context is None and job is not None and profile is not None:
        yolo_context = build_yolo_context(job=job, profile=profile)

    extraction_schema = build_data_extraction_schema()
    notes: list[str] = []
    if qa_scope_hints:
        notes.append(
            "qa_scope_hints="
            + ",".join(f"{scope}:{value or ''}" for scope, value in qa_scope_hints)
        )

    client: SkyvernSDKClient
    run_response: Any
    with _prepare_upload_references(
        resume_path=resume_path,
        cover_letter_path=cover_letter_path,
    ) as upload_refs:
        notes.extend(upload_refs.notes)
        prompt = build_runner_prompt(
            job_url=job_url,
            job=job,
            profile=profile,
            resume_path=upload_refs.resume_path,
            cover_letter_path=upload_refs.cover_letter_path,
            yolo_mode=yolo_mode,
            yolo_context=yolo_context,
            auto_submit=auto_submit,
        )

        with temporary_env_overrides(config.llm_env_overrides):
            try:
                client = SkyvernSDKClient(config=config)
            except Exception as exc:
                result = ApplicationRunResult(
                    success=False,
                    status=RunStatus.FAILED,
                    errors=[str(exc)],
                    notes=notes + config.llm_mapping_notes,
                )
                with contextlib.suppress(Exception):
                    result.save_json(result_path)
                return result

            if config.verify_health:
                try:
                    await client.check_health()
                except SkyvernSDKError as exc:
                    result = ApplicationRunResult(
                        success=False,
                        status=RunStatus.FAILED,
                        errors=[str(exc)],
                    )
                    with contextlib.suppress(Exception):
                        result.save_json(result_path)
                    return result

            bootstrap_data = build_workflow_data(
                prompt=prompt,
                job=job,
                profile=profile,
                resume_path=upload_refs.resume_path,
                cover_letter_path=upload_refs.cover_letter_path,
            )
            try:
                profile_resolution = await resolve_browser_profile(
                    config=config,
                    client=client,
                    bootstrap_data=bootstrap_data,
                )
                notes.extend(profile_resolution.notes)
            except SkyvernProfileError as exc:
                result = ApplicationRunResult(
                    success=False,
                    status=RunStatus.FAILED,
                    errors=[str(exc)],
                )
                with contextlib.suppress(Exception):
                    result.save_json(result_path)
                return result

            browser_profile_id = profile_resolution.browser_profile_id

            try:
                if config.workflow_id:
                    workflow_data = build_workflow_data(
                        prompt=prompt,
                        job=job,
                        profile=profile,
                        resume_path=upload_refs.resume_path,
                        cover_letter_path=upload_refs.cover_letter_path,
                    )
                    if browser_profile_id:
                        workflow_data["browser_profile_id"] = browser_profile_id
                    if config.browser_session_id:
                        workflow_data["browser_session_id"] = config.browser_session_id
                    if config.browser_address:
                        workflow_data["browser_address"] = config.browser_address
                    if upload_refs.available_file_paths:
                        workflow_data["available_file_paths"] = (
                            upload_refs.available_file_paths
                        )
                    run_response = await asyncio.wait_for(
                        client.run_workflow(
                            workflow_id=config.workflow_id,
                            data=workflow_data,
                        ),
                        timeout=config.max_wait_seconds,
                    )
                    notes.append(f"skyvern_workflow_id={config.workflow_id}")
                else:
                    run_task_kwargs: dict[str, Any] = {
                        "prompt": prompt,
                        "url": job_url,
                        "wait_for_completion": True,
                        "data_extraction_schema": extraction_schema,
                        "max_steps": getattr(settings, "runner_max_actions_per_step", 4)
                        * 8,
                        "browser_profile_id": browser_profile_id,
                        "browser_session_id": config.browser_session_id,
                        "browser_address": config.browser_address,
                        "persist_browser_session": config.persist_browser_session,
                        "error_code_mapping": {
                            "otp_required_non_interactive": (
                                "OTP/CAPTCHA required and cannot be bypassed."
                            ),
                            "unknown_required_question": (
                                "Required question lacked a known truthful answer."
                            ),
                        },
                    }
                    run_response = await asyncio.wait_for(
                        client.run_task(**run_task_kwargs),
                        timeout=config.max_wait_seconds,
                    )
                    notes.append(
                        "skyvern_wait_policy="
                        f"max_wait={config.max_wait_seconds}s poll={config.poll_interval_seconds}s"
                    )
            except TimeoutError:
                result = ApplicationRunResult(
                    success=False,
                    status=RunStatus.FAILED,
                    errors=[
                        "Skyvern run timed out before reaching a terminal state. "
                        f"Increase RUNNER_SKYVERN_MAX_WAIT_SECONDS (current={config.max_wait_seconds})."
                    ],
                    notes=notes + config.llm_mapping_notes,
                )
                with contextlib.suppress(Exception):
                    result.save_json(result_path)
                return result
            except SkyvernSDKError as exc:
                result = ApplicationRunResult(
                    success=False,
                    status=RunStatus.FAILED,
                    errors=[str(exc)],
                    notes=notes + config.llm_mapping_notes,
                )
                with contextlib.suppress(Exception):
                    result.save_json(result_path)
                return result
            except Exception as exc:  # pragma: no cover - defensive for SDK drift
                result = ApplicationRunResult(
                    success=False,
                    status=RunStatus.FAILED,
                    errors=[f"Skyvern execution failed: {exc}"],
                    notes=notes + config.llm_mapping_notes,
                )
                with contextlib.suppress(Exception):
                    result.save_json(result_path)
                return result

    payload = client.to_plain_data(run_response)
    with contextlib.suppress(Exception):
        execution_path.write_text(
            json.dumps(payload, indent=2, default=str),
            encoding="utf-8",
        )

    with (
        contextlib.suppress(Exception),
        conversation_path.open("w", encoding="utf-8") as stream,
    ):
        stream.write(json.dumps(payload, default=str))
        stream.write("\n")

    result = _map_skyvern_result(
        run_response=run_response,
        auto_submit=auto_submit,
        notes=notes + config.llm_mapping_notes,
    )

    if prohibited_domains:
        prohibited_hit = _find_first_prohibited_url(
            urls=[result.final_url, *result.visited_urls],
            prohibited_domains=prohibited_domains,
        )
        if prohibited_hit:
            result.success = False
            result.status = RunStatus.BLOCKED
            result.errors.append(f"Prohibited domain encountered: {prohibited_hit}")

    screenshot_urls = client.get_screenshot_urls(run_response)
    recording_url = client.get_recording_url(run_response)
    if screenshot_urls or recording_url:
        artifact_payload = {
            "screenshot_urls": screenshot_urls,
            "recording_url": recording_url,
        }
        with contextlib.suppress(Exception):
            artifacts_path.write_text(
                json.dumps(artifact_payload, indent=2),
                encoding="utf-8",
            )
        if recording_url:
            result.notes.append(f"skyvern_recording_url={recording_url}")
        if screenshot_urls:
            result.notes.append(f"skyvern_screenshot_urls={len(screenshot_urls)}")

    if screenshot_urls:
        proof_path = run_dir / "proof.png"
        downloaded = await _download_first_screenshot(
            screenshot_urls=screenshot_urls,
            output_path=proof_path,
            timeout_seconds=config.timeout_seconds,
        )
        if downloaded:
            result.proof_screenshot_path = str(proof_path)

    if result.visited_urls:
        for visited in result.visited_urls:
            if prohibited_domains and is_prohibited(visited, prohibited_domains):
                continue
            with contextlib.suppress(Exception):
                record_allowed_domain(visited, allowlist_log_path)

    with contextlib.suppress(Exception):
        result.save_json(result_path)

    return result


def _map_skyvern_result(
    *,
    run_response: Any,
    auto_submit: bool,
    notes: list[str],
) -> ApplicationRunResult:
    client_status = SkyvernSDKClient.get_status(run_response)
    extracted = SkyvernSDKClient.get_extracted_information(run_response)
    extracted_status = _coerce_status(extracted.get("status"))

    status = _derive_run_status(
        sdk_status=client_status,
        extracted_status=extracted_status,
        auto_submit=auto_submit,
    )

    errors = SkyvernSDKClient.get_errors(run_response)
    extracted_errors = extracted.get("errors")
    if isinstance(extracted_errors, list):
        errors.extend(str(item) for item in extracted_errors if str(item).strip())

    extracted_notes = extracted.get("notes")
    collected_notes = list(notes)
    if isinstance(extracted_notes, list):
        collected_notes.extend(
            str(item) for item in extracted_notes if str(item).strip()
        )

    proof_text = _coerce_optional_string(extracted.get("proof_text"))
    final_url = _coerce_optional_string(extracted.get("final_url"))
    visited_urls = _coerce_list(extracted.get("visited_urls"))

    raw_payload = SkyvernSDKClient.to_plain_data(run_response)
    if not final_url:
        final_url = _coerce_optional_string(raw_payload.get("final_url"))
    if not visited_urls:
        visited_urls = _coerce_list(raw_payload.get("visited_urls"))
    if final_url and final_url not in visited_urls:
        visited_urls.append(final_url)

    success_raw = extracted.get("success")
    success = (
        bool(success_raw)
        if isinstance(success_raw, bool)
        else _status_is_success(status)
    )

    if status in {RunStatus.FAILED, RunStatus.BLOCKED}:
        success = False

    return ApplicationRunResult(
        success=success,
        status=status,
        final_url=final_url,
        visited_urls=visited_urls,
        proof_text=proof_text,
        errors=_dedupe(errors),
        notes=_dedupe(collected_notes),
    )


def _derive_run_status(
    *,
    sdk_status: str | None,
    extracted_status: RunStatus | None,
    auto_submit: bool,
) -> RunStatus:
    if extracted_status is not None:
        return extracted_status

    status = (sdk_status or "").lower()
    if status == "completed":
        return RunStatus.SUBMITTED if auto_submit else RunStatus.STOPPED_BEFORE_SUBMIT
    if status in {"failed", "terminated"}:
        return RunStatus.FAILED
    if status in {"cancelled", "canceled"}:
        return RunStatus.BLOCKED
    if status in {"running", "created"}:
        return RunStatus.FAILED
    return RunStatus.FAILED


def _coerce_status(value: Any) -> RunStatus | None:
    if not value:
        return None
    normalized = str(value).strip().lower()
    mapping = {
        "submitted": RunStatus.SUBMITTED,
        "stopped_before_submit": RunStatus.STOPPED_BEFORE_SUBMIT,
        "skipped": RunStatus.SKIPPED,
        "duplicate_skipped": RunStatus.DUPLICATE_SKIPPED,
        "failed": RunStatus.FAILED,
        "blocked": RunStatus.BLOCKED,
    }
    return mapping.get(normalized)


def _coerce_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _status_is_success(status: RunStatus) -> bool:
    return status in {
        RunStatus.SUBMITTED,
        RunStatus.STOPPED_BEFORE_SUBMIT,
        RunStatus.SKIPPED,
        RunStatus.DUPLICATE_SKIPPED,
    }


def _dedupe(values: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def _find_first_prohibited_url(
    *, urls: list[str | None], prohibited_domains: list[str]
) -> str | None:
    for url in urls:
        if not url:
            continue
        if is_prohibited(url, prohibited_domains):
            return url
    return None


async def _download_first_screenshot(
    *,
    screenshot_urls: list[str],
    output_path: Path,
    timeout_seconds: int,
) -> bool:
    if not screenshot_urls:
        return False

    target = screenshot_urls[0]
    if not target.startswith(("http://", "https://")):
        return False

    request = Request(target, method="GET")

    def _download() -> bool:
        with urlopen(request, timeout=timeout_seconds) as resp:
            status = int(getattr(resp, "status", 500))
            if not (200 <= status < 400):
                return False
            output_path.write_bytes(resp.read())
        return True

    try:
        return await asyncio.to_thread(_download)
    except Exception:
        return False
