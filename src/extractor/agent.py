"""Browser Use agent factory for job extraction.

This module provides factory functions for creating Browser Use components:
- Browser instances with configuration
- Extraction agents with structured output
- LLM instances for different providers
"""

from __future__ import annotations

import contextlib
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.extractor.config import ExtractorConfig
from src.extractor.models import JobDescription

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


_CHROME_PROFILE_SNAPSHOT_SKIP_DIRS = {
    # Very large (extensions can be hundreds of MB) and not needed for auth reuse.
    "Extensions",
    # Caches
    "Cache",
    "Code Cache",
    "GPUCache",
    "GrShaderCache",
    "ShaderCache",
    "DawnGraphiteCache",
    "DawnWebGPUCache",
    # Often large and not required for login state.
    "Service Worker",
}


def _create_chrome_profile_snapshot(
    chrome_user_data_dir: Path, profile_directory: str
) -> Path:
    """Create a lightweight temp user-data-dir containing the selected Chrome profile.

    Browser Use's Chrome handling copies the selected profile AND "Local State" to a
    temp directory for safety. On managed installs, "Local State" can be unreadable
    (often root-owned), which makes startup fail.

    This snapshot avoids that by:
    - Copying only the selected profile directory (skipping large caches/extensions)
    - Copying "Local State" only if readable (otherwise Chrome regenerates it)
    - Using a path containing "browser-use-user-data-dir-" so Browser Use does NOT try
      to copy again.
    """
    src_profile = chrome_user_data_dir / profile_directory
    if not src_profile.exists():
        raise FileNotFoundError(f"Chrome profile directory not found: {src_profile}")

    snapshot_root = Path(
        tempfile.mkdtemp(prefix="browser-use-user-data-dir-job-easy-")
    ).resolve()
    dst_profile = snapshot_root / profile_directory

    for root, dirs, files in os.walk(src_profile):
        dirs[:] = [d for d in dirs if d not in _CHROME_PROFILE_SNAPSHOT_SKIP_DIRS]
        rel = Path(root).relative_to(src_profile)
        (dst_profile / rel).mkdir(parents=True, exist_ok=True)
        for file_name in files:
            src_path = Path(root) / file_name
            dst_path = dst_profile / rel / file_name
            try:
                if src_path.is_symlink():
                    target = os.readlink(src_path)
                    dst_path.symlink_to(target)
                else:
                    shutil.copy2(src_path, dst_path)
            except Exception:
                continue

    local_state_src = chrome_user_data_dir / "Local State"
    if local_state_src.exists() and os.access(local_state_src, os.R_OK):
        with contextlib.suppress(Exception):
            shutil.copy2(local_state_src, snapshot_root / "Local State")

    logger.info("Prepared Chrome profile snapshot at %s", snapshot_root)
    return snapshot_root


