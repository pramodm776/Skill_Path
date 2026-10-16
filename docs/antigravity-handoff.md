# SkillPath AI — complete end-to-end handoff for Antigravity

This is the operational handoff for an Antigravity IDE assistant or teammate. Read it completely before proposing changes, running deployments, or editing cross-cutting files.

**Project:** SkillPath AI  
**Challenge:** W-PS-2 — AI Career Coach  
**Repository:** `https://github.com/vedantsable56/Skill_Path.git`  
**Workspace:** `C:\Users\HP\OneDrive\Desktop\hackathon-project`

## 0. Immediate instruction for Antigravity

Use this sequence at the beginning of every task:

1. Read `AGENTS.md`, this document, and `docs/team-context.md`.
2. Run `git status --short` before editing anything.
3. Preserve all unrelated uncommitted work. Never use `git reset --hard`, `git checkout --`, or a broad `git add .`.
4. Keep all provider credentials in `.env` or Azure secrets. Never read secret values into chat, source code, logs, tests, documentation, browser JavaScript, or Git.
5. Do not clone, execute, import, install, or run code from an inspected GitHub repository. The GitHub integration is strictly read-only.
6. Before changing an API contract, persistence shape, security boundary, or demo step, update the relevant documentation and tests in the same focused change.

The technical non-negotiable is:

```text
real job source → real GitHub evidence → careful gap wording
→ real default-branch commit → automatic reassessment → evidence delta
```

Never describe missing evidence as a student lacking a skill. The required wording is:

> **not demonstrated in this inspected scope**

---

## 1. Current repository and worktree state

### Published baseline

- Current local branch: `feature/skillpath-mvp`
- Published feature branch: `origin/feature/skillpath-mvp`
- Baseline commit: `ada8e4d feat: deliver SkillPath AI evidence workflow`
- The remote repository began empty. From this workspace, `main` has not been initialized because direct pushes require the repository owner’s explicit approval. Before acting on this status, verify it with `git ls-remote --heads origin`; do not force-push or bypass the pull-request workflow.

### Uncommitted work that must be preserved

At the time of this handoff, these changes are intentionally uncommitted:

| Path | Purpose |
| --- | --- |
| `backend/main.py` | Makes job `company` optional and stores `Company not specified` when absent. |
| `frontend/index.html` | Clarifies optional company and source-URL traceability in the job form. |
| `frontend/script.js` | Allows an empty company while keeping source URL and title required. |
| `docs/api-contracts.md` | Documents `company?` and required `source_url`. |
| `tests/test_evidence_and_monitoring.py` | Adds coverage for blank company and required source URL. |
| `docs/ppt-generation-context.md` | Judge-safe PPT source material and a copy-ready ChatGPT presentation prompt. |
| `docs/antigravity-handoff.md` | This handoff document. |

The local folder `Actual Problem Statement/` is intentionally untracked. Do not stage, move, delete, or include it in a code commit unless the repository owner explicitly asks.

### Current validation after the company UX update

```text
10 passed
```

The following also passed after the update:

```powershell
python -m compileall -q backend tests
node --check frontend\script.js
git diff --check
```

---

## 2. What SkillPath AI is

SkillPath AI is an **evidence-first AI Career Coach**. It compares requirements from a real public job or internship posting against skills that are demonstrably present in a real GitHub repository.

It is not a static resume analyzer and it is not a generic chatbot. The product stores an immutable assessment for each inspected commit SHA, then reassesses automatically when the repository’s default branch changes.

### Product promise

For each skill, the product can show:

- requirement source excerpt;
- assessment status;
- evidence file path;
- line range and code excerpt;
- inspected commit SHA and public commit link;
- confidence and limitations;
- careful gap explanation;
- a future-only task that could produce better evidence.

### The differentiator: Proof Delta

After a real commit, **Proof Delta** compares the previous and new snapshots. It shows exactly which requirement gained/lost evidence, what files changed, which evidence excerpts changed, and what the new commit proves or does not prove.

---

## 3. Architecture and runtime flow

