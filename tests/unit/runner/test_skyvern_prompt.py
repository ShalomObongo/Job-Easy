from __future__ import annotations

from src.runner.skyvern_prompt import build_runner_prompt


def test_build_runner_prompt_preserves_http_upload_reference() -> None:
    upload_url = "http://127.0.0.1:9999/files/token/resume.pdf"
    prompt = build_runner_prompt(
        job_url="https://example.com/apply",
        profile=None,
        resume_path=upload_url,
        cover_letter_path=None,
        yolo_mode=False,
        yolo_context=None,
        auto_submit=False,
    )

    assert f"- Resume: {upload_url}" in prompt
    assert "http:/127.0.0.1" not in prompt
