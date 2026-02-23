"""Human-in-the-loop (HITL) tools and prompt helpers.

This module provides:
- small, testable parsing/validation helpers
- interactive prompt wrappers for the CLI
- Browser Use custom tools via `Tools().action(...)` for agents
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
from pathlib import Path
from typing import Literal

from browser_use import BrowserSession, Tools
from browser_use.agent.views import ActionResult

logger = logging.getLogger(__name__)

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

_BOT_PROTECTION_BLOCK_PHRASES = (
    # Ashby / reCAPTCHA spam blocks
    "flagged as possible spam",
    "we couldn't submit your application",
    # Common captcha / bot-protection language
    "please complete the captcha",
    "complete the captcha",
    "verify you are human",
    "robot check",
    "unusual traffic",
    "access denied",
    "attention required",
)

_OTP_BLOCK_PHRASES = (
    "security code",
    "verification code",
    "invalid security code",
    "enter the code",
    "one-time password",
    "two-factor",
    "2fa",
    "otp",
)
_OTP_UNAVAILABLE_SENTINEL = "__OTP_UNAVAILABLE_NON_INTERACTIVE__"

# Placeholder values that often indicate an unselected required combobox/select.
_PLACEHOLDER_VALUES = (
    "select...",
    "select",
    "choose...",
    "choose",
    "start typing...",
    "start typing",
    "search...",
    "search",
)
_INTENTIONAL_BLANK_ATTRIBUTE = "data-job-easy-intentionally-blank"

_UPLOAD_RESUME_HINTS = ("resume", "cv", "curriculum vitae")
_UPLOAD_COVER_HINTS = ("cover", "cover letter")

_COOKIE_BANNER_HINTS = ("cookie", "cookies", "consent", "gdpr", "privacy")
_COOKIE_ACCEPT_TEXTS = (
    "accept all",
    "accept",
    "agree",
    "i agree",
    "allow all",
    "ok",
    "okay",
    "got it",
)
_COOKIE_REJECT_TEXTS = (
    "reject",
    "decline",
    "manage",
    "preferences",
    "settings",
    "learn more",
    "more info",
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


def create_hitl_tools(*, auto_submit: bool = False) -> Tools:
    """Create a Browser Use Tools registry with HITL actions.

    Args:
        auto_submit: If True, confirm_submit will automatically submit without
            prompting the human. Use with caution.
    """
    tools = Tools()
    preflight_last_signature = ""
    preflight_repeat_count = 0

    def _normalize_whitespace(value: str) -> str:
        return " ".join(str(value or "").strip().split()).lower()

    def _digits_only(value: str) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())

    def _values_match(*, expected: str, actual: str) -> bool:
        expected_norm = _normalize_whitespace(expected)
        actual_norm = _normalize_whitespace(actual)
        if expected_norm == actual_norm:
            return True

        expected_digits = _digits_only(expected)
        actual_digits = _digits_only(actual)
        return bool(expected_digits) and expected_digits == actual_digits

    def _detect_sensitive_key_name(
        text: str, sensitive_data: dict[str, str | dict[str, str]] | None
    ) -> str | None:
        if not sensitive_data or not text:
            return None

        for domain_or_key, content in sensitive_data.items():
            if isinstance(content, dict):
                for key, value in content.items():
                    if value and value == text:
                        return key
                continue

            if content and content == text:
                return domain_or_key

        return None

    async def _build_element_for_node(browser_session: BrowserSession, node) -> object:
        from browser_use.actor.element import Element

        page = await browser_session.must_get_current_page()
        session_id = (
            str(getattr(node, "session_id", None) or "") or await page.session_id
        )
        return Element(browser_session, node.backend_node_id, session_id=session_id)

    def _infer_upload_purpose(
        file_path: str,
    ) -> Literal["resume", "cover_letter", "unknown"]:
        name = Path(str(file_path)).name.lower()
        if any(hint in name for hint in _UPLOAD_COVER_HINTS):
            return "cover_letter"
        if any(hint in name for hint in _UPLOAD_RESUME_HINTS):
            return "resume"
        return "unknown"

    def _node_label_hint(node) -> str:
        parts: list[str] = []
        ax = getattr(node, "ax_node", None)
        if ax is not None:
            name = getattr(ax, "name", None)
            description = getattr(ax, "description", None)
            if name:
                parts.append(str(name))
            if description:
                parts.append(str(description))

        attrs = getattr(node, "attributes", None) or {}
        for key in ("aria-label", "name", "id", "data-testid", "data-test", "accept"):
            value = attrs.get(key)
            if value:
                parts.append(str(value))

        return " ".join(parts).strip().lower()

    def _score_upload_candidate(
        *, purpose: Literal["resume", "cover_letter", "unknown"], label_hint: str
    ) -> int:
        if purpose == "unknown":
            return 0

        score = 0
        if purpose == "resume":
            if any(token in label_hint for token in _UPLOAD_RESUME_HINTS):
                score += 10
            if any(token in label_hint for token in _UPLOAD_COVER_HINTS):
                score -= 10
        if purpose == "cover_letter":
            if any(token in label_hint for token in _UPLOAD_COVER_HINTS):
                score += 10
            if any(token in label_hint for token in _UPLOAD_RESUME_HINTS):
                score -= 10
        return score

    def _iter_descendants(root_node, *, max_nodes: int = 1500):
        queue = [root_node]
        seen: set[int] = set()
        count = 0
        while queue and count < max_nodes:
            node = queue.pop(0)
            node_id = getattr(node, "backend_node_id", None)
            if isinstance(node_id, int):
                if node_id in seen:
                    continue
                seen.add(node_id)

            yield node
            count += 1

            for child in getattr(node, "children_nodes", None) or []:
                queue.append(child)
            for shadow in getattr(node, "shadow_roots", None) or []:
                queue.append(shadow)
            content_doc = getattr(node, "content_document", None)
            if content_doc is not None:
                queue.append(content_doc)

    async def _read_typed_value(element) -> str:
        raw = await element.evaluate(
            """
() => {
  const el = this;
  const tag = (el && el.tagName) ? el.tagName.toLowerCase() : '';
  const isEditable = Boolean(el && el.isContentEditable);
  if (isEditable) return (el.textContent || '').trim();
  if (tag === 'input' || tag === 'textarea' || tag === 'select') return String(el.value || '');
  return String(el.innerText || el.textContent || '');
}
"""
        )
        return str(raw or "")

    async def _set_value_with_events(element, value: str) -> str:
        raw = await element.evaluate(
            """
