from __future__ import annotations

import json
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


def test_scoped_lookup_prefers_company_over_global(tmp_path: Path) -> None:
    path = tmp_path / "qa.json"
    bank = QABank(path)
    bank.record_answer("What is your name?", "Global")
    bank.record_answer(
        "What is your name?",
        "Company",
        scope_type="company",
        scope_key="acme",
    )

    bank2 = QABank(path)
    bank2.load()

    assert (
        bank2.get_answer(
            "What is your name?",
            scope_hints=[("company", "acme"), ("global", None)],
        )
        == "Company"
    )


def test_global_motivation_answer_is_not_reused(tmp_path: Path) -> None:
    path = tmp_path / "qa.json"
    bank = QABank(path)
    bank.record_answer(
        "Why do you want to work here?",
        "Because reasons.",
        scope_type="global",
        category="motivation",
    )

    bank2 = QABank(path)
    bank2.load()

    assert bank2.get_answer("Why do you want to work here?") is None


def test_loads_legacy_entry_without_scope_fields(tmp_path: Path) -> None:
    path = tmp_path / "qa.json"
    path.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "question": "What is your name?",
                        "answer": "John Doe",
                        "context": None,
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    bank = QABank(path)
    bank.load()

    assert bank.get_answer("What is your name?") == "John Doe"
