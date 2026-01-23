"""Browser Use agent factory for the application runner."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Literal, cast

from src.extractor.agent import get_llm
from src.extractor.config import ExtractorConfig, get_extractor_config
from src.hitl.tools import create_hitl_tools
from src.runner.models import ApplicationRunResult
from src.runner.qa_bank import QABank, ScopeHint, ScopeType
from src.runner.yolo import classify_question, resolve_yolo_answer

logger = logging.getLogger(__name__)


def _normalize_use_vision(value: bool | str) -> bool | Literal["auto"]:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "auto":
            return "auto"
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
        return "auto"
    return bool(value)


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
    qa_scope_hints: list[ScopeHint] | None = None,
    sensitive_data: dict[str, str | dict[str, str]] | None = None,
    yolo_mode: bool = False,
    yolo_context: dict[str, Any] | None = None,
    auto_submit: bool = False,
    max_failures: int = 3,
    max_actions_per_step: int = 4,
    step_timeout: int = 120,
    use_vision: bool | str = "auto",
) -> Any:
    """Create a Browser Use Agent configured for generic application flows."""
    from browser_use import Agent

    task = get_application_prompt(
        job_url,
        yolo_mode=yolo_mode,
        yolo_context=yolo_context,
        auto_submit=auto_submit,
        available_file_paths=available_file_paths,
    )

    if tools is None:
        tools = create_hitl_tools(auto_submit=auto_submit)

    if qa_bank_path is not None:
        qa_bank = QABank(qa_bank_path)
        qa_bank.load()

        scope_hints: list[ScopeHint] = qa_scope_hints or [("global", None)]

        def infer_category(question: str, category: str | None) -> str:
            return str(category or classify_question(question)).strip().lower()

        def pick_scope(category: str) -> tuple[ScopeType, str | None]:
            # Motivation prompts are commonly company/job-specific; prefer the most specific
            # scope available.
            if category == "motivation":
                for scope_type, scope_key in scope_hints:
                    if scope_type != "global" and scope_key is not None:
                        return scope_type, scope_key
            return "global", None

        resolve_description = (
            "Resolve an answer for an application question from the saved Q&A bank. "
            "If missing, ask the human and save the answer for next time."
            if not yolo_mode
            else "YOLO mode: retrieve or generate a best-effort answer (never prompts the human; may return an empty string when not possible)."
        )

        @tools.action(description=resolve_description)
        def resolve_answer(
            question: str,
            context: str | None = None,
            category: str | None = None,
            field_type: str | None = None,
            options: list[str] | None = None,
        ) -> str:
            effective_category = infer_category(question, category)
            existing = qa_bank.get_answer(
                question,
                context,
                scope_hints=scope_hints,
                category=effective_category,
            )
            if existing is not None:
                return existing

            if yolo_mode:
                answer, inferred_category = resolve_yolo_answer(
                    question,
                    yolo_context=yolo_context,
                    field_type=field_type,
                    options=options,
                )
                category_value = effective_category or inferred_category
                if answer:
                    scope_type, scope_key = pick_scope(category_value)
                    qa_bank.record_answer(
                        question,
                        answer,
                        context,
                        scope_type=scope_type,
                        scope_key=scope_key,
                        source="yolo",
                        category=category_value,
                    )
                return answer

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

                scope_type, scope_key = pick_scope(effective_category)
                qa_bank.record_answer(
                    question,
                    answer,
                    context,
                    scope_type=scope_type,
                    scope_key=scope_key,
                    source="user",
                    category=effective_category,
                )
                return answer

        @tools.action(
            description=(
                "Record an answer in the Q&A bank for future reuse. "
                "When in YOLO mode, use this after you generate an answer yourself."
            )
        )
        def record_answer(
            question: str,
            answer: str,
            category: str | None = None,
        ) -> str:
            answer_str = str(answer).strip()
            if not answer_str:
                return "rejected_blank"

            effective_category = infer_category(question, category)
            scope_type, scope_key = pick_scope(effective_category)
            qa_bank.record_answer(
                question,
                answer_str,
                scope_type=scope_type,
                scope_key=scope_key,
                source="yolo" if yolo_mode else "agent",
                category=effective_category,
            )
            return "ok"

    return Agent(
        task=task,
        browser=browser,
        llm=llm,
        tools=tools,
        output_model_schema=ApplicationRunResult,
        available_file_paths=available_file_paths,
        save_conversation_path=save_conversation_path,
        sensitive_data=cast(dict[str, str | dict[str, str]] | None, sensitive_data),
        max_failures=max_failures,
        max_actions_per_step=max_actions_per_step,
        step_timeout=step_timeout,
        use_vision=cast(bool | Literal["auto"], _normalize_use_vision(use_vision)),
    )


def get_application_prompt(
    job_url: str,
    *,
    yolo_mode: bool = False,
    yolo_context: dict[str, Any] | None = None,
    auto_submit: bool = False,
    available_file_paths: list[str] | None = None,
) -> str:
    """Build the task prompt for a generic job application flow."""
    yolo_section = ""
    if yolo_mode:
        context_json = "{}"
        if yolo_context is not None:
            try:
                context_json = json.dumps(yolo_context, indent=2)
            except Exception:
                context_json = "{}"

        yolo_section = f"""

