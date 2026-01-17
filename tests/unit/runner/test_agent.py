from __future__ import annotations

from pathlib import Path

import browser_use

from src.hitl.tools import create_hitl_tools
from src.runner.agent import create_application_agent
from src.runner.models import ApplicationRunResult


def test_creates_agent_with_tools_and_output_model_schema(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, object] = {}

    class DummyAgent:
        def __init__(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs

    monkeypatch.setattr(browser_use, "Agent", DummyAgent)

    tools = create_hitl_tools()
    conversation_path = tmp_path / "conversation.jsonl"

    create_application_agent(
        job_url="https://example.com/jobs/123",
        browser=object(),
        llm=object(),
        tools=tools,
        available_file_paths=["/tmp/resume.pdf"],
        save_conversation_path=conversation_path,
        max_failures=7,
        max_actions_per_step=5,
    )

    kwargs = captured["kwargs"]
    assert kwargs["tools"] is tools
    assert kwargs["output_model_schema"] is ApplicationRunResult


def test_agent_is_configured_for_batching_and_retries(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, object] = {}

    class DummyAgent:
        def __init__(self, *_args, **kwargs):
            captured["kwargs"] = kwargs

    monkeypatch.setattr(browser_use, "Agent", DummyAgent)

    create_application_agent(
        job_url="https://example.com/jobs/123",
        browser=object(),
        llm=object(),
        tools=create_hitl_tools(),
        available_file_paths=["/tmp/resume.pdf"],
        save_conversation_path=tmp_path / "conversation.jsonl",
        max_failures=9,
        max_actions_per_step=6,
    )

    kwargs = captured["kwargs"]
    assert kwargs["max_failures"] == 9
    assert kwargs["max_actions_per_step"] == 6


def test_passes_available_file_paths_limited_to_generated_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, object] = {}

    class DummyAgent:
        def __init__(self, *_args, **kwargs):
            captured["kwargs"] = kwargs

    monkeypatch.setattr(browser_use, "Agent", DummyAgent)

    create_application_agent(
        job_url="https://example.com/jobs/123",
        browser=object(),
        llm=object(),
        tools=create_hitl_tools(),
        available_file_paths=["/tmp/resume.pdf", "/tmp/cover.pdf"],
        save_conversation_path=tmp_path / "conversation.jsonl",
        max_failures=3,
        max_actions_per_step=4,
    )

    assert captured["kwargs"]["available_file_paths"] == [
        "/tmp/resume.pdf",
        "/tmp/cover.pdf",
    ]


def test_sets_save_conversation_path_per_run(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    class DummyAgent:
        def __init__(self, *_args, **kwargs):
            captured["kwargs"] = kwargs

    monkeypatch.setattr(browser_use, "Agent", DummyAgent)

    path = tmp_path / "conversation.jsonl"
    create_application_agent(
        job_url="https://example.com/jobs/123",
        browser=object(),
        llm=object(),
        tools=create_hitl_tools(),
        available_file_paths=["/tmp/resume.pdf"],
        save_conversation_path=path,
        max_failures=3,
        max_actions_per_step=4,
    )

    assert captured["kwargs"]["save_conversation_path"] == path
