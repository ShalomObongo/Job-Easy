# Research — Browser Use Docs (References for Our Job Application System)

> Date: 2026-01-15  
> This document compiles **relevant Browser Use documentation** for the system we’re building.  
> Every section includes **citations/references** to the Browser Use docs pages used.

---

## 0) Scope: what we’re building (mapped to Browser Use)
Our system needs Browser Use support for:
- Browser automation primitives (navigate/click/input/upload/evaluate/done)
- LLM-assisted page extraction (`extract`)
- Agent configuration for reliability (retries, action batching, initial actions)
- Safe file handling (allowed upload paths) and sensitive data handling
- Optional vision/screenshot behavior for robustness
- Using an existing Chrome profile (user data dir + profile directory)
- Domain allowlisting / blocklisting
- Logging/audit (saving conversations, proof artifacts)
- Human-in-the-loop prompts for duplicates + submit confirmation + 2FA

References:
- Code agent / browser tools: https://docs.browser-use.com/customize/code-agent/basics
- Default tool list (including `extract`): https://docs.browser-use.com/customize/tools/available
- Add custom tools (`@tools.action`, human-in-loop): https://docs.browser-use.com/customize/tools/add
- Agent parameters: https://docs.browser-use.com/customize/agent/all-parameters
- Browser parameters (profiles/domains/downloads/etc.): https://docs.browser-use.com/customize/browser/all-parameters

---

## 1) Browser automation primitives (what the agent can do)

Browser Use exposes browser control functions usable by agents, including:
- `navigate(url)` — go to a URL
- `click(index)` — click an element by index
- `input(index, text)` — type into a field
- `scroll(down, pages)` — scroll the page
- `upload_file(path)` — upload a local file to a file input
- `evaluate(code, variables={})` — run custom JavaScript in the page (useful for advanced interactions, shadow DOM, custom selectors, and extraction)
- `done(text, success, files_to_display=[])` — mark a run complete

Why this matters for our system:
- The application runner relies on `navigate/click/input/upload_file` for typical job-board flows.
- `evaluate` is the “escape hatch” when DOM is complex or elements are in shadow DOM.
- `done` is used to finalize a run with a structured summary.

References:
- Browser control functions: https://docs.browser-use.com/customize/code-agent/basics

---

## 2) Built-in extraction tool (`extract`) and default tool set

Browser Use includes a default tool `extract` described as:
- **`extract` — Extract data from webpages using an LLM**

The docs also list common page interaction tools:
- click, input, upload_file, scroll, find_text (scroll to specific text), send_keys (Enter/Escape/etc.)
- `evaluate` is listed for JavaScript execution for advanced interactions

Why this matters for our system:
- We can use `extract` to turn the job posting page into structured JD JSON.
- `find_text` is helpful for “scroll until section header appears” patterns on job pages.
- `send_keys` is useful when forms require Enter/Escape or special key handling.

References:
- Tool list and `extract`: https://docs.browser-use.com/customize/tools/available

---

## 3) Custom tools & human-in-the-loop (prompting the user)

Browser Use supports adding custom tools via `@tools.action(...)` with:
- a required `description` (so the LLM knows when to call it)
- optional `allowed_domains` restrictions for where the tool can run
- function parameters are filled by the agent based on names/type hints/defaults

The docs include a “Ask human for help” tool pattern:
- a tool function uses `input()` to ask the user a question and returns the response

The docs also list “available objects” accessible inside tool functions, including:
- `file_system` (file system access)
- `available_file_paths` (list of allowed files for upload/processing)
- `browser_session` and a direct CDP client for deeper control
- `page_extraction_llm` for custom LLM calls

Why this matters for our system:
- Duplicate detection prompt: “Already applied — proceed anyway?”
- Pre-submit confirmation prompt: “Type YES to submit”
- 2FA/CAPTCHA prompt: request user input or manual takeover
- The `available_file_paths` mechanism supports safe “only upload these documents” constraints.

