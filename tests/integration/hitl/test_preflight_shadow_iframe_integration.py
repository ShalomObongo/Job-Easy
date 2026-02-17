from __future__ import annotations

import asyncio
import contextlib
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import cast

import pytest
from browser_use import BrowserSession

from src.hitl.tools import preflight_find_blockers


@contextlib.contextmanager
def _serve_directory(directory: Path):
    class _FixtureHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, format: str, *_args) -> None:
            _ = format
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    host, port = cast(tuple[str, int], server.server_address)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_preflight_find_blockers_detects_required_in_shadow_and_iframe() -> None:
    """Optional integration test for real DOM traversal (shadow root + iframe).

    This is best-effort and requires a working local Browser Use setup.
    """
    if not os.getenv("RUN_PREFLIGHT_INTEGRATION"):
        pytest.skip("Set RUN_PREFLIGHT_INTEGRATION=1 to run this test")

    fixture_dir = Path(__file__).resolve().parents[1] / "fixtures"
    fixture_name = "preflight_shadow_iframe.html"

    session = BrowserSession(is_local=True, headless=True)  # type: ignore[call-arg]
    await session.start()
    blockers: list[str] = []
    try:
        with _serve_directory(fixture_dir) as base_url:
            await session.navigate_to(f"{base_url}/{fixture_name}")
            for _ in range(20):
                await asyncio.sleep(0.25)
                blockers = await preflight_find_blockers(session)
                labels = {str(item).removeprefix("invalid:") for item in blockers}
                if {"Shadow Required", "Iframe Required"} <= labels:
                    break
    finally:
        await session.kill()

    labels = {str(item).removeprefix("invalid:") for item in blockers}
    assert {"Shadow Required", "Iframe Required"} <= labels
