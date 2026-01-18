"""Lead file parsing for autonomous mode."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from src.autonomous.models import LeadItem


class LeadFileParser:
    """Parse a leads file into `LeadItem` entries."""

    def parse(self, file_path: Path) -> list[LeadItem]:
        """Parse a leads file with one URL per line.

        Ignores blank lines and comments (lines that start with '#', after stripping).
        Invalid URLs are returned as LeadItems with `valid=False` and an error message.
        """
        raw = file_path.read_text(encoding="utf-8")
        items: list[LeadItem] = []

        for line_number, line in enumerate(raw.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue

            error = _validate_http_url(stripped)
            if error is None:
                items.append(
                    LeadItem(
                        url=stripped,
                        line_number=line_number,
                        valid=True,
                        error=None,
                    )
                )
            else:
                items.append(
                    LeadItem(
                        url=stripped,
                        line_number=line_number,
                        valid=False,
                        error=error,
                    )
                )

        return items


def _validate_http_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "Invalid URL: must start with http:// or https://"
    if not parsed.netloc:
        return "Invalid URL: missing host"
    return None
