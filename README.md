<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/AI-Powered-purple?style=for-the-badge&logo=openai&logoColor=white" alt="AI Powered">
  <img src="https://img.shields.io/badge/Browser-Automation-orange?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Browser Automation">
</p>

<h1 align="center">🚀 Job-Easy</h1>

<p align="center">
  <strong>Stop applying manually. Start applying intelligently.</strong>
</p>

<p align="center">
  AI-powered job application automation that extracts, scores, tailors, and applies — <br>
  with <em>you</em> in control of every submission.
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-usage">Usage</a> •
  <a href="#-documentation">Docs</a>
</p>

---

## ✨ Why Job-Easy?

Job hunting is exhausting. You spend hours tailoring resumes, writing cover letters, and filling out the same forms over and over. **Job-Easy changes that.**

| The Old Way 😫 | The Job-Easy Way 🎯 |
|----------------|---------------------|
| Manually read job descriptions | AI extracts key requirements automatically |
| Guess if you're a good fit | Smart scoring tells you before you apply |
| Rewrite your resume every time | Tailored documents generated in seconds |
| Fill out endless form fields | Browser automation handles the tedious parts |
| Lose track of applications | Built-in tracker prevents duplicates |

---

## 🎯 Features

<table>
<tr>
<td width="50%">

### 🔍 Smart Extraction
Pulls structured data from **Greenhouse**, **Lever**, **Workday**, **LinkedIn**, **Indeed**, and more. Gets the requirements, salary, location — everything you need.

### 📊 Intelligent Scoring
Compares jobs against your profile with a weighted algorithm. Know instantly if it's worth your time: **Apply**, **Review**, or **Skip**.

### 📝 AI Document Tailoring
Generates customized resumes and cover letters that highlight your relevant experience. **Truthful enhancement** — never fabricates skills.

</td>
<td width="50%">

### 🛡️ Human-in-the-Loop Safety
**You approve everything.** Review documents, confirm submissions, override recommendations. Nothing happens without your explicit YES.

### 🔄 Batch Processing
Feed it a list of jobs. It filters duplicates, ranks by fit score, and processes the best matches — while you grab a coffee.

### 📈 Application Tracking
Local database tracks every application. Never accidentally reapply. Always know where you stand.

</td>
</tr>
</table>

---

## 🚀 Quick Start

### 1️⃣ Install

```bash
git clone https://github.com/ShalomObongo/job-easy.git
cd job-easy
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### 2️⃣ Configure

```bash
cp .env.example .env        # Add your API keys
cp profiles/profile.example.yaml profiles/profile.yaml  # Add your info
```

Profile tips:
- Add `github_url` to your `profiles/profile.yaml` (optional) so it can be included on the resume and used by YOLO mode to answer “GitHub/portfolio” questions.

### 3️⃣ Start Local Skyvern (Runner Backend)

Runner execution is local Skyvern only. Extractor/scoring/tailoring still use Browser Use + LLM providers.

```bash
# Terminal 1
./scripts/start_skyvern_local.sh
```

Notes:
- Script reads `RUNNER_LLM_*` from `.env` and maps them to Skyvern-compatible env values.
- Script sets browser window size/position automatically (override with `BROWSER_WIDTH` / `BROWSER_HEIGHT`).
- Default database is `postgresql+psycopg://localhost/skyvern` (override with `DATABASE_STRING`).

### 4️⃣ Run Job-Easy

```bash
# Single job - full pipeline
python -m src single https://jobs.lever.co/company/position-id

# Single job (YOLO auto-answering)
python -m src single https://jobs.lever.co/company/position-id --yolo

# Single job (YOLO + auto-approve fit/doc prompts)
python -m src single https://jobs.lever.co/company/position-id --yolo --yes

# Single job (YOLO + auto-submit final submit)
python -m src single https://jobs.lever.co/company/position-id --yolo --yes --auto-submit

# Batch mode - process multiple jobs
python -m src autonomous leads.txt --dry-run
```

**That's it.** You're ready to apply smarter.

---