(val) => {
  const el = this;
  const tag = (el && el.tagName) ? el.tagName.toLowerCase() : '';
  const isEditable = Boolean(el && el.isContentEditable);

  if (isEditable) {
    el.focus?.();
    el.textContent = String(val || '');
    el.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
    el.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
    el.blur?.();
    return (el.textContent || '').trim();
  }

  if (tag === 'input' || tag === 'textarea' || tag === 'select') {
    const proto = Object.getPrototypeOf(el);
    const desc = proto ? Object.getOwnPropertyDescriptor(proto, 'value') : null;
    if (desc && typeof desc.set === 'function') {
      desc.set.call(el, String(val || ''));
    } else {
      el.value = String(val || '');
    }

    el.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
    el.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
    el.blur?.();
    return String(el.value || '');
  }

  return '';
}
""",
            value,
        )
        return str(raw or "")

    async def _read_control_snapshot(element) -> dict[str, str]:
        raw = await element.evaluate(
            """
() => JSON.stringify({
  tag: (this && this.tagName) ? this.tagName.toLowerCase() : '',
  value: (this && 'value' in this) ? String(this.value || '') : '',
  text: String(this && (this.innerText || this.textContent || '') || ''),
  selectedText: (this && this.tagName && this.tagName.toLowerCase() === 'select' && this.selectedOptions && this.selectedOptions[0])
    ? String(this.selectedOptions[0].textContent || '')
    : '',
})
"""
        )
        try:
            decoded = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            decoded = {}

        if not isinstance(decoded, dict):
            return {}
        return {key: str(value or "") for key, value in decoded.items()}

    async def _read_dropdown_meta(element) -> dict[str, str]:
        raw = await element.evaluate(
            """
() => JSON.stringify({
  tag: (this && this.tagName) ? this.tagName.toLowerCase() : '',
  role: (this && this.getAttribute) ? String(this.getAttribute('role') || '') : '',
  className: (this && this.className) ? String(this.className) : '',
  ariaExpanded: (this && this.getAttribute) ? String(this.getAttribute('aria-expanded') || '') : '',
  ariaControls: (this && this.getAttribute) ? String(this.getAttribute('aria-controls') || '') : '',
})
"""
        )
        try:
            decoded = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            decoded = {}

        if not isinstance(decoded, dict):
            return {}
        return {key: str(value or "") for key, value in decoded.items()}

    async def _expand_combobox(element) -> None:
        await element.evaluate(
            """
() => {
  const el = this;
  if (!el) return false;
  const expanded = String(el.getAttribute?.('aria-expanded') || '').toLowerCase() === 'true';

  const clickNode = (node) => {
    if (!node || typeof node.click !== 'function') return false;
    try {
      node.click();
      return true;
    } catch (_) {
      return false;
    }
  };

  // Keep an already-open combobox open; avoid accidental toggle-close.
  if (expanded) {
    try { el.focus?.(); } catch (_) {}
    return true;
  }

  // Focus/click the combobox input itself first.
  try { el.focus?.(); } catch (_) {}
  try {
    el.dispatchEvent(new FocusEvent('focusin', { bubbles: true, cancelable: true }));
  } catch (_) {}
  clickNode(el);

  // Greenhouse/React-Select often requires clicking the explicit toggle control.
  const root =
    el.closest('[class*="select__control"]') ||
    el.closest('[class*="select__container"]') ||
    el.closest('[role="group"]') ||
    el.parentElement;
  if (root) {
    const toggle =
      root.querySelector('button[aria-label*="Toggle"]') ||
      root.querySelector('button[aria-label*="toggle"]') ||
      root.querySelector('[aria-label*="Toggle flyout"]');
    clickNode(toggle);
  }

  return true;
}
"""
        )

    async def _extract_visible_combobox_options(element) -> list[str]:
        raw = await element.evaluate(
            """
() => {
  const normalize = (value) => String(value || '').trim();
  const isVisible = (node) => {
    if (!node || node.nodeType !== 1) return false;
    const style = window.getComputedStyle(node);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    const rect = node.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };

  const results = [];
  const controlsId = this && this.getAttribute ? this.getAttribute('aria-controls') : '';
  const pushOption = (node) => {
    const text = normalize(node && (node.innerText || node.textContent || node.value));
    if (text) results.push(text);
  };

  if (controlsId) {
    const listbox = document.getElementById(controlsId);
    if (listbox) {
      listbox
        .querySelectorAll('[role="option"], option')
        .forEach((node) => isVisible(node) && pushOption(node));
    }
  }

  if (!results.length) {
    document
      .querySelectorAll('[role="option"], option')
      .forEach((node) => isVisible(node) && pushOption(node));
  }

  return Array.from(new Set(results));
}
"""
        )
        if isinstance(raw, list):
            return [str(item) for item in raw if str(item).strip()]
        return []

    def _selection_candidates(text: str) -> list[str]:
        base = str(text or "").strip()
        if not base:
            return []

        candidates: list[str] = [base]
        lowered = base.lower()

        normalized = (
            lowered.replace("’", "'")
            .replace(".", " ")
            .replace("-", " ")
            .replace("_", " ")
        )
        compact = " ".join(normalized.split())
        if compact and compact != lowered:
            candidates.append(compact)

        if "bachelor" in compact and "degree" not in compact:
            candidates.extend(["Bachelor's Degree", "Bachelors Degree", "Bachelor Degree"])
        if "master" in compact and "degree" not in compact:
            candidates.extend(["Master's Degree", "Masters Degree", "Master Degree"])
        if "doctor" in compact and "degree" not in compact:
            candidates.extend(["Doctoral Degree", "Doctorate"])

        deduped: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            key = item.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    async def _type_combobox_query(element, query: str) -> None:
        await element.evaluate(
            """
(value) => {
  const el = this;
  if (!el) return '';

  const nextValue = String(value || '');
  try { el.focus?.(); } catch (_) {}

  const proto = Object.getPrototypeOf(el);
  const desc = proto ? Object.getOwnPropertyDescriptor(proto, 'value') : null;
  if (desc && typeof desc.set === 'function') {
    desc.set.call(el, nextValue);
  } else {
    el.value = nextValue;
  }

  try {
    el.dispatchEvent(
      new InputEvent('input', {
        bubbles: true,
        cancelable: true,
        data: nextValue,
        inputType: 'insertText',
      })
    );
  } catch (_) {
    el.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
  }

  el.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));

  try {
    el.dispatchEvent(
      new KeyboardEvent('keydown', {
        key: 'ArrowDown',
        code: 'ArrowDown',
        bubbles: true,
        cancelable: true,
      })
    );
  } catch (_) {}

  return String(el.value || '');
}
""",
            query,
        )

    async def _verify_file_attached(element) -> tuple[int, list[str]]:
        raw = await element.evaluate(
            """