```text
Browser dashboard (vanilla HTML/CSS/JavaScript)
  │  same-origin requests, no credentials
  ▼
FastAPI application
  ├─ job intake and conservative skill normalization
  ├─ optional JSearch discovery
  ├─ GitHub REST inspection (read-only and bounded)
  ├─ deterministic evidence extraction and validation
  ├─ SQLite snapshots/history/events
  ├─ commit-SHA polling monitor
  ├─ optional OpenAI explanation
  │    └─ optional xAI/Grok fallback on retryable OpenAI failures only
  └─ optional Telegram pairing and reassessment alert
```

### The end-to-end lifecycle

1. A user saves a title, optional company, required public source URL, and job description.
2. Directly mentioned supported skill phrases are normalized; their source excerpts are retained.
3. The user connects a GitHub repository URL.
4. The backend reads metadata, default branch, SHA, tree, and a bounded set of safe text files using GitHub REST APIs.
5. Deterministic rules inspect non-comment source/configuration lines. Every candidate citation is validated against the inspected content.
6. SQLite stores the first immutable snapshot, keyed by repository and commit SHA.
7. The monitor polls the default branch. A duplicate SHA does nothing.
8. A new SHA triggers comparison where possible, exact-SHA inspection, a new snapshot, an automatic event, and Proof Delta.
9. If Telegram is paired and enabled, it receives at most one short alert for that automatic new-SHA reassessment.

---

## 4. The LLM and agentic-workflow boundary

### Correct project description

SkillPath AI uses a **bounded deterministic orchestration workflow**, not an autonomous multi-agent swarm.

```text
job normalizer
  → GitHub inspector
  → evidence validator
  → deterministic assessor
  → SQLite snapshot store
  → SHA monitor
  → Proof Delta comparison
  → optional LLM explanation
```

The named stages are predictable program components. They are not independent LLM agents making unreviewable decisions.

### OpenAI and xAI/Grok role

The core product works without any LLM credential.

When `ENABLE_LLM_EXPLANATIONS=true` and an OpenAI key exists, the backend may ask OpenAI to phrase a short explanation of evidence that has already been verified. It sends only job title/company, requirement excerpts, deterministic statuses, and up to two validated evidence excerpts per skill.

xAI/Grok is a fallback only when all of the following are true:

1. OpenAI was enabled;
2. the OpenAI failure is transient/retryable (network, timeout, 408/409/429, or 5xx);
3. `ENABLE_XAI_FALLBACK=true`;
4. xAI key and model are configured.

OpenAI authentication, validation, or configuration failures do **not** fail over.

### Hard LLM constraints

The LLM must never:

- invent a requirement;
- create evidence paths, line references, excerpts, or SHAs;
- change a deterministic status or score;
- make hiring, authorship, or competency claims;
- receive credentials or an uninspected full repository.

Judge-ready wording:

> “The deterministic verifier decides what the repository proves. The LLM is optional and only explains already-validated evidence in plain language.”

---

## 5. Folder map and ownership

```text
hackathon-project/
├── AGENTS.md                         # mandatory working rules
├── README.md                         # local setup, feature overview, demo instructions
├── .env.example                      # blank placeholders only
├── Dockerfile                        # application container
├── frontend/
│   ├── index.html                    # dashboard structure
│   ├── style.css                     # responsive dashboard styling
│   └── script.js                     # frontend state and same-origin API calls
├── backend/
│   ├── main.py                       # FastAPI routes, request validation, static serving
│   ├── config.py                     # server-side environment configuration
│   ├── errors.py                     # safe application/GitHub errors
│   ├── github_client.py              # bounded read-only GitHub REST inspection
│   ├── skills.py                     # evidence patterns, validation, comparisons
│   ├── storage.py                    # SQLite data store
│   ├── monitor.py                    # SHA polling and automatic reassessment
│   ├── job_search.py                 # optional JSearch provider
│   ├── llm.py                        # optional controlled LLM interpretation
│   ├── telegram.py                   # Telegram pairing/notification logic
│   ├── telegram_setup.py             # secure operator webhook setup command
│   └── requirements.txt              # Python dependencies
├── tests/
│   ├── test_evidence_and_monitoring.py
│   └── test_optional_integrations.py
├── docs/
│   ├── team-context.md               # concise shared rules and ownership
│   ├── architecture.md                # component/data-flow detail
│   ├── api-contracts.md               # request/response contract summary
│   ├── decisions.md                   # key engineering trade-offs
│   ├── demo-script.md                 # five-minute judge demo
│   ├── azure-deployment.md            # exact Azure steps and caveats
│   ├── ppt-generation-context.md      # presentation source material
│   └── antigravity-handoff.md         # this document
├── infra/
│   ├── foundation.bicep               # ACR, Container Apps environment, Azure Files, identity
│   └── app.bicep                      # single-replica Container App
└── .github/workflows/ci.yml           # test workflow
```

