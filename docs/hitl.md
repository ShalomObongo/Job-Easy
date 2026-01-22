# Human-in-the-Loop (HITL) Module Documentation

## Overview

The **hitl** (Human-in-the-Loop) module provides interactive prompts, user input validation, and Browser Use custom tools that enable human oversight and control throughout the job application process. This module serves as the critical safety layer that prevents unintended actions by requiring explicit user confirmation at key decision points.

### Purpose

- **User Confirmation Gates**: Require explicit approval before critical actions (document upload, final submission)
- **Interactive Prompts**: Collect user input for decisions, questions, and OTP/2FA codes
- **Browser Tool Integration**: Provide custom Browser Use tools that agents can invoke for human interaction
- **Submit Verification**: Intelligently verify submission success and detect blocking errors
- **Input Validation**: Parse and normalize user responses with clear error handling

The HITL module is fundamental to maintaining human control while benefiting from automation, ensuring the system operates as a "human-augmentation tool" rather than a fully autonomous agent.

## Architecture

### Module Structure

```
src/hitl/
├── __init__.py          # Module docstring
└── tools.py             # HITL tools, prompts, and browser automation helpers
```

### Key Design Principles

1. **Explicit Over Implicit**: All critical actions require clear user confirmation
2. **Safety First**: Default to blocking dangerous operations (e.g., submission requires exact "yes" string)
3. **Testable Components**: Small, pure parsing functions separate from I/O operations
4. **Browser Use Integration**: Tools registry pattern for agent-invocable actions
5. **Best-Effort Automation**: Fallback strategies for submit button detection and verification

## Core Components

### 1. Input Parsing Functions

#### `parse_yes_no(answer: str) -> bool`

Parses yes/no responses with tolerance for common variants.

**Parameters:**
- `answer` (str): User input string

**Returns:**
- `bool`: True for yes, False for no

**Raises:**
- `ValueError`: If answer is not a recognized yes/no variant

**Accepted Values:**
- Yes: `"y"`, `"yes"` (case-insensitive, whitespace-tolerant)
- No: `"n"`, `"no"` (case-insensitive, whitespace-tolerant)

**Example:**
```python
from src.hitl.tools import parse_yes_no

parse_yes_no("  YES  ")  # True
parse_yes_no("n")        # False
parse_yes_no("maybe")    # raises ValueError
```

#### `is_submit_confirmed(answer: str) -> bool`

Validates explicit submission confirmation (requires exact "yes" or "YES").

**Parameters:**
- `answer` (str): User input string

**Returns:**
- `bool`: True only if answer is exactly "yes" or "YES" (after stripping whitespace)

**Rationale:**
More restrictive than `parse_yes_no` to prevent accidental submissions. Single-character answers like "y" are intentionally rejected.

**Example:**
```python
from src.hitl.tools import is_submit_confirmed

is_submit_confirmed("yes")     # True
is_submit_confirmed("YES")     # True
is_submit_confirmed("y")       # False (too casual for submission)
is_submit_confirmed("no")      # False
```

#### `normalize_otp_code(answer: str) -> str`

Normalizes OTP/2FA codes by stripping whitespace.

**Parameters:**
- `answer` (str): Raw user input

**Returns:**
- `str`: Normalized code

**Example:**
```python
from src.hitl.tools import normalize_otp_code

normalize_otp_code("  123456  ")  # "123456"
```

### 2. Interactive Prompt Functions

These functions handle direct user interaction via `input()` and implement retry logic for invalid responses.

#### `prompt_yes_no(question: str) -> bool`

Prompts the user for a yes/no response with validation and retry.

**Parameters:**
- `question` (str): Question to display to the user

**Returns:**
- `bool`: User's response (True for yes, False for no)

**Behavior:**
- Displays: `{question} (y/n) > `
- Retries on invalid input with helpful error message
- Only returns when valid response received

**Example:**
```python
from src.hitl.tools import prompt_yes_no

proceed = prompt_yes_no("Continue with this application?")
if proceed:
    # User confirmed
    ...
```

#### `prompt_free_text(question: str) -> str`

Prompts the user for free-form text input.

**Parameters:**
- `question` (str): Question to display

**Returns:**
- `str`: User's response (stripped of leading/trailing whitespace)

**Example:**
```python
from src.hitl.tools import prompt_free_text

reason = prompt_free_text("Why are you overriding this decision?")
```

#### `prompt_confirm_submit(prompt: str) -> bool`

Prompts for explicit submission confirmation (requires exact "yes"/"YES").

**Parameters:**
- `prompt` (str): Confirmation message to display

**Returns:**
- `bool`: True if user typed exactly "yes" or "YES", False otherwise

**Example:**
```python
from src.hitl.tools import prompt_confirm_submit

confirmed = prompt_confirm_submit("Type YES to submit this application")
if confirmed:
    # User explicitly confirmed with "yes" or "YES"
    ...
```

#### `prompt_otp_code(prompt: str) -> str`

Prompts the user for an OTP/2FA code.

**Parameters:**
- `prompt` (str): Prompt message

**Returns:**
- `str`: Normalized OTP code

**Example:**
```python
from src.hitl.tools import prompt_otp_code

code = prompt_otp_code("Enter your 2FA code")
```

### 3. Browser Use Tools Registry

#### `create_hitl_tools() -> Tools`

Creates a Browser Use `Tools` registry with human-in-the-loop actions that agents can invoke.

**Returns:**
- `Tools`: Configured tools registry with HITL actions

**Registered Tools:**

##### `ask_yes_no(question: str) -> str`
- **Description**: "Ask the human a yes/no question. Returns 'yes' or 'no'."
- **Parameters**:
  - `question` (str): Question to ask
- **Returns**: `"yes"` or `"no"` (string, not boolean)
- **Use Case**: Agent needs a binary decision from the user

