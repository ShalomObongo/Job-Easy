"""Tests for Browser Use agent configuration."""

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestCreateBrowser:
    """Test create_browser function."""

    def test_create_browser_returns_configured_browser(self):
        """create_browser should return a Browser with correct configuration."""
        from src.extractor.agent import create_browser
        from src.extractor.config import ExtractorConfig

        config = ExtractorConfig(
            _env_file=None,
            headless=True,
            window_width=1920,
            window_height=1080,
        )

        with (
            patch("src.config.settings.get_settings") as mock_get_settings,
            patch("browser_use.Browser") as mock_browser_class,
        ):
            mock_get_settings.return_value = MagicMock(
                use_existing_chrome_profile=False,
                chrome_user_data_dir=None,
                chrome_profile_dir="Default",
                chrome_profile_mode="auto",
            )
            mock_browser = MagicMock()
            mock_browser_class.return_value = mock_browser

            result = create_browser(config)

            mock_browser_class.assert_called_once_with(
                is_local=True,
                use_cloud=False,
                cloud_browser=False,
                headless=True,
                window_size={"width": 1920, "height": 1080},
            )
            assert result is mock_browser

    def test_create_browser_uses_config_values(self):
        """create_browser should use values from config."""
        from src.extractor.agent import create_browser
        from src.extractor.config import ExtractorConfig

        config = ExtractorConfig(
            _env_file=None,
            headless=False,
            window_width=1280,
            window_height=720,
        )

        with (
            patch("src.config.settings.get_settings") as mock_get_settings,
            patch("browser_use.Browser") as mock_browser_class,
        ):
            mock_get_settings.return_value = MagicMock(
                use_existing_chrome_profile=False,
                chrome_user_data_dir=None,
                chrome_profile_dir="Default",
                chrome_profile_mode="auto",
            )
            create_browser(config)

            call_kwargs = mock_browser_class.call_args[1]
            assert call_kwargs["headless"] is False
            assert call_kwargs["is_local"] is True
            assert call_kwargs["window_size"]["width"] == 1280
            assert call_kwargs["window_size"]["height"] == 720

    def test_create_browser_can_use_existing_chrome_profile(self):
        """create_browser should pass Chrome profile settings when enabled."""
        from src.extractor.agent import create_browser
        from src.extractor.config import ExtractorConfig

        config = ExtractorConfig(_env_file=None, headless=False)

        with (
            patch("src.config.settings.get_settings") as mock_get_settings,
            patch(
                "src.extractor.agent._create_chrome_profile_snapshot"
            ) as mock_snapshot,
            patch("browser_use.Browser") as mock_browser_class,
        ):
            mock_get_settings.return_value = MagicMock(
                use_existing_chrome_profile=True,
                chrome_user_data_dir=Path("/tmp/chrome-user-data"),
                chrome_profile_dir="Default",
                chrome_profile_mode="copy",
            )
            snapshot_dir = Path("/tmp/browser-use-user-data-dir-snapshot")
            mock_snapshot.return_value = snapshot_dir

            create_browser(config)

            call_kwargs = mock_browser_class.call_args[1]
            assert call_kwargs["channel"] == "chrome"
            assert call_kwargs["user_data_dir"] == snapshot_dir
            assert call_kwargs["profile_directory"] == "Default"

    def test_create_browser_direct_retries_with_snapshot_on_permission_error(self):
        """direct mode should retry with snapshot when Browser Use copy fails."""
        from src.extractor.agent import create_browser
        from src.extractor.config import ExtractorConfig

        config = ExtractorConfig(_env_file=None, headless=True)

        with (
            patch("src.config.settings.get_settings") as mock_get_settings,
            patch(
                "src.extractor.agent._create_chrome_profile_snapshot"
            ) as mock_snapshot,
            patch("browser_use.Browser") as mock_browser_class,
        ):
            mock_get_settings.return_value = MagicMock(
                use_existing_chrome_profile=True,
                chrome_user_data_dir=Path("/tmp/chrome-user-data"),
                chrome_profile_dir="Profile 1",
                chrome_profile_mode="direct",
            )

            snapshot_dir = Path("/tmp/browser-use-user-data-dir-snapshot")
            mock_snapshot.return_value = snapshot_dir

            mock_browser = MagicMock()
            mock_browser_class.side_effect = [
                PermissionError("[Errno 13] Permission denied: 'Local State'"),
                mock_browser,
            ]

            result = create_browser(config)

            assert result is mock_browser
            assert mock_browser_class.call_count == 2
            assert (
                mock_browser_class.call_args_list[1].kwargs["user_data_dir"]
                == snapshot_dir
            )


