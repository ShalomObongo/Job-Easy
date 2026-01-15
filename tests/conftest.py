"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def sample_job_url() -> str:
    """Sample job URL for testing."""
    return "https://example.com/jobs/123"
