"""LLM client for scoring operations.

Uses LiteLLM to generate structured fit scoring outputs.
"""

from __future__ import annotations

import logging
import os
import time
import warnings
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from src.scoring.config import ScoringConfig, get_scoring_config

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

warnings.filterwarnings(
    "ignore",
    message=r"(?s)^Pydantic serializer warnings:.*",
    category=UserWarning,
)


# LiteLLM loads `.env` into process environment by default (DEV mode).
# This can cause surprising side-effects (e.g., tests unintentionally picking up
# local config). We default to PRODUCTION unless the user explicitly opted into DEV.
os.environ.setdefault("LITELLM_MODE", "PRODUCTION")


class ScoringLLMError(Exception):
    """Exception raised when scoring LLM operations fail."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


class ScoringLLM:
    """LLM client for fit scoring."""

    def __init__(self, config: ScoringConfig | None = None) -> None:
        self.config = config or get_scoring_config()
        self._setup_provider_env()

    def _setup_provider_env(self) -> None:
        """Set up provider-specific environment variables."""
        import os

        if self.config.llm_base_url and self.config.llm_provider == "anthropic":
            base_url = self.config.llm_base_url.rstrip("/")
            if base_url.endswith("/v1"):
                base_url = base_url[:-3]
            os.environ["ANTHROPIC_BASE_URL"] = base_url
            if self.config.llm_api_key:
                os.environ["ANTHROPIC_API_KEY"] = self.config.llm_api_key

    def _get_model_name(self) -> str:
        """Return provider-qualified model name for LiteLLM routing."""
        if self.config.llm_provider == "anthropic":
            if "/" in self.config.llm_model:
                return self.config.llm_model
            return f"anthropic/{self.config.llm_model}"

        if self.config.llm_base_url:
            if "/" in self.config.llm_model:
                return self.config.llm_model
            return f"openai/{self.config.llm_model}"

        if self.config.llm_provider == "openai":
            return self.config.llm_model

        return f"{self.config.llm_provider}/{self.config.llm_model}"

    def generate_structured(
        self,
        *,
        prompt: str,
        output_model: type[T],
        system_prompt: str | None = None,
    ) -> T:
        """Generate structured output matching a Pydantic model."""
        from litellm.exceptions import Timeout

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error: Exception | None = None
        for attempt in range(self.config.llm_max_retries + 1):
            try:
                response = self._call_completion(
                    messages=messages,
                    response_format=output_model,
                )
                return self._parse_response(response, output_model)

            except ScoringLLMError:
                raise

            except Timeout as e:
                raise ScoringLLMError(
                    "LLM request timed out. "
                    f"Increase SCORING_LLM_TIMEOUT (timeout={self.config.llm_timeout}s).",
                    e,
                ) from e

            except Exception as e:
                last_error = e
                if attempt < self.config.llm_max_retries:
                    delay = min(0.5 * (2**attempt), 8.0)
                    logger.warning(
                        "LLM call failed (attempt %s), retrying in %.1fs: %s",
                        attempt + 1,
                        delay,
                        e,
                    )
                    time.sleep(delay)
                    continue
                raise ScoringLLMError(f"LLM call failed after retries: {e}", e) from e

        raise ScoringLLMError(f"LLM call failed: {last_error}", last_error)

    def _call_completion(
        self,
        *,
        messages: list[dict[str, str]],
        response_format: type[BaseModel] | None = None,
    ):
        from litellm import completion

        kwargs: dict[str, Any] = {
            "model": self._get_model_name(),
            "messages": messages,
            "timeout": self.config.llm_timeout,
        }

        reasoning_effort = _normalize_reasoning_effort(self.config.llm_reasoning_effort)
        if reasoning_effort is not None:
            kwargs["reasoning_effort"] = reasoning_effort

        if self.config.llm_api_key:
            kwargs["api_key"] = self.config.llm_api_key

        if self.config.llm_base_url and self.config.llm_provider != "anthropic":
            kwargs["base_url"] = self.config.llm_base_url

        if response_format is not None:
            kwargs["response_format"] = response_format

        return completion(**kwargs)

    def _parse_response(self, response, output_model: type[T]) -> T:
        message = response.choices[0].message
        content = getattr(message, "content", None)

        if content is None:
            tool_calls = getattr(message, "tool_calls", None) or []
            if tool_calls:
                function = getattr(tool_calls[0], "function", None)
                arguments = getattr(function, "arguments", None)
                if isinstance(arguments, str) and arguments.strip():
                    content = arguments

        if content is None:
            raise ScoringLLMError("LLM returned no content to parse.")

        content = self._extract_json_from_response(str(content))

        try:
            return output_model.model_validate_json(content)
        except ValidationError as e:
            raise ScoringLLMError(
                f"Failed to parse LLM response - validation error: {e}", e
            ) from e
        except Exception as e:
            raise ScoringLLMError(
                f"Failed to parse LLM response as JSON: {e}", e
            ) from e

    def _extract_json_from_response(self, content: str) -> str:
        content = content.strip()

        if content.startswith("```"):
            first_newline = content.find("\n")
            if first_newline != -1:
                content = content[first_newline + 1 :]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        if content.startswith("{") or content.startswith("["):
            return content

        def extract_balanced(text: str, open_char: str, close_char: str) -> str | None:
            start = text.find(open_char)
            if start == -1:
                return None

            depth = 0
            for idx in range(start, len(text)):
                ch = text[idx]
                if ch == open_char:
                    depth += 1
                elif ch == close_char:
                    depth -= 1
                    if depth == 0:
                        return text[start : idx + 1].strip()
            return None

        extracted = extract_balanced(content, "{", "}")
        if extracted is not None:
            return extracted

        extracted = extract_balanced(content, "[", "]")
        if extracted is not None:
            return extracted

        return content


def _normalize_reasoning_effort(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if not normalized:
        return None
    if normalized in {"off", "disabled", "0", "false"}:
        return "disable"
    return normalized