### Ownership boundaries

| Area | Primary files | Do not break |
| --- | --- | --- |
| GitHub and monitoring | `github_client.py`, `monitor.py`, `storage.py` | Read-only access, default-branch SHA detection, immutable history, duplicate suppression. |
| Assessment integrity | `skills.py`, `llm.py` | Evidence must resolve to inspected path/lines/excerpt; LLM cannot create proof. |
| API integration | `main.py`, `api-contracts.md` | Safe validation/error format and server-side-only credentials. |
| Dashboard | `frontend/` | No browser keys; calls must remain same-origin. |
| Tests/demo | `tests/`, `demo-script.md`, `README.md` | Only report executed tests and real demo outcomes. |
| Job/Telegram integrations | `job_search.py`, `telegram.py`, `telegram_setup.py` | Provider keys/chat IDs never reach the browser. |
| Azure | `Dockerfile`, `infra/`, `azure-deployment.md` | One replica while SQLite is used; do not claim deployment without proof. |

---

## 6. Job-source UX and API rules

### Company is optional

The current UX/API decision is deliberate:

- `title` is required;
- `company` is optional display context;
- if omitted, backend storage uses `Company not specified`;
- JSearch fills company when its result includes one;
- company does not affect evidence extraction or score calculation.

### Source posting URL is required

The official problem requires retention of a real job/internship source URL. The URL is the traceability anchor for the job requirements.

- For manual entry, the user must paste the public source URL.
- For JSearch, choosing a search result fills the URL, title, company when available, and description in the form.
- A JSearch result is never persisted automatically: the user must review the candidate and click Save.
- The URL may be from a public company careers page or a public job board, provided it is a real public posting link.

Do not remove URL retention or make it silently generated; that would violate the problem statement and weaken the evidence trail.

---

## 7. Local development setup

### Important frontend rule

Do **not** double-click `frontend/index.html` or use a standalone Live Server. The HTML expects `/static/...` assets and `/api/...` routes from FastAPI.

Run the application, then browse to:

```text
http://127.0.0.1:8000/
```

### Windows PowerShell commands