##### `ask_free_text(question: str) -> str`
- **Description**: "Ask the human for free text input."
- **Parameters**:
  - `question` (str): Question to ask
- **Returns**: User's text response
- **Use Case**: Agent needs custom information (e.g., answer to application question)

##### `confirm_submit(prompt: str, browser_session: BrowserSession, submit_button_index: int | None = None) -> str`
- **Description**: "Before final submit, require the human to type YES/yes to confirm; when confirmed, click the final submit button."
- **Parameters**:
  - `prompt` (str): Confirmation message
  - `browser_session` (BrowserSession): Current browser session
  - `submit_button_index` (int | None): DOM index of submit button (optional)
- **Returns**: One of:
  - `"submitted"`: User confirmed and submit button was clicked successfully
  - `"confirmed"`: User confirmed but automatic button click failed (agent must click manually)
  - `"cancelled"`: User did not confirm
  - `"blocked_missing_fields"`: Form has required field errors, cannot submit yet
- **Use Case**: Gate final submission behind human approval
- **Special Behavior**:
  - Pre-checks for required field errors before prompting
  - Automatically clicks submit button if user confirms
  - Post-submission verification for success/error messages

##### `ask_otp_code(prompt: str) -> str`
- **Description**: "Ask the human for an OTP/2FA code."
- **Parameters**:
  - `prompt` (str): Prompt message
- **Returns**: OTP code
- **Use Case**: Handle two-factor authentication

**Example:**
```python
from src.hitl.tools import create_hitl_tools
from browser_use import Agent, Browser

browser = Browser(headless=False)
tools = create_hitl_tools()

agent = Agent(
    task="Apply to this job",
    browser=browser,
    llm=my_llm,
    tools=tools,  # Agent can now invoke HITL actions
)

# Agent can call:
# - ask_yes_no("Should I upload the cover letter?")
# - ask_free_text("What is your current salary expectation?")
# - confirm_submit("Type YES to submit", browser_session, submit_button_index=42)
# - ask_otp_code("Enter your 2FA code")
```

### 4. Browser Automation Helpers

These internal helpers support the `confirm_submit` tool with intelligent button detection and verification.

#### `_click_submit_button(browser_session: BrowserSession, submit_button_index: int | None) -> bool`

Best-effort click of a submit/apply button on the current page.

**Strategy:**
1. **Prefer explicit DOM index** (if provided by agent)
2. **Fallback to CSS selector search**: `button[type="submit"], input[type="submit"]`
3. **Heuristic scoring** to find the best candidate button

**Parameters:**
- `browser_session` (BrowserSession): Current browser session
- `submit_button_index` (int | None): Explicit DOM index of submit button

**Returns:**
- `bool`: True if button was clicked successfully, False otherwise

**Error Handling:**
- Returns False on any exception (graceful degradation)
- Falls back from index-based to CSS-based search if index lookup fails

#### `_score_submit_candidate(element) -> int`

Heuristic scoring for submit/apply button candidates.

**Scoring Logic:**
- **Positive keywords** (+10 each): "submit", "apply", "send", "finish", "complete", "sign up"
- **Negative keywords** (-10 each): "next", "continue", "back", "cancel", "save", "later"
- **No label text** (-5): Deprioritize unlabeled buttons
- **Invisible elements** (-1000): Skip zero-size or hidden elements

**Returns:**
- `int`: Score for this button candidate (higher = more likely to be final submit)

**Example:**
- Button with text "Submit Application" → Score: +20 (submit, apply)
- Button with text "Next" → Score: -10 (next)
- Button with text "Submit and Continue" → Score: 0 (submit +10, continue -10)

#### `_get_page_text(browser_session: BrowserSession) -> str`

Extracts all visible text from the current page's body.

**Returns:**
- `str`: Page text content (empty string on error)

**Use Case:**
- Verify submission success messages
- Detect required field errors

#### `_has_required_field_errors(browser_session: BrowserSession) -> bool`

Detects if the page contains required field error messages.

**Error Phrases Detected:**
- "this field is required."
- "resume/cv is required."
- "cover letter is required."

**Returns:**
- `bool`: True if any error phrase is found (case-insensitive)

**Use Case:**
- Prevent submit confirmation prompt when form is incomplete
- Return `"blocked_missing_fields"` from `confirm_submit`

#### `_has_submit_success_text(browser_session: BrowserSession) -> bool`

Detects if the page contains submission success messages.

**Success Phrases Detected:**
- "thank you for applying"
- "your application has been submitted"
- "application submitted"
- "application received"

**Behavior:**
- Waits 0.75 seconds for page transition
- Searches page text case-insensitively

**Returns:**
- `bool`: True if success message is found

**Use Case:**
- Verify submission after clicking submit button
- Distinguish successful submission from error state

## Integration with Other Modules

### Dependencies

**Internal Modules:**
- None (hitl is a leaf module with no internal dependencies)

**External Dependencies:**
- `browser_use`: For `BrowserSession` and `Tools` registry
- Standard library: `asyncio`, `input()`

### Used By

#### 1. Runner Module (`src/runner/`)

**Files:**
- `/Users/shalom/Developer/Job-Easy/src/runner/agent.py`
- `/Users/shalom/Developer/Job-Easy/src/runner/service.py`

**Integration Points:**

##### Agent Creation (`runner/agent.py`)
```python
from src.hitl.tools import create_hitl_tools

def create_application_agent(...) -> Agent:
    tools = create_hitl_tools()  # Default HITL tools

    # Optional: Add QA Bank tool for reusable answers
    if qa_bank_path:
        @tools.action(description="Resolve answer from Q&A bank...")
        def resolve_answer(question: str, context: str | None) -> str:
            # Prompt user if answer not in bank
            ...

    return Agent(
        task=task,
        browser=browser,
        llm=llm,
        tools=tools,  # Pass HITL tools to agent
        ...
    )
```

