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

1. **Job Requirements Ingestion & Live Search:**
   - Ingest any public job posting URL with preserved traceability.
   - **1-Click Live Search:** Search real-time postings across India & globally using Jooble and JSearch. Click *"Use this posting"* to auto-fill description, role, and source URL.
   - **Saved Jobs Management:** Switch between multiple saved roles with one click or delete unwanted postings.

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

6. **Telegram Bot Alerts:**
   - Connect a Telegram bot using a secure one-time pairing code.
   - Automatically sends a deduplicated notification to your Telegram chat when a new commit is reassessed.

7. **Modern Responsive UI:**
   - High-contrast dark mode theme with IDE-styled code excerpt inspector, syntax badges, and collapsible citations.
   - Fully responsive layouts tailored for desktop, tablet, and mobile presentation.

---

## 📽️ Hackathon Presentation & Pitch Deck Guide (Slide-by-Slide)

Use this structured section to generate your hackathon pitch slides in PowerPoint, Google Slides, Gamma, or Canva:

### Slide 1: Title & Vision
- **Header:** SkillPath AI: The Living Portfolio Evidence Ledger
- **Subtitle:** Match what your code proves to the role you want — without guesswork or hallucination.
- **Presenter Hook:** *"Recruiters receive thousands of résumés with copied buzzwords, while student developers build great code that ATS algorithms ignore. SkillPath AI replaces résumé keywords with cryptographic, verifiable GitHub code evidence."*
- **Key Metrics / Badges:** 22+ AST Skill Detectors · 0% Hallucination Policy · Real-Time Commit Proof Deltas

### Slide 2: The Industry Problem
- **Headline:** The Résumé Trust Deficit in Junior Hiring
- **Three Core Friction Points:**
  1. **Self-Reported Keywords:** Anyone can list "FastAPI, Docker, SQL" on a resume; recruiters cannot verify it without hours of manual repo browsing.
  2. **Opaque & Unfair Rejections:** Students get rejected without knowing *why* or what missing project evidence would satisfy the role.
  3. **Static Portfolio Reviews:** When a student learns a skill and pushes new code, their application status remains stagnant.

### Slide 3: The Solution — Evidence, Not Assumptions
- **Headline:** From Chatbot Claims to Deterministic Code Proof
- **Core Pillars:**
  - **Deterministic AST Engine:** Parses AST trees and real code constructs (filtering out comments, docstrings, and package manifests).
  - **Exact Citations:** Every validated skill cites `file path`, `1-indexed line numbers`, `code excerpt`, and `commit SHA`.
  - **Ethical Integrity:** A missing skill is never an insult. It is strictly labelled: *"not demonstrated in this inspected scope"*.

### Slide 4: The 5-Stage Live Evidence Loop
- **Headline:** How SkillPath AI Works End-to-End
- **Workflow Diagram:**
  ```text
  1. Target Job Intake (Jooble / JSearch live posting)
       ↓
  2. Read-Only Bounded GitHub Scan (routes, queries, test assertions)
       ↓
  3. Evidence Baseline (deterministic match score & citations)
       ↓
  4. Student Commits Code (Git push to GitHub repository)
       ↓
  5. Live Proof Delta & Alert (instant reassessment + Telegram push)
  ```

### Slide 5: Real-Time Job Discovery & Intelligent Mapping
- **Headline:** Real Roles from Real Companies in Real Time
- **Features Highlighted:**
  - Integrated with **Jooble** and **JSearch** APIs for live job openings across India and worldwide.
  - 1-click **"⚡ Find Live Postings"**: Fetches real roles (BMC, Persistent Systems, Map My Crop, Cybage).
  - One-click auto-population into requirement extractor.

### Slide 6: Continuous Monitoring & The Proof Delta
- **Headline:** Portfolios that Grow with Every Git Commit
- **Key Capabilities:**
  - **Dual Trigger System:** 10-second background polling + instant `X-Hub-Signature-256` GitHub push webhook.
  - **The Proof Delta Comparison:** Displays exact before-and-after status changes (e.g., *SQL and database queries* transitioning from "not demonstrated" to "demonstrated" at commit `261191c`).
  - **Actionable Growth Tasks:** Provides concrete next proof coding tasks for every undemonstrated requirement.

### Slide 7: Technical Architecture & Security Guardrails
- **Headline:** Production-Grade Single-Service Architecture
- **Tech Stack:**
  - **Core Backend:** Python 3.11 + FastAPI (async REST API, Swagger docs).
  - **Storage:** SQLite with Write-Ahead Logging (WAL) for atomic snapshot history.
  - **Frontend:** Vanilla HTML5, CSS3 Custom Properties (Dark IDE theme), Vanilla JS.
  - **Security Boundary:** Strictly read-only GitHub API; bounded scans (max 20 files, 200 KB per file); secrets strictly server-side.

