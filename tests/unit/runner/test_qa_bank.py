from __future__ import annotations

from pathlib import Path

from src.runner.qa_bank import QABank


def test_loads_empty_bank_when_file_missing(tmp_path: Path) -> None:
    path = tmp_path / "qa.json"
    bank = QABank(path)
    bank.load()

    assert bank.get_answer("Any question?") is None


def test_persists_new_entries_deterministically(tmp_path: Path) -> None:
    path = tmp_path / "qa.json"
    bank = QABank(path)
    bank.record_answer("What is your name?", "John Doe")

    bank2 = QABank(path)
    bank2.load()

    assert bank2.get_answer("What is your name?") == "John Doe"


def test_question_normalization_and_lookup(tmp_path: Path) -> None:
    path = tmp_path / "qa.json"
    bank = QABank(path)
    bank.record_answer("What is your name?", "John Doe")

    assert bank.get_answer("  WHAT is   your NAME? ") == "John Doe"
