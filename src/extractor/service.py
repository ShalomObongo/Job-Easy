"""Job extraction service using Browser Use."""

from __future__ import annotations

import contextlib
import logging
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from src.extractor.config import ExtractorConfig, get_extractor_config
from src.extractor.models import JobDescription

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_BROWSER_USE_TEMP_PREFIX = "browser-use-user-data-dir-"


class JobExtractor:
    """Service for extracting job descriptions from job posting URLs.

    Uses Browser Use's `output_model_schema` parameter to get structured
    output from the extraction agent.

    Attributes:
        config: Extractor configuration settings.
    """

    def __init__(self, config: ExtractorConfig | None = None) -> None:
        """Initialize the JobExtractor.

        Args:
            config: Extractor configuration. If not provided, uses default.
        """
        self.config = config or get_extractor_config()

    async def extract(
        self, url: str, save_artifact: bool = False
    ) -> JobDescription | None:
        """Extract job description from a URL.

        Args:
            url: The job posting URL to extract from.
            save_artifact: Whether to save jd.json artifact.

        Returns:
            JobDescription if extraction succeeds, None otherwise.
        """
        try:
            logger.info(f"Extracting job from: {url}")
            result = await self._run_extraction_agent(url)

            if result is None:
                logger.warning(f"Extraction failed for: {url}")
                return None

            # Set extraction source based on URL
            result.extraction_source = self._detect_source(url)
            # Set extracted_at based on system time (do not rely on the LLM).
            result.extracted_at = datetime.now(UTC)
            # If the model didn't extract a job_id, try deriving it from the URL.
            if not result.job_id:
                with contextlib.suppress(Exception):
                    from src.tracker.fingerprint import extract_job_id

                    result.job_id = extract_job_id(result.job_url or url)

            # Save artifact if requested
            if save_artifact and result:
                output_path = self.config.output_dir / "jd.json"
                result.save_json(output_path)
                logger.info(f"Saved job description to: {output_path}")

            return result

        except Exception as e:
            logger.error(f"Error extracting job from {url}: {e}")
            return None

    async def _run_extraction_agent(self, url: str) -> JobDescription | None:
        """Run the Browser Use agent to extract job data.

        Args:
            url: The job posting URL.

        Returns:
            JobDescription if extraction succeeds, None otherwise.
        """
        browser = None
        try:
            from src.extractor.agent import create_browser, create_extraction_agent

            browser = create_browser(self.config)

            # Get the LLM - try different providers
            llm = self._get_llm()
            if llm is None:
                logger.error(
                    "No LLM configured. Set `EXTRACTOR_LLM_PROVIDER` and credentials "
                    "(`EXTRACTOR_LLM_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, "
                    "or `LLM_API_KEY`). For local OpenAI-compatible servers, set "
                    "`EXTRACTOR_LLM_BASE_URL` (API key can be a dummy value)."
                )
                return None

            agent = create_extraction_agent(
                url=url,
                browser=browser,
                llm=llm,
                config=self.config,
            )

            # Run the agent
            history = await agent.run()

            # Get structured output
            if history and history.structured_output:
                result = history.structured_output
                # Ensure job_url is set
                if not result.job_url:
                    result.job_url = url
                return result

            return None

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return None
        finally:
            if browser:
                with contextlib.suppress(Exception):
                    await browser.close()
                if not self.config.keep_browser_use_temp_dirs:
                    self._cleanup_browser_use_temp_profile(browser)

    def _cleanup_browser_use_temp_profile(self, browser) -> None:
        """Delete Browser Use temp `user_data_dir` directories to prevent disk bloat."""
        profile = getattr(browser, "browser_profile", None)
        user_data_dir = getattr(profile, "user_data_dir", None)
        if not user_data_dir:
            return

        try:
            user_data_path = Path(str(user_data_dir))
        except Exception:
            return

        user_data_str = str(user_data_path)
        if _BROWSER_USE_TEMP_PREFIX not in user_data_str:
            return

        tmp_roots: list[Path] = []
        for root in (tempfile.gettempdir(), os.getenv("TMPDIR"), "/var/folders"):
            if not root:
                continue
            with contextlib.suppress(Exception):
                tmp_roots.append(Path(str(root)).expanduser().resolve())

        with contextlib.suppress(Exception):
            user_data_path = user_data_path.expanduser().resolve()

        if not any(
            str(user_data_path).startswith(str(root) + os.sep) for root in tmp_roots
        ):
            return

        with contextlib.suppress(Exception):
            shutil.rmtree(user_data_path, ignore_errors=True)

    def _get_llm(self):
        """Get the LLM instance for extraction.

        Returns:
            LLM instance or None if not configured.
        """
        from src.extractor.agent import get_llm

        return get_llm(self.config)

    def _create_extraction_prompt(self, url: str) -> str:
        """Create the extraction task prompt for the agent.

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

    def _detect_source(self, url: str) -> str:
        """Detect the job board source from URL.

        Args:
            url: The job posting URL.

        Returns:
            Source identifier string.
        """
        url_lower = url.lower()

        if "lever.co" in url_lower or "jobs.lever" in url_lower:
            return "lever"
        if "greenhouse.io" in url_lower or "boards.greenhouse" in url_lower:
            return "greenhouse"
        if "workday" in url_lower or "myworkdayjobs" in url_lower:
            return "workday"
        if "linkedin.com" in url_lower:
            return "linkedin"
        if "indeed.com" in url_lower:
            return "indeed"
        if "glassdoor.com" in url_lower:
            return "glassdoor"

        return "generic"
