# SkillPath AI — Comprehensive Live Demo & Rehearsal Script

> **Challenge:** W-PS-2 — AI Career Coach  
> **Pitch Differentiator:** A **career evidence ledger** that proves skills from real GitHub commits and job postings with deterministic citations and live Proof Deltas.

---

## 1. Pre-Demo Setup Checklist

### A. Environment Configuration (`.env`)
Create or verify `.env` in the repository root:
```env
GITHUB_TOKEN=ghp_your_github_token_here
MONITORING_ENABLED=true
POLL_INTERVAL_SECONDS=10

# Optional providers (demo works 100% deterministically without them):
# OPENAI_API_KEY=sk-...
# GITHUB_WEBHOOK_SECRET=your-secret
# TELEGRAM_BOT_TOKEN=...
```

### B. Start the Service
```powershell
# From the repository root:
uvicorn backend.main:app --reload --port 8000
```
Open **`http://127.0.0.1:8000`** in your browser. Verify the green topbar indicator: `Monitoring active (10s poll)`.

---

## 2. Prepared Demo Data

### Recommended Public Job Posting

**Job Title:** `Backend Software Engineer (Python / FastAPI)`  
**Company:** `Example Tech Labs`  
**Source URL:** `https://jobs.example.org/backend-engineer-python`  
**Job Description:**
```text
We are seeking a Backend Software Engineer to build resilient APIs and microservices.

Requirements:
- Strong proficiency in Python and FastAPI for REST API development.
- Hands-on experience with SQL databases, schema design, and parameterized queries.
- Commitment to automated testing with Pytest, unit tests, and CI/CD automation.
- Familiarity with Docker containerization and clean software architecture.
```

### Controlled GitHub Repository
Use a public GitHub repository under your control (e.g. `https://github.com/<your-username>/skillpath-demo-portfolio`).

**Initial State:** Contains only basic Python and FastAPI route code in `server.py`:
```python
from fastapi import FastAPI

app = FastAPI(title="Demo Service")

@app.get("/api/items")
def list_items():
    return [{"id": 1, "name": "sample"}]
```
*(Notice: no SQL, no Pytest tests yet).*

**Second State (The Live Commit to Push During Demo):** Add SQL and tests:
```python
import sqlite3
import pytest

def get_db():
    conn = sqlite3.connect("data.db")
    return conn

def test_items_route():
    assert True
```

---

## 3. Five-Minute Live Demo Flow

### Step 1: Ingest Job Requirements (45 Seconds)
1. **Show Saved Jobs:** Click the "Saved job postings" dropdown to show pre-loaded jobs.
2. **Or Ingest New Job:** Fill in Title, Company, Source URL, and paste the job description above.
3. Click **"Save job posting"**.
4. **Point to the Screen:**
   - Notice the extracted skill requirement badges: `Python`, `FastAPI`, `SQL Databases`, `Automated Testing`, `Docker`.
   - Point out that every requirement cites the exact excerpt from the posting text.
   - Emphasize: *Company context is optional, but the source URL is mandatory and traceable.*

### Step 2: Connect Repository & Initial Assessment (75 Seconds)
1. In the **Repository** panel, paste the URL of your controlled GitHub repository.
2. Click **"Connect repository"**.
3. **Walk Through the Findings:**
   - **Fit Score:** e.g., 40% (2 of 5 requirements demonstrated).
   - **Demonstrated Skills (`Python`, `FastAPI`):** Click each card to reveal the evidence citation — exact file path (`server.py`), 1-indexed line numbers, and bounded code excerpt.
   - **Missing Evidence (`SQL Databases`, `Automated Testing`):**
     > **Key Speaking Point:** *"Notice the wording: **'not demonstrated in this inspected scope'**. We never say the engineer doesn't know SQL. We say the inspected repository hasn't proven it yet. That distinction is critical for trust."*

### Step 3: Trigger Live Reassessment (60 Seconds)