### Slide 8: Live Demo Scenario (Demonstration Script)
- **Headline:** Watching the Live Loop in Action
- **Step 1:** Select "Python Backend Engineer (Pune)" or search live jobs via Jooble.
- **Step 2:** Connect `vedantsable56/HydroRAG` repository.
- **Step 3:** Review initial evidence: SQL queries demonstrated at `app.py:51-53` and `rag_engine.py:165-167`.
- **Step 4:** Push a new commit adding an endpoint or test.
- **Step 5:** Watch monitor auto-reassess in 10s and deliver an instant Telegram alert.
- **Step 6:** Click "View comparison" to inspect the generated Proof Delta.

### Slide 9: Competitive Advantage & Differentiation
- **Comparison Matrix:**
  | Feature | Generic Resume AI | SkillPath AI |
  | --- | --- | --- |
  | Verification Method | Fuzzy LLM matching | Deterministic AST Code Parser |
  | Traceability | None (Hallucinated) | Exact file, line range, commit SHA |
  | Reassessment | Manual re-upload | Automatic Git commit tracking |
  | Missing Skill Claim | "Candidate lacks skill" | "Not demonstrated in inspected scope" |
  | Instant Alerts | Email summaries | Live Telegram push notifications |

### Slide 10: Future Roadmap & Vision
- **Headline:** The Future of Verifiable Technical Hiring
- **Upcoming Horizons:**
  1. **Multi-Repo Developer Graph:** Unified evidence graph aggregating multiple repositories into a single developer profile.
  2. **Recruiter Audit Portal:** Cryptographically signed proof reports recruiters can verify in one click.
  3. **Automated PR Coach:** GitHub Action bot commenting on pull requests with proof delta updates.

---

## 🌐 Deployment Guide: Where & How to Deploy

SkillPath AI is architected as a lightweight, single-service FastAPI application with SQLite and vanilla frontend assets. Because it runs background asyncio tasks (repository commit monitoring & Telegram polling), it thrives on platforms that support persistent processes.

### Recommended Platform: **Render (Free & Fast)**

Render provides free Python Web Services with automatic HTTPS (mandatory for Telegram webhooks), background process execution, and auto-deploy on Git push.

#### Step 1: Push Repository to GitHub
Ensure your code is pushed to your GitHub repository (`main` or `feature/skillpath-mvp`).

#### Step 2: Create a New Web Service on Render
1. Log in to [dashboard.render.com](https://dashboard.render.com/).
2. Click **New +** → **Web Service**.
3. Connect your GitHub repository: `vedantsable56/Skill_Path`.
4. Render will automatically detect [`render.yaml`](render.yaml) in the root. If setting manually:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `python -m backend.seed_jobs && python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** `Free`

#### Step 3: Configure Environment Variables in Render
In the **Environment** tab, set:
```env
DATABASE_PATH=data/career_coach.sqlite3
SQLITE_JOURNAL_MODE=WAL
MONITORING_ENABLED=true
POLL_INTERVAL_SECONDS=10
GITHUB_TOKEN=your_personal_access_token
JOOBLE_API_KEY=57182337-177a-4e64-ae00-45ea25742460
JOOBLE_API_URL=https://in.jooble.org/api
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_BOT_USERNAME=MySkillPathBot
TELEGRAM_NOTIFICATIONS_ENABLED=true
PUBLIC_BASE_URL=https://your-app-name.onrender.com
OPENAI_API_KEY=your_openai_key_optional
ENABLE_LLM_EXPLANATIONS=true
```

#### Step 4: Verify Deployment
1. Open `https://your-app-name.onrender.com`.
2. Visit `https://your-app-name.onrender.com/api/health` — it should return:
   ```json
   {"status":"ok","service":"SkillPath AI","monitoring_enabled":true}
   ```
3. Set your GitHub Webhook in your repo settings pointing to:
   `https://your-app-name.onrender.com/api/integrations/github/webhook`
   with `Content type: application/json`.

---

### Alternative Platform: **Railway**
1. Go to [railway.app](https://railway.app/) and create a new project from your GitHub repo.
2. Railway detects the `Procfile` automatically (`web: python -m backend.seed_jobs && python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}`).
3. Add a persistent volume mounted at `/app/data` to preserve your SQLite database across restarts.
4. Add environment variables in the Railway dashboard.

---

### Alternative Platform: **Azure Container Apps**
The repository includes production Bicep templates for Azure Container Apps:
```powershell
az login
az group create --name skillpath-rg --location centralindia
az deployment group create --resource-group skillpath-rg --template-file infra/foundation.bicep
az acr build --registry <acrName> --image skillpath-ai:v1 .
az deployment group create --resource-group skillpath-rg --template-file infra/app.bicep
```
See [docs/azure-deployment.md](docs/azure-deployment.md) for full instructions.

---

## Quickstart: Running Locally

### 1. Prerequisites
- Python 3.11+
- Node.js (for syntax check validation)
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
JOOBLE_API_KEY=your_jooble_api_key_here
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
# Run 16 passing unit and integration tests
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

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