```powershell
cd "C:\Users\HP\OneDrive\Desktop\hackathon-project"

# Create only if .venv does not already exist.
py -3.11 -m venv .venv

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install --no-cache-dir -r requirements.txt

# Create only if .env does not already exist; never overwrite a populated .env.
if (-not (Test-Path .env)) { Copy-Item .env.example .env }

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Expected server success text includes:

```text
Application startup complete.
```

Health endpoint:

```text
http://127.0.0.1:8000/api/health
```

### Recovery for a broken virtual environment

If startup fails with:

```text
ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'
```

stop Uvicorn, recreate only `.venv`, and reinstall dependencies. Do not delete `.env`.

```powershell
deactivate
Remove-Item -Recurse -Force .venv
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --no-cache-dir -r requirements.txt
python -c "import pydantic_core; print('pydantic-core OK:', pydantic_core.__version__)"
```

---

## 8. Environment variable contract

Never include actual values in source, documentation, tickets, images, or chat. Use `.env.example` for names and blank placeholders.

### Minimum local demo configuration

```text
POLL_INTERVAL_SECONDS=10
MONITORING_ENABLED=true
```

Public GitHub repositories work without a token. Add a fine-grained, read-only GitHub token only for private repositories or better rate limits.

### Optional server-side integrations

| Configuration | Purpose | Enable only when |
| --- | --- | --- |
| `GITHUB_TOKEN` | Private repo access / improved GitHub limits | A read-only fine-grained token has been configured server-side. |
| `JSEARCH_API_KEY` | India-friendly job discovery | The team wants to demonstrate live job search. |
| `OPENAI_API_KEY` + `ENABLE_LLM_EXPLANATIONS=true` | Secondary evidence explanation | Core deterministic demo has already passed. |
| `XAI_API_KEY`, `XAI_MODEL`, `ENABLE_XAI_FALLBACK=true` | Controlled fallback | OpenAI fallback behavior needs to be shown. |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_NOTIFICATIONS_ENABLED=true` | Optional Proof Delta alert | Public HTTPS deployment and bot setup are ready. |
| `PUBLIC_BASE_URL`, `TELEGRAM_BOT_USERNAME` | Telegram deep links/webhook setup | Azure URL and bot name are known. |
| `AZURE_KEY_VAULT_URL`, `APPLICATIONINSIGHTS_CONNECTION_STRING` | Azure deployment/observability | Deployment is underway. |

---

## 9. API contract summary

All safe API errors follow this shape:

```json
{
  "error": {
    "code": "machine_readable_code",
    "message": "Safe message for the dashboard",
    "details": null
  }
}
```

| Route | Function |
| --- | --- |
| `GET /api/health` | Health and non-secret integration status. |
| `POST /api/jobs` | Save `{title, company?, source_url, description}`. Source URL is required; company is optional. |
| `POST /api/jobs/fetch` | User-triggered best-effort public-page text extraction. |
| `POST /api/job-search` | Optional JSearch discovery; results are review-only until saved. |
| `POST /api/repositories` | Inspect real GitHub repository and create initial snapshot. |
| `POST /api/repositories/{id}/scan` | Explicit manual scan; does not duplicate existing SHA. |
| `GET /api/repositories/{id}/monitor` | Monitor state, timestamps, safe error events. |
| `POST /api/repositories/{id}/monitor/check` | Runs the same change-detection path immediately. |
| `GET /api/repositories/{id}/history` | Immutable snapshot summaries. |
| `GET /api/assessments/{current}/compare/{previous}` | Evidence/status Proof Delta. |
| `POST /api/repositories/{id}/telegram/pair` | Create a one-time expiring Telegram pairing command. |
| `POST /api/integrations/telegram/webhook` | Authenticated Telegram webhook; accepts only pairing/stop commands. |

Read `docs/api-contracts.md` before changing an endpoint.

---

## 10. Tests and quality gate

Run these from the project root with the virtual environment active:

```powershell
python -m pytest -q
python -m compileall -q backend tests
node --check frontend\script.js
git diff --check
```

Current automated coverage verifies:

- retained source URL;
- validated evidence file paths, excerpts, and lines;
- fabricated excerpt rejection;
- missing-evidence scope wording;
- comments not counted as implementation proof;
- new-SHA automatic reassessment;
- changed-file and evidence-delta storage;
- duplicate-SHA suppression;
- GitHub rate-limit behavior;
- JSearch key isolation and review-before-save behavior;
- controlled OpenAI/xAI fallback behavior;
- Telegram pairing, webhook authentication, and notification deduplication;
- optional company with required traceable source URL.

Tests do not replace the required final live GitHub commit rehearsal.

---

## 11. Required live demo rehearsal

This is the judge-critical sequence. Complete it before marking the MVP finished.

### Preparation

1. Start SkillPath AI with `POLL_INTERVAL_SECONDS=10` and `MONITORING_ENABLED=true`.
2. Choose a public GitHub repository controlled by the team.
3. Make sure its **default branch** has an initial commit that demonstrates some, but not all, selected job skills.
4. Choose a real public role whose actual description mentions the planned skills, such as Python, FastAPI/API work, SQL, and automated tests.