Choose **Method A** (Webhook), **Method B** (Live Git Push), or **Method C** (Fast Rehearsal Simulation):

#### Method A: Live Git Push (Default)
In your terminal inside the controlled demo repo:
```bash
# Add SQL and automated testing code to server.py or test_server.py
git add .
git commit -m "feat: add sqlite database connection and pytest test suite"
git push origin main
```
Watch the SkillPath AI dashboard:
- Within 10 seconds, the monitor detects the new commit SHA.
- The history panel appends a new snapshot automatically.

#### Method B: GitHub Push Webhook (Instant)
If using GitHub webhook with ngrok or localtunnel (`/api/integrations/github/webhook`):
- The push triggers immediate reassessment without waiting for the 10s poll cycle!

#### Method C: Fast Webhook Simulation (For rehearsal without network push)
Run this PowerShell command in another window:
```powershell
$payload = @{
    ref = "refs/heads/main"
    after = "2222222222222222222222222222222222222222"
    repository = @{
        full_name = "<your-username>/skillpath-demo-portfolio"
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/integrations/github/webhook" -Method Post -ContentType "application/json" -Headers @{"X-GitHub-Event"="push"} -Body $payload
```

### Step 4: Highlight the Proof Delta (60 Seconds)
1. Click **"Compare"** on the latest snapshot in the History panel.
2. **Show the Evidence Changes Panel:**
   - **Fit Score Delta:** Increased from 40% → 80% (+40%).
   - **Gained Evidence:** `SQL Databases` and `Automated Testing` show new green citations linking to the exact lines added in the commit.
   - **Changed Files Metadata:** Lists modified files and commit URL.
   - Emphasize: *This is the **Proof Delta**. Instead of reviewing an entire repository from scratch, an applicant or employer sees exactly what proof was gained with each commit.*

### Step 5: Duplicate SHA Suppression & Guardrails (30 Seconds)
1. Click **"Check monitor now"** without pushing any new commit.
2. Show that **no duplicate snapshot** is created. History count remains identical.
3. Show the **Interactive API Docs** link (`/docs`) in the footer for judges who want to inspect the REST API contracts.

---

## 4. Judge Q&A Cheat Sheet

| Question | Winning Answer |
|---|---|
| **Why not let an LLM read and grade the whole repo?** | *"LLMs are prone to hallucination, sycophancy, and variable grading. SkillPath AI uses a **bounded deterministic AST scanner** for fact-checking. Every single proof citation must point to a real file, line range, and code snippet. If LLM explanations are enabled, they only summarize verified evidence — they cannot invent skills or citations."* |
| **What happens if someone puts keywords in comments or README?** | *"Our skill rules specifically filter out comments, string literals, and documentation files. Evidence requires substantive syntax — e.g. for Automated Testing, both a test declaration AND an assertion statement must be present."* |
| **How does this scale with GitHub rate limits?** | *"Inspections are bounded: max 20 files, 100 KB per file, 500 KB total. We inspect git trees and files directly via GitHub REST API without cloning. New commits are checked via 1-call SHA comparison, keeping API calls minimal. Webhooks provide instant zero-polling updates."* |
| **Why 'not demonstrated' instead of 'lacks skill'?** | *"Fairness and ethical AI. Code repositories only represent bounded public evidence. A student might know Docker from class without having a Dockerfile in this repo. Stating 'not demonstrated in this inspected scope' is factual and defensible."* |
| **Can you track multiple jobs or repos?** | *"Yes! The SQLite schema supports multiple jobs and multiple repositories. The push webhook looks up all monitored repositories matching the pushed repo and updates all connected jobs simultaneously."* |

---

## 5. Rehearsal Verification Script

Before presenting, run the automated merge gate to verify that all 13 tests and compilation passes:

```powershell
python -m pytest -q
python -m compileall -q backend
node --check frontend\script.js
```
Expected output:
```text
.............
13 passed in 3.5s
```
