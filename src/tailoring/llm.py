"""LLM client for the Tailoring module.

Provides a unified interface for LLM calls with structured output support,
retry logic, and error handling using LiteLLM.
"""

from __future__ import annotations

import asyncio
import logging
import warnings
from typing import TypeVar

from litellm import Timeout, acompletion
from pydantic import BaseModel, ValidationError

from src.tailoring.config import TailoringConfig, get_tailoring_config

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

warnings.filterwarnings(
    "ignore",
    message=r"(?s)^Pydantic serializer warnings:.*",
    category=UserWarning,
)


class LLMError(Exception):
    """Exception raised when LLM operations fail."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


class TailoringLLM:
    """LLM client for tailoring operations.

    Provides structured output generation with Pydantic models,
    automatic retries, and error handling.
    """

    def __init__(self, config: TailoringConfig | None = None):
        """Initialize the LLM client.

        Args:
            config: Optional TailoringConfig. Uses global config if not provided.
        """
        self.config = config or get_tailoring_config()
        self._setup_provider_env()

    def _setup_provider_env(self) -> None:
        """Set up provider-specific environment variables.

        Some providers (like Anthropic) require environment variables for
        custom base URLs rather than passing them as parameters.
        """
        import os

        if self.config.llm_base_url and self.config.llm_provider == "anthropic":
            # Anthropic needs ANTHROPIC_BASE_URL environment variable
            # Strip /v1 suffix if present since Anthropic SDK adds it
            base_url = self.config.llm_base_url.rstrip("/")
            if base_url.endswith("/v1"):
                base_url = base_url[:-3]
            os.environ["ANTHROPIC_BASE_URL"] = base_url
            if self.config.llm_api_key:
                os.environ["ANTHROPIC_API_KEY"] = self.config.llm_api_key

    def _get_model_name(self) -> str:
        """Get the model name formatted for LiteLLM.

        Returns:
            Model name with provider prefix if needed.
        """
        # For Anthropic provider with custom base URL, use anthropic/ prefix
        if self.config.llm_provider == "anthropic":
            if "/" in self.config.llm_model:
                return self.config.llm_model
            return f"anthropic/{self.config.llm_model}"

        # For custom base URLs (local models, proxies), always use openai/ prefix
        # so LiteLLM routes to the OpenAI-compatible endpoint
        if self.config.llm_base_url:
            # If model already has a prefix (e.g., groq/openai/...), use as-is
            if "/" in self.config.llm_model:
                return self.config.llm_model
            return f"openai/{self.config.llm_model}"

        # For standard OpenAI API (no custom base URL), no prefix needed
        if self.config.llm_provider == "openai":
            return self.config.llm_model

        # Other providers need prefix format: provider/model
        return f"{self.config.llm_provider}/{self.config.llm_model}"

    async def generate_structured(
        self,
        prompt: str,
        output_model: type[T],
        system_prompt: str | None = None,
    ) -> T:
        """Generate structured output matching a Pydantic model.

        Args:
            prompt: The user prompt to send to the LLM.
            output_model: Pydantic model class defining the expected output structure.
            system_prompt: Optional system prompt for context.

        Returns:
            Parsed Pydantic model instance.

        Raises:
            LLMError: If the LLM call fails or response cannot be parsed.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error: Exception | None = None
        for attempt in range(self.config.llm_max_retries + 1):
            try:
                response = await self._call_completion(
                    messages=messages,
                    response_format=output_model,
                )
                return self._parse_response(response, output_model)

            except LLMError:
                # Don't retry parse/validation errors
                raise

            except Timeout as e:
                raise LLMError(
                    "LLM request timed out. This usually means the model/server is slow "
                    f"(timeout={self.config.llm_timeout}s). Increase "
                    "`TAILORING_LLM_TIMEOUT` (or use a faster model).",
                    e,
                ) from e

            except Exception as e:
                last_error = e
                if attempt < self.config.llm_max_retries:
                    # Use longer base wait for rate limits (common with Groq free tier)
                    is_rate_limit = "rate_limit" in str(e).lower() or "429" in str(e)
                    base_wait = 8 if is_rate_limit else 2
                    wait_time = base_wait * (
                        attempt + 1
                    )  # Linear backoff for rate limits
                    logger.warning(
                        f"LLM call failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise LLMError(f"LLM call failed after retries: {e}", e) from e

        # Should not reach here, but satisfy type checker
        raise LLMError(f"LLM call failed: {last_error}", last_error)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Generate plain text response.

        Args:
            prompt: The user prompt to send to the LLM.
            system_prompt: Optional system prompt for context.

        Returns:
            Generated text response.

        Raises:
            LLMError: If the LLM call fails.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_error: Exception | None = None
        for attempt in range(self.config.llm_max_retries + 1):
            try:
                response = await self._call_completion(messages=messages)
                return response.choices[0].message.content

            except Timeout as e:
                raise LLMError(
                    "LLM request timed out. This usually means the model/server is slow "
                    f"(timeout={self.config.llm_timeout}s). Increase "
                    "`TAILORING_LLM_TIMEOUT` (or use a faster model).",
                    e,
                ) from e

            except Exception as e:
                last_error = e
                if attempt < self.config.llm_max_retries:
                    # Use longer base wait for rate limits (common with Groq free tier)
                    is_rate_limit = "rate_limit" in str(e).lower() or "429" in str(e)
                    base_wait = 8 if is_rate_limit else 2
                    wait_time = base_wait * (
                        attempt + 1
                    )  # Linear backoff for rate limits
                    logger.warning(
                        f"LLM call failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise LLMError(f"LLM call failed after retries: {e}", e) from e

        raise LLMError(f"LLM call failed: {last_error}", last_error)

    async def _call_completion(
        self,
        messages: list[dict],
        response_format: type[BaseModel] | None = None,
    ):
        """Make the actual LLM API call.

        Args:
            messages: List of message dictionaries.
            response_format: Optional Pydantic model for structured output.

        Returns:
            LiteLLM completion response.
        """
        kwargs = {
            "model": self._get_model_name(),
            "messages": messages,
            "timeout": self.config.llm_timeout,
        }

        reasoning_effort = _normalize_reasoning_effort(self.config.llm_reasoning_effort)
        if reasoning_effort is not None:
            kwargs["reasoning_effort"] = reasoning_effort

        if self.config.llm_api_key:
            kwargs["api_key"] = self.config.llm_api_key

        # For Anthropic, base_url is set via env var in _setup_provider_env()
        # For other providers, pass base_url directly
        if self.config.llm_base_url and self.config.llm_provider != "anthropic":
            kwargs["base_url"] = self.config.llm_base_url

        if response_format:
            kwargs["response_format"] = response_format

        return await acompletion(**kwargs)

    def _parse_response(self, response, output_model: type[T]) -> T:
        """Parse and validate LLM response.

        Args:
            response: LiteLLM completion response.
            output_model: Pydantic model to validate against.

        Returns:
            Validated Pydantic model instance.

        Raises:
            LLMError: If parsing or validation fails.
        """
        message = response.choices[0].message
        content = getattr(message, "content", None)

        # Some providers return structured output as tool call arguments with no content.
        if content is None:
            tool_calls = getattr(message, "tool_calls", None) or []
            if tool_calls:
                function = getattr(tool_calls[0], "function", None)
                arguments = getattr(function, "arguments", None)
                if isinstance(arguments, str) and arguments.strip():
                    content = arguments

        if content is None:
            raise LLMError("LLM returned no content to parse.")

        # Strip markdown code fences if present (common with some models)
        content = self._extract_json_from_response(content)

        try:
            return output_model.model_validate_json(content)
        except ValidationError as e:
            raise LLMError(
                f"Failed to parse LLM response - validation error: {e}", e
            ) from e
        except Exception as e:
            raise LLMError(f"Failed to parse LLM response as JSON: {e}", e) from e

    def _extract_json_from_response(self, content: str) -> str:
        """Extract JSON from response, handling markdown code fences.

        Args:
            content: Raw response content.

        Returns:
            Extracted JSON string.
        """
        content = content.strip()

        # Remove markdown code fences (```json ... ``` or ``` ... ```)
        if content.startswith("```"):
            # Find the end of the first line (language specifier)
            first_newline = content.find("\n")
            if first_newline != -1:
                content = content[first_newline + 1 :]

            # Remove trailing ```
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

        # Some models prepend non-JSON text (reasoning). Extract the first JSON object/array.
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