References:
- Adding tools + ask-human example: https://docs.browser-use.com/customize/tools/add

---

## 4) Agent configuration: reliability, batching, retries, and behavior

### 4.1 Action batching for form filling
Key parameter:
- `max_actions_per_step` (default 4): allows the agent to output multiple actions in a single step (e.g., fill multiple fields at once), executed until the page changes.

Why it matters:
- Job application forms often have many fields; batching helps speed and reduces overhead.

### 4.2 Reliability controls
Key parameter:
- `max_failures` (default 3): retry failed steps up to N times.
- `final_response_after_failure` (default True): attempt one final model call with intermediate output after hitting failure limit.

Why it matters:
- Job portals are flaky; retries + a final response improves recoverability and debugging.

### 4.3 Deterministic pre-actions
Key parameter:
- `initial_actions`: run actions before the main task **without the LLM**.

Why it matters:
- Accept cookie banner, open the apply section, or set language preferences reliably before “reasoning” begins.

### 4.4 Model reasoning / speed mode
Parameters:
- `use_thinking` (default True): whether the agent uses an internal “thinking” field for explicit reasoning.
- `flash_mode` (default False): fast mode that skips evaluation/next-goal/thinking and only uses memory; overrides `use_thinking`.

Why it matters:
- During debugging, keep `use_thinking=True`.
- For production speed once stable, `flash_mode` may be considered (but can reduce introspection).

References:
- Agent behavior parameters: https://docs.browser-use.com/customize/agent/all-parameters

---

## 5) Vision & page processing options (screenshots, extraction LLM)

Parameters:
- `use_vision` (default "auto"):
  - "auto" includes screenshot tooling but only uses vision when requested
  - True always includes screenshots
  - False never includes screenshots and excludes screenshot tool
- `vision_detail_level` (default "auto"): low/high/auto
- `page_extraction_llm`: separate LLM model used for page content extraction (can be smaller/faster; default is the same as main LLM)

Why this matters for our system:
- Some job sites are heavily dynamic; screenshots can improve robustness.
- Splitting `page_extraction_llm` from the main LLM can reduce cost/latency for extraction-heavy pipelines.
- In autonomous mode, "auto" is a good default; enable higher detail only when needed.

References:
- Vision & processing parameters: https://docs.browser-use.com/customize/agent/all-parameters

---

## 6) Agent “core settings” for extensibility and structured outputs

The docs mention:
- `tools`: registry of tools the agent can call
- `skills` / `skill_ids`: list of skill IDs to load (supports `'*'` for all), requires `BROWSER_USE_API_KEY`
- `browser`: Browser object configuration
- `output_model_schema`: a Pydantic model for structured output validation
- System prompt controls:
  - `override_system_message` — replace default system prompt
  - `extend_system_message` — append to default system prompt

Why this matters for our system:
- We can enforce structured outputs (e.g., a “Pre-submit review packet” schema) with `output_model_schema`.
- `extend_system_message` is useful to enforce “NEVER submit without confirmation” and “do not fabricate experience”.
- Skills can package reusable behaviors (e.g., common job-board patterns) if we decide to use Browser Use Cloud skills.

References:
- Core settings + system messages: https://docs.browser-use.com/customize/agent/all-parameters

---

## 7) File handling, sensitive data, and audit logs

Agent parameters include:
- `available_file_paths`: list of file paths the agent can access (useful to constrain uploads)
- `sensitive_data`: dictionary for sensitive data to handle carefully
- `save_conversation_path`: path to save complete conversation history
- `save_conversation_path_encoding` (default 'utf-8')

Why this matters for our system:
- **Security:** limit uploads to only the tailored resume and cover letter paths.
- **Privacy:** keep applicant PII in `sensitive_data` rather than scattering in prompts.
- **Audit:** keep a conversation log per application for troubleshooting and compliance.

References:
- File & data management parameters: https://docs.browser-use.com/customize/agent/all-parameters
- Tool function accessible objects (incl. `file_system`, `available_file_paths`): https://docs.browser-use.com/customize/tools/add

