"""Fingerprint generation for the Application Tracker.

This module provides functions for:
- URL normalization (removing tracking params, normalizing scheme)
- Job ID extraction from common job board URLs
- Fingerprint computation using a cascading strategy
"""

import hashlib
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

# Tracking parameters to remove during normalization
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "referrer",
    "source",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
}

# Regex patterns for job ID extraction
# Greenhouse: https://boards.greenhouse.io/company/jobs/12345
GREENHOUSE_PATTERN = re.compile(
    r"boards\.greenhouse\.io/[^/]+/jobs/(\d+)", re.IGNORECASE
)

# Lever: https://jobs.lever.co/company/uuid-style-id
LEVER_PATTERN = re.compile(r"jobs\.lever\.co/[^/]+/([a-zA-Z0-9-]+)", re.IGNORECASE)

# Workday: https://company.wd5.myworkdayjobs.com/.../Title_REQ-123456
WORKDAY_PATTERN = re.compile(r"myworkdayjobs\.com/.*_(REQ-?\d+)", re.IGNORECASE)


def normalize_url(url: str) -> str:
    """Normalize a URL for consistent fingerprinting.

    This function:
    - Converts http to https
    - Removes tracking parameters (utm_*, ref, etc.)
    - Removes trailing slashes
    - Sorts remaining query parameters

    Args:
        url: The URL to normalize.

    Returns:
        The normalized URL.
    """
    parsed = urlparse(url)

    # Normalize scheme to https
    scheme = "https"

    # Parse query parameters and filter out tracking params
    query_params = parse_qs(parsed.query, keep_blank_values=False)
    filtered_params = {
        key: values
        for key, values in query_params.items()
        if key.lower() not in TRACKING_PARAMS
    }

    # Sort parameters and rebuild query string
    # Use first value of each param (parse_qs returns lists)
    sorted_params = sorted(
        (key, values[0]) for key, values in filtered_params.items() if values
    )
    query_string = urlencode(sorted_params)

    # Remove trailing slash from path
    path = parsed.path.rstrip("/")
    if not path:
        path = ""

    # Rebuild URL
    normalized = urlunparse(
        (
            scheme,
            parsed.netloc,
            path,
            "",  # params
            query_string,
            "",  # fragment
        )
    )

    return normalized


def extract_job_id(url: str) -> str | None:
    """Extract a job ID from known job board URL patterns.

    Supports:
    - Greenhouse: Returns "greenhouse:<id>"
    - Lever: Returns "lever:<uuid>"
    - Workday: Returns "workday:<req-id>"

    Args:
        url: The job posting URL.

    Returns:
        A prefixed job ID string, or None if pattern not recognized.
    """
    # Try Greenhouse
    match = GREENHOUSE_PATTERN.search(url)
    if match:
        return f"greenhouse:{match.group(1)}"

    # Try Lever
    match = LEVER_PATTERN.search(url)
    if match:
        return f"lever:{match.group(1)}"

    # Try Workday
    match = WORKDAY_PATTERN.search(url)
    if match:
        return f"workday:{match.group(1)}"

    return None


def compute_fingerprint(
    url: str | None,
    job_id: str | None,
    company: str,
    role: str,
    location: str | None,
) -> str:
    """Compute a fingerprint for a job application.

    Uses a cascading strategy:
    1. If job_id is available, hash it
    2. Else if url is available, hash the normalized URL
    3. Else hash company|role|location

    Args:
        url: The job posting URL (optional).
        job_id: The extracted job ID (optional).
        company: The company name.
        role: The job role/title.
        location: The job location (optional).

    Returns:
        A SHA-256 hash string representing the fingerprint.
    """
    if job_id:
        source = job_id
    elif url:
        source = normalize_url(url)
    else:
        # Fallback to company|role|location
        location_part = location or ""
        source = f"{company}|{role}|{location_part}"

    return hashlib.sha256(source.encode()).hexdigest()