() => {
  const el = this;
  if (!el || !el.files) return JSON.stringify({ count: 0, names: [] });
  const names = Array.from(el.files).map((f) => f && f.name ? String(f.name) : '').filter(Boolean);
  return JSON.stringify({ count: el.files.length || 0, names });
}
"""
        )
        try:
            decoded = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            decoded = {}

        count = int(decoded.get("count") or 0) if isinstance(decoded, dict) else 0
        names_raw = decoded.get("names") if isinstance(decoded, dict) else None
        names = [str(item) for item in names_raw] if isinstance(names_raw, list) else []
        return count, names

    @tools.action(description="Ask the human a yes/no question. Returns 'yes' or 'no'.")
    def ask_yes_no(question: str) -> str:
        try:
            return "yes" if prompt_yes_no(question) else "no"
        except EOFError:
            logger.warning(
                "ask_yes_no received EOF in non-interactive mode; defaulting to 'no'. "
                "question=%r",
                question,
            )
            return "no"

    @tools.action(description="Ask the human for free text input.")
    def ask_free_text(question: str) -> str:
        try:
            return prompt_free_text(question)
        except EOFError:
            logger.warning(
                "ask_free_text received EOF in non-interactive mode; returning empty string. "
                "question=%r",
                question,
            )
            return ""

    @tools.action(
        description=(
            "Mark a field as intentionally blank by element index. "
            "Preflight ignores this marker only for non-required fields."
        )
    )
    async def mark_field_intentionally_blank(
        index: int, browser_session
    ) -> ActionResult:
        node = await browser_session.get_dom_element_by_index(index)
        if node is None:
            msg = (
                f"Element index {index} not available - page may have changed. "
                "Try refreshing browser state."
            )
            logger.warning(msg)
            return ActionResult(extracted_content=msg)

        try:
            element = await _build_element_for_node(browser_session, node)
            await element.evaluate(
                """
(attr) => {
  this.setAttribute(attr, 'true');
  return this.getAttribute(attr);
}
""",
                _INTENTIONAL_BLANK_ATTRIBUTE,
            )
        except Exception as exc:
            return ActionResult(
                error=f"Failed to mark field as intentionally blank: {exc}"
            )

        msg = f"Marked field index {index} as intentionally blank"
        return ActionResult(extracted_content=msg, long_term_memory=msg)

    @tools.action(
        description=(
            "Run a non-submitting preflight check for required/invalid fields. "
            "Returns a JSON list of blockers (missing required fields and invalid fields). "
            "Use this to verify completeness before attempting to submit."
        )
    )
    async def preflight_check(browser_session) -> str:
        nonlocal preflight_last_signature, preflight_repeat_count
        blockers = await preflight_find_blockers(browser_session)
        normalized = tuple(
            sorted({str(item).strip() for item in blockers if str(item).strip()})
        )
        signature = json.dumps(normalized, ensure_ascii=False)

        if not normalized:
            preflight_last_signature = ""
            preflight_repeat_count = 0
        elif signature == preflight_last_signature:
            preflight_repeat_count += 1
        else:
            preflight_last_signature = signature
            preflight_repeat_count = 1

        if normalized and preflight_repeat_count >= 3:
            blockers.append(
                f"stuck:preflight_blockers_repeated:{preflight_repeat_count}"
            )
        return json.dumps(blockers)

    @tools.action(
        description=(
            "Input text into an element by index with verification and retries. "
            "Uses focus+clear+type and then reads the field value to confirm it stuck."
        )
    )
    async def input(
        index: int,
        text: str,
        browser_session,
        clear: bool = True,
        has_sensitive_data=False,
        sensitive_data: dict[str, str | dict[str, str]] | None = None,
    ) -> ActionResult:
        node = await browser_session.get_dom_element_by_index(index)
        if node is None:
            msg = (
                f"Element index {index} not available - page may have changed. "
                "Try refreshing browser state."
            )
            logger.warning(msg)
            return ActionResult(extracted_content=msg)

        element = await _build_element_for_node(browser_session, node)

        meta_raw = await element.evaluate(
            """
