from __future__ import annotations

import json

import pytest

from src.hitl.tools import (
    _click_submit_button,
    _has_bot_protection_block,
    _has_otp_block,
    create_hitl_tools,
    is_submit_confirmed,
    normalize_otp_code,
    parse_yes_no,
    preflight_find_blockers,
)


def test_yes_no_prompt_parsing_case_and_whitespace_tolerant() -> None:
    assert parse_yes_no(" yes ") is True
    assert parse_yes_no("Y") is True
    assert parse_yes_no("No") is False
    assert parse_yes_no(" n ") is False


def test_yes_no_prompt_parsing_rejects_unknown_values() -> None:
    with pytest.raises(ValueError):
        parse_yes_no("maybe")


def test_yes_to_submit_requires_exact_confirmation_string() -> None:
    assert is_submit_confirmed("YES") is True
    assert is_submit_confirmed(" YES ") is True
    assert is_submit_confirmed("yes") is True
    assert is_submit_confirmed("y") is False


def test_otp_prompt_returns_raw_string_without_logging_secrets() -> None:
    assert normalize_otp_code(" 123456 ") == "123456"


class _DummyBoundingBox:
    width = 120
    height = 40


class _DummyElement:
    def __init__(self) -> None:
        self.clicked = False

    async def click(self) -> None:
        self.clicked = True

    async def get_bounding_box(self):
        return _DummyBoundingBox()

    async def get_attribute(self, _name: str):
        return None

    async def evaluate(self, _fn: str, *_args):
        return "Submit"


class _DummyPage:
    def __init__(self, element: _DummyElement) -> None:
        self._element = element
        self.css_queries: list[str] = []

    async def get_element(self, _backend_node_id: int):
        return self._element

    async def get_elements_by_css_selector(self, selector: str):
        self.css_queries.append(selector)
        return [self._element]

    async def evaluate(self, _fn: str):
        return ""


class _DummyNode:
    def __init__(self, backend_node_id: int) -> None:
        self.backend_node_id = backend_node_id


class _DummyBrowserSession:
    def __init__(self, page: _DummyPage, node: _DummyNode | None) -> None:
        self._page = page
        self._node = node
        self.index_lookups: list[int] = []

    async def must_get_current_page(self):
        return self._page

    async def get_dom_element_by_index(self, index: int):
        self.index_lookups.append(index)
        return self._node


@pytest.mark.asyncio
async def test_click_submit_button_prefers_dom_index() -> None:
    element = _DummyElement()
    page = _DummyPage(element)
    session = _DummyBrowserSession(page, _DummyNode(backend_node_id=999))

    clicked = await _click_submit_button(
        browser_session=session, submit_button_index=1316
    )

    assert clicked is True
    assert element.clicked is True
    assert session.index_lookups == [1316]
    assert page.css_queries == []


@pytest.mark.asyncio
async def test_click_submit_button_falls_back_to_css_search() -> None:
    element = _DummyElement()
    page = _DummyPage(element)
    session = _DummyBrowserSession(page, node=None)

    clicked = await _click_submit_button(
        browser_session=session, submit_button_index=1316
    )

    assert clicked is True
    assert element.clicked is True
    assert session.index_lookups == [1316]
    assert page.css_queries == ['button[type="submit"], input[type="submit"]']


class _DummyEvalPage:
    def __init__(self, result) -> None:
        self._result = result
        self.evaluate_calls: list[str] = []

    async def evaluate(self, fn: str):
        self.evaluate_calls.append(fn)
        return self._result


class _SequencedEvalPage:
    def __init__(self, results: list[object]) -> None:
        self._results = list(results)
        self._index = 0
        self.evaluate_calls: list[str] = []

    async def evaluate(self, fn: str):
        self.evaluate_calls.append(fn)
        if not self._results:
            return {"missing": [], "invalid": []}
        if self._index >= len(self._results):
            return self._results[-1]
        result = self._results[self._index]
        self._index += 1
        return result


class _DummyEvalBrowserSession:
    def __init__(self, page: _DummyEvalPage) -> None:
        self._page = page

    async def must_get_current_page(self):
        return self._page


@pytest.mark.asyncio
async def test_preflight_find_blockers_returns_empty_when_no_issues() -> None:
    session = _DummyEvalBrowserSession(_DummyEvalPage({"missing": [], "invalid": []}))
    assert await preflight_find_blockers(session) == []


@pytest.mark.asyncio
async def test_preflight_find_blockers_returns_missing_and_invalid_labels() -> None:
    session = _DummyEvalBrowserSession(
        _DummyEvalPage({"missing": ["Email"], "invalid": ["Phone"]})
    )
    assert await preflight_find_blockers(session) == ["Email", "invalid:Phone"]


