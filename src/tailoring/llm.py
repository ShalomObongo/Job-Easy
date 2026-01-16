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

    def _get_model_name(self) -> str:
        """Get the model name formatted for LiteLLM.

        Returns:
            Model name with provider prefix if needed.
        """
        # OpenAI models don't need a prefix
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
                    wait_time = 2**attempt  # Exponential backoff
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
                    wait_time = 2**attempt
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

        if self.config.llm_api_key:
            kwargs["api_key"] = self.config.llm_api_key

        if self.config.llm_base_url:
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
        content = response.choices[0].message.content

        try:
            return output_model.model_validate_json(content)
        except ValidationError as e:
            raise LLMError(
                f"Failed to parse LLM response - validation error: {e}", e
            ) from e
        except Exception as e:
            raise LLMError(f"Failed to parse LLM response as JSON: {e}", e) from e
