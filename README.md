# SkillPath AI

> **AI Career Coach & Portfolio Evidence Ledger**  
> *Match what your code proves to the role you want — with verifiable citations, automatic commit reassessment, and live Proof Deltas.*

[![CI](https://github.com/vedantsable56/Skill_Path/actions/workflows/ci.yml/badge.svg)](https://github.com/vedantsable56/Skill_Path/actions)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-1.0.0-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## The Core Problem & Differentiator

Most AI career tools are résumé chatbots or keyword matchers: they hallucinate skills, invent qualifications from fluff, or make arbitrary assumptions.

**SkillPath AI is fundamentally different: it is an evidence-backed career ledger.**
- **Deterministic Fact-Checking:** Never uses an LLM to guess if code works. Uses a bounded AST & pattern analysis engine that requires **real code syntax** (e.g. testing requires both test declarations AND assertions; comments and docstrings are filtered out).
- **Verifiable Citations:** Every single demonstrated skill links directly to an **exact GitHub file path, 1-indexed line range, code excerpt, and commit SHA**.
- **Ethical Safeguard:** Missing evidence is strictly labelled **"not demonstrated in this inspected scope"** — never as a verdict that a student lacks the skill.
- **The Proof Delta:** When a student pushes a commit to GitHub, SkillPath AI detects the new commit SHA (via 10s poll or instant push webhook) and produces a **before-and-after comparison** proving exactly what new requirements were satisfied.

```text
Real Job Posting  ──>  Bounded GitHub Scan  ──>  Accurate Gaps
                                                      │
                                             New Commit Pushed
                                                      │
                                                      ▼
Proof Delta  <──  Before/After Comparison  <──  Automatic Reassessment
```

---

## Key Features

1. **Job Requirements Ingestion:**
   - Ingest any public job posting URL with preserved traceability.
   - **Saved Jobs Dropdown:** Switch between multiple saved roles with one click or delete unwanted postings.
   - **Optional JSearch Discovery:** Search live Indian or global postings by keyword and location.

2. **Read-Only Bounded GitHub Code Inspection:**
   - 22 skill detection rules across Python, FastAPI, Flask, SQL Databases, React, TypeScript, JavaScript, Docker, CI/CD, AWS, Azure, Machine Learning, RAG, Embeddings, Java, C++, and more.
   - Inspects public repositories without authentication (60 req/hr) or with a read-only GitHub PAT (5,000 req/hr).
   - Never clones, installs, or executes code. Inspects up to 20 files (max 200 KB per file, 1.5 MB total).

3. **Live Reassessment & Instant Webhook:**
   - **Background Polling Monitor:** Automatically checks for new commit SHAs every 10 seconds.
   - **GitHub Push Webhook (`POST /api/integrations/github/webhook`):** Receives instant GitHub push events and triggers immediate reassessment without waiting for polling cycles.
   - **Multi-Job Reassessment:** One repository push updates all jobs tracking that repository simultaneously.

4. **Snapshot History & Proof Delta:**
   - Immutable SQLite snapshot history deduplicated by `(repository_id, commit_sha)`.
   - Side-by-side Proof Delta comparison showing gained evidence, status changes, and fit score progression.

5. **Optional AI Interpretations & Growth Plan:**
   - **OpenAI Responses Integration:** When configured, generates plain-English assessment summaries and personalized next-step task recommendations.
   - **Controlled xAI / Grok Fallback:** Fallback activates only on transient OpenAI failures.
   - **Integrity Rule:** AI models can *never* invent evidence citations or alter deterministic skill statuses.

6. **Optional Telegram Alerts:**
   - Connect a Telegram bot using a secure one-time pairing code.
   - Automatically sends a notification to your Telegram chat when a new commit is reassessed.

7. **Modern Responsive UI:**
   - High-contrast, dark mode theme with glassmorphic accents and accessible typography.
   - Fully responsive layouts tailored for desktop, tablet, and mobile presentation.

---

## Architecture & Technology Stack

- **Backend:** Python 3.11 + FastAPI (single service, dependency injection pattern)
- **Database:** SQLite with WAL mode (`data/career_coach.sqlite3`)
- **Frontend:** Vanilla HTML5, modern CSS3 (custom design system, dark mode), Vanilla JavaScript (IIFE, no bundler needed)
- **External APIs:** GitHub REST API, optional OpenAI API, optional RapidAPI JSearch, optional Telegram Bot API
- **Infra:** Docker (non-root `python:3.11-slim`), Azure Container Apps (`infra/foundation.bicep` & `infra/app.bicep`)

---

## Quickstart: Running Locally

### 1. Prerequisites
- Python 3.11+
- Node.js (for syntax validation check)
- Git

### 2. Setup & Installation
```powershell
# Clone the repository
git clone https://github.com/vedantsable56/Skill_Path.git
cd Skill_Path

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

### 3. Configure Environment (`.env`)
Create a `.env` file in the project root:
```env
# Core settings
DATABASE_PATH=data/career_coach.sqlite3
SQLITE_JOURNAL_MODE=WAL
MONITORING_ENABLED=true
POLL_INTERVAL_SECONDS=10

# GitHub Integration (Recommended: fine-grained read-only PAT for 5,000 req/hr)
GITHUB_TOKEN=your_github_token_here

# Optional: Instant GitHub Push Webhook (leave blank for open dev mode)
GITHUB_WEBHOOK_SECRET=

# Optional: AI Interpretations & Growth Recommendations
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
ENABLE_LLM_EXPLANATIONS=false

# Optional: Live Job Search via Jooble & RapidAPI/JSearch
JOOBLE_API_KEY=57182337-177a-4e64-ae00-45ea25742460
JOOBLE_API_URL=https://in.jooble.org/api
JSEARCH_API_KEY=
JSEARCH_API_URL=https://jsearch.p.rapidapi.com

# Optional: Telegram Reassessment Alerts
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=
TELEGRAM_BOT_USERNAME=
TELEGRAM_NOTIFICATIONS_ENABLED=false
PUBLIC_BASE_URL=
```

### 4. Seed Demo Job Roles (Recommended)
To pre-populate 4 production-grade job postings into your local database:
```powershell
python -m backend.seed_jobs
```
This adds:
- `Python Cloud Backend Engineer` (FastAPI, SQL, Pytest, Docker, CI/CD)
- `Full-Stack Web Developer` (React, TypeScript, REST APIs, Testing)
- `AI / Generative AI Engineer` (Python, ML, RAG, Embeddings, LLM Integration)
- `Systems Software Engineer` (Java, C++, SQL, Algorithms, Git)
directly to your **"Saved job postings"** dropdown.

### 5. Start the Application
```powershell
python -m uvicorn backend.main:app --reload --port 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.  
Interactive Swagger API documentation is available at **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**.

---

## Running Tests & Merge Gate

Run the automated test suite and merge gate checks:
```powershell
# Run 15 passing unit and integration tests
pytest -q

# Run Python compilation check
python -m compileall -q backend

# Run JavaScript syntax check
node --check frontend\script.js
```

---

## Live Demonstration Guide

Follow our comprehensive rehearsal and demo guide in [docs/demo-script.md](docs/demo-script.md) for:
- Pre-prepared Python/FastAPI and Full-Stack job postings.
- 5-minute step-by-step judge demonstration flow.
- Fast webhook simulation commands for rehearsals.
- Judge Q&A talking points explaining how SkillPath AI prevents LLM hallucination and handles rate limits.

---

## Cloud Deployment (Azure)

SkillPath AI is ready for single-container deployment to Azure Container Apps:
```powershell
# See docs/azure-deployment.md for complete details
az login
az group create --name skillpath-rg --location centralindia
az deployment group create --resource-group skillpath-rg --template-file infra/foundation.bicep
az acr build --registry <acrName> --image skillpath-ai:v1 .
az deployment group create --resource-group skillpath-rg --template-file infra/app.bicep
```
For full instructions, see [docs/azure-deployment.md](docs/azure-deployment.md).

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