() => JSON.stringify({
  tag: (this && this.tagName) ? this.tagName.toLowerCase() : '',
  type: (this && this.getAttribute) ? (this.getAttribute('type') || '') : '',
  isContentEditable: Boolean(this && this.isContentEditable),
})
"""
        )
        try:
            meta = json.loads(meta_raw) if meta_raw else {}
        except json.JSONDecodeError:
            meta = {}

        tag = str(meta.get("tag") or "")
        input_type = str(meta.get("type") or "")
        is_content_editable = bool(meta.get("isContentEditable"))

        if input_type.lower() == "file":
            return ActionResult(
                error="Cannot type into file inputs. Use upload_file(index, path) instead."
            )

        if tag not in {"input", "textarea"} and not is_content_editable:
            return ActionResult(
                error=(
                    f"Element index {index} is not a text input/textarea (tag={tag}). "
                    "Click it first or choose a real input field."
                )
            )

        expected_text = str(text or "")

        last_error: str | None = None
        for attempt in range(1, 4):
            try:
                await element.fill(expected_text, clear=clear)
            except Exception as exc:
                last_error = str(exc)

            actual = await _read_typed_value(element)
            if _values_match(expected=expected_text, actual=actual):
                sensitive_key_name = (
                    _detect_sensitive_key_name(expected_text, sensitive_data)
                    if has_sensitive_data
                    else None
                )
                if has_sensitive_data:
                    msg = (
                        f"Typed {sensitive_key_name}"
                        if sensitive_key_name
                        else "Typed sensitive data"
                    )
                else:
                    msg = f"Typed '{expected_text}'"
                return ActionResult(
                    extracted_content=msg,
                    long_term_memory=msg,
                )

            # Fallback: set value and dispatch events (reactive frameworks).
            try:
                actual = await _set_value_with_events(element, expected_text)
            except Exception as exc:
                last_error = str(exc)
                actual = ""

            if _values_match(expected=expected_text, actual=actual):
                sensitive_key_name = (
                    _detect_sensitive_key_name(expected_text, sensitive_data)
                    if has_sensitive_data
                    else None
                )
                if has_sensitive_data:
                    msg = (
                        f"Typed {sensitive_key_name}"
                        if sensitive_key_name
                        else "Typed sensitive data"
                    )
                else:
                    msg = f"Typed '{expected_text}'"
                return ActionResult(
                    extracted_content=msg,
                    long_term_memory=msg,
                )

            logger.warning(
                "Input verify failed (attempt %s/3): expected=%r actual=%r",
                attempt,
                expected_text,
                actual,
            )
            await asyncio.sleep(0.05)

        error = f"Input did not persist after retries for index {index}." + (
            f" Last error: {last_error}" if last_error else ""
        )
        return ActionResult(error=error)

    @tools.action(
        description=(
            "Get dropdown options by index with combobox support. "
            "For React/ARIA comboboxes, this opens the menu first and extracts visible options."
        )
    )
    async def dropdown_options(index: int, browser_session) -> ActionResult:
        node = await browser_session.get_dom_element_by_index(index)
        if node is None:
            msg = (
                f"Element index {index} not available - page may have changed. "
                "Try refreshing browser state."
            )
            logger.warning(msg)
            return ActionResult(extracted_content=msg)

        from browser_use.browser.events import GetDropdownOptionsEvent

        element = await _build_element_for_node(browser_session, node)
        meta = await _read_dropdown_meta(element)
        is_combobox = meta.get("role") == "combobox"

        # Many React-select controls don't expose aria-controls until expanded.
        if is_combobox and not meta.get("ariaControls"):
            with contextlib.suppress(Exception):
                await _expand_combobox(element)
                await asyncio.sleep(0.12)

        try:
            event = browser_session.event_bus.dispatch(GetDropdownOptionsEvent(node=node))
            dropdown_data = await event.event_result(timeout=3.0)

            if isinstance(dropdown_data, dict):
                short_term = str(dropdown_data.get("short_term_memory") or "").strip()
                long_term = str(dropdown_data.get("long_term_memory") or "").strip()
                if short_term:
                    return ActionResult(
                        extracted_content=short_term,
                        long_term_memory=long_term or f"Got dropdown options for index {index}",
                        include_extracted_content_only_once=True,
                    )
        except Exception as exc:
            logger.warning("dropdown_options event failed at index %s: %s", index, exc)

        # Fallback for combobox/listbox patterns where built-in extraction fails.
        with contextlib.suppress(Exception):
            await _expand_combobox(element)
            await asyncio.sleep(0.12)

        options = await _extract_visible_combobox_options(element)
        if options:
            lines = [
                f'Found dropdown options for index {index}:',
                *[f'{i}: text={json.dumps(option)}' for i, option in enumerate(options)],
                "",
                f"Use select_dropdown(index={index}, text=...) with exact option text.",
            ]
            msg = "\n".join(lines)
            return ActionResult(
                extracted_content=msg,
                long_term_memory=f"Got dropdown options for index {index}",
                include_extracted_content_only_once=True,
            )

        if is_combobox:
            msg = (
                f"No visible options currently for combobox index {index}. "
                "Use select_dropdown(index, text) directly."
            )
            return ActionResult(
                extracted_content=msg,
                long_term_memory=f"Combobox options not currently visible for index {index}",
            )

        return ActionResult(
            error=(
                f"Failed to get dropdown options for index {index}. "
                "Try select_dropdown directly with visible option text."
            )
        )

    @tools.action(
        description=(
            "Select a dropdown option by exact visible text (with verification + fallback). "
            "If the built-in selection fails but options are visible, uses click_visible_option."
        )
    )
    async def select_dropdown(
        index: int,
        text: str,
        browser_session,
    ) -> ActionResult:
        node = await browser_session.get_dom_element_by_index(index)
        if node is None:
            msg = (
                f"Element index {index} not available - page may have changed. "
                "Try refreshing browser state."
            )
            logger.warning(msg)
            return ActionResult(extracted_content=msg)

        from browser_use.browser.events import SelectDropdownOptionEvent

        element = await _build_element_for_node(browser_session, node)
        meta = await _read_dropdown_meta(element)
        if meta.get("role") == "combobox" and not meta.get("ariaControls"):
            with contextlib.suppress(Exception):
                await _expand_combobox(element)
                await asyncio.sleep(0.12)

        selection_data: dict[str, str] | None = None
        chosen_text = str(text or "").strip()
        candidates = _selection_candidates(chosen_text) or [chosen_text]
        is_combobox = meta.get("role") == "combobox"

        # Some comboboxes already contain the chosen value (resume/profile prefill).
        # Treat that as success instead of forcing a fragile re-selection.
        if is_combobox:
            with contextlib.suppress(Exception):
                snapshot = await _read_control_snapshot(element)
                existing_values = [
                    str(snapshot.get("value") or ""),
                    str(snapshot.get("selectedText") or ""),
                    str(snapshot.get("text") or ""),
                ]
                for candidate in candidates:
                    if any(
                        _values_match(expected=candidate, actual=value)
                        for value in existing_values
                        if value
                    ):
                        msg = f"Selected option: {candidate}"
                        return ActionResult(
                            extracted_content=msg,
                            include_in_memory=True,
                            long_term_memory=f"Selected dropdown option '{candidate}' at index {index}",
                        )

        for candidate in candidates:
            try:
                event = browser_session.event_bus.dispatch(
                    SelectDropdownOptionEvent(node=node, text=candidate)
                )
                selection_data = await event.event_result()
            except Exception as exc:
                logger.warning("select_dropdown event failed: %s", exc)
                selection_data = None

            if isinstance(selection_data, dict) and selection_data.get("success") == "true":
                chosen_text = candidate
                break

        success = bool(selection_data and selection_data.get("success") == "true")
        if not success and is_combobox:
            with contextlib.suppress(Exception):
                await _expand_combobox(element)
                await _type_combobox_query(element, chosen_text)
                await asyncio.sleep(0.12)
                for candidate in candidates:
                    event = browser_session.event_bus.dispatch(
                        SelectDropdownOptionEvent(node=node, text=candidate)
                    )
                    retry_data = await event.event_result(timeout=2.0)
                    if isinstance(retry_data, dict):
                        selection_data = retry_data
                        if retry_data.get("success") == "true":
                            chosen_text = candidate
                            break

            success = bool(selection_data and selection_data.get("success") == "true")

        if not success:
            try:
                await _expand_combobox(element)
                await asyncio.sleep(0.05)
            except Exception:
                pass

            for candidate in candidates:
                if is_combobox:
                    with contextlib.suppress(Exception):
                        await _expand_combobox(element)
                        await _type_combobox_query(element, candidate)
                        await asyncio.sleep(0.12)

                fallback_raw = await click_visible_option(
                    option_text=candidate,
                    browser_session=browser_session,
                    exact_match=True,
                )
                try:
                    fallback = json.loads(fallback_raw) if fallback_raw else {}
                except json.JSONDecodeError:
                    fallback = {}

                if isinstance(fallback, dict) and fallback.get("status") == "clicked":
                    msg = f"Selected option: {candidate}"
                    return ActionResult(
                        extracted_content=msg,
                        long_term_memory=f"Selected dropdown option '{candidate}' at index {index}",
                    )

            # Last attempt: allow partial text match for dynamic option labels.
            for candidate in candidates:
                if is_combobox:
                    with contextlib.suppress(Exception):
                        await _expand_combobox(element)
                        await _type_combobox_query(element, candidate)
                        await asyncio.sleep(0.12)

                fallback_raw = await click_visible_option(
                    option_text=candidate,
                    browser_session=browser_session,
                    exact_match=False,
                )
                try:
                    fallback = json.loads(fallback_raw) if fallback_raw else {}
                except json.JSONDecodeError:
                    fallback = {}

                if isinstance(fallback, dict) and fallback.get("status") == "clicked":
                    chosen = str(fallback.get("chosen") or candidate).strip()
                    msg = f"Selected option: {chosen}"
                    return ActionResult(
                        extracted_content=msg,
                        long_term_memory=f"Selected dropdown option '{chosen}' at index {index}",
                    )

            # Final combobox fallback: if the typed value persisted in the control,
            # continue and let preflight_check validate whether the field is acceptable.
            if is_combobox:
                with contextlib.suppress(Exception):
                    element = await _build_element_for_node(browser_session, node)
                    snapshot = await _read_control_snapshot(element)
                    existing_values = [
                        str(snapshot.get("value") or ""),
                        str(snapshot.get("selectedText") or ""),
                        str(snapshot.get("text") or ""),
                    ]
                    for candidate in candidates:
                        if any(
                            _values_match(expected=candidate, actual=value)
                            for value in existing_values
                            if value
                        ):
                            msg = f"Selected option: {candidate}"
                            return ActionResult(
                                extracted_content=msg,
                                include_in_memory=True,
                                long_term_memory=(
                                    f"Selected dropdown option '{candidate}' at index {index}"
                                ),
                            )

            error = (
                selection_data.get("error") if selection_data else None
            ) or f"Failed to select option: {chosen_text}"
            return ActionResult(error=error)

        # Best-effort verification for native selects / input-based comboboxes.
        try:
            element = await _build_element_for_node(browser_session, node)
            decoded = await _read_control_snapshot(element)
            candidates = [
                str(decoded.get("value") or ""),
                str(decoded.get("selectedText") or ""),
                str(decoded.get("text") or ""),
            ]
            if any(
                _values_match(expected=chosen_text, actual=value)
                for value in candidates
                if value
            ):
                msg = selection_data.get("message") if selection_data else None
                msg = msg or f"Selected option: {chosen_text}"
                return ActionResult(
                    extracted_content=msg,
                    include_in_memory=True,
                    long_term_memory=f"Selected dropdown option '{chosen_text}' at index {index}",
                )
        except Exception:
            pass

        msg = selection_data.get("message") if selection_data else None
        msg = msg or f"Selected option: {chosen_text}"
        return ActionResult(
            extracted_content=msg,
            include_in_memory=True,
            long_term_memory=f"Selected dropdown option '{chosen_text}' at index {index}",
        )

    @tools.action(
        description=(
            "Upload a file to a file input by index (robust). If the provided element is "
            "a button/label that controls a hidden file input, it will try to locate the "
            "associated <input type=file> in the same DOM subtree and upload there. "
            "Verifies that a file is attached afterward."
        )
    )
    async def upload_file(
        index: int,
        path: str,
        browser_session,
        available_file_paths,
    ) -> ActionResult:
        # Enforce available_file_paths for local runs.
        if path not in set(available_file_paths or []) and getattr(
            browser_session, "is_local", True
        ):
            return ActionResult(
                error=(
                    "File path is not allowed. Use only paths listed in "
                    "available_file_paths."
                )
            )

        node = await browser_session.get_dom_element_by_index(index)
        if node is None:
            msg = (
                f"Element index {index} not available - page may have changed. "
                "Try refreshing browser state."
            )
            logger.warning(msg)
            return ActionResult(extracted_content=msg)

        purpose = _infer_upload_purpose(path)

        selector_map = await browser_session.get_selector_map()
        candidates: list[object] = []

        def add_if_file_input(candidate) -> None:
            try:
                if browser_session.is_file_input(candidate):
                    candidates.append(candidate)
            except Exception:
                return

        add_if_file_input(node)
        if not candidates:
            for candidate in _iter_descendants(node):
                add_if_file_input(candidate)

        ancestor = getattr(node, "parent_node", None)
        for _ in range(4):
            if candidates:
                break
            if ancestor is None:
                break
            for candidate in _iter_descendants(ancestor):
                add_if_file_input(candidate)
            ancestor = getattr(ancestor, "parent_node", None)

        # As a last resort, scan the selector map for file inputs in the current DOM.
        if not candidates and selector_map:
            for candidate in selector_map.values():
                add_if_file_input(candidate)

        if not candidates:
            return ActionResult(error="No file input found to upload into.")

        scored: list[tuple[int, object]] = []
        for candidate in candidates:
            label_hint = _node_label_hint(candidate)
            score = _score_upload_candidate(purpose=purpose, label_hint=label_hint)
            scored.append((score, candidate))

        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_node = scored[0]

        # Safety: never overwrite Resume/CV with cover letter.
        if purpose == "cover_letter" and best_score <= 0:
            return ActionResult(
                error=(
                    "Refusing to upload cover letter without a clear dedicated Cover Letter field. "
                    "Only upload the cover letter if there is a dedicated Cover Letter field."
                )
            )

        from browser_use.browser.events import UploadFileEvent

        try:
            event = browser_session.event_bus.dispatch(
                UploadFileEvent(node=best_node, file_path=path)
            )
            await event
            await event.event_result(raise_if_any=True, raise_if_none=False)
        except Exception as exc:
            return ActionResult(error=f"Upload failed: {exc}")

        try:
            element = await _build_element_for_node(browser_session, best_node)
            count, names = await _verify_file_attached(element)
            if count <= 0:
                return ActionResult(
                    error="Upload did not attach a file (files.length=0)."
                )
            msg = f"Uploaded file to element (files={count})"
            if names:
                msg = f"Uploaded file: {names[0]}"
            return ActionResult(extracted_content=msg, long_term_memory=msg)
        except Exception:
            msg = "Uploaded file"
            return ActionResult(extracted_content=msg, long_term_memory=msg)

    @tools.action(
        description=(
            "Best-effort cookie banner dismissal. Clicks common 'Accept/Agree/Got it' "
            "buttons inside cookie/consent banners across open shadow roots and same-origin iframes."
        )
    )
    async def dismiss_cookie_banner(browser_session) -> str:
        try:
            page = await browser_session.must_get_current_page()
        except Exception:
            return json.dumps({"status": "error", "error": "no_page"})

        script = f"""
