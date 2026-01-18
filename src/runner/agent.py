"""Browser Use agent factory for the application runner."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from src.extractor.agent import get_llm
from src.extractor.config import ExtractorConfig, get_extractor_config
from src.hitl.tools import create_hitl_tools
from src.runner.models import ApplicationRunResult
from src.runner.qa_bank import QABank

logger = logging.getLogger(__name__)


def create_browser(settings: Any, prohibited_domains: list[str] | None = None) -> Any:
    """Create a Browser instance for application runs.

    Uses a blocklist-first policy by default (prohibited_domains only).
    """
    from browser_use import Browser

    # Prefer a visible browser for application flows.
    headless = getattr(settings, "runner_headless", False)
    window_width = getattr(settings, "runner_window_width", 1280)
    window_height = getattr(settings, "runner_window_height", 720)

    browser_kwargs: dict[str, Any] = {
        "is_local": True,
        "use_cloud": False,
        "cloud_browser": False,
        "headless": headless,
        "window_size": {"width": window_width, "height": window_height},
    }

    if prohibited_domains:
        browser_kwargs["prohibited_domains"] = prohibited_domains

    if getattr(settings, "use_existing_chrome_profile", False) and getattr(
        settings, "chrome_user_data_dir", None
    ):
        from src.extractor.agent import _create_chrome_profile_snapshot

        browser_kwargs["channel"] = "chrome"
        browser_kwargs["profile_directory"] = settings.chrome_profile_dir

        if settings.chrome_profile_mode == "copy":
            browser_kwargs["user_data_dir"] = _create_chrome_profile_snapshot(
                Path(settings.chrome_user_data_dir), settings.chrome_profile_dir
            )
        else:
            local_state_path = Path(settings.chrome_user_data_dir) / "Local State"
            if local_state_path.exists() and not os.access(local_state_path, os.R_OK):
                browser_kwargs["user_data_dir"] = _create_chrome_profile_snapshot(
                    Path(settings.chrome_user_data_dir),
                    settings.chrome_profile_dir,
                )
            else:
                browser_kwargs["user_data_dir"] = settings.chrome_user_data_dir

    try:
        return Browser(**browser_kwargs)
    except Exception as e:
        if (
            getattr(settings, "use_existing_chrome_profile", False)
            and getattr(settings, "chrome_user_data_dir", None)
            and ("Permission denied" in str(e) or isinstance(e, PermissionError))
        ):
            from src.extractor.agent import _create_chrome_profile_snapshot

            profile_dir = (
                Path(settings.chrome_user_data_dir) / settings.chrome_profile_dir
            )

            if settings.chrome_profile_mode in {"auto", "direct"}:
                logger.warning(
                    "Failed to use Chrome profile at %s (permission denied). "
                    "Retrying with a lightweight profile snapshot.",
                    profile_dir,
                )
                browser_kwargs["user_data_dir"] = _create_chrome_profile_snapshot(
                    Path(settings.chrome_user_data_dir),
                    settings.chrome_profile_dir,
                )
                return Browser(**browser_kwargs)

            logger.warning(
                "Failed to use existing Chrome profile at %s (permission denied). "
                "Falling back to a fresh browser profile. "
                "Fix by using `CHROME_PROFILE_MODE=auto` (recommended), choosing a different "
                "`CHROME_PROFILE_DIR` (e.g. `Profile 2`), or fixing file permissions.",
                profile_dir,
            )
            browser_kwargs.pop("channel", None)
            browser_kwargs.pop("user_data_dir", None)
            browser_kwargs.pop("profile_directory", None)
            return Browser(**browser_kwargs)

        raise


def create_application_agent(
    *,
    job_url: str,
    browser: Any,
    llm: Any,
    tools: Any | None = None,
    available_file_paths: list[str] | None = None,
    save_conversation_path: str | Path | None = None,
    qa_bank_path: str | Path | None = None,
    sensitive_data: dict[str, str] | None = None,
    max_failures: int = 3,
    max_actions_per_step: int = 4,
    step_timeout: int = 120,
    use_vision: bool | str = "auto",
) -> Any:
    """Create a Browser Use Agent configured for generic application flows."""
    from browser_use import Agent

    task = get_application_prompt(job_url)

    if tools is None:
        tools = create_hitl_tools()

    if qa_bank_path is not None:
        qa_bank = QABank(qa_bank_path)
        qa_bank.load()

        @tools.action(
            description=(
                "Resolve an answer for an application question from the saved Q&A bank. "
                "If missing, ask the human and save the answer for next time."
            )
        )
        def resolve_answer(question: str, context: str | None = None) -> str:
            existing = qa_bank.get_answer(question, context)
            if existing is not None:
                return existing

            while True:
                answer = input(f"{question} > ").strip()
                if not answer:
                    print("Please enter an answer (cannot be blank).")
                    continue
                normalized = answer.strip().lower()
                if (
                    normalized in {"answer yourself", "make it up", "invent"}
                    or "fabricat" in normalized
                ):
                    print(
                        "Please provide your own truthful answer (I can't fabricate responses for applications)."
                    )
                    continue
                qa_bank.record_answer(question, answer, context)
                return answer

    return Agent(
        task=task,
        browser=browser,
        llm=llm,
        tools=tools,
        output_model_schema=ApplicationRunResult,
        available_file_paths=available_file_paths,
        save_conversation_path=save_conversation_path,
        sensitive_data=sensitive_data,
        max_failures=max_failures,
        max_actions_per_step=max_actions_per_step,
        step_timeout=step_timeout,
        use_vision=use_vision,
    )


def get_application_prompt(job_url: str) -> str:
    """Build the task prompt for a generic job application flow."""
    return f"""You are applying to a job starting from this URL: {job_url}

