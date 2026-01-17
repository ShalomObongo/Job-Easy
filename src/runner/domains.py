"""Domain policy utilities for the runner.

Policy: blocklist-first.
- Only URLs matching `prohibited_domains` are blocked.
- All other domains are permitted, and are logged to an allowlist log for visibility.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from browser_use.utils import match_url_with_domain_pattern


def _ensure_scheme(url: str) -> str:
    if "://" in url:
        return url
    return f"https://{url}"


def is_prohibited(url: str, prohibited_domains: list[str]) -> bool:
    """Return True when the URL matches any prohibited domain pattern."""
    candidate = _ensure_scheme(url)
    for pattern in prohibited_domains:
        if match_url_with_domain_pattern(candidate, pattern):
            return True
    return False


def extract_hostname(url: str) -> str | None:
    """Extract hostname from a URL (best-effort)."""
    parsed = urlparse(_ensure_scheme(url))
    return parsed.hostname


def record_allowed_domain(url: str, allowlist_log_path: str | Path) -> str | None:
    """Append the hostname to an allowlist log file, if not already present."""
    hostname = extract_hostname(url)
    if not hostname:
        return None

    path = Path(allowlist_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing: set[str] = set()
    if path.exists():
        existing = {
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }

    if hostname in existing:
        return hostname

    prefix = "\n" if path.exists() and path.read_text(encoding="utf-8") else ""
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{prefix}{hostname}")

    return hostname