---

## 8) Browser configuration: profiles, sessions, and login reuse

Browser parameters include:
- `user_data_dir`: directory for browser profile data (default is auto-generated temp). Use `None` for incognito mode.
- `profile_directory`: Chrome profile subdirectory name (e.g., 'Default', 'Profile 1', 'Work Profile')
- `storage_state`: cookies/localStorage state (file path or dict)

Why this matters for our system:
- Using `user_data_dir` + `profile_directory` allows reusing existing logins (LinkedIn, Workday, etc.).
- `storage_state` can be used as an alternative to full profile sharing.

References:
- User Data & Profiles: https://docs.browser-use.com/customize/browser/all-parameters

---

## 9) Browser navigation security: allowlist and blocklist domains

Browser Use supports:
- `allowed_domains`: restrict navigation to specific domains
  - accepted patterns include:
    - `example.com` (only that domain)
    - `*.example.com` (domain + subdomains)
    - `http*://example.com` (http and https)
    - `chrome-extension://*` (extension URLs)
  - security note: wildcards in TLD (e.g., `example.*`) are not allowed
  - performance note: lists with 100+ domains are optimized to sets for O(1) lookup (pattern matching disabled for optimized lists)
  - both `www.example.com` and `example.com` variants are checked automatically
- `prohibited_domains`: block navigation to domains using the same pattern formats
  - if both are set, `allowed_domains` takes precedence

Why this matters for our system:
- We can constrain the agent to job sites + known company domains only.
- This reduces risk of wandering, phishing pages, or accidental data leaks.

References:
- Browser behavior (allowed/prohibited domains details): https://docs.browser-use.com/customize/browser/all-parameters

---

## 10) Browser launch and runtime options (practical ops)

The docs list key launch/runtime parameters:
- `executable_path`: custom Chrome/Chromium path (platform examples included)
- `channel`: choose browser channel (chromium, chrome, chrome-beta, msedge, etc.)
- `args`: extra command-line flags
- `env`: environment variables for browser process
- `chromium_sandbox` (default True except in Docker): sandboxing
- `devtools` (default False): opens devtools when `headless=False`
- `ignore_default_args`: disable default args

Browser behavior options:
- `keep_alive`: keep browser running after agent completes
- `enable_default_extensions` (default True): loads automation extensions (e.g., uBlock Origin, cookie handlers, ClearURLs)
- `cross_origin_iframes` (default False): enables cross-origin iframe support (may add complexity)
- `is_local` (default True): whether browser is local; affects download behavior

Advanced options (warned as not recommended):
- `disable_security`
- `deterministic_rendering`

Why this matters for our system:
- Dev mode: set `headless=False` + `devtools=True` for debugging.
- Some job boards embed forms in iframes; `cross_origin_iframes=True` may help, but adds complexity.
- Extensions can reduce tracking/cookie popups (useful, but still keep allowlist on).

References:
- Browser launch/behavior/advanced options: https://docs.browser-use.com/customize/browser/all-parameters

---

## 11) Downloads and PDFs

Browser parameters include:
- `accept_downloads` (default True): automatically accept downloads
- `downloads_path`: where downloads are saved
- `auto_download_pdfs` (default True): automatically download PDFs instead of viewing in browser

Why this matters for our system:
- Some portals provide “application summary PDF” or “job description PDF”; these settings control handling.
- We can also route downloads to the per-job artifact folder.

References:
- Downloads & files parameters: https://docs.browser-use.com/customize/browser/all-parameters

---

## 12) CodeAgent: when to use it vs standard Agent

The docs describe **CodeAgent** as:
- It writes and executes Python code locally with browser automation capabilities.
- Designed for repetitive tasks where the agent can write reusable functions.
- Best for data extraction at scale (100s–1000s items), repetitive interactions, tasks requiring data processing + file operations.
- Outputs runnable Python code; supports exporting runs to:
  - a Jupyter notebook (`export_to_ipynb`)
  - a Python script (`session_to_python_script`)

