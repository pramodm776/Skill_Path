# SkillPath AI

> **An AI Career Coach powered by verifiable portfolio evidence.**  
> Match a target role against what your code actually demonstrates—and see how that evidence changes with every GitHub commit.

[![CI](https://github.com/vedantsable56/Skill_Path/actions/workflows/ci.yml/badge.svg)](https://github.com/vedantsable56/Skill_Path/actions)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## The problem

Students and early-career developers often list skills on resumes, but recruiters have to inspect projects manually to verify them. Most AI career tools rely on keyword matching or generated claims, while portfolios become outdated as new work is pushed.

## Our solution

**SkillPath AI turns a GitHub portfolio into a traceable, continuously reassessed evidence ledger.** It compares job requirements with code from a bounded, read-only repository inspection, cites the evidence it finds, and tracks changes after new commits.

### What makes it different?

- **Evidence before claims:** skill status and fit scores are calculated by deterministic application logic—not decided by an LLM.
- **Traceable citations:** evidence can point to a repository file, line range, excerpt, and commit SHA.
- **Honest boundaries:** a missing signal is reported as **“not demonstrated in this inspected scope”**, not as proof that someone lacks the skill.
- **Proof Delta:** compare assessment snapshots to identify which requirement signals improved, regressed, or stayed unchanged.
- **Continuous reassessment:** GitHub push webhooks trigger updates, with background polling as a fallback.
- **Actionable next steps:** recommendations connect identified evidence gaps to concrete tasks a developer can implement.

## How it works

```text
Job posting / requirements
          |
          v
Read-only, bounded GitHub inspection
          |
          v
Deterministic skill assessment + cited evidence
          |
          v
Saved assessment snapshot
          |
     New GitHub commit
       /          \
 Push webhook   Polling fallback
       \          /
          v
   Reassessment of the commit
          |
          v
 Before/after Proof Delta + Telegram alert
```

## Key capabilities

| Capability | What it does |
|---|---|
| Job requirements | Accepts a job-posting URL and supports live job discovery through configured providers. The source URL is retained for traceability. |
| GitHub evidence inspection | Inspects public repositories through the GitHub API without cloning, installing, or executing repository code. Inspection is bounded by configured file and size limits. |
| Skill assessment | Applies deterministic rules to supported technologies and code signals; presents demonstrated, partial, and not-demonstrated statuses. |
| Evidence explorer | Shows validated code excerpts and their repository locations so a user can inspect why a signal was recognized. |
| Commit monitoring | Uses GitHub push webhooks and periodic polling to detect new commit SHAs and reassess tracked repositories. |
| Snapshot comparison | Compares stored assessments to show requirement-level changes and fit-score progression. |
| Telegram notifications | Sends assessment updates when enabled and configured. |
| Optional AI explanations | Can summarize validated results and suggest learning tasks. AI output does not create evidence citations or override deterministic statuses. |

## Product walkthrough

The presentation flow is designed around three stages:

1. **Setup** — choose a target role/job posting and connect the GitHub repository.
2. **Skill Analysis** — review the evidence-fit score, skill status breakdown, citations, and recommended next steps.
3. **Compare / Proof Delta** — compare commits and inspect newly demonstrated, improved, regressed, or unchanged requirement signals.

For a live demo, use a repository and job posting prepared in advance, capture the initial assessment, push a meaningful code change, then show the resulting reassessment and comparison. Avoid presenting a notification or comparison as live-tested unless it has been verified during rehearsal.

## Architecture

```text
Frontend: HTML + CSS + JavaScript
                 |
                 v
        FastAPI REST backend
          /      |       \
         v       v        v
 GitHub API   Assessment  Optional AI
              engine     explanations
                 |
                 v
          SQLite snapshots
                 |
        +--------+--------+
        |                 |
        v                 v
 GitHub webhook     Background polling
        \                 /
         v               v
        Proof Delta + Telegram alerts
```

### Technology stack

- **Frontend:** HTML5, CSS3, vanilla JavaScript, Chart.js
- **Backend:** Python 3.11, FastAPI
- **Persistence:** SQLite assessment snapshots
- **Integrations:** GitHub API/webhooks, Telegram Bot API, optional Jooble/JSearch job discovery
- **Optional AI:** OpenAI API for explanation and recommendation text; deterministic application logic remains authoritative
- **Deployment direction:** Firebase Hosting for the static frontend and Azure Container Apps for the continuously running backend/monitor

> **Deployment note:** the monitoring requirement needs a continuously running backend. A free service that sleeps when idle is not suitable for instant commit-trigger handling. The Azure deployment plan will keep at least one backend replica running and must use durable storage for production data.

## Run locally

### Prerequisites

- Python 3.11+
- Git
- Node.js (for the JavaScript syntax check)

### 1. Clone and install

```powershell
git clone https://github.com/vedantsable56/Skill_Path.git
cd Skill_Path

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the repository root. Add only the integrations you want to use.

```env
DATABASE_PATH=data/career_coach.sqlite3
SQLITE_JOURNAL_MODE=WAL
MONITORING_ENABLED=true
POLL_INTERVAL_SECONDS=10

# GitHub: recommended for higher API rate limits
GITHUB_TOKEN=

# Optional: verify GitHub push webhook signatures
GITHUB_WEBHOOK_SECRET=

# Optional AI explanations
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
ENABLE_LLM_EXPLANATIONS=false

# Optional job discovery
JOOBLE_API_KEY=
JOOBLE_API_URL=https://in.jooble.org/api
JSEARCH_API_KEY=
JSEARCH_API_URL=https://jsearch.p.rapidapi.com

# Optional Telegram notifications
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=
TELEGRAM_BOT_USERNAME=
TELEGRAM_NOTIFICATIONS_ENABLED=false
PUBLIC_BASE_URL=
```

**Never commit real API keys, bot tokens, webhook secrets, or other credentials.** Keep them in local environment configuration or your deployment platform's secret settings.

### 3. Seed example job roles (optional)

```powershell
python -m backend.seed_jobs
```

### 4. Start the application

```powershell
python -m uvicorn backend.main:app --reload --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Configuration and operational notes

- A GitHub token is optional for public repositories, but authenticated API access provides a higher rate limit.
- Configure a GitHub repository webhook to send `push` events to `/api/integrations/github/webhook` and set the matching webhook secret.
- Telegram alerts require a bot token, a linked chat, and notifications enabled.
- Job search and AI explanations are optional integrations; the core evidence assessment should remain usable without them.
- For hosted deployment, use server-side secrets and durable database storage. Do not assume a container's local filesystem survives replacement or restart.

## Tests and quality checks

Run from the repository root:

```powershell
pytest -q
python -m compileall -q backend
node --check frontend\script.js
```

The tests should use mocks for external services; do not send real Telegram messages or make paid API calls from the test suite.

## Presentation / pitch deck outline

This section can be used as a source for a hackathon presentation or PowerPoint deck.

1. **Title & vision** — SkillPath AI: evidence, not assumptions.
2. **Problem** — self-reported skills, manual portfolio review, and static feedback.
3. **Solution** — deterministic, traceable evidence from GitHub code.
4. **Workflow** — job requirements → bounded scan → assessment snapshot.
5. **Evidence experience** — status breakdown, cited excerpts, and recommendations.
6. **Continuous monitoring** — commit webhook with polling fallback.
7. **Proof Delta** — before/after comparison of requirement-level changes.
8. **Architecture & safeguards** — read-only inspection, bounded scanning, secret handling, and AI boundaries.
9. **Live demo** — baseline assessment, code change, reassessment, comparison, and Telegram alert.
10. **Roadmap** — stronger deployment reliability, expanded language/framework coverage, and recruiter-facing evidence reports.

Use verified screenshots and real test results in the final deck. Clearly label planned capabilities as roadmap items rather than implemented features.

## Documentation

- [Demo rehearsal guide](docs/demo-script.md)
- [Azure deployment guide](docs/azure-deployment.md)

## License

Licensed under the MIT License. See [LICENSE](LICENSE).