() => {{
  const BANNER_HINTS = {list(_COOKIE_BANNER_HINTS)!r}.map((t) => String(t).toLowerCase());
  const ACCEPT = {list(_COOKIE_ACCEPT_TEXTS)!r}.map((t) => String(t).toLowerCase());
  const REJECT = {list(_COOKIE_REJECT_TEXTS)!r}.map((t) => String(t).toLowerCase());

  const normalize = (value) => String(value || '').trim().replace(/\\s+/g, ' ').toLowerCase();

  const isVisible = (el) => {{
    if (!el || el.nodeType !== 1) return false;
    if (el.closest('[aria-hidden=\"true\"]')) return false;
    const style = (el.ownerDocument && el.ownerDocument.defaultView)
      ? el.ownerDocument.defaultView.getComputedStyle(el)
      : window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }};

  const inCookieContext = (el) => {{
    const container = el.closest('[id*=\"cookie\"], [class*=\"cookie\"], [id*=\"consent\"], [class*=\"consent\"], [id*=\"gdpr\"], [class*=\"gdpr\"], [id*=\"privacy\"], [class*=\"privacy\"]');
    if (!container) return false;
    const text = normalize(container.innerText || container.textContent || '');
    return BANNER_HINTS.some((h) => text.includes(h));
  }};

  const matchesAcceptText = (text) => {{
    const t = normalize(text);
    if (!t) return false;
    if (REJECT.some((r) => t.includes(r))) return false;
    return ACCEPT.some((a) => t === a || t.includes(a));
  }};

  const findCandidates = (root) => {{
    let buttons = [];
    try {{
      buttons = Array.from(root.querySelectorAll('button, input[type=\"button\"], input[type=\"submit\"], a[role=\"button\"]'));
    }} catch (_) {{}}

    return buttons.filter((el) => {{
      if (!isVisible(el)) return false;
      if (!inCookieContext(el)) return false;
      const label = el.innerText || el.textContent || el.getAttribute('aria-label') || el.value || '';
      return matchesAcceptText(label);
    }});
  }};

  const queue = [document];
  const seen = new Set();
  while (queue.length) {{
    const root = queue.pop();
    if (!root || seen.has(root)) continue;
    seen.add(root);

    const candidates = findCandidates(root);
    if (candidates.length) {{
      const chosen = candidates[0];
      try {{
        chosen.scrollIntoView({{ block: 'center', inline: 'nearest' }});
      }} catch (_) {{}}
      const label = String(chosen.innerText || chosen.textContent || chosen.getAttribute('aria-label') || chosen.value || '').trim();
      try {{
        chosen.click();
        return JSON.stringify({{ status: 'clicked', label }});
      }} catch (e) {{
        return JSON.stringify({{ status: 'error', error: String(e || 'click_failed'), label }});
      }}
    }}

    let elements = [];
    try {{
      elements = root.querySelectorAll ? Array.from(root.querySelectorAll('*')) : [];
    }} catch (_) {{}}

    for (const el of elements) {{
      try {{
        if (el.shadowRoot) queue.push(el.shadowRoot);
      }} catch (_) {{}}

      if (el.tagName === 'IFRAME') {{
        try {{
          const doc = el.contentDocument;
          if (doc) queue.push(doc);
        }} catch (_) {{}}
      }}
    }}
  }}

  return JSON.stringify({{ status: 'not_found' }});
}}
"""

        try:
            return await page.evaluate(script)
        except Exception as exc:
            return json.dumps({"status": "error", "error": str(exc)})

    @tools.action(
        description=(
            "Fallback dropdown helper: click a visible option by its text. "
            "Searches common listbox patterns (role=option, <option>) across open shadow roots "
            "and same-origin iframes. Returns JSON with status=clicked|not_found|error."
        )
    )
    async def click_visible_option(
        option_text: str,
        browser_session,
        exact_match: bool = True,
    ) -> str:
        try:
            page = await browser_session.must_get_current_page()
        except Exception:
            return json.dumps({"status": "error", "error": "no_page"})

        script = """