## 🔧 How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   📥 URL    │────▶│  🔍 Extract │────▶│  📊 Score   │────▶│  📝 Tailor  │────▶│  ✅ Apply   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                           │                   │                   │                   │
                           ▼                   ▼                   ▼                   ▼
                    Job description      Fit analysis        Resume + CL         Form filled
                    + requirements       + recommendation    customized          + submitted
```

### Runner Backend (Skyvern Local)

- `extractor` remains Browser Use-based.
- `runner` executes via local Skyvern (`RUNNER_BACKEND=skyvern_local`).
- Runner injects structured job + profile context into apply prompts for tailored answers.
- Upload routing is strict: resume goes to Resume/CV fields, cover letter PDF only to explicit cover upload fields.
- If a cover-letter text field exists, runner writes tailored text into that field instead of uploading a file.
- Runner guards against early completion by requiring a full required-field sweep before complete/submit.
- Default max wait is `RUNNER_SKYVERN_MAX_WAIT_SECONDS=1800` for longer forms.

### Safety Gates at Every Step

| Gate | What Happens |
|------|--------------|
| 🔄 **Duplicate Check** | Already applied? You decide whether to proceed |
| 📊 **Fit Review** | Borderline score? Your call |
| 📄 **Document Approval** | Review every tailored document before use |
| ✅ **Submit Confirmation** | Type **YES** to submit — no accidents |

---

## 💻 Usage

### Single Job Mode

Process one job through the complete pipeline:

```bash
# Full pipeline run
python -m src single https://jobs.lever.co/company/position-id

# YOLO mode (best-effort auto-answering)
python -m src single https://jobs.lever.co/company/position-id --yolo

# YOLO + auto-approve fit score + document prompts
python -m src single https://jobs.lever.co/company/position-id --yolo --yes
```

Note: `--yes` only applies to non-submit prompts (fit skip/review and document approval). Final submit is still gated and requires typing `YES`.

### Auto-Submit (Optional)

If you explicitly opt in, you can skip the final “Type YES” submit confirmation:

```bash
python -m src single <url> --yolo --yes --auto-submit
```

Auto-submit is only allowed when both `--yolo` and `--yes` are enabled.

### Autonomous Mode

Process a batch of jobs:

```bash
# Process all jobs
python -m src autonomous leads.txt

# Dry run - generate docs without applying
python -m src autonomous leads.txt --dry-run

# With filters
python -m src autonomous leads.txt --min-score 0.8 --dry-run

# YOLO mode (best-effort auto-answering)
python -m src autonomous leads.txt --yolo
```

**Leads file format:**
```text
# One URL per line
https://jobs.lever.co/company/position-1
https://boards.greenhouse.io/company/jobs/123456
```

### Component Commands

Run individual stages:

| Command | What It Does |
|---------|--------------|
| `python -m src extract <url>` | 🔍 Extract job data |
| `python -m src score --jd <file> --profile <file>` | 📊 Score job fit |
| `python -m src score-eval --input <path> --profile <file>` | 🧪 Compare deterministic vs LLM scoring |
| `python -m src tailor --jd <file> --profile <file>` | 📝 Generate documents |
| `python -m src apply <url> --resume <file> [--cover-letter <file>]` | ✅ Run application (runner only) |
| `python -m src queue <leads> --profile <file>` | 📋 Preview ranked batch |
| `python -m src tracker stats` | 📈 View statistics |

---

## ⚙️ Configuration

### Required Settings

| Variable | Description |
|----------|-------------|
| `EXTRACTOR_LLM_PROVIDER` | `openai`, `anthropic`, or `auto` |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Your LLM credentials |
| `SCORING_PROFILE_PATH` | Path to your profile YAML |
| `SCORING_SCORING_MODE` | `deterministic` or `llm` |
| `RUNNER_BACKEND` | Must be `skyvern_local` |
| `RUNNER_SKYVERN_BASE_URL` | Local Skyvern API URL (`http://localhost:8000`) |
| `RUNNER_SKYVERN_ENFORCE_LOCAL` | Keep `true` to reject remote runner endpoints |
| `RUNNER_SKYVERN_MAX_WAIT_SECONDS` | Max runner wait (default `1800`) |

