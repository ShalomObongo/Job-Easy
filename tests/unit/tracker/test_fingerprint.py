"""Tests for fingerprint generation."""

import hashlib


class TestNormalizeUrl:
    """Test URL normalization function."""

    def test_removes_utm_tracking_parameters(self):
        """Should remove utm_* tracking parameters."""
        from src.tracker.fingerprint import normalize_url

        url = "https://example.com/jobs/123?utm_source=linkedin&utm_medium=social"
        result = normalize_url(url)
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert result == "https://example.com/jobs/123"

    def test_removes_ref_parameter(self):
        """Should remove ref tracking parameter."""
        from src.tracker.fingerprint import normalize_url

        url = "https://example.com/jobs/123?ref=google"
        result = normalize_url(url)
        assert "ref=" not in result

    def test_normalizes_http_to_https(self):
        """Should normalize http to https."""
        from src.tracker.fingerprint import normalize_url

        url = "http://example.com/jobs/123"
        result = normalize_url(url)
        assert result.startswith("https://")

    def test_removes_trailing_slash(self):
        """Should remove trailing slash for consistency."""
        from src.tracker.fingerprint import normalize_url

        url = "https://example.com/jobs/123/"
        result = normalize_url(url)
        assert not result.endswith("/")

    def test_preserves_necessary_query_params(self):
        """Should preserve non-tracking query parameters."""
        from src.tracker.fingerprint import normalize_url

        url = "https://example.com/jobs?id=123&department=engineering"
        result = normalize_url(url)
        assert "id=123" in result
        assert "department=engineering" in result

    def test_sorts_query_parameters(self):
        """Should sort query parameters for consistency."""
        from src.tracker.fingerprint import normalize_url

        url1 = "https://example.com/jobs?b=2&a=1"
        url2 = "https://example.com/jobs?a=1&b=2"
        assert normalize_url(url1) == normalize_url(url2)


class TestExtractJobId:
    """Test job ID extraction from URLs."""

    def test_extracts_greenhouse_job_id(self):
        """Should extract job ID from Greenhouse URLs."""
        from src.tracker.fingerprint import extract_job_id

        url = "https://boards.greenhouse.io/company/jobs/4567890"
        result = extract_job_id(url)
        assert result == "greenhouse:4567890"

    def test_extracts_lever_job_id(self):
        """Should extract job ID from Lever URLs."""
        from src.tracker.fingerprint import extract_job_id

        url = "https://jobs.lever.co/company/abcd-1234-efgh-5678"
        result = extract_job_id(url)
        assert result == "lever:abcd-1234-efgh-5678"

    def test_extracts_workday_job_id(self):
        """Should extract job ID from Workday URLs."""
        from src.tracker.fingerprint import extract_job_id

        url = "https://company.wd5.myworkdayjobs.com/en-US/careers/job/Location/Title_REQ-123456"
        result = extract_job_id(url)
        assert result == "workday:REQ-123456"

    def test_returns_none_for_unknown_pattern(self):
        """Should return None for unknown URL patterns."""
        from src.tracker.fingerprint import extract_job_id

        url = "https://example.com/careers/software-engineer"
        result = extract_job_id(url)
        assert result is None


class TestComputeFingerprint:
    """Test fingerprint computation."""

    def test_uses_job_id_when_available(self):
        """Should use job_id as primary fingerprint source."""
        from src.tracker.fingerprint import compute_fingerprint

        result = compute_fingerprint(
            url="https://example.com/jobs/123",
            job_id="greenhouse:4567890",
            company="ExampleCo",
            role="Engineer",
            location="Remote",
        )
        # Should hash the job_id
        expected = hashlib.sha256(b"greenhouse:4567890").hexdigest()
        assert result == expected

    def test_falls_back_to_canonical_url(self):
        """Should use canonical_url when job_id is None."""
        from src.tracker.fingerprint import compute_fingerprint

        result = compute_fingerprint(
            url="https://example.com/jobs/123",
            job_id=None,
            company="ExampleCo",
            role="Engineer",
            location="Remote",
        )
        # Should hash the normalized URL
        expected = hashlib.sha256(b"https://example.com/jobs/123").hexdigest()
        assert result == expected

    def test_falls_back_to_company_role_location(self):
        """Should use company|role|location when url is also None."""
        from src.tracker.fingerprint import compute_fingerprint

        result = compute_fingerprint(
            url=None,
            job_id=None,
            company="ExampleCo",
            role="Engineer",
            location="Remote",
        )
        # Should hash the combination
        expected = hashlib.sha256(b"ExampleCo|Engineer|Remote").hexdigest()
        assert result == expected

    def test_fingerprint_is_deterministic(self):
        """Same inputs should produce same fingerprint."""
        from src.tracker.fingerprint import compute_fingerprint

        result1 = compute_fingerprint(
            url="https://example.com/jobs/123",
            job_id=None,
            company="ExampleCo",
            role="Engineer",
            location="Remote",
        )
        result2 = compute_fingerprint(
            url="https://example.com/jobs/123",
            job_id=None,
            company="ExampleCo",
            role="Engineer",
            location="Remote",
        )
        assert result1 == result2
