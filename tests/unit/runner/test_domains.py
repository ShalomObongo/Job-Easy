from __future__ import annotations

from pathlib import Path

from src.runner.domains import is_prohibited, record_allowed_domain


def test_navigation_is_blocked_when_domain_matches_prohibited_list() -> None:
    assert is_prohibited("https://example.com/jobs/123", ["example.com"]) is True
    assert is_prohibited("https://sub.example.com/jobs/123", ["*.example.com"]) is True


def test_non_prohibited_domains_are_permitted() -> None:
    assert is_prohibited("https://good.com/jobs/123", ["bad.com"]) is False


def test_allowlist_log_is_appended_when_encountering_new_domains(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "allowlist.log"

    record_allowed_domain("https://a.com/jobs/1", log_path)
    assert log_path.read_text().strip().splitlines() == ["a.com"]

    record_allowed_domain("https://a.com/jobs/2", log_path)
    assert log_path.read_text().strip().splitlines() == ["a.com"]

    record_allowed_domain("https://b.com/jobs/3", log_path)
    assert log_path.read_text().strip().splitlines() == ["a.com", "b.com"]