### Scoring Weights

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| 🎯 Must-Have Skills | 40% | Required skills match |
| ⭐ Preferred Skills | 20% | Nice-to-have match |
| 📅 Experience | 25% | Years alignment |
| 🎓 Education | 15% | Degree level match |

### Thresholds

| Score | Recommendation |
|-------|----------------|
| ≥ 0.75 | ✅ **Apply** — Great match |
| 0.70 - 0.74 | 🤔 **Review** — Your call |
| < 0.70 | ⏭️ **Skip** — Not recommended |

---

## 🏗️ Architecture

Nine specialized modules working together:

| Module | Purpose |
|--------|---------|
| `config` | ⚙️ Centralized settings |
| `extractor` | 🔍 Job data extraction |
| `scoring` | 📊 Fit evaluation |
| `tailoring` | 📝 Document generation |
| `runner` | 🤖 Browser automation |
| `tracker` | 📈 Application history |
| `autonomous` | 🔄 Batch orchestration |
| `hitl` | 🛡️ Safety gates |
| `utils` | 🔧 Shared utilities |

---

## 📁 Artifacts

Each run creates:

| File | Description |
|------|-------------|
| `jd.json` | 📋 Extracted job data |
| `fit_result.json` | 📊 Score breakdown |
| `resume.pdf` | 📄 Tailored resume |
| `cover_letter.pdf` | ✉️ Generated cover letter |
| `application_result.json` | ✅ Submission status |
| `skyvern_execution.json` | 🤖 Raw Skyvern run payload + output |
| `skyvern_artifacts.json` | 🎥 Screenshot/recording metadata (when available) |
| `conversation.jsonl` | 🧾 Serialized runner conversation payload |

---

## 📚 Documentation

Deep-dive into each module:

| Module | Docs |
|--------|------|
| Batch Processing | [autonomous.md](docs/autonomous.md) |
| Configuration | [config.md](docs/config.md) |
| Job Extraction | [extractor.md](docs/extractor.md) |
| Safety Gates | [hitl.md](docs/hitl.md) |
| Application Runner | [runner.md](docs/runner.md) |
| Runner Local Setup | [runner-skyvern-local.md](docs/runner-skyvern-local.md) |
| Runner Manual Verification | [runner-manual-test.md](docs/runner-manual-test.md) |
| Fit Scoring | [scoring.md](docs/scoring.md) |
| Document Tailoring | [tailoring.md](docs/tailoring.md) |
| Application Tracking | [tracker.md](docs/tracker.md) |
| Utilities | [utils.md](docs/utils.md) |

---

## 🧪 Testing

```bash
pytest                      # Run all tests
pytest --cov=src            # With coverage
pytest tests/unit/scoring/  # Specific module
```

## 🧩 PDF Rendering Dependencies (WeasyPrint)

This project uses WeasyPrint for PDF generation. It requires system libraries
(Pango/Cairo/GObject). If you hit import/linker errors, install the OS deps.

macOS (Homebrew):
```bash
brew install pango cairo gdk-pixbuf libffi
```

---

## ⚠️ Safety First

> **Job-Easy is designed to assist, not replace your judgment.**

- 🔒 **No auto-submit by default** — You must type YES
- ✅ **Auto-submit is opt-in** — Requires `--yolo --yes --auto-submit` (or `RUNNER_AUTO_SUBMIT=true` with the same prerequisites)
- 🚫 **No CAPTCHA bypass** — System pauses and asks for help
- 🛑 **Duplicate protection** — Won't reapply accidentally
- 👀 **Full transparency** — Review everything before it's sent

---

## 🤝 Contributing

Contributions welcome! See [AGENTS.md](AGENTS.md) for development guidelines.

---

## 📄 License

MIT — Use it, modify it, make your job search easier.

---

<p align="center">
  <strong>Built with 🤖 Skyvern (Runner) + Browser Use (Extractor) + AI-Powered Document Generation</strong>
</p>

<p align="center">
  <sub>Stop the grind. Start the hustle smarter.</sub>
</p>