### Initial snapshot

1. Save the real job URL and actual description in the dashboard.
2. Connect the controlled public repository.
3. Show the initial SHA, inspection bounds, evidence cards, and at least one accurately worded gap.
4. Capture a screenshot for the presentation.

### Meaningful external repository commit

Choose a gap shown by the initial assessment and implement it genuinely. Examples:

| Existing gap | Meaningful follow-up commit |
| --- | --- |
| Testing | Add a real `pytest` test with assertion(s). |
| FastAPI | Add an actual route/endpoint and server implementation. |
| SQL | Add a parameterized query or real ORM/database operation. |
| RAG | Add vector-store plus retriever/use of retrieval result in non-comment code. |
| OpenAI integration | Add a server-side OpenAI client integration without exposing a key. |

Do not add comments claiming a skill. Comment-only claims are intentionally ignored.

Push the actual change to the repository’s **default branch**:

```powershell
git add <specific changed files>
git commit -m "Add verified evidence for <skill>"
git push
```

### Automatic proof

1. Do not press a manual Analyse button.
2. Wait for the server poll (normally 10–20 seconds in demo configuration).
3. Verify a new SHA, an automatic reassessment event, a second history snapshot, changed-file metadata, and Proof Delta.
4. Poll again with no new commit. History must not grow; this proves duplicate suppression.
5. Capture before/after screenshots.

`Check monitor now` is acceptable for a short demo only because it executes the same change-detection code path; it is not a manual assessment rewrite.

---

## 12. JSearch, OpenAI/xAI, and Telegram rehearsal order

Do not attempt every integration at once.

1. **Core GitHub loop first:** manual job URL/text, public repo, real commit, automatic reassessment.
2. **JSearch:** enter a server-side JSearch key, search an India location, choose a result, verify URL/text prefill, review it, and save manually.
3. **OpenAI:** set `ENABLE_LLM_EXPLANATIONS=true`, restart, and verify an optional explanation appears without changing evidence/states.
4. **xAI fallback:** test only if needed and only with a configured xAI model; do not induce an auth failure because auth errors must not fail over.
5. **Telegram:** configure only after a public HTTPS Azure URL exists. Pair through the dashboard, push a new default-branch commit, and verify one short alert.

If an optional provider is unavailable, the app must keep working in deterministic mode. Show this as resilience, not as an error.

---

## 13. Docker and Azure plan

### Deployment choice

Deploy frontend and backend together as one FastAPI container on Azure Container Apps. Do not split the frontend to Firebase for this MVP; same-origin serving avoids CORS complexity and keeps credentials entirely server-side.

### Azure profile

- One Container Apps replica is intentional.
- Azure Files mounts SQLite data at `/app/data`.
- Container App uses `SQLITE_JOURNAL_MODE=DELETE` for SMB/Azure Files compatibility.
- Azure Container Registry builds/pulls the image through a user-assigned identity.
- Log Analytics provides operational logs.

This is a hackathon deployment profile. Use PostgreSQL before any multi-replica/production scale-out.

### Deployment order

1. Start Docker Desktop only if building locally; Azure Container Registry build can build remotely.
2. Sign in to Azure and create a budget alert before creating resources.
3. Deploy `infra/foundation.bicep`.
4. Build the Docker image in ACR.
5. Deploy `infra/app.bicep` with one replica.
6. Test `$appUrl/api/health`.
7. Add only required integration secrets through Container Apps secrets/Key Vault.
8. Configure `PUBLIC_BASE_URL` after the app URL is known.
9. Rehearse the real commit flow against Azure.
10. Remove the test resource group only after preserving required evidence; deletion is destructive.

Use the exact PowerShell commands in `docs/azure-deployment.md`. Do not run cloud-creation commands without the repository owner’s approval, subscription choice, and budget awareness.

---

## 14. Git and collaboration workflow

### Before the remote `main` branch exists

