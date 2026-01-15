"""Tests for extractor service."""

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest


class TestJobExtractor:
    """Test JobExtractor service."""

    def test_job_extractor_initializes_with_config(self):
        """JobExtractor should initialize with ExtractorConfig."""
        from src.extractor.config import ExtractorConfig
        from src.extractor.service import JobExtractor

        config = ExtractorConfig(_env_file=None)
        extractor = JobExtractor(config=config)

        assert extractor.config is config

    def test_job_extractor_uses_default_config_if_not_provided(self):
        """JobExtractor should use default config if none provided."""
        from src.extractor.config import ExtractorConfig
        from src.extractor.service import JobExtractor

        extractor = JobExtractor()

        assert isinstance(extractor.config, ExtractorConfig)

    @pytest.mark.asyncio
    async def test_job_extractor_extract_returns_job_description_for_valid_url(self):
        """JobExtractor.extract() should return JobDescription for valid URL."""
        from src.extractor.config import ExtractorConfig
        from src.extractor.models import JobDescription
        from src.extractor.service import JobExtractor

        config = ExtractorConfig(_env_file=None)
        extractor = JobExtractor(config=config)

        # Mock the agent run
        mock_job_data = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://jobs.lever.co/acme/123",
            location="Remote",
            work_type="remote",
        )

        with patch.object(
            extractor, "_run_extraction_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = mock_job_data

            result = await extractor.extract("https://jobs.lever.co/acme/123")

            assert result is not None
            assert isinstance(result, JobDescription)
            assert result.company == "Acme Corp"
            assert result.role_title == "Software Engineer"
            mock_run.assert_called_once_with("https://jobs.lever.co/acme/123")

    @pytest.mark.asyncio
    async def test_job_extractor_extract_returns_none_on_failure(self):
        """JobExtractor.extract() should return None on extraction failure."""
        from src.extractor.config import ExtractorConfig
        from src.extractor.service import JobExtractor

        config = ExtractorConfig(_env_file=None)
        extractor = JobExtractor(config=config)

        with patch.object(
            extractor, "_run_extraction_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = None

            result = await extractor.extract("https://invalid-url.com/job")

            assert result is None

    @pytest.mark.asyncio
    async def test_job_extractor_extract_handles_exception_gracefully(self):
        """JobExtractor.extract() should handle exceptions gracefully."""
        from src.extractor.config import ExtractorConfig
        from src.extractor.service import JobExtractor

        config = ExtractorConfig(_env_file=None)
        extractor = JobExtractor(config=config)

        with patch.object(
            extractor, "_run_extraction_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.side_effect = Exception("Network error")

            result = await extractor.extract("https://jobs.lever.co/acme/123")

            assert result is None

    @pytest.mark.asyncio
    async def test_job_extractor_saves_jd_json_when_output_dir_configured(
        self, tmp_path: Path
    ):
        """JobExtractor should save jd.json when output_dir is configured."""
        from src.extractor.config import ExtractorConfig
        from src.extractor.models import JobDescription
        from src.extractor.service import JobExtractor

        config = ExtractorConfig(_env_file=None, output_dir=tmp_path)
        extractor = JobExtractor(config=config)

        mock_job_data = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://jobs.lever.co/acme/123",
        )

        with patch.object(
            extractor, "_run_extraction_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = mock_job_data

            result = await extractor.extract(
                "https://jobs.lever.co/acme/123", save_artifact=True
            )

            assert result is not None
            # Check that jd.json was saved
            jd_file = tmp_path / "jd.json"
            assert jd_file.exists()

    @pytest.mark.asyncio
    async def test_job_extractor_integrates_with_tracker_fingerprint(self):
        """JobExtractor should return data compatible with tracker fingerprint."""
        from src.extractor.config import ExtractorConfig
        from src.extractor.models import JobDescription
        from src.extractor.service import JobExtractor
        from src.tracker.fingerprint import compute_fingerprint

        config = ExtractorConfig(_env_file=None)
        extractor = JobExtractor(config=config)

        mock_job_data = JobDescription(
            company="Acme Corp",
            role_title="Software Engineer",
            job_url="https://jobs.lever.co/acme/abc123",
            location="San Francisco, CA",
        )

        with patch.object(
            extractor, "_run_extraction_agent", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = mock_job_data

            result = await extractor.extract("https://jobs.lever.co/acme/abc123")

            # Verify we can compute fingerprint from extracted data
            job_id = None  # Could use extract_job_id(result.job_url) if needed
            fingerprint = compute_fingerprint(
                url=result.job_url,
                job_id=job_id,
                company=result.company,
                role=result.role_title,
                location=result.location,
            )
            assert fingerprint is not None
            assert len(fingerprint) > 0


class TestJobExtractorAgentSetup:
    """Test JobExtractor agent setup methods."""

    def test_job_extractor_creates_extraction_task_prompt(self):
        """JobExtractor should create appropriate extraction task prompt."""
        from src.extractor.config import ExtractorConfig
        from src.extractor.service import JobExtractor

        config = ExtractorConfig(_env_file=None)
        extractor = JobExtractor(config=config)

        url = "https://jobs.lever.co/acme/123"
        prompt = extractor._create_extraction_prompt(url)

        assert url in prompt
        assert "extract" in prompt.lower() or "job" in prompt.lower()

    def test_job_extractor_detects_extraction_source(self):
        """JobExtractor should detect extraction source from URL."""
        from src.extractor.config import ExtractorConfig
        from src.extractor.service import JobExtractor

        config = ExtractorConfig(_env_file=None)
        extractor = JobExtractor(config=config)

        assert extractor._detect_source("https://jobs.lever.co/acme/123") == "lever"
        assert (
            extractor._detect_source("https://boards.greenhouse.io/acme/jobs/456")
            == "greenhouse"
        )
        assert (
            extractor._detect_source("https://acme.wd1.myworkdayjobs.com/job/789")
            == "workday"
        )
        assert (
            extractor._detect_source("https://linkedin.com/jobs/view/123") == "linkedin"
        )
        assert extractor._detect_source("https://acme.com/careers/job/123") == "generic"


class TestBrowserUseTempDirCleanup:
    def test_cleanup_removes_browser_use_temp_user_data_dir(self):
        from src.extractor.config import ExtractorConfig
        from src.extractor.service import JobExtractor

        temp_dir = Path(tempfile.mkdtemp(prefix="browser-use-user-data-dir-"))
        (temp_dir / "sentinel.txt").write_text("x")

        dummy_browser = SimpleNamespace(
            browser_profile=SimpleNamespace(user_data_dir=str(temp_dir))
        )

        extractor = JobExtractor(config=ExtractorConfig(_env_file=None))
        extractor._cleanup_browser_use_temp_profile(dummy_browser)

        assert not temp_dir.exists()