**Agent Prompt Guidance** (`get_application_prompt`):
The agent receives instructions to use HITL tools:
- Use `resolve_answer()` for unknown application questions
- Call `confirm_submit()` when ready to submit
- Stop and ask for help with CAPTCHA/2FA (via `ask_otp_code`)

##### Service Orchestration (`runner/service.py`)
```python
from src.hitl import tools as hitl

class SingleJobApplicationService:
    async def run(self, url: str) -> ApplicationRunResult:
        # 1. Duplicate detection gate
        if duplicate.status == ApplicationStatus.SUBMITTED:
            proceed = hitl.prompt_yes_no(
                "Tracker indicates this job was already submitted. Proceed anyway?"
            )
            if not proceed:
                return ApplicationRunResult(status=RunStatus.DUPLICATE_SKIPPED)

            reason = hitl.prompt_free_text("Optional override reason")
            await self.tracker_service.record_override(...)

        # 2. Fit scoring review gate
        if fit.recommendation == "skip":
            proceed = hitl.prompt_yes_no(
                "Fit scoring recommends SKIP. Proceed anyway?"
            )
            if not proceed:
                return ApplicationRunResult(status=RunStatus.SKIPPED)

        # 3. Document approval gate
        approved = hitl.prompt_yes_no(
            "Documents are ready. Approve resume/cover letter for upload?"
        )
        if not approved:
            return ApplicationRunResult(status=RunStatus.STOPPED_BEFORE_SUBMIT)

        # 4. Run browser agent (which has confirm_submit tool)
        result = await self._run_application_flow(...)
        return result
```

#### 2. Autonomous Module (`src/autonomous/`)

**File:** `/Users/shalom/Developer/Job-Easy/src/autonomous/service.py`

**Integration Point:**

```python
from src.hitl import tools as hitl

class AutonomousService:
    async def run(self, *, leads_file: Path, ...) -> BatchResult:
        # Build queue of jobs to process
        queue = await self.queue_manager.build_queue(...)

        # Batch confirmation gate
        if not assume_yes:
            summary = self._format_queue_summary(leads_file, queue)

            if self.confirm_callback:
                confirmed = await self.confirm_callback(summary)
            else:
                confirmed = hitl.prompt_yes_no(summary)

            if not confirmed:
                return BatchResult(processed=0, ...)

        # Execute batch (each job still has individual HITL gates)
        return await runner.run(queue, dry_run=dry_run)
```

**Note:** Autonomous mode prompts once for batch approval, but each individual application still goes through per-job HITL gates (duplicate check, fit review, document approval, submit confirmation).

#### 3. CLI Entry Point (`src/__main__.py`)

**File:** `/Users/shalom/Developer/Job-Easy/src/__main__.py`

**Integration Point:**

```python
from src.hitl.tools import create_hitl_tools
from src.runner.agent import create_application_agent, create_browser

if parsed.mode == "apply":
    # Direct apply mode (no orchestration service)
    browser = create_browser(settings, prohibited_domains=prohibited)
    agent = create_application_agent(
        job_url=parsed.url,
        browser=browser,
        llm=llm,
        tools=create_hitl_tools(),  # Provide HITL tools
        available_file_paths=[resume, cover_letter],
        ...
    )

    history = asyncio.run(agent.run())
    # Agent uses HITL tools during execution
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Journey                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Job URL Submitted (via CLI or autonomous queue)             │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Tracker Check (runner/service.py)                           │
│     ┌────────────────────────────────────────────┐              │
│     │ hitl.prompt_yes_no():                      │              │
│     │ "Already submitted. Proceed anyway?"       │              │
│     │                                            │              │
│     │ ┌─────────────┐    ┌──────────────────┐   │              │
│     │ │ User: "no"  │───▶│ SKIP (early exit)│   │              │
│     │ └─────────────┘    └──────────────────┘   │              │
│     │                                            │              │
│     │ ┌─────────────┐    ┌──────────────────┐   │              │
│     │ │ User: "yes" │───▶│ Continue + log   │   │              │
│     │ └─────────────┘    │ override reason  │   │              │
│     │                    └──────────────────┘   │              │
│     └────────────────────────────────────────────┘              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Job Extraction → Fit Scoring (extractor + scoring modules)  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Fit Review Gate (runner/service.py)                         │
│     ┌────────────────────────────────────────────┐              │
│     │ hitl.prompt_yes_no():                      │              │
│     │ "Fit scoring recommends SKIP. Proceed?"    │              │
│     │                                            │              │
│     │ User: "no" ───▶ SKIP (mark as skipped)    │              │
│     │ User: "yes" ──▶ Continue to tailoring     │              │
│     └────────────────────────────────────────────┘              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. Tailoring (tailoring module)                                │
│     - Generate resume + cover letter                            │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. Document Approval Gate (runner/service.py)                  │
│     ┌────────────────────────────────────────────┐              │
│     │ hitl.prompt_yes_no():                      │              │
│     │ "Approve resume/cover letter for upload?"  │              │
│     │                                            │              │
│     │ User: "no" ───▶ STOP (no submission)      │              │
│     │ User: "yes" ──▶ Continue to browser agent │              │
│     └────────────────────────────────────────────┘              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  7. Browser Agent Execution (runner/agent.py)                   │
│                                                                 │
│     Agent uses HITL tools:                                      │
│                                                                 │
│     ┌────────────────────────────────────────────┐              │
│     │ ask_yes_no("Upload cover letter?")         │              │
│     │ ───▶ User responds: "yes" or "no"          │              │
│     └────────────────────────────────────────────┘              │
│                                                                 │
│     ┌────────────────────────────────────────────┐              │
│     │ resolve_answer(question, context)          │              │
│     │ ───▶ Check Q&A bank                        │              │
│     │ ───▶ If missing: prompt user + save answer │              │
│     └────────────────────────────────────────────┘              │
│                                                                 │
│     ┌────────────────────────────────────────────┐              │
│     │ ask_otp_code("Enter 2FA code")             │              │
│     │ ───▶ User enters code: "123456"            │              │
│     └────────────────────────────────────────────┘              │
│                                                                 │
│     ┌────────────────────────────────────────────┐              │
│     │ confirm_submit(                            │              │
│     │   "Type YES to submit",                    │              │
│     │   browser_session,                         │              │
│     │   submit_button_index=42                   │              │
│     │ )                                          │              │
│     │                                            │              │
│     │ ┌──────────────────────────────────────┐   │              │
│     │ │ 1. Pre-check: required field errors? │   │              │
│     │ │    ───▶ YES: return "blocked"        │   │              │
│     │ │    ───▶ NO: proceed to prompt        │   │              │
│     │ └──────────────────────────────────────┘   │              │
│     │                                            │              │
│     │ ┌──────────────────────────────────────┐   │              │
│     │ │ 2. Prompt: "Type YES to submit > "   │   │              │
│     │ │    User: "yes" ───▶ Confirmed        │   │              │
│     │ │    User: "no" ────▶ Cancelled        │   │              │
│     │ └──────────────────────────────────────┘   │              │
│     │                                            │              │
│     │ ┌──────────────────────────────────────┐   │              │
│     │ │ 3. If confirmed: click submit button │   │              │
│     │ │    - Try DOM index first             │   │              │
│     │ │    - Fallback to CSS selector        │   │              │
│     │ │    - Heuristic scoring for best btn  │   │              │
│     │ └──────────────────────────────────────┘   │              │
│     │                                            │              │
│     │ ┌──────────────────────────────────────┐   │              │
│     │ │ 4. Post-submit verification:         │   │              │
│     │ │    - Success message? ──▶ "submitted"│   │              │
│     │ │    - Error message? ───▶ "blocked"   │   │              │
│     │ │    - Click failed? ────▶ "confirmed" │   │              │
│     │ └──────────────────────────────────────┘   │              │
│     │                                            │              │
│     │ Return: "submitted" | "confirmed" |        │              │
│     │         "cancelled" | "blocked"            │              │
│     └────────────────────────────────────────────┘              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  8. Result Handling (runner/service.py)                         │
│     - Update tracker status                                     │
│     - Save proof artifacts                                      │
│     - Return ApplicationRunResult                               │
└─────────────────────────────────────────────────────────────────┘
```