@pytest.mark.asyncio
async def test_preflight_find_blockers_parses_json_string_from_page_evaluate() -> None:
    payload = {"missing": ["Email"], "invalid": ["Phone"]}
    session = _DummyEvalBrowserSession(_DummyEvalPage(json.dumps(payload)))
    assert await preflight_find_blockers(session) == ["Email", "invalid:Phone"]


@pytest.mark.asyncio
async def test_preflight_check_marks_repeated_blocker_loops() -> None:
    tools = create_hitl_tools()
    action = tools.registry.registry.actions["preflight_check"].function

    page = _SequencedEvalPage(
        [
            {"missing": ["Email"], "invalid": []},
            {"missing": ["Email"], "invalid": []},
            {"missing": ["Email"], "invalid": []},
        ]
    )
    session = _DummyEvalBrowserSession(page)

    first = json.loads(await action(browser_session=session))
    second = json.loads(await action(browser_session=session))
    third = json.loads(await action(browser_session=session))

    assert all(
        not str(item).startswith("stuck:preflight_blockers_repeated:") for item in first
    )
    assert all(
        not str(item).startswith("stuck:preflight_blockers_repeated:")
        for item in second
    )
    assert any(
        str(item).startswith("stuck:preflight_blockers_repeated:3") for item in third
    )


@pytest.mark.asyncio
async def test_preflight_check_resets_repeat_tracking_after_clear_pass() -> None:
    tools = create_hitl_tools()
    action = tools.registry.registry.actions["preflight_check"].function

    page = _SequencedEvalPage(
        [
            {"missing": ["Email"], "invalid": []},
            {"missing": ["Email"], "invalid": []},
            {"missing": [], "invalid": []},
            {"missing": ["Email"], "invalid": []},
        ]
    )
    session = _DummyEvalBrowserSession(page)

    await action(browser_session=session)
    await action(browser_session=session)
    clear_pass = json.loads(await action(browser_session=session))
    after_reset = json.loads(await action(browser_session=session))

    assert clear_pass == []
    assert all(
        not str(item).startswith("stuck:preflight_blockers_repeated:")
        for item in after_reset
    )


@pytest.mark.asyncio
async def test_has_bot_protection_block_ignores_recaptcha_footer_only() -> None:
    text = "This site is protected by reCAPTCHA and the Google Privacy Policy and Terms of Service apply."
    session = _DummyEvalBrowserSession(_DummyEvalPage(text))
    assert await _has_bot_protection_block(session) is False


@pytest.mark.asyncio
async def test_has_bot_protection_block_detects_spam_flag() -> None:
    text = "We couldn't submit your application. Your application submission was flagged as possible spam."
    session = _DummyEvalBrowserSession(_DummyEvalPage(text))
    assert await _has_bot_protection_block(session) is True


@pytest.mark.asyncio
async def test_has_otp_block_detects_security_code() -> None:
    session = _DummyEvalBrowserSession(_DummyEvalPage("Invalid security code"))
    assert await _has_otp_block(session) is True


def test_create_hitl_tools_registers_custom_form_actions() -> None:
    tools = create_hitl_tools()
    actions = tools.registry.registry.actions

    for name in (
        "input",
        "dropdown_options",
        "select_dropdown",
        "upload_file",
        "mark_field_intentionally_blank",
        "preflight_check",
        "confirm_submit",
    ):
        assert name in actions


@pytest.mark.asyncio
async def test_ask_yes_no_defaults_to_no_on_eof(monkeypatch) -> None:
    tools = create_hitl_tools()
    ask_yes_no = tools.registry.registry.actions["ask_yes_no"].function

    def _raise_eof(_question: str) -> bool:
        raise EOFError

    monkeypatch.setattr("src.hitl.tools.prompt_yes_no", _raise_eof)
    assert await ask_yes_no(question="continue?") == "no"


@pytest.mark.asyncio
async def test_ask_free_text_defaults_empty_on_eof(monkeypatch) -> None:
    tools = create_hitl_tools()
    ask_free_text = tools.registry.registry.actions["ask_free_text"].function

    def _raise_eof(_question: str) -> str:
        raise EOFError

    monkeypatch.setattr("src.hitl.tools.prompt_free_text", _raise_eof)
    assert await ask_free_text(question="text?") == ""


@pytest.mark.asyncio
async def test_ask_otp_code_defaults_empty_on_eof(monkeypatch) -> None:
    tools = create_hitl_tools()
    ask_otp_code = tools.registry.registry.actions["ask_otp_code"].function

    def _raise_eof(_prompt: str) -> str:
        raise EOFError

    monkeypatch.setattr("src.hitl.tools.prompt_otp_code", _raise_eof)
    assert await ask_otp_code(prompt="otp?") == "__OTP_UNAVAILABLE_NON_INTERACTIVE__"