YOLO mode is enabled.

You are given a job+user context payload to answer application questions best-effort.

Job + user context (JSON):
```json
{context_json}
```
"""

    file_section = ""
    if available_file_paths:
        lines = [str(p) for p in available_file_paths if str(p).strip()]
        if lines:
            joined = "\n".join(lines)
            file_section = f"""

Files available for upload (only use these exact paths):
```
{joined}
```
"""

    form_rule_0 = (
        "0) Never guess answers for application questions. If the answer is not one of "
        "the placeholders above, use resolve_answer(question, context)."
        if not yolo_mode
        else "0) YOLO mode: use resolve_answer(...) to retrieve or generate best-effort answers from the provided job+user context. Do not prompt the human for normal questions."
    )

    # Build goal section based on auto_submit mode
    if auto_submit:
        goal_section = """Goal:
- Fill out the application form completely and submit it automatically.
- AUTO-SUBMIT mode is enabled: the confirm_submit tool will automatically submit without prompting."""
    else:
        goal_section = """Goal:
- Reach the final submit step, then STOP and ask for explicit confirmation.
- Only submit after the user explicitly confirms by typing YES (use the confirm_submit tool)."""

    # Build submit gate section based on auto_submit mode
    if auto_submit:
        submit_gate_section = """Submit gate (auto-submit enabled):
- When you are on the final review step and the next click would submit the application:
  - Call confirm_submit when all required fields are complete and you are truly ready to submit.
  - Pass submit_button_index as the element index of the final submit button you intend to click.
  - AUTO-SUBMIT: The tool will automatically click the submit button without prompting the human.
  - If the tool returns "submitted", proceed to verify submission (confirmation text/screenshot) and finish with status submitted.
  - If the tool returns "blocked_missing_fields", do NOT submit; fill the missing required fields and only then call confirm_submit again.
  - If the tool returns "confirmed", the click may have failed; click the final submit button yourself."""
    else:
        submit_gate_section = """Submit gate (required):
- When you are on the final review step and the next click would submit the application:
  - Call confirm_submit only when all required fields are complete and you are truly ready to submit.
  - Call confirm_submit with prompt: "Type YES to submit this application"
  - Also pass submit_button_index as the element index of the final submit button you intend to click.
  - The confirm_submit tool will ask the human and (if confirmed) click the submit button for you.
  - If the tool returns "submitted", proceed to verify submission (confirmation text/screenshot) and finish with status submitted.
  - If the tool returns "blocked_missing_fields", do NOT submit; fill the missing required fields and only then call confirm_submit again.
  - If the tool returns "confirmed", the human confirmed but the click failed; you must click the final submit button yourself.
  - If the tool returns anything else ("cancelled"), do not submit and finish with status stopped_before_submit."""

    return f"""You are applying to a job starting from this URL: {job_url}

{goal_section}

Applicant info (sensitive placeholders; never invent values):
- first_name
- last_name
- full_name
- email
- phone
- location
- linkedin_url
- github_url

{yolo_section}

{file_section}

Form filling rules:
{form_rule_0}
1) For dropdowns/combobox fields, do NOT type with input(). Instead:
   - Use dropdown_options(index) to see available options (if needed), then
   - Use select_dropdown(index, text) with the exact visible option text.
2) If browser_state shows required-field errors (e.g. "This field is required.", "Resume/CV is required.", or invalid=true on required inputs), you are NOT at the final submit step yet. Fix missing fields/uploads first.
3) Only upload the cover letter if there is a dedicated "Cover Letter" upload field. Never overwrite the Resume/CV field with the cover letter.
4) If the cover letter field is text-only (no upload), generate a brief cover letter using the job information and company name from the page.
5) For radio button and checkbox questions (e.g., salary range, education level), you MUST select an option before proceeding. Never skip required radio/checkbox fields.

Flow handling:
1) If this is a job posting page, find and click an Apply / Apply Now button.
2) If this is a direct application form, start filling it.
3) Handle multi-step flows (Next/Continue buttons, modals, multiple pages).
4) Upload the provided resume/cover letter files when asked (only use available_file_paths).
5) For unknown questions:
   - Non-YOLO mode: use resolve_answer(question, context) to load from the Q&A bank; if missing, it will ask the human and persist for next time.
   - YOLO mode: call resolve_answer(...) to retrieve or generate a best-effort answer (it may return "" when not possible).
6) If CAPTCHA/2FA appears, stop and ask the user for manual help; do not bypass.
7) IMPORTANT: Complete ALL required fields before calling confirm_submit. Do not give up or return "blocked" status until you have tried to fill every required field including radio buttons, checkboxes, and dropdowns.

{submit_gate_section}

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
    reasoning_effort = getattr(
        settings, "runner_llm_reasoning_effort", None
    ) or getattr(base, "llm_reasoning_effort", None)

    runner_config = ExtractorConfig(
        llm_provider=provider,
        llm_api_key=api_key,
        llm_base_url=base_url,
        llm_model=model,
        llm_reasoning_effort=reasoning_effort,
    )
    return get_llm(runner_config)
