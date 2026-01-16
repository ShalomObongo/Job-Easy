"""Unit tests for the tailoring LLM client.

Tests for TailoringLLM class including initialization, structured output,
error handling, and retry logic.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from src.tailoring.config import TailoringConfig, reset_tailoring_config
from src.tailoring.llm import LLMError, TailoringLLM


# Keys to remove for isolated tests (prevents fallback to EXTRACTOR_* settings)
ENV_KEYS_TO_REMOVE = [
    "TAILORING_LLM_PROVIDER",
    "TAILORING_LLM_MODEL",
    "TAILORING_LLM_API_KEY",
    "TAILORING_LLM_BASE_URL",
    "EXTRACTOR_LLM_PROVIDER",
    "EXTRACTOR_LLM_MODEL",
    "EXTRACTOR_LLM_API_KEY",
    "EXTRACTOR_LLM_BASE_URL",
]


@pytest.fixture
def isolated_env():
    """Remove LLM env vars for isolated testing."""
    # Save original values
    saved = {k: os.environ.pop(k, None) for k in ENV_KEYS_TO_REMOVE}
    reset_tailoring_config()
    yield
    # Restore original values
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v
        elif k in os.environ:
            del os.environ[k]
    reset_tailoring_config()


class SampleOutput(BaseModel):
    """Sample Pydantic model for testing structured output."""

    name: str
    value: int


class TestTailoringLLMInitialization:
    """Tests for TailoringLLM initialization."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    def test_init_with_default_config(self, isolated_env):
        """Test initialization with default configuration."""
        llm = TailoringLLM()
        assert llm.config is not None
        assert llm.config.llm_provider == "openai"
        assert llm.config.llm_model == "gpt-4o"

    def test_init_with_custom_config(self, isolated_env):
        """Test initialization with custom configuration."""
        config = TailoringConfig(
            llm_provider="anthropic",
            llm_model="claude-3-opus",
            llm_max_retries=5,
        )
        llm = TailoringLLM(config=config)
        assert llm.config.llm_provider == "anthropic"
        assert llm.config.llm_model == "claude-3-opus"
        assert llm.config.llm_max_retries == 5

    def test_model_name_formatting(self, isolated_env):
        """Test model name is formatted correctly for LiteLLM."""
        config = TailoringConfig(llm_provider="anthropic", llm_model="claude-3-opus")
        llm = TailoringLLM(config=config)
        assert llm._get_model_name() == "anthropic/claude-3-opus"

    def test_model_name_formatting_openai(self, isolated_env):
        """Test OpenAI model names don't need prefix."""
        config = TailoringConfig(llm_provider="openai", llm_model="gpt-4o")
        llm = TailoringLLM(config=config)
        # OpenAI models don't need prefix
        assert llm._get_model_name() == "gpt-4o"


