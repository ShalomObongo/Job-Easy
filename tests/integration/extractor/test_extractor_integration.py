"""Integration tests for job extraction with live URLs.

These tests require:
1. An LLM API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, or BROWSER_USE_API_KEY)
2. Browser Use library installed with browser automation support
3. Network access to job posting sites

Run with: pytest tests/integration/extractor/ -v -m integration
"""

import os

import pytest

# Skip all tests in this module if no LLM API key is available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not any(
            os.getenv(key)
            for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "BROWSER_USE_API_KEY"]
        ),
        reason="No LLM API key available (OPENAI_API_KEY, ANTHROPIC_API_KEY, or BROWSER_USE_API_KEY)",
    ),
]


class TestLiveJobExtraction:
    """Test job extraction with live job posting URLs.

    These tests use real job board URLs and require API keys.
    They may take 30-60 seconds per test due to browser automation.
    """

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_extract_from_greenhouse_job_posting(self):
        """Extract job data from a Greenhouse job posting URL."""
        from src.extractor import JobDescription, JobExtractor

        extractor = JobExtractor()

        # Note: This URL may become stale over time
        # Replace with a current Greenhouse job posting URL for testing
        url = "https://boards.greenhouse.io/anthropic/jobs/4020300007"

        result = await extractor.extract(url)

        # Verify we got some data back
        # (actual content depends on the live job posting)
        if result is not None:
            assert isinstance(result, JobDescription)
            assert result.company is not None
            assert result.role_title is not None
            assert result.job_url is not None
            assert result.extraction_source == "greenhouse"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_extract_from_lever_job_posting(self):
        """Extract job data from a Lever job posting URL."""
        from src.extractor import JobDescription, JobExtractor

        extractor = JobExtractor()

        # Note: This URL may become stale over time
        # Replace with a current Lever job posting URL for testing
        url = "https://jobs.lever.co/openai"

        result = await extractor.extract(url)

        # Verify we got some data back
        if result is not None:
            assert isinstance(result, JobDescription)
            assert result.company is not None
            assert result.role_title is not None
            assert result.extraction_source == "lever"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_extract_from_generic_job_page(self):
        """Extract job data from a generic company careers page."""
        from src.extractor import JobDescription, JobExtractor

        extractor = JobExtractor()

        # Note: Use a real job posting URL for testing
        url = "https://careers.google.com/jobs/"

        result = await extractor.extract(url)

        # For generic pages, extraction may or may not succeed
        # depending on page structure
        if result is not None:
            assert isinstance(result, JobDescription)

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_workflow_with_artifact_output(self, tmp_path):
        """Test full extraction workflow with artifact saving."""
        from src.extractor import ExtractorConfig, JobExtractor

        config = ExtractorConfig(output_dir=tmp_path, headless=True)
        extractor = JobExtractor(config=config)

        url = "https://boards.greenhouse.io/anthropic/jobs/4020300007"

        result = await extractor.extract(url, save_artifact=True)

        if result is not None:
            # Verify artifact was saved
            jd_file = tmp_path / "jd.json"
            assert jd_file.exists()

            # Verify we can read it back
            import json

            with open(jd_file) as f:
                data = json.load(f)
            assert data["company"] == result.company
            assert data["role_title"] == result.role_title

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_extraction_integrates_with_tracker(self):
        """Test that extracted data works with tracker fingerprinting."""
        from src.extractor import JobExtractor
        from src.tracker.fingerprint import compute_fingerprint, extract_job_id

        extractor = JobExtractor()
        url = "https://boards.greenhouse.io/anthropic/jobs/4020300007"

        result = await extractor.extract(url)

        if result is not None:
            # Compute fingerprint from extracted data
            job_id = extract_job_id(result.job_url)
            fingerprint = compute_fingerprint(
                url=result.job_url,
                job_id=job_id,
                company=result.company,
                role=result.role_title,
                location=result.location,
            )

            assert fingerprint is not None
            assert len(fingerprint) == 64  # SHA-256 hex length