## User Interaction Patterns

### 1. Duplicate Detection Flow

**Trigger:** Tracker finds existing record with SUBMITTED status

**Prompt:**
```
Tracker indicates this job was already submitted. Proceed anyway?
https://jobs.example.com/apply/12345
(y/n) >
```

**Outcomes:**
- User types `y`/`yes`: Continue with override
  - Follow-up prompt: `Optional override reason (press Enter to skip) > `
  - Record override in tracker with reason
- User types `n`/`no`: Skip application
  - Return `RunStatus.DUPLICATE_SKIPPED`

### 2. Fit Scoring Review Flow

**Trigger:** Fit scorer recommends "skip" or "review"

**Prompt (skip):**
```
Fit scoring recommends SKIP. Proceed with application anyway?

[Detailed scoring reasoning...]

(y/n) >
```

**Prompt (review):**
```
Fit score recommends REVIEW. Proceed with application?
[Reasoning...]
(y/n) >
```

**Outcomes:**
- User types `y`/`yes`: Continue despite low score
  - Log override in notes
- User types `n`/`no`: Skip application
  - Mark as SKIPPED in tracker

### 3. Document Approval Flow

**Trigger:** Tailoring completes successfully

**Prompt:**
```
Documents are ready. Approve resume/cover letter for upload?
(y/n) >
```

**Outcomes:**
- User types `y`/`yes`: Proceed to browser automation
- User types `n`/`no`: Stop before submission
  - Return `RunStatus.STOPPED_BEFORE_SUBMIT`
  - Documents are generated but not uploaded

**Note:** This gate allows users to review tailored documents externally before approving.

### 4. Browser Agent Interactions

#### Ask Yes/No (Agent-Driven)

**Example Scenario:** Agent encounters optional cover letter field

**Agent Action:**
```python
response = ask_yes_no("Should I upload the cover letter to this optional field?")
```

**User Sees:**
```
Should I upload the cover letter to this optional field?
(y/n) >
```

**Agent Receives:** `"yes"` or `"no"` (string)

#### Ask Free Text (Agent-Driven)

**Example Scenario:** Agent encounters unknown application question

**Agent Action:**
```python
answer = ask_free_text("What is your desired start date?")
```

**User Sees:**
```
What is your desired start date? >
```

**User Types:** `April 1, 2026`

**Agent Receives:** `"April 1, 2026"`

#### OTP/2FA Flow

**Example Scenario:** Application site requires two-factor authentication

**Agent Action:**
```python
code = ask_otp_code("Enter the 6-digit code sent to your phone")
```

**User Sees:**
```
Enter the 6-digit code sent to your phone >
```

**User Types:** `  123456  `

**Agent Receives:** `"123456"` (normalized)

### 5. Submit Confirmation Flow

**Trigger:** Agent reaches final submit step (all required fields filled)

**Agent Action:**
```python
result = confirm_submit(
    prompt="Type YES to submit this application",
    browser_session=session,
    submit_button_index=42  # DOM element index
)
```

**Flow Diagram:**