(text, exact) => {
  const needle = String(text || '').trim();
  if (!needle) return JSON.stringify({ status: 'error', error: 'empty_text' });

  const normalize = (value) =>
    String(value || '').trim().replace(/\\s+/g, ' ').toLowerCase();
  const target = normalize(needle);

  const isVisible = (el) => {
    if (!el || el.nodeType !== 1) return false;
    if (el.closest('[aria-hidden=\"true\"]')) return false;
    const style = (el.ownerDocument && el.ownerDocument.defaultView)
      ? el.ownerDocument.defaultView.getComputedStyle(el)
      : window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };

  const getText = (el) =>
    normalize(el.innerText || el.textContent || el.value || '');

  const matches = [];
  const queue = [document];
  const seen = new Set();

  while (queue.length) {
    const root = queue.pop();
    if (!root || seen.has(root)) continue;
    seen.add(root);

    let options = [];
    try {
      options = Array.from(root.querySelectorAll('[role=\"option\"], option'));
    } catch (_) {}

    for (const el of options) {
      if (!isVisible(el)) continue;
      const value = getText(el);
      if (!value) continue;
      const ok = exact ? value === target : value.includes(target);
      if (ok) matches.push(el);
    }

    let elements = [];
    try {
      elements = root.querySelectorAll ? Array.from(root.querySelectorAll('*')) : [];
    } catch (_) {}

    for (const el of elements) {
      try {
        if (el.shadowRoot) queue.push(el.shadowRoot);
      } catch (_) {}

      if (el.tagName === 'IFRAME') {
        try {
          const doc = el.contentDocument;
          if (doc) queue.push(doc);
        } catch (_) {}
      }
    }
  }

  if (!matches.length) {
    return JSON.stringify({ status: 'not_found', needle });
  }

  const chosen = matches[0];
  try {
    chosen.scrollIntoView({ block: 'center', inline: 'nearest' });
  } catch (_) {}

  try {
    chosen.click();
  } catch (e) {
    return JSON.stringify({ status: 'error', error: String(e || 'click_failed') });
  }

  const chosenText = chosen.innerText || chosen.textContent || chosen.value || '';
  return JSON.stringify({ status: 'clicked', count: matches.length, chosen: String(chosenText || '').trim() });
}
"""

        try:
            return await page.evaluate(script, option_text, exact_match)
        except Exception as exc:
            return json.dumps({"status": "error", "error": str(exc)})

    confirm_submit_description = (
        "Before final submit, require the human to type YES/yes to confirm; "
        "when confirmed, click the final submit button."
    )
    if auto_submit:
        confirm_submit_description = (
            "Auto-submit mode: Click the final submit button automatically "
            "(no human confirmation required)."
        )

    @tools.action(description=confirm_submit_description)
    async def confirm_submit(
        prompt: str,
        browser_session,
        submit_button_index: int | None = None,
    ) -> str:
        """Ask for confirmation and, if confirmed, click the final submit button.

        Returns:
            - "submitted": user confirmed and we clicked a submit button
            - "confirmed": user confirmed but we could not click automatically
            - "cancelled": user did not confirm
            - "blocked_missing_fields": form has required field errors
            - "blocked_otp": an OTP/verification step is blocking submission
            - "blocked_captcha": bot protection/CAPTCHA is blocking submission
        """
        # Preflight: If the form is not actually ready, do not submit yet.
        missing = await preflight_find_blockers(browser_session)
        if missing:
            logger.info("Preflight blocked submit: %s", ", ".join(missing[:8]))
            return "blocked_missing_fields"

        # If the page is already blocked by OTP/CAPTCHA, don't prompt/click yet.
        if await _has_bot_protection_block(browser_session):
            return "blocked_captcha"
        if await _has_otp_block(browser_session):
            return "blocked_otp"

        if auto_submit:
            logger.warning(
                "AUTO-SUBMIT: Submitting application without human confirmation"
            )
            confirmed = True
        else:
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
        if await _has_bot_protection_block(browser_session):
            return "blocked_captcha"
        if await _has_otp_block(browser_session):
            return "blocked_otp"
        if await _has_required_field_errors(browser_session):
            return "blocked_missing_fields"
        return "confirmed"

    @tools.action(description="Ask the human for an OTP/2FA code.")
    def ask_otp_code(prompt: str) -> str:
        try:
            return prompt_otp_code(prompt)
        except EOFError:
            logger.warning(
                "ask_otp_code received EOF in non-interactive mode; "
                "returning OTP unavailable sentinel."
            )
            return _OTP_UNAVAILABLE_SENTINEL

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


async def _has_bot_protection_block(browser_session: BrowserSession) -> bool:
    text = (await _get_page_text(browser_session)).lower()
    # Avoid false positives from pages that merely mention reCAPTCHA in a footer.
    if "recaptcha" in text and "protected by recaptcha" in text:
        # Only treat it as blocking if there's an explicit failure indicator.
        return any(phrase in text for phrase in _BOT_PROTECTION_BLOCK_PHRASES)
    return any(phrase in text for phrase in _BOT_PROTECTION_BLOCK_PHRASES)


async def _has_otp_block(browser_session: BrowserSession) -> bool:
    text = (await _get_page_text(browser_session)).lower()
    return any(phrase in text for phrase in _OTP_BLOCK_PHRASES)


async def preflight_find_blockers(browser_session: BrowserSession) -> list[str]:
    """Find high-confidence blockers without submitting the form.

    Returns a list of short labels describing what appears to be missing/invalid.

    Important:
    - Only blocks on required or explicitly invalid fields.
    - Does not block on intentionally empty optional fields.
    """
    try:
        page = await browser_session.must_get_current_page()
    except Exception:
        return []

    script = f"""
