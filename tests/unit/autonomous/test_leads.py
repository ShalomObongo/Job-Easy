from __future__ import annotations

from pathlib import Path

import pytest

from src.autonomous.leads import LeadFileParser


def test_lead_parser_parse_file_with_valid_urls_returns_lead_items(
    tmp_path: Path,
) -> None:
    leads_file = tmp_path / "leads.txt"
    leads_file.write_text(
        "https://example.com/jobs/1\nhttps://example.com/jobs/2\n",
        encoding="utf-8",
    )

    items = LeadFileParser().parse(leads_file)

    assert [item.url for item in items] == [
        "https://example.com/jobs/1",
        "https://example.com/jobs/2",
    ]
    assert [item.line_number for item in items] == [1, 2]
    assert all(item.valid for item in items)


def test_lead_parser_blank_lines_and_comments_are_ignored(tmp_path: Path) -> None:
    leads_file = tmp_path / "leads.txt"
    leads_file.write_text(
        "\n"
        "# comment\n"
        "  # indented comment\n"
        "https://example.com/jobs/1\n"
        "\n"
        "https://example.com/jobs/2\n",
        encoding="utf-8",
    )

    items = LeadFileParser().parse(leads_file)

    assert [item.url for item in items] == [
        "https://example.com/jobs/1",
        "https://example.com/jobs/2",
    ]
    assert [item.line_number for item in items] == [4, 6]


def test_lead_parser_invalid_urls_are_marked_invalid(tmp_path: Path) -> None:
    leads_file = tmp_path / "leads.txt"
    leads_file.write_text("notaurl\nhttps://example.com/jobs/1\n", encoding="utf-8")

    items = LeadFileParser().parse(leads_file)

    assert items[0].valid is False
    assert items[0].error is not None
    assert "http" in items[0].error.lower()
    assert items[1].valid is True


def test_lead_parser_file_not_found_raises_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing.txt"
    with pytest.raises(FileNotFoundError):
        LeadFileParser().parse(missing)


def test_lead_parser_empty_file_returns_empty_list(tmp_path: Path) -> None:
    leads_file = tmp_path / "leads.txt"
    leads_file.write_text("", encoding="utf-8")

    items = LeadFileParser().parse(leads_file)

    assert items == []