The published baseline is currently `feature/skillpath-mvp`. Do not attempt to create/force a remote main branch without explicit approval from the repository owner.

### After `main` is initialized

Each teammate should use:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feature/<area>-<summary>
```

Rules:

- One concern per branch and commit.
- Never commit `.env`, `data/*.sqlite3`, generated Bicep JSON, secrets, or `Actual Problem Statement/`.
- Never force-push.
- Stage named paths only; do not use broad `git add .`.
- Open a pull request into `main` only after the test gate passes.
- Resolve cross-cutting conflicts with the release owner before editing another person’s core files.

### Suggested team division

| Owner | Responsibilities |
| --- | --- |
| Release owner | Secrets, branch/main coordination, final integration, live demo, Azure approval/deploy, presentation proof. |
| Frontend owner | Dashboard polish, accessibility, responsive testing, safe empty/loading/error states. |
| Demo/test owner | Controlled GitHub demo repository, real posting selection, regression tests, screenshots, narration rehearsal. |
| Cloud/integration owner | Docker validation, Azure Bicep deployment, Key Vault/Container Apps secrets, optional Telegram setup. |

---

## 15. Presentation rules

The presentation source is in `docs/ppt-generation-context.md`.

The PPT can accurately claim:

- evidence-backed matching with paths/lines/excerpts/SHAs;
- automatic SHA-based reassessment design and tested behavior;
- optional controlled LLM explanation;
- one-service Azure deployment templates;
- passed automated tests, if the latest test run is shown truthfully.

The PPT must not claim, until real evidence exists:

- Azure is deployed;
- Telegram alerts were sent;
- JSearch/OpenAI/xAI live calls succeeded;
- accuracy percentage, hiring success, user count, time savings, or any invented metric;
- authorship, proficiency, or hiring suitability conclusions;
- an autonomous multi-agent swarm.

Prefer actual screenshots of source URL, commit SHA, evidence card, new automatic event, and Proof Delta over generic AI imagery.

---

## 16. Final release checklist

Before calling the project complete, check every item:

- [ ] Current worktree reviewed; no unrelated changes overwritten.
- [ ] All intended source/docs/tests changes committed on a focused branch.
- [ ] `.env`, databases, generated assets, tokens, and problem-statement attachment excluded from Git.
- [ ] `python -m pytest -q` passes.
- [ ] Python compilation, JavaScript syntax, and `git diff --check` pass.
- [ ] Browser loads through FastAPI at `http://127.0.0.1:8000/`.
- [ ] Real public job source URL and description are saved.
- [ ] Real public controlled GitHub repository is inspected.
- [ ] Initial evidence paths, excerpts, lines, and SHA are shown.
- [ ] A meaningful real default-branch commit is pushed.
- [ ] The monitor automatically detects a new SHA and creates exactly one new snapshot.
- [ ] Proof Delta shows changed evidence and correct bounded-scope language.
- [ ] The no-change monitor check does not create a duplicate snapshot.
- [ ] Optional provider claims in the PPT match actual completed tests.
- [ ] Azure/Telegram are demonstrated only if actually deployed/configured.
- [ ] Screenshots and demo narration use real data and never reveal secrets.

---

## 17. Useful prompt for Antigravity

Use the following as the first task prompt in Antigravity:

```text
You are continuing the SkillPath AI hackathon MVP in this repository. First read AGENTS.md, docs/antigravity-handoff.md, docs/team-context.md, docs/api-contracts.md, and git status. Preserve existing uncommitted work and do not reset, overwrite, stage broadly, or expose any .env values. The product must remain one FastAPI service with SQLite and vanilla HTML/CSS/JavaScript. GitHub inspection is read-only and evidence must resolve to actually inspected file path, line range, excerpt, and commit SHA. Missing evidence must always be described as “not demonstrated in this inspected scope.” Before changing an API, persistence, security, or demo behavior, state the targeted files and validation plan. Implement only the requested scoped task, run relevant tests, report real results, and do not claim live provider/deployment success without executing it.
```