```
┌────────────────────────────────────────┐
│ Pre-check: Required field errors?      │
└────────┬───────────────────────────────┘
         │
    ┌────▼────┐
    │  Found? │
    └────┬────┘
         │
    YES  │  NO
    ─────┼─────
         │
    ┌────▼────────────────────────────────┐
    │ Return "blocked_missing_fields"      │
    │ (Don't prompt user yet)              │
    └──────────────────────────────────────┘

         │
         │ NO errors
         ▼
┌────────────────────────────────────────┐
│ Prompt: Type YES to submit > ________  │
└────────┬───────────────────────────────┘
         │
    ┌────▼────────┐
    │ User input? │
    └────┬────────┘
         │
    ┌────┴────┐
    │   "no"  │ or anything except "yes"/"YES"
    │         │
    ▼         │
┌───────────────────────┐
│ Return "cancelled"    │
│ (Stop submission)     │
└───────────────────────┘

         │
         │ "yes" or "YES"
         ▼
┌────────────────────────────────────────┐
│ Click submit button                    │
│ 1. Try DOM index (if provided)         │
│ 2. Fallback: CSS selector search       │
│ 3. Score candidates by heuristics      │
└────────┬───────────────────────────────┘
         │
    ┌────▼────────┐
    │ Clicked OK? │
    └────┬────────┘
         │
    NO   │  YES
    ─────┼─────
         │
    ┌────▼────────────────────────────────┐
    │ Return "confirmed"                   │
    │ (User confirmed but click failed;    │
    │  agent must click manually)          │
    └──────────────────────────────────────┘

         │
         │ YES (clicked successfully)
         ▼
┌────────────────────────────────────────┐
│ Wait 0.75s for page transition         │
│ Check page text for:                   │
│ - Success messages?                    │
│ - Error messages?                      │
└────────┬───────────────────────────────┘
         │
    ┌────▼────────────┐
    │ Success found?  │
    └────┬────────────┘
         │
    YES  │  NO
    ─────┼─────
         │
    ┌────▼────────────────────────────────┐
    │ Return "submitted"                   │
    │ (Confirmed success)                  │
    └──────────────────────────────────────┘

         │
         │ NO success message
         ▼
┌────────────────────────────────────────┐
│ Check for error messages               │
└────────┬───────────────────────────────┘
         │
    ┌────▼────────┐
    │ Errors?     │
    └────┬────────┘
         │
    YES  │  NO
    ─────┼─────
         │
    ┌────▼────────────────────────────────┐
    │ Return "blocked_missing_fields"      │
    │ (Submission rejected by form)        │
    └──────────────────────────────────────┘

         │
         │ NO errors (uncertain state)
         ▼
┌────────────────────────────────────────┐
│ Return "confirmed"                      │
│ (Clicked but can't verify outcome)     │
└────────────────────────────────────────┘
```

**Return Values:**

| Return Value | Meaning | Agent Should |
|--------------|---------|--------------|
| `"submitted"` | User confirmed + click succeeded + success message detected | Mark as SUBMITTED, capture proof |
| `"confirmed"` | User confirmed but click failed OR outcome uncertain | Attempt manual click or verify status |
| `"cancelled"` | User declined to submit | Stop gracefully, return STOPPED_BEFORE_SUBMIT |
| `"blocked_missing_fields"` | Form has required field errors | Fill missing fields, retry confirmation |

### 6. Batch Processing Confirmation (Autonomous Mode)

**Trigger:** Autonomous mode builds job queue

**Prompt:**
```
Leads: total=50 valid=45 duplicates_skipped=3 below_threshold=2
Queue size: 10
Leads file: /path/to/leads.txt
Proceed with batch processing? (This will still prompt before any submit)
(y/n) >
```

**Outcomes:**
- User types `y`/`yes`: Start batch processing
  - Each job still goes through individual HITL gates
- User types `n`/`no`: Cancel batch
  - Return empty BatchResult

**Note:** The message "(This will still prompt before any submit)" clarifies that batch approval does NOT bypass per-job safety gates.

## Decision Points and Review Processes

### Critical Decision Points

The HITL module enforces **4 mandatory decision points** in the standard job application flow:

1. **Duplicate Detection** (runner/service.py)
   - **When:** Tracker finds existing submission record
   - **Gate:** `hitl.prompt_yes_no()`
   - **Default:** Safe (blocks duplicate)
   - **Override:** Requires yes + optional reason logging

2. **Fit Score Review** (runner/service.py)
   - **When:** Scorer recommends "skip" or "review"
   - **Gate:** `hitl.prompt_yes_no()`
   - **Default:** Safe (respects recommendation)
   - **Override:** Requires yes + logs override in notes

3. **Document Approval** (runner/service.py)
   - **When:** Tailoring completes successfully
   - **Gate:** `hitl.prompt_yes_no()`
   - **Default:** Safe (no upload without approval)
   - **Purpose:** Human review of tailored documents before sharing with employer

4. **Final Submission** (agent via `confirm_submit` tool)
   - **When:** Agent reaches final submit step
   - **Gate:** `confirm_submit()` requiring exact "yes"/"YES"
   - **Default:** Safe (no submission without exact confirmation)
   - **Pre-checks:** Validates no required field errors
   - **Post-verification:** Confirms success or detects errors

### Optional Interaction Points (Agent-Driven)

These interactions are invoked by the Browser Use agent as needed:

- **Yes/No Questions** (`ask_yes_no`): Binary decisions during form filling
- **Free Text Answers** (`ask_free_text`): Custom responses to application questions
- **OTP/2FA Codes** (`ask_otp_code`): Two-factor authentication
- **Q&A Bank Lookups** (`resolve_answer`): Reusable answers with learning capability

### Safety Design Patterns

1. **Explicit Over Implicit**
   - Submission requires exact "yes"/"YES", not just "y"
   - Prevents accidental confirmations

2. **Pre-flight Checks**
   - `confirm_submit` validates form completeness before prompting
   - Avoids wasting user confirmation on broken forms

3. **Post-action Verification**
   - Checks for success/error messages after clicking submit
   - Distinguishes actual submission from form rejection