class TestCreateExtractionAgent:
    """Test create_extraction_agent function."""

    def test_create_extraction_agent_returns_agent(self):
        """create_extraction_agent should return an Agent with correct parameters."""
        from src.extractor.agent import create_extraction_agent
        from src.extractor.config import ExtractorConfig
        from src.extractor.models import JobDescription

        config = ExtractorConfig(
            _env_file=None,
            use_vision="auto",
            max_failures=3,
        )

        mock_browser = MagicMock()
        mock_llm = MagicMock()
        url = "https://jobs.lever.co/acme/123"

        with patch("browser_use.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent

            result = create_extraction_agent(
                url=url,
                browser=mock_browser,
                llm=mock_llm,
                config=config,
            )

            # Verify Agent was called with correct parameters
            call_kwargs = mock_agent_class.call_args[1]
            assert "task" in call_kwargs
            assert url in call_kwargs["task"]
            assert call_kwargs["browser"] is mock_browser
            assert call_kwargs["llm"] is mock_llm
            assert call_kwargs["output_model_schema"] is JobDescription
            assert call_kwargs["use_vision"] == "auto"
            assert call_kwargs["max_failures"] == 3
            assert call_kwargs["step_timeout"] == 60
            assert result is mock_agent

    def test_create_extraction_agent_uses_output_model_schema(self):
        """create_extraction_agent should set output_model_schema to JobDescription."""
        from src.extractor.agent import create_extraction_agent
        from src.extractor.config import ExtractorConfig
        from src.extractor.models import JobDescription

        config = ExtractorConfig(_env_file=None)
        mock_browser = MagicMock()
        mock_llm = MagicMock()

        with patch("browser_use.Agent") as mock_agent_class:
            create_extraction_agent(
                url="https://example.com/job/123",
                browser=mock_browser,
                llm=mock_llm,
                config=config,
            )

            call_kwargs = mock_agent_class.call_args[1]
            assert call_kwargs["output_model_schema"] is JobDescription
            assert call_kwargs["step_timeout"] == 60


class TestGetExtractionPrompt:
    """Test get_extraction_prompt function."""

    def test_get_extraction_prompt_contains_url(self):
        """get_extraction_prompt should include the URL in the prompt."""
        from src.extractor.agent import get_extraction_prompt

        url = "https://jobs.lever.co/acme/123"
        prompt = get_extraction_prompt(url)

        assert url in prompt

    def test_get_extraction_prompt_mentions_extraction_fields(self):
        """get_extraction_prompt should mention key extraction fields."""
        from src.extractor.agent import get_extraction_prompt

        prompt = get_extraction_prompt("https://example.com/job")

        # Check that key fields are mentioned
        assert "company" in prompt.lower()
        assert "title" in prompt.lower() or "role" in prompt.lower()
        assert "location" in prompt.lower()
        assert "description" in prompt.lower()


class TestGetLLM:
    """Test get_llm function."""

    def test_get_llm_returns_none_if_no_api_keys(self, monkeypatch):
        """get_llm should return None if no API keys are set."""
        from src.extractor.agent import get_llm

        # Clear all relevant API keys
        monkeypatch.delenv("BROWSER_USE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)

        result = get_llm()

        assert result is None

    def test_get_llm_uses_openai_when_key_available(self, monkeypatch):
        """get_llm should use OpenAI when OPENAI_API_KEY is set."""
        from src.extractor.agent import get_llm

        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.delenv("BROWSER_USE_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)

        with patch("browser_use.ChatOpenAI") as mock_chat_openai:
            mock_llm = MagicMock()
            mock_chat_openai.return_value = mock_llm
            result = get_llm()

            assert result is mock_llm
            # Verify ChatOpenAI was called with correct model and api_key
            mock_chat_openai.assert_called_once()
            call_kwargs = mock_chat_openai.call_args[1]
            assert call_kwargs["model"] == "gpt-4o"
            assert call_kwargs["api_key"] == "test-key"
            assert call_kwargs["base_url"] is None

    def test_get_llm_uses_config_settings(self, monkeypatch):
        """get_llm should use settings from config when provided."""
        from src.extractor.agent import get_llm
        from src.extractor.config import ExtractorConfig

        # Clear environment variables
        monkeypatch.delenv("BROWSER_USE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)

        # Create config with explicit settings
        config = ExtractorConfig(
            _env_file=None,
            llm_provider="openai",
            llm_api_key="config-api-key",
            llm_base_url="https://custom.endpoint.com/v1",
            llm_model="gpt-4o-mini",
            llm_reasoning_effort="high",
        )

        with patch("browser_use.ChatOpenAI") as mock_chat_openai:
            mock_llm = MagicMock()
            mock_chat_openai.return_value = mock_llm
            result = get_llm(config)

            assert result is mock_llm
            mock_chat_openai.assert_called_once()
            call_kwargs = mock_chat_openai.call_args[1]
            assert call_kwargs["model"] == "gpt-4o-mini"
            assert call_kwargs["api_key"] == "config-api-key"
            assert call_kwargs["base_url"] == "https://custom.endpoint.com/v1"
            assert call_kwargs["reasoning_effort"] == "high"

    def test_get_llm_normalizes_disable_reasoning_effort(self, monkeypatch):
        """get_llm should normalize disable -> none for Browser Use ChatOpenAI."""
        from src.extractor.agent import get_llm
        from src.extractor.config import ExtractorConfig

        monkeypatch.delenv("BROWSER_USE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)

        config = ExtractorConfig(
            _env_file=None,
            llm_provider="openai",
            llm_api_key="config-api-key",
            llm_model="gpt-5-mini",
            llm_reasoning_effort="disable",
        )

        with patch("browser_use.ChatOpenAI") as mock_chat_openai:
            mock_chat_openai.return_value = MagicMock()
            get_llm(config)
            call_kwargs = mock_chat_openai.call_args[1]
            assert call_kwargs["reasoning_effort"] == "none"