def create_browser(config: ExtractorConfig) -> Any:
    """Create a Browser instance with the given configuration.

    Args:
        config: Extractor configuration.

    Returns:
        Configured Browser instance.
    """
    from browser_use import Browser

    from src.config.settings import get_settings

    settings = get_settings()

    browser_kwargs: dict[str, Any] = {
        # Browser Use defaults to cloud mode; force local Playwright browser.
        "is_local": True,
        "use_cloud": False,
        "cloud_browser": False,
        "headless": config.headless,
        "window_size": {
            "width": config.window_width,
            "height": config.window_height,
        },
    }

    if config.allowed_domains:
        browser_kwargs["allowed_domains"] = config.allowed_domains

    if settings.use_existing_chrome_profile and settings.chrome_user_data_dir:
        browser_kwargs["channel"] = "chrome"
        browser_kwargs["profile_directory"] = settings.chrome_profile_dir

        if settings.chrome_profile_mode == "copy":
            browser_kwargs["user_data_dir"] = _create_chrome_profile_snapshot(
                Path(settings.chrome_user_data_dir),
                settings.chrome_profile_dir,
            )
        else:
            # direct/auto: Browser Use will attempt to copy the profile + "Local State".
            # If "Local State" is unreadable, that copy fails deterministically, so skip
            # straight to our snapshot fallback.
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
            settings.use_existing_chrome_profile
            and settings.chrome_user_data_dir
            and ("Permission denied" in str(e) or isinstance(e, PermissionError))
        ):
            profile_dir = (
                Path(settings.chrome_user_data_dir) / settings.chrome_profile_dir
            )

            if settings.chrome_profile_mode in {"auto", "direct"}:
                logger.warning(
                    "Failed to use Chrome profile at %s (permission denied). "
                    "Retrying with a lightweight profile snapshot (avoids copying Local State).",
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


def create_extraction_agent(
    url: str,
    browser: Any,
    llm: Any,
    config: ExtractorConfig,
) -> Any:
    """Create an extraction Agent with structured output.

    Args:
        url: The job posting URL to extract from.
        browser: Browser instance.
        llm: LLM instance for the agent.
        config: Extractor configuration.

    Returns:
        Configured Agent instance.
    """
    from browser_use import Agent

    task = get_extraction_prompt(url)

    return Agent(
        task=task,
        browser=browser,
        llm=llm,
        output_model_schema=JobDescription,
        use_vision=config.use_vision,
        max_failures=config.max_failures,
        step_timeout=config.step_timeout,
    )


def get_extraction_prompt(url: str) -> str:
    """Generate the extraction task prompt for the agent.

    Args:
        url: The job posting URL.

    Returns:
        Task prompt string.
    """
    return f"""Navigate to {url} and extract all job posting details.

Extract the following information:
- Company name
- Job title/role
- Location (city, state, country, or "Remote")
- Full job description text
- Key responsibilities (as a list)
- Required qualifications (as a list)
- Required skills/technologies
- Preferred/nice-to-have skills
- Years of experience required (min and max if specified)
- Education requirements
- Salary range (if disclosed)
- Work type (remote, hybrid, or onsite)
- Employment type (full-time, part-time, or contract)
- Direct application URL (if different from the job page URL)
- Job ID (if visible on the page)

Be thorough and extract as much information as possible from the job posting."""


def get_llm(config: ExtractorConfig | None = None) -> Any | None:
    """Get the LLM instance for extraction.

    Uses configuration settings if provided, otherwise falls back to
    environment variables. Tries providers in order based on configuration.

    Args:
        config: Extractor configuration with LLM settings.

    Returns:
        LLM instance or None if no API key is configured.
    """
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None
    provider = "auto"

    if config:
        api_key = config.llm_api_key
        base_url = config.llm_base_url
        model = config.llm_model
        reasoning_effort = getattr(config, "llm_reasoning_effort", None)
        provider = config.llm_provider.lower()

    # If provider is specified explicitly, use it
    if provider == "openai":
        return _create_openai_llm(
            api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY"),
            base_url,
            model,
            reasoning_effort,
        )
    elif provider == "anthropic":
        return _create_anthropic_llm(
            api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("LLM_API_KEY"),
            base_url,
            model,
        )
    elif provider == "browser_use":
        return _create_browser_use_llm(
            api_key or os.getenv("BROWSER_USE_API_KEY"),
            base_url,
            model,
        )

    # Auto-detect provider based on available API keys
    # If a base URL is configured, prefer OpenAI-compatible mode first (local servers).
    openai_api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if base_url or openai_api_key:
        llm = _create_openai_llm(openai_api_key, base_url, model, reasoning_effort)
        if llm:
            return llm

    if os.getenv("BROWSER_USE_API_KEY"):
        llm = _create_browser_use_llm(os.getenv("BROWSER_USE_API_KEY"), base_url, model)
        if llm:
            return llm

    anthropic_api_key = (
        api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("LLM_API_KEY")
    )
    if anthropic_api_key:
        llm = _create_anthropic_llm(anthropic_api_key, base_url, model)
        if llm:
            return llm

    return None


def _create_openai_llm(
    api_key: str | None,
    base_url: str | None,
    model: str | None,
    reasoning_effort: str | None = None,
) -> Any | None:
    """Create an OpenAI LLM instance.

    Args:
        api_key: OpenAI API key.
        base_url: Custom base URL for OpenAI-compatible endpoints.
        model: Model ID to use.

    Returns:
        ChatOpenAI instance or None if not available.
    """
    # For local endpoints (Ollama, LM Studio), API key may not be required
    # Use a dummy key if base_url is set but no api_key provided
    if not api_key and not base_url:
        return None

    effective_api_key = api_key or "not-needed"

    normalized_effort = _normalize_reasoning_effort(reasoning_effort)

    try:
        from browser_use import ChatOpenAI

        kwargs: dict[str, Any] = {
            "model": model or "gpt-4o",
            "api_key": effective_api_key,
            "base_url": base_url,
        }
        if normalized_effort is not None:
            kwargs["reasoning_effort"] = normalized_effort

        return ChatOpenAI(**kwargs)
    except ImportError:
        return None


def _normalize_reasoning_effort(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if not normalized:
        return None
    if normalized in {"disable", "disabled", "off", "0", "false"}:
        return "none"
    if normalized == "min":
        return "minimal"
    return normalized


def _create_anthropic_llm(
    api_key: str | None, base_url: str | None, model: str | None
) -> Any | None:
    """Create an Anthropic LLM instance.

    Args:
        api_key: Anthropic API key.
        base_url: Custom base URL (if supported).
        model: Model ID to use.

    Returns:
        ChatAnthropic instance or None if not available.
    """
    if not api_key:
        return None

    try:
        from browser_use import ChatAnthropic

        return ChatAnthropic(
            model=model or "claude-sonnet-4-20250514",
            api_key=api_key,
            base_url=base_url,
        )
    except ImportError:
        return None


def _create_browser_use_llm(
    api_key: str | None, base_url: str | None, model: str | None
) -> Any | None:
    """Create a Browser Use LLM instance.

    Args:
        api_key: Browser Use API key.

    Returns:
        ChatBrowserUse instance or None if not available.
    """
    if not api_key:
        return None

    try:
        from browser_use import ChatBrowserUse

        return ChatBrowserUse(
            api_key=api_key,
            base_url=base_url,
            model=model or "bu-latest",
        )
    except ImportError:
        return None