4. **Graceful Degradation**
   - All browser helpers return False/empty on errors
   - System continues safely even if automation fails

5. **Audit Trail**
   - Override reasons are logged for duplicates
   - All prompts and responses are implicitly captured in conversation logs
   - Submission proof (text + screenshot) saved for verification

### Review Process Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              HITL Review Gates (Sequential)                  │
└─────────────────────────────────────────────────────────────┘

Stage 1: Pre-Execution Review
┌────────────────────────────────────────────────────────────┐
│ Duplicate Check                                            │
│ ────────────────────────────────────────────────────────── │
│ Input:  URL + extracted job metadata                       │
│ Action: Query tracker for existing submissions             │
│ Gate:   IF duplicate THEN prompt_yes_no()                  │
│ Effect: Early exit if user declines                        │
└────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────┐
│ Fit Score Review                                           │
│ ────────────────────────────────────────────────────────── │
│ Input:  Job description + user profile                     │
│ Action: Evaluate match quality                             │
│ Gate:   IF skip/review THEN prompt_yes_no()                │
│ Effect: Skip job if user agrees with recommendation        │
└────────────────────────────────────────────────────────────┘
                          │
                          ▼
Stage 2: Document Review
┌────────────────────────────────────────────────────────────┐
│ Tailoring Approval                                         │
│ ────────────────────────────────────────────────────────── │
│ Input:  Generated resume + cover letter                    │
│ Action: User reviews files externally                      │
│ Gate:   ALWAYS prompt_yes_no() before upload               │
│ Effect: Abort if user rejects documents                    │
└────────────────────────────────────────────────────────────┘
                          │
                          ▼
Stage 3: Execution Review (Agent-Driven)
┌────────────────────────────────────────────────────────────┐
│ Interactive Form Filling                                   │
│ ────────────────────────────────────────────────────────── │
│ Tools:  ask_yes_no, ask_free_text, ask_otp_code           │
│ Action: Agent requests user input as needed                │
│ Gate:   Dynamic (depends on form complexity)               │
│ Effect: Human provides missing information                 │
└────────────────────────────────────────────────────────────┘
                          │
                          ▼
Stage 4: Final Review (Most Critical)
┌────────────────────────────────────────────────────────────┐
│ Submit Confirmation                                        │
│ ────────────────────────────────────────────────────────── │
│ Input:  Completed application form                         │
│ Pre:    Check for required field errors                    │
│ Gate:   ALWAYS confirm_submit() requiring "yes"/"YES"      │
│ Action: Click submit + verify success                      │
│ Post:   Detect success message or errors                   │
│ Effect: Application submitted only with explicit approval  │
└────────────────────────────────────────────────────────────┘
```

## Testing

### Test Coverage

**Test File:** `/Users/shalom/Developer/Job-Easy/tests/unit/hitl/test_tools.py`

**Covered Functionality:**

1. **Input Parsing**
   - `test_yes_no_prompt_parsing_case_and_whitespace_tolerant()`
   - `test_yes_no_prompt_parsing_rejects_unknown_values()`
   - `test_yes_to_submit_requires_exact_confirmation_string()`
   - `test_otp_prompt_returns_raw_string_without_logging_secrets()`

2. **Browser Automation**
   - `test_click_submit_button_prefers_dom_index()`
   - `test_click_submit_button_falls_back_to_css_search()`

**Test Patterns:**

```python
# Example: Yes/No parsing
def test_yes_no_prompt_parsing_case_and_whitespace_tolerant():
    assert parse_yes_no(" yes ") is True
    assert parse_yes_no("Y") is True
    assert parse_yes_no("No") is False
    assert parse_yes_no(" n ") is False

def test_yes_no_prompt_parsing_rejects_unknown_values():
    with pytest.raises(ValueError):
        parse_yes_no("maybe")

# Example: Submit confirmation strictness
def test_yes_to_submit_requires_exact_confirmation_string():
    assert is_submit_confirmed("YES") is True
    assert is_submit_confirmed(" YES ") is True
    assert is_submit_confirmed("yes") is True
    assert is_submit_confirmed("y") is False  # Too casual!

# Example: Browser automation with mocks
@pytest.mark.asyncio
async def test_click_submit_button_prefers_dom_index():
    element = _DummyElement()
    page = _DummyPage(element)
    session = _DummyBrowserSession(page, _DummyNode(backend_node_id=999))

    clicked = await _click_submit_button(
        browser_session=session,
        submit_button_index=1316
    )

    assert clicked is True
    assert element.clicked is True
    assert session.index_lookups == [1316]  # Verified index used
    assert page.css_queries == []  # No fallback needed
```

### Testing Best Practices

1. **Separate I/O from Logic**
   - Parsing functions (`parse_yes_no`, `is_submit_confirmed`, `normalize_otp_code`) are pure and easily testable
   - Prompt functions (`prompt_yes_no`, `prompt_free_text`) wrap I/O but delegate to testable parsers

2. **Mock Browser Dependencies**
   - Tests use dummy classes (`_DummyBrowserSession`, `_DummyPage`, `_DummyElement`)
   - Verify behavior without actual browser automation

3. **Test Edge Cases**
   - Whitespace tolerance
   - Case insensitivity
   - Invalid input rejection
   - Fallback strategies

## Configuration

The HITL module itself has **no configuration**. All behavior is hardcoded for safety.

**Related Configuration** (in other modules that use HITL):

- `prohibited_domains` (runner): Domain filtering
- `qa_bank_path` (runner): Path to Q&A bank for `resolve_answer` tool
- `runner_max_failures` (runner): Agent retry limit
- `runner_step_timeout` (runner): Agent step timeout

**Rationale for No Configuration:**

HITL gates are intentionally **not configurable** to prevent users from accidentally disabling critical safety mechanisms. There is no "skip confirmation" flag.

## Error Handling

### Input Validation Errors

**Scenario:** User provides invalid yes/no response

**Handling:**
```python
# prompt_yes_no implementation
while True:
    answer = input(f"{question} (y/n) > ")
    try:
        return parse_yes_no(answer)
    except ValueError:
        print("Please answer with 'y'/'yes' or 'n'/'no'.")
        # Retry loop continues