class TestTailoringLLMStructuredOutput:
    """Tests for structured output generation."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_generate_structured_returns_pydantic_model(self):
        """Test that generate_structured returns parsed Pydantic model."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"name": "test", "value": 42}'))
        ]

        with patch("src.tailoring.llm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            llm = TailoringLLM()
            result = await llm.generate_structured(
                prompt="Generate a sample",
                output_model=SampleOutput,
            )

            assert isinstance(result, SampleOutput)
            assert result.name == "test"
            assert result.value == 42

    @pytest.mark.asyncio
    async def test_generate_structured_with_system_prompt(self):
        """Test that system prompt is included in messages."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"name": "result", "value": 1}'))
        ]

        with patch("src.tailoring.llm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            llm = TailoringLLM()
            await llm.generate_structured(
                prompt="User prompt",
                output_model=SampleOutput,
                system_prompt="You are a helpful assistant",
            )

            call_args = mock_completion.call_args
            messages = call_args.kwargs["messages"]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == "You are a helpful assistant"
            assert messages[1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_generate_structured_passes_response_format(self):
        """Test that response_format is passed to LiteLLM."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"name": "test", "value": 1}'))
        ]

        with patch("src.tailoring.llm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            llm = TailoringLLM()
            await llm.generate_structured(
                prompt="Generate",
                output_model=SampleOutput,
            )

            call_args = mock_completion.call_args
            assert call_args.kwargs["response_format"] == SampleOutput


class TestTailoringLLMErrorHandling:
    """Tests for error handling and retries."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_raises_llm_error_on_failure(self):
        """Test that LLMError is raised when LLM call fails."""
        with patch("src.tailoring.llm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.side_effect = Exception("API Error")

            config = TailoringConfig(llm_max_retries=0)
            llm = TailoringLLM(config=config)

            with pytest.raises(LLMError) as exc_info:
                await llm.generate_structured(
                    prompt="Generate",
                    output_model=SampleOutput,
                )

            assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raises_llm_error_on_invalid_json(self):
        """Test that LLMError is raised when response is invalid JSON."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="not valid json"))
        ]

        with patch("src.tailoring.llm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            llm = TailoringLLM()
            with pytest.raises(LLMError) as exc_info:
                await llm.generate_structured(
                    prompt="Generate",
                    output_model=SampleOutput,
                )

            assert "Failed to parse" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raises_llm_error_on_validation_error(self):
        """Test that LLMError is raised when response fails validation."""
        mock_response = MagicMock()
        # Missing required field 'value'
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"name": "test"}'))
        ]

        with patch("src.tailoring.llm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            llm = TailoringLLM()
            with pytest.raises(LLMError) as exc_info:
                await llm.generate_structured(
                    prompt="Generate",
                    output_model=SampleOutput,
                )

            assert "validation" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_retries_on_transient_failure(self):
        """Test that transient failures trigger retries."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"name": "success", "value": 1}'))
        ]

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Transient error")
            return mock_response

        with patch("src.tailoring.llm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.side_effect = side_effect

            config = TailoringConfig(llm_max_retries=3)
            llm = TailoringLLM(config=config)

            result = await llm.generate_structured(
                prompt="Generate",
                output_model=SampleOutput,
            )

            assert result.name == "success"
            assert call_count == 3


class TestTailoringLLMTextGeneration:
    """Tests for plain text generation."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_generate_text_returns_string(self):
        """Test that generate_text returns a string."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Generated text response"))
        ]

        with patch("src.tailoring.llm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            llm = TailoringLLM()
            result = await llm.generate_text(prompt="Generate some text")

            assert isinstance(result, str)
            assert result == "Generated text response"

    @pytest.mark.asyncio
    async def test_generate_text_with_system_prompt(self):
        """Test that system prompt is included for text generation."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Response"))
        ]

        with patch("src.tailoring.llm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            llm = TailoringLLM()
            await llm.generate_text(
                prompt="User prompt",
                system_prompt="System instructions",
            )

            call_args = mock_completion.call_args
            messages = call_args.kwargs["messages"]
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == "System instructions"


class TestTailoringLLMConfiguration:
    """Tests for LLM configuration options."""

    def teardown_method(self):
        """Reset config after each test."""
        reset_tailoring_config()

    @pytest.mark.asyncio
    async def test_timeout_is_passed_to_completion(self):
        """Test that timeout setting is passed to LiteLLM."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"name": "test", "value": 1}'))
        ]

        with patch("src.tailoring.llm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            config = TailoringConfig(llm_timeout=120.0)
            llm = TailoringLLM(config=config)

            await llm.generate_structured(
                prompt="Generate",
                output_model=SampleOutput,
            )

            call_args = mock_completion.call_args
            assert call_args.kwargs["timeout"] == 120.0

    @pytest.mark.asyncio
    async def test_api_key_is_passed_when_set(self, isolated_env):
        """Test that API key is passed to LiteLLM when configured."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"name": "test", "value": 1}'))
        ]

        with patch("src.tailoring.llm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            config = TailoringConfig(llm_api_key="test-api-key")
            llm = TailoringLLM(config=config)

            await llm.generate_structured(
                prompt="Generate",
                output_model=SampleOutput,
            )

            call_args = mock_completion.call_args
            assert call_args.kwargs["api_key"] == "test-api-key"
