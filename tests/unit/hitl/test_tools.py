from __future__ import annotations

import pytest

from src.hitl.tools import (
    _click_submit_button,
    is_submit_confirmed,
    normalize_otp_code,
    parse_yes_no,
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

    clicked = await _click_submit_button(browser_session=session, submit_button_index=1316)

    assert clicked is True
    assert element.clicked is True
    assert session.index_lookups == [1316]
    assert page.css_queries == []


@pytest.mark.asyncio
async def test_click_submit_button_falls_back_to_css_search() -> None:
    element = _DummyElement()
    page = _DummyPage(element)
    session = _DummyBrowserSession(page, node=None)

    clicked = await _click_submit_button(browser_session=session, submit_button_index=1316)

    assert clicked is True
    assert element.clicked is True
    assert session.index_lookups == [1316]
    assert page.css_queries == ['button[type=\"submit\"], input[type=\"submit\"]']