```

**User Experience:**
```
Proceed with application? (y/n) > maybe
Please answer with 'y'/'yes' or 'n'/'no'.
Proceed with application? (y/n) > yes
```

### Browser Automation Errors

**Scenario:** Submit button click fails

**Handling:**
- All browser helpers use try/except with graceful returns
- `_click_submit_button` returns `False` on any exception
- `confirm_submit` returns `"confirmed"` if user said yes but click failed
- Agent receives signal to attempt manual click

**Code Example:**
```python
async def _click_submit_button(...) -> bool:
    try:
        page = await browser_session.must_get_current_page()
    except Exception:
        return False  # Graceful failure

    # ... click logic ...

    try:
        await best_element.click()
        return True
    except Exception:
        return False  # Click failed, but doesn't crash
```

### Page Text Extraction Errors

**Scenario:** Page is unresponsive or destroyed

**Handling:**
```python
async def _get_page_text(browser_session: BrowserSession) -> str:
    try:
        page = await browser_session.must_get_current_page()
    except Exception:
        return ""  # Return empty rather than crash

    try:
        text = await page.evaluate("() => document.body.innerText || ''")
    except Exception:
        return ""

    return text or ""
```

**Effect:**
- Verification functions (`_has_required_field_errors`, `_has_submit_success_text`) return `False` when text is unavailable
- System continues safely with conservative assumptions

## Performance Considerations

### Synchronous User Input

**Impact:**
- All `prompt_*` functions block execution waiting for user input
- This is intentional and desired for safety

**Implication:**
- Applications cannot proceed without human approval
- No background submission possible

### Browser Automation Delays

**Intentional Delays:**
```python
# After clicking submit
await asyncio.sleep(0.75)  # Wait for page transition before verification
```

**Rationale:**
- Gives page time to navigate/update before checking for success messages
- Balance between responsiveness and reliability

**Optimization:**
- Could be made configurable if needed, but 0.75s is conservative default

### Heuristic Scoring Performance

**Complexity:**
- `_score_submit_candidate` is O(n) where n = number of label tokens
- Typically runs on 1-10 button candidates
- Negligible performance impact

## Security and Privacy

### Sensitive Data Handling

**OTP/2FA Codes:**
- `normalize_otp_code` strips whitespace but does not log or store codes
- Codes are passed directly to browser automation
- Not persisted anywhere

**Q&A Bank Answers:**
- User responses to `resolve_answer` are saved to Q&A bank JSON
- Stored in plaintext at configured path (default: `./data/qa_bank.json`)
- Users should not enter passwords or secrets in application questions

**Conversation Logs:**
- User prompts and responses may appear in Browser Use conversation logs
- Logs are saved to `{run_dir}/conversation.jsonl`
- Contains full interaction history for debugging

### Input Sanitization

**Current State:**
- No sanitization of user free-text input
- Inputs are passed as-is to browser automation

**Rationale:**
- Users are trusted actors (this is a personal automation tool)
- Over-sanitization could corrupt legitimate answers (e.g., special characters in names)

**Risk Mitigation:**
- Browser Use handles escaping for browser input fields
- No shell command execution with user input

## Limitations and Known Issues

### 1. Submit Button Detection Limitations

**Problem:** Heuristic scoring may fail on unconventional submit buttons

**Example:**
- Button with no label/text → Score: -5 (deprioritized)
- Button with misleading label ("Next Step" that actually submits) → May be skipped

**Mitigation:**
- Agent can pass explicit `submit_button_index` to `confirm_submit`
- Fallback to CSS selector finds standard submit buttons
- User can manually intervene if automatic click fails (return value: `"confirmed"`)

### 2. Success Verification Limitations

**Problem:** Success message detection relies on hardcoded phrases

**Current Phrases:**
- "thank you for applying"
- "your application has been submitted"
- "application submitted"
- "application received"

**Risk:**
- Sites with non-standard confirmation messages may not be detected
- False negatives possible (actual submission not verified)

**Mitigation:**
- Agent still marks submission attempt in tracker
- User can manually verify from final screenshot/URL
- Conservative: `confirm_submit` returns `"confirmed"` (uncertain) rather than `"submitted"` (certain) when verification fails

### 3. Required Field Error Detection Limitations

**Problem:** Error phrase detection relies on common patterns

**Current Phrases:**
- "this field is required."
- "resume/cv is required."
- "cover letter is required."

**Risk:**
- Sites with custom error messages may not be detected
- `confirm_submit` may prompt user even when form is incomplete

**Mitigation:**
- User will see form errors after attempting to submit
- Can decline submission and fix errors manually
- Agent may retry after user intervention

### 4. No Visual Confirmation

**Problem:** User must trust HITL gates without seeing the form

**Current Behavior:**
- Prompts appear in CLI without browser screenshot

**Impact:**
- User cannot visually verify form state before confirming submission

**Potential Enhancement:**
- Could add screenshot capture before submit confirmation
- Could add browser window focus to show form to user

### 5. Blocking I/O Model

**Problem:** All prompts block the main thread

**Impact:**
- No concurrent task execution while waiting for user input
- Batch processing is fully sequential (one job at a time)

**Rationale:**
- Intentional for safety and simplicity
- Parallel submissions would complicate user interaction model

## Future Enhancements

### Potential Improvements

1. **Visual Confirmation**
   - Capture screenshot before submit confirmation
   - Display form preview in terminal or browser window
   - Highlight submit button in screenshot

2. **Configurable Verification Phrases**
   - Allow users to customize success/error phrase lists
   - Support regex patterns for detection

3. **Enhanced Submit Button Detection**
   - Machine learning model for button classification
   - Computer vision for visual button recognition
   - More sophisticated heuristics (form context, button position)

4. **Confirmation Timeouts**
   - Add timeout to `confirm_submit` to prevent indefinite blocking
   - Auto-cancel after N minutes of inactivity

5. **Audit Logging**
   - Dedicated HITL decision log (separate from conversation logs)
   - Structured JSON with timestamps, decisions, and reasons
   - Facilitates compliance and debugging

6. **Rich Terminal UI**
   - Use libraries like `rich` or `textual` for better prompts
   - Show form data summary before confirmation
   - Interactive menus instead of y/n prompts

7. **Voice Confirmation** (Advanced)
   - Voice-based confirmation for hands-free operation
   - Requires speaker identification for security

8. **Remote Confirmation** (Enterprise)
   - Send confirmation requests to mobile app or web dashboard
   - Asynchronous approval workflow
   - Multi-user approval chains

## API Reference

### Public Functions

#### Input Parsing

```python
def parse_yes_no(answer: str) -> bool
```
Parse yes/no answer with tolerance for common variants.

**Parameters:**
- `answer` (str): User input

**Returns:**
- `bool`: True for yes, False for no

**Raises:**
- `ValueError`: Invalid input

---

```python
def is_submit_confirmed(answer: str) -> bool
```
Validate explicit submission confirmation.

**Parameters:**
- `answer` (str): User input

**Returns:**
- `bool`: True only for exact "yes"/"YES"

---

```python
def normalize_otp_code(answer: str) -> str
```
Normalize OTP/2FA code.

**Parameters:**
- `answer` (str): Raw input

**Returns:**
- `str`: Normalized code

---

#### Interactive Prompts

```python
def prompt_yes_no(question: str) -> bool
```
Prompt for yes/no with validation and retry.

**Parameters:**
- `question` (str): Question to display

**Returns:**
- `bool`: User's response

---

```python
def prompt_free_text(question: str) -> str
```
Prompt for free-form text input.

**Parameters:**
- `question` (str): Question to display

**Returns:**
- `str`: User's response (stripped)

---

```python
def prompt_confirm_submit(prompt: str) -> bool
```
Prompt for explicit submission confirmation.

**Parameters:**
- `prompt` (str): Confirmation message

**Returns:**
- `bool`: True if user typed "yes"/"YES"

---

```python
def prompt_otp_code(prompt: str) -> str
```
Prompt for OTP/2FA code.

**Parameters:**
- `prompt` (str): Prompt message

**Returns:**
- `str`: Normalized OTP code

---

#### Tools Registry

```python
def create_hitl_tools() -> Tools
```
Create Browser Use Tools registry with HITL actions.

**Returns:**
- `Tools`: Configured tools registry

**Registered Tools:**
- `ask_yes_no(question: str) -> str`
- `ask_free_text(question: str) -> str`
- `confirm_submit(prompt: str, browser_session: BrowserSession, submit_button_index: int | None = None) -> str`
- `ask_otp_code(prompt: str) -> str`

---

### Internal Functions (Private API)

These functions are implementation details and may change without notice.

```python
async def _click_submit_button(
    *,
    browser_session: BrowserSession,
    submit_button_index: int | None
) -> bool
```

```python
async def _score_submit_candidate(element) -> int
```

```python
async def _get_page_text(browser_session: BrowserSession) -> str
```

```python
async def _has_required_field_errors(browser_session: BrowserSession) -> bool
```

```python
async def _has_submit_success_text(browser_session: BrowserSession) -> bool
```

## Glossary

- **HITL**: Human-in-the-Loop - design pattern requiring human oversight for automated systems
- **Browser Use**: Third-party library for browser automation with LLM agents
- **Tools Registry**: Browser Use pattern for providing custom actions to agents
- **BrowserSession**: Browser Use object representing active browser session
- **Submit Gate**: Critical confirmation point before final application submission
- **Q&A Bank**: Persistent storage for reusable application question answers
- **Heuristic Scoring**: Algorithm that uses practical rules to make decisions (vs. perfect algorithms)
- **Graceful Degradation**: System continues safely even when components fail
- **Pre-flight Check**: Validation before executing an operation
- **Post-verification**: Confirmation after executing an operation

## Related Documentation

- **Runner Module**: `/Users/shalom/Developer/Job-Easy/docs/runner.md` (if exists)
- **Autonomous Module**: `/Users/shalom/Developer/Job-Easy/docs/autonomous.md`
- **Extractor Module**: `/Users/shalom/Developer/Job-Easy/docs/extractor.md`
- **Tracker Module**: Integration with duplicate detection and status tracking
- **Project Brief**: `/Users/shalom/Developer/Job-Easy/docs/project-brief.md`

## Summary

The HITL module is the **safety backbone** of the Job-Easy application, ensuring that automation serves users without removing their control. By providing clear confirmation gates, flexible interaction tools, and intelligent verification, it enables confident use of browser automation for sensitive tasks like job applications.

**Key Takeaways:**

1. **Four mandatory gates**: Duplicate check, fit review, document approval, submit confirmation
2. **Agent-driven interactions**: Tools for dynamic questions, OTP, and custom answers
3. **Safety by design**: Strict confirmation requirements, pre-flight checks, post-verification
4. **Testable architecture**: Pure parsing functions, dependency injection for browser components
5. **Graceful failure**: All browser helpers degrade safely on errors
6. **Zero configuration**: Safety gates cannot be disabled accidentally

The module demonstrates that automation and control are not mutually exclusive - they are complementary when designed with human oversight as a first-class concern.
