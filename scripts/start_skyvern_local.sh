#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

read_dotenv_value() {
  local key="$1"
  local line
  if [[ ! -f ".env" ]]; then
    return 0
  fi
  line="$(grep -E "^${key}=" ".env" | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    return 0
  fi

  local value="${line#*=}"
  if [[ "$value" == \"*\" && "$value" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "$value"
}

screen_width="${SCREEN_WIDTH:-}"
screen_height="${SCREEN_HEIGHT:-}"
if [[ -z "$screen_width" || -z "$screen_height" ]] && command -v osascript >/dev/null 2>&1; then
  bounds="$(osascript -e 'tell application "Finder" to get bounds of window of desktop' 2>/dev/null || true)"
  if [[ "$bounds" =~ ^[[:space:]]*([0-9]+),[[:space:]]*([0-9]+),[[:space:]]*([0-9]+),[[:space:]]*([0-9]+)[[:space:]]*$ ]]; then
    left="${BASH_REMATCH[1]}"
    top="${BASH_REMATCH[2]}"
    right="${BASH_REMATCH[3]}"
    bottom="${BASH_REMATCH[4]}"
    screen_width="$((right - left))"
    screen_height="$((bottom - top))"
  fi
fi

screen_width="${screen_width:-1440}"
screen_height="${screen_height:-900}"

export BROWSER_WIDTH="${BROWSER_WIDTH:-$screen_width}"
export BROWSER_HEIGHT="${BROWSER_HEIGHT:-$screen_height}"

default_args="$(printf '[\"--window-position=0,0\",\"--window-size=%s,%s\",\"--force-device-scale-factor=1\"]' "$BROWSER_WIDTH" "$BROWSER_HEIGHT")"
export BROWSER_ADDITIONAL_ARGS="${BROWSER_ADDITIONAL_ARGS:-$default_args}"

export DATABASE_STRING="${DATABASE_STRING:-postgresql+psycopg://localhost/skyvern}"

runner_llm_base_url="${RUNNER_LLM_BASE_URL:-$(read_dotenv_value RUNNER_LLM_BASE_URL)}"
runner_llm_model="${RUNNER_LLM_MODEL:-$(read_dotenv_value RUNNER_LLM_MODEL)}"
runner_llm_api_key="${RUNNER_LLM_API_KEY:-$(read_dotenv_value RUNNER_LLM_API_KEY)}"
runner_llm_reasoning="${RUNNER_LLM_REASONING_EFFORT:-$(read_dotenv_value RUNNER_LLM_REASONING_EFFORT)}"

if [[ -n "$runner_llm_base_url" ]] && [[ -z "${OPENAI_COMPATIBLE_API_BASE:-}" ]]; then
  export ENABLE_OPENAI_COMPATIBLE="${ENABLE_OPENAI_COMPATIBLE:-true}"
  export OPENAI_COMPATIBLE_API_BASE="$runner_llm_base_url"
  export OPENAI_COMPATIBLE_MODEL_NAME="${runner_llm_model:-gpt-4o}"
  export LLM_KEY="${LLM_KEY:-OPENAI_COMPATIBLE}"
fi

if [[ -n "$runner_llm_api_key" ]] && [[ -z "${OPENAI_COMPATIBLE_API_KEY:-}" ]]; then
  export OPENAI_COMPATIBLE_API_KEY="$runner_llm_api_key"
fi

if [[ -n "$runner_llm_reasoning" ]] && [[ -z "${OPENAI_COMPATIBLE_REASONING_EFFORT:-}" ]]; then
  export OPENAI_COMPATIBLE_REASONING_EFFORT="$runner_llm_reasoning"
fi

exec ".venv/bin/python" -m skyvern run server
