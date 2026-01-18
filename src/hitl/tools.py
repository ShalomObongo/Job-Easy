"""Human-in-the-loop (HITL) tools and prompt helpers.

This module provides:
- small, testable parsing/validation helpers
- interactive prompt wrappers for the CLI
- Browser Use custom tools via `Tools().action(...)` for agents
"""

import asyncio

from browser_use import BrowserSession, Tools

_REQUIRED_ERROR_PHRASES = (
    "this field is required.",
    "resume/cv is required.",
    "cover letter is required.",
)

_SUBMIT_SUCCESS_PHRASES = (
    "thank you for applying",
    "your application has been submitted",
    "application submitted",
    "application received",
)


def parse_yes_no(answer: str) -> bool:
    """Parse a yes/no answer.

    Accepts common variants (y/yes, n/no), case- and whitespace-insensitive.
    """
    normalized = answer.strip().lower()
    if normalized in {"y", "yes"}:
        return True
    if normalized in {"n", "no"}:
        return False
    raise ValueError("Expected yes/no answer")


def is_submit_confirmed(answer: str) -> bool:
    """Return True only when the user explicitly confirms submission."""
    return answer.strip().lower() == "yes"


def normalize_otp_code(answer: str) -> str:
    """Normalize an OTP/2FA code entered by the user."""
    return answer.strip()


def prompt_yes_no(question: str) -> bool:
    """Prompt the user for a yes/no response until valid."""
    while True:
        answer = input(f"{question} (y/n) > ")
        try:
            return parse_yes_no(answer)
        except ValueError:
            print("Please answer with 'y'/'yes' or 'n'/'no'.")


def prompt_free_text(question: str) -> str:
    """Prompt the user for free text."""
    return input(f"{question} > ").strip()


def prompt_confirm_submit(prompt: str) -> bool:
    """Prompt for explicit submit confirmation ('YES' / 'yes')."""
    answer = input(f"{prompt} > ")
    return is_submit_confirmed(answer)


def prompt_otp_code(prompt: str) -> str:
    """Prompt user for OTP/2FA code."""
    return normalize_otp_code(input(f"{prompt} > "))


def create_hitl_tools() -> Tools:
    """Create a Browser Use Tools registry with HITL actions."""
    tools = Tools()

    @tools.action(description="Ask the human a yes/no question. Returns 'yes' or 'no'.")
    def ask_yes_no(question: str) -> str:
        return "yes" if prompt_yes_no(question) else "no"

    @tools.action(description="Ask the human for free text input.")
    def ask_free_text(question: str) -> str:
        return prompt_free_text(question)

    @tools.action(
        description=(
            "Before final submit, require the human to type YES/yes to confirm; "
            "when confirmed, click the final submit button."
        )
    )
    async def confirm_submit(
        prompt: str,
        browser_session: BrowserSession,
        submit_button_index: int | None = None,
    ) -> str:
        """Ask for confirmation and, if confirmed, click the final submit button.

        Returns:
            - "submitted": user confirmed and we clicked a submit button
            - "confirmed": user confirmed but we could not click automatically
            - "cancelled": user did not confirm
        """
        # If the form is not actually ready, do not ask for confirmation yet.
        if await _has_required_field_errors(browser_session):
            return "blocked_missing_fields"

        confirmed = prompt_confirm_submit(prompt)
        if not confirmed:
            return "cancelled"

        clicked = await _click_submit_button(
            browser_session=browser_session, submit_button_index=submit_button_index
        )
        if not clicked:
            return "confirmed"

        # After clicking submit, best-effort verify if submission succeeded.
        if await _has_submit_success_text(browser_session):
            return "submitted"
        if await _has_required_field_errors(browser_session):
            return "blocked_missing_fields"
        return "confirmed"

    @tools.action(description="Ask the human for an OTP/2FA code.")
    def ask_otp_code(prompt: str) -> str:
        return prompt_otp_code(prompt)

    return tools


async def _click_submit_button(
    *, browser_session: BrowserSession, submit_button_index: int | None
) -> bool:
    """Best-effort click of a submit/apply button on the current page.

    Prefers an explicit DOM index (when provided) and falls back to CSS selectors.
    """
    try:
        page = await browser_session.must_get_current_page()
    except Exception:
        return False

    # 1) If the agent found a specific index for the final submit button, use it.
    if submit_button_index is not None:
        try:
            node = await browser_session.get_dom_element_by_index(submit_button_index)
            if node and node.backend_node_id:
                element = await page.get_element(node.backend_node_id)
                await element.click()
                await asyncio.sleep(0)
                return True
        except Exception:
            # Fall back to selector-based search below.
            pass

    # 2) Fallback: find submit-style controls.
    try:
        candidates = await page.get_elements_by_css_selector(
            'button[type="submit"], input[type="submit"]'
        )
    except Exception:
        return False

    if not candidates:
        return False

    best_element = None
    best_score: int | None = None
    for element in candidates:
        try:
            score = await _score_submit_candidate(element)
        except Exception:
            continue
        if best_score is None or score > best_score:
            best_score = score
            best_element = element

    if best_element is None:
        return False

    try:
        await best_element.click()
        await asyncio.sleep(0)
        return True
    except Exception:
        return False


async def _score_submit_candidate(element) -> int:
    """Heuristic scoring for submit/apply buttons."""
    # Prefer visible-ish elements.
    try:
        bbox = await element.get_bounding_box()
        if bbox is None:
            return -1000
        if getattr(bbox, "width", 0) <= 0 or getattr(bbox, "height", 0) <= 0:
            return -1000
    except Exception:
        pass

    label_parts: list[str] = []
    for attr in ("aria-label", "value"):
        try:
            value = await element.get_attribute(attr)
        except Exception:
            value = None
        if value:
            label_parts.append(value)

    try:
        text = await element.evaluate("el => (el.innerText || el.value || '').trim()")
        if text:
            label_parts.append(text)
    except Exception:
        pass

    label = " ".join(label_parts).strip().lower()

    score = 0
    positive = ("submit", "apply", "send", "finish", "complete", "sign up")
    negative = ("next", "continue", "back", "cancel", "save", "later")

    for token in positive:
        if token in label:
            score += 10
    for token in negative:
        if token in label:
            score -= 10

    # If we can't read any label text, still allow it but de-prioritize.
    if not label:
        score -= 5

    return score


async def _get_page_text(browser_session: BrowserSession) -> str:
    try:
        page = await browser_session.must_get_current_page()
    except Exception:
        return ""

    try:
        text = await page.evaluate(
            "() => (document.body && document.body.innerText) ? document.body.innerText : ''"
        )
    except Exception:
        return ""

    return text or ""


async def _has_required_field_errors(browser_session: BrowserSession) -> bool:
    text = (await _get_page_text(browser_session)).lower()
    return any(phrase in text for phrase in _REQUIRED_ERROR_PHRASES)


async def _has_submit_success_text(browser_session: BrowserSession) -> bool:
    # Give the page a moment to transition after submit.
    await asyncio.sleep(0.75)
    text = (await _get_page_text(browser_session)).lower()
    return any(phrase in text for phrase in _SUBMIT_SUCCESS_PHRASES)