() => {{
  const PLACEHOLDERS = new Set({list(_PLACEHOLDER_VALUES)!r});
  const INTENTIONAL_BLANK_ATTR = {_INTENTIONAL_BLANK_ATTRIBUTE!r};

  const normalize = (value) => String(value || '').trim().toLowerCase();

  const isVisible = (el) => {{
    if (!el || el.nodeType !== 1) return false;
    if (el.closest('[aria-hidden=\"true\"]')) return false;
    const style = (el.ownerDocument && el.ownerDocument.defaultView)
      ? el.ownerDocument.defaultView.getComputedStyle(el)
      : window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    const rect = el.getBoundingClientRect();
    return (rect.width > 0 && rect.height > 0);
  }};

  const isRequired = (el) => {{
    if (!el) return false;
    if (el.disabled) return false;
    if (el.getAttribute && el.getAttribute('aria-required') === 'true') return true;
    return Boolean(el.required);
  }};

  const isIntentionallyBlank = (el) => {{
    if (!el || !el.getAttribute) return false;
    return String(el.getAttribute(INTENTIONAL_BLANK_ATTR) || '').toLowerCase() === 'true';
  }};

  const labelFor = (el) => {{
    const aria = el.getAttribute && (el.getAttribute('aria-label') || el.getAttribute('name'));
    if (aria) return String(aria).trim();
    const doc = el.ownerDocument || document;
    if (el.id) {{
      const lbl = doc.querySelector(`label[for=\"${{CSS.escape(el.id)}}\"]`);
      if (lbl && lbl.innerText) return lbl.innerText.trim();
    }}
    const wrapperLabel = el.closest('label');
    if (wrapperLabel && wrapperLabel.innerText) return wrapperLabel.innerText.trim();
    return el.id ? `#${{el.id}}` : el.tagName.toLowerCase();
  }};

  const isPlaceholderValue = (value) => {{
    const norm = normalize(value);
    return norm === '' || PLACEHOLDERS.has(norm);
  }};

  const hasComboboxSelection = (el) => {{
    if (!el || !el.getAttribute) return false;
    if (String(el.getAttribute('role') || '').toLowerCase() !== 'combobox') return false;

    const owner = el.ownerDocument || document;
    const controlsId = String(el.getAttribute('aria-controls') || '').trim();
    if (controlsId) {{
      const listbox = owner.getElementById(controlsId);
      if (listbox) {{
        const selected = listbox.querySelector('[role=\"option\"][aria-selected=\"true\"]');
        if (selected && normalize(selected.textContent || selected.innerText || selected.value)) {{
          return true;
        }}
      }}
    }}

    const root =
      el.closest('[class*=\"select__control\"]') ||
      el.closest('[class*=\"select__container\"]') ||
      el.closest('[role=\"group\"]') ||
      el.parentElement;
    if (!root) return false;

    if (root.querySelector('[aria-label=\"Clear selections\"]')) return true;

    const selectedNode = root.querySelector(
      '.select__single-value, [class*=\"single-value\"], [class*=\"multi-value__label\"], [aria-selected=\"true\"]'
    );
    if (selectedNode && normalize(selectedNode.textContent || selectedNode.innerText)) {{
      return true;
    }}

    const valueContainer = root.querySelector('.select__value-container, [class*=\"value-container\"]');
    if (valueContainer && /has-value|selected/i.test(String(valueContainer.className || ''))) {{
      return true;
    }}

    return false;
  }};

  const addUnique = (set, item) => {{
    const value = String(item || '').trim();
    if (value) set.add(value);
  }};

  const collectFromRoot = (root, out) => {{
    if (!root || !root.querySelectorAll) return;

    const inputs = Array.from(root.querySelectorAll('input, textarea, select'));

    // Radios: group by name when required.
    const requiredRadioNames = new Set();
    for (const el of inputs) {{
      const tag = String(el.tagName || '').toLowerCase();
      if (tag !== 'input') continue;
      const type = String(el.type || el.getAttribute('type') || '').toLowerCase();
      if (type !== 'radio') continue;
      if (!isVisible(el)) continue;
      if (!isRequired(el)) continue;
      if (el.name) requiredRadioNames.add(el.name);
    }}
    for (const name of requiredRadioNames) {{
      const group = Array.from(root.querySelectorAll(`input[type=\"radio\"][name=\"${{CSS.escape(name)}}\"]`));
      const anyChecked = group.some((r) => Boolean(r.checked));
      if (!anyChecked) addUnique(out.missing, `radio:${{name}}`);
    }}

    // Checkboxes: group by name when required (at least one must be checked).
    const requiredCheckboxNames = new Set();
    for (const el of inputs) {{
      const tag = String(el.tagName || '').toLowerCase();
      if (tag !== 'input') continue;
      const type = String(el.type || el.getAttribute('type') || '').toLowerCase();
      if (type !== 'checkbox') continue;
      if (!isVisible(el)) continue;
      if (!isRequired(el)) continue;
      if (el.name) requiredCheckboxNames.add(el.name);
    }}
    for (const name of requiredCheckboxNames) {{
      const group = Array.from(
        root.querySelectorAll(`input[type=\"checkbox\"][name=\"${{CSS.escape(name)}}\"]`)
      ).filter((c) => isVisible(c) && !c.disabled);
      if (!group.length) continue;
      const anyChecked = group.some((c) => Boolean(c.checked));
      if (!anyChecked) addUnique(out.missing, `checkbox:${{name}}`);
    }}

    for (const el of inputs) {{
      if (!isVisible(el)) continue;
      if (isIntentionallyBlank(el) && !isRequired(el)) continue;
      const tag = String(el.tagName || '').toLowerCase();

      if (tag === 'input') {{
        const type = String(el.type || el.getAttribute('type') || '').toLowerCase();
        if (type === 'hidden') continue;
        if (type === 'radio') continue;

        if (type === 'checkbox') {{
          if (el.name && requiredCheckboxNames.has(el.name)) continue;
          if (isRequired(el) && !el.checked) addUnique(out.missing, labelFor(el));
          continue;
        }}

        if (type === 'file') {{
          if (isRequired(el) && (!el.files || el.files.length === 0)) {{
            addUnique(out.missing, labelFor(el));
          }}
          continue;
        }}

        const required = isRequired(el);
        const value = String(el.value || '');
        const comboboxSelected = hasComboboxSelection(el);
        if (required && !comboboxSelected && isPlaceholderValue(value)) {{
          addUnique(out.missing, labelFor(el));
        }}

        const ariaInvalid = el.getAttribute('aria-invalid') === 'true';
        let invalid = ariaInvalid || (typeof el.checkValidity === 'function' && !el.checkValidity());
        if (String(el.getAttribute('role') || '').toLowerCase() === 'combobox' && comboboxSelected) {{
          // React-select style comboboxes often keep stale aria-invalid on the input
          // even after a visible value is selected.
          invalid = false;
        }}
        if (invalid && (required || String(value || '').trim() !== '')) addUnique(out.invalid, labelFor(el));
        continue;
      }}

      if (tag === 'textarea') {{
        const required = isRequired(el);
        const value = String(el.value || '');
        if (required && isPlaceholderValue(value)) addUnique(out.missing, labelFor(el));

        const ariaInvalid = el.getAttribute('aria-invalid') === 'true';
        const invalid = ariaInvalid || (typeof el.checkValidity === 'function' && !el.checkValidity());
        if (invalid && (required || String(value || '').trim() !== '')) addUnique(out.invalid, labelFor(el));
        continue;
      }}

      if (tag === 'select') {{
        const required = isRequired(el);
        const option = el.selectedOptions && el.selectedOptions[0];
        const text = option ? option.textContent : '';
        const value = String(el.value || '');
        const missingValue = isPlaceholderValue(value) || isPlaceholderValue(text);
        if (required && missingValue) addUnique(out.missing, labelFor(el));

        const ariaInvalid = el.getAttribute('aria-invalid') === 'true';
        const invalid = ariaInvalid || (typeof el.checkValidity === 'function' && !el.checkValidity());
        if (invalid && (required || String(value || '').trim() !== '')) addUnique(out.invalid, labelFor(el));
      }}
    }}
  }};

  const queue = [document];
  const seen = new Set();
  const out = {{ missing: new Set(), invalid: new Set() }};

  while (queue.length) {{
    const root = queue.pop();
    if (!root || seen.has(root)) continue;
    seen.add(root);
    try {{
      collectFromRoot(root, out);
    }} catch (_) {{}}

    let elements = [];
    try {{
      elements = root.querySelectorAll ? Array.from(root.querySelectorAll('*')) : [];
    }} catch (_) {{}}

    for (const el of elements) {{
      try {{
        if (el.shadowRoot) queue.push(el.shadowRoot);
      }} catch (_) {{}}

      if (el.tagName === 'IFRAME') {{
        try {{
          const doc = el.contentDocument;
          if (doc) queue.push(doc);
        }} catch (_) {{}}
      }}
    }}
  }}

  return {{
    missing: Array.from(out.missing).slice(0, 50),
    invalid: Array.from(out.invalid).slice(0, 50),
  }};
}}
"""

    try:
        raw_result = await page.evaluate(script)
    except Exception:
        # Fall back to text-based required error detection.
        return (
            ["required_field_error_text"]
            if await _has_required_field_errors(browser_session)
            else []
        )

    result: dict[str, object] | None = None
    if isinstance(raw_result, dict):
        result = raw_result
    elif isinstance(raw_result, str):
        try:
            decoded = json.loads(raw_result) if raw_result.strip() else {}
        except json.JSONDecodeError:
            decoded = {}
        if isinstance(decoded, dict):
            result = decoded

    missing = result.get("missing") if result is not None else None
    invalid = result.get("invalid") if result is not None else None

    blockers: list[str] = []
    if isinstance(missing, list):
        blockers.extend(str(item) for item in missing if str(item).strip())
    if isinstance(invalid, list):
        blockers.extend(f"invalid:{item}" for item in invalid if str(item).strip())
    return blockers


async def _has_submit_success_text(browser_session: BrowserSession) -> bool:
    # Give the page a moment to transition after submit.
    await asyncio.sleep(0.75)
    text = (await _get_page_text(browser_session)).lower()
    return any(phrase in text for phrase in _SUBMIT_SUCCESS_PHRASES)