Goal:
- Reach the final submit step, then STOP and ask for explicit confirmation.
- Only submit after the user explicitly confirms by typing YES (use the confirm_submit tool).

Applicant info (sensitive placeholders; never invent values):
- first_name
- last_name
- full_name
- email
- phone
- location
- linkedin_url

Form filling rules:
0) Never guess answers for application questions. If the answer is not one of the placeholders above, use resolve_answer(question, context).
1) For dropdowns/combobox fields, do NOT type with input(). Instead:
   - Use dropdown_options(index) to see available options (if needed), then
   - Use select_dropdown(index, text) with the exact visible option text.
2) If browser_state shows required-field errors (e.g. "This field is required.", "Resume/CV is required.", or invalid=true on required inputs), you are NOT at the final submit step yet. Fix missing fields/uploads first.
3) Only upload the cover letter if there is a dedicated "Cover Letter" upload field. Never overwrite the Resume/CV field with the cover letter.

Flow handling:
1) If this is a job posting page, find and click an Apply / Apply Now button.
2) If this is a direct application form, start filling it.
3) Handle multi-step flows (Next/Continue buttons, modals, multiple pages).
4) Upload the provided resume/cover letter files when asked (only use available_file_paths).
5) For unknown questions, use resolve_answer(question, context) to load from the Q&A bank; if missing,
   it will ask the human and persist for next time.
6) If CAPTCHA/2FA appears, stop and ask the user for manual help; do not bypass.

Submit gate (required):
- When you are on the final review step and the next click would submit the application:
  - Call confirm_submit only when all required fields are complete and you are truly ready to submit.
  - Call confirm_submit with prompt: "Type YES to submit this application"
  - Also pass submit_button_index as the element index of the final submit button you intend to click.
  - The confirm_submit tool will ask the human and (if confirmed) click the submit button for you.
  - If the tool returns "submitted", proceed to verify submission (confirmation text/screenshot) and finish with status submitted.
  - If the tool returns "blocked_missing_fields", do NOT submit; fill the missing required fields and only then call confirm_submit again.
  - If the tool returns "confirmed", the human confirmed but the click failed; you must click the final submit button yourself.
  - If the tool returns anything else ("cancelled"), do not submit and finish with status stopped_before_submit.

Return a structured result matching ApplicationRunResult with:
- success (bool)
- status: submitted | stopped_before_submit | failed | blocked
- proof_text if a confirmation message is visible after submit
- any errors/notes you encountered
"""


def get_runner_llm(settings: Any | None = None) -> Any | None:
    """Get an LLM instance for the runner.

    Priority order:
    1) RUNNER_LLM_* (settings)
    2) EXTRACTOR_LLM_* (extractor config)
    3) Provider defaults (OPENAI_API_KEY / ANTHROPIC_API_KEY / BROWSER_USE_API_KEY)
    """
    base = get_extractor_config()

    provider = getattr(settings, "runner_llm_provider", None) or base.llm_provider
    api_key = getattr(settings, "runner_llm_api_key", None) or base.llm_api_key
    base_url = getattr(settings, "runner_llm_base_url", None) or base.llm_base_url
    model = getattr(settings, "runner_llm_model", None) or base.llm_model

    runner_config = ExtractorConfig(
        llm_provider=provider,
        llm_api_key=api_key,
        llm_base_url=base_url,
        llm_model=model,
    )
    return get_llm(runner_config)
