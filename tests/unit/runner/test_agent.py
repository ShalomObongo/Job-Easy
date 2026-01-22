from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import browser_use

from src.hitl.tools import create_hitl_tools
from src.runner.agent import create_application_agent, get_application_prompt
from src.runner.models import ApplicationRunResult


def test_creates_agent_with_tools_and_output_model_schema(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, Any] = {}

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

    kwargs: dict[str, Any] = captured["kwargs"]
    assert kwargs["tools"] is tools
    assert kwargs["output_model_schema"] is ApplicationRunResult


def test_agent_is_configured_for_batching_and_retries(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, Any] = {}

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

    kwargs: dict[str, Any] = captured["kwargs"]
    assert kwargs["max_failures"] == 9
    assert kwargs["max_actions_per_step"] == 6


def test_passes_available_file_paths_limited_to_generated_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, Any] = {}

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
    captured: dict[str, Any] = {}

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


def test_get_runner_llm_passes_reasoning_effort_override(monkeypatch) -> None:
    from src.extractor.config import ExtractorConfig
    from src.runner.agent import get_runner_llm

    captured: dict[str, Any] = {}

    def fake_get_llm(config: ExtractorConfig):
        captured["config"] = config
        return object()

    monkeypatch.setattr("src.runner.agent.get_llm", fake_get_llm)
    monkeypatch.setattr(
        "src.runner.agent.get_extractor_config",
        lambda: ExtractorConfig.model_validate({"llm_provider": "openai"}),
    )

    settings = SimpleNamespace(
        runner_llm_provider=None,
        runner_llm_api_key=None,
        runner_llm_base_url=None,
        runner_llm_model=None,
        runner_llm_reasoning_effort="high",
    )

    get_runner_llm(settings)
    config: Any = captured["config"]
    assert isinstance(config, ExtractorConfig)
    assert config.llm_reasoning_effort == "high"


def test_get_runner_llm_falls_back_to_extractor_reasoning_effort(monkeypatch) -> None:
    from src.extractor.config import ExtractorConfig
    from src.runner.agent import get_runner_llm

    captured: dict[str, Any] = {}

    def fake_get_llm(config: ExtractorConfig):
        captured["config"] = config
        return object()

    monkeypatch.setattr("src.runner.agent.get_llm", fake_get_llm)
    monkeypatch.setattr(
        "src.runner.agent.get_extractor_config",
        lambda: ExtractorConfig.model_validate(
            {"llm_provider": "openai", "llm_reasoning_effort": "medium"}
        ),
    )

    settings = SimpleNamespace(
        runner_llm_provider=None,
        runner_llm_api_key=None,
        runner_llm_base_url=None,
        runner_llm_model=None,
        runner_llm_reasoning_effort=None,
    )

    get_runner_llm(settings)
    config: Any = captured["config"]
    assert isinstance(config, ExtractorConfig)
    assert config.llm_reasoning_effort == "medium"


def test_get_application_prompt_includes_yolo_context() -> None:
    prompt = get_application_prompt(
        "https://example.com/jobs/123",
        yolo_mode=True,
        yolo_context={"job": {"company": "ACME"}, "user": {"name": "Jane"}},
        available_file_paths=["artifacts/runs/example/resume.pdf"],
    )

    assert "YOLO mode is enabled" in prompt
    assert '"company": "ACME"' in prompt
    assert "Files available for upload" in prompt
    assert "artifacts/runs/example/resume.pdf" in prompt
    assert "confirm_submit" in prompt