The docs also mention common Python libraries are available (examples include pandas/numpy/requests/BeautifulSoup/csv/json/openpyxl/matplotlib and utilities).

Why this matters for our system:
- Autonomous mode can benefit from CodeAgent for large-scale job scraping, lead dedupe, and structured processing.
- Standard Agent can remain best for one-off, interactive applications with frequent user checkpoints.
- Exporting to scripts/notebooks helps debugging and repeatability.

References:
- CodeAgent overview and export helpers: https://docs.browser-use.com/customize/code-agent/basics

---

## 13) MCP integrations (optional: controlling Browser Use via MCP clients)

Browser Use provides:
- a hosted **MCP server** enabling assistants to control browser automation (HTTP-based)
  - MCP Server URL: `https://api.browser-use.com/mcp`
- a local stdio-based option for Claude Desktop:
  - run via `uvx browser-use --mcp` (free, open-source)
- programmatic usage examples that call tools like `browser_navigate` and `browser_get_state`

Browser Use also provides a documentation MCP:
- read-only access to Browser Use docs for MCP clients
- serves docs over HTTP
- no browser automation capability
- lightweight; no API keys required

Why this matters for our system:
- If you want to operate this system via Cursor/Claude Code integrations, MCP can be the control plane.
- Docs MCP can help an assistant reason about Browser Use usage while coding.

References:
- MCP server: https://docs.browser-use.com/customize/integrations/mcp-server
- Docs MCP: https://docs.browser-use.com/customize/integrations/docs-mcp

---

## 14) Practical mapping: our system requirements → Browser Use features

### 14.1 “Extract JD and metadata”
- Use `extract` tool for LLM-based extraction from the job posting page.  
  Reference: https://docs.browser-use.com/customize/tools/available

### 14.2 “Tailor resume + generate cover letter”
- Run custom LLM calls via:
  - the main agent LLM, or
  - `page_extraction_llm` for extraction tasks
- Use `available_file_paths` to allow only generated resume/cover letter for uploads.  
  References: https://docs.browser-use.com/customize/agent/all-parameters

### 14.3 “Use existing Chrome profile”
- Configure `user_data_dir` + `profile_directory` or use `storage_state`.  
  Reference: https://docs.browser-use.com/customize/browser/all-parameters

### 14.4 “Prevent reapplying”
- Implement tracker in app code; use a custom tool (ask-human) to confirm overrides.  
  References: https://docs.browser-use.com/customize/tools/add

### 14.5 “Safety rails”
- Domain allowlist (`allowed_domains`) + optional blocklist (`prohibited_domains`).  
  Reference: https://docs.browser-use.com/customize/browser/all-parameters
- Human-in-loop gates via custom tools.  
  Reference: https://docs.browser-use.com/customize/tools/add

### 14.6 “Audit + proof”
- `save_conversation_path` for saved run logs; plus optional screenshots via `use_vision`.  
  References: https://docs.browser-use.com/customize/agent/all-parameters

---

## 15) Reference index (docs)
- Browser parameters (profiles, domains, downloads, launch options):  
  https://docs.browser-use.com/customize/browser/all-parameters
- Agent parameters (behavior, retries, logs, sensitive data, vision):  
  https://docs.browser-use.com/customize/agent/all-parameters
- Default tool list (incl. `extract`):  
  https://docs.browser-use.com/customize/tools/available
- Add custom tools (`@tools.action`, ask-human, available objects):  
  https://docs.browser-use.com/customize/tools/add
- CodeAgent basics + export helpers:  
  https://docs.browser-use.com/customize/code-agent/basics
- MCP server (browser automation via MCP):  
  https://docs.browser-use.com/customize/integrations/mcp-server
- Docs MCP (read-only docs context via MCP):  
  https://docs.browser-use.com/customize/integrations/docs-mcp
