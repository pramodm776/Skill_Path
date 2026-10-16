# SkillPath AI

SkillPath AI is a working 24-hour hackathon MVP that keeps a portfolio-vs-job assessment current as a real GitHub repository changes.

It is built for the required loop:

```text
real job posting -> GitHub repository evidence -> transparent gaps
-> real pushed commit -> automatic reassessment -> before/after evidence
```

The product is intentionally conservative: no evidence is ever treated as proof that a student lacks a skill. It is shown as **not demonstrated in this inspected scope**.

## What works

- Saves a job title, optional company context, real public source URL, and pasted description. There is also a best-effort page-text fetch helper; pasted text remains the reliable fallback.
- Normalizes only directly mentioned, supported skills and retains the original job-description excerpt.
- Uses the real GitHub REST API for public repositories and server-side-token private repositories.
- Reads the default branch, commit SHA/link, tree, and a bounded subset of text files without cloning or executing repository code.
- Filters binary, generated, minified, dependency, lock, and likely secret files, and records the inspection scope/limits.
- Produces per-skill evidence with file path, line range, excerpt, commit SHA, confidence, limitations, and careful gap wording.
- Persists immutable SQLite snapshots. A unique repository/SHA constraint prevents duplicate snapshots.
- Runs a server-side polling monitor that detects a new default-branch commit, obtains changed files where GitHub permits it, automatically reassesses the exact new SHA, and records an event.
- Includes a responsive vanilla HTML/CSS/JS dashboard with evidence cards, monitor state, history, before/after comparison, loading/error states, and future-only recommendations.
- Supports optional JSearch discovery with India queries. Search results only prefill a review step; the selected direct posting URL and description are still explicitly saved.
- Adds a Proof Delta on comparison: changed evidence, status transitions, claim boundary, and a clearly labelled future evidence task.
- Works without an LLM key in labelled deterministic mode. OpenAI interpretation is opt-in; xAI/Grok is a controlled fallback only after retryable OpenAI failures and neither provider can create evidence citations or statuses.
- Supports opt-in Telegram pairing and one concise automatic-reassessment alert per new snapshot. It stores only a one-time pairing-code hash and never sends source excerpts or credentials to Telegram.
- Includes a Docker image and Azure Container Apps Bicep deployment profile for one same-origin service; see [docs/azure-deployment.md](docs/azure-deployment.md).

## Stack

- Frontend: HTML, CSS, vanilla JavaScript
- Backend: Python and FastAPI
- Data: SQLite
- Repository access: GitHub REST API via `httpx`
- Optional interpretation: OpenAI Responses API, controlled xAI Responses fallback, server-side only
- Optional discovery/alerts: JSearch via RapidAPI and Telegram Bot API, server-side only

## Run locally on Windows PowerShell

From the workspace root:

```powershell
cd "C:\Users\HP\OneDrive\Desktop\hackathon-project"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

If PowerShell blocks activation in this one session, run this first:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Stop the server with `Ctrl+C`.

Run tests from the same activated environment:

```powershell
cd "C:\Users\HP\OneDrive\Desktop\hackathon-project"
python -m pytest -q
```

## Environment variables

Copy `.env.example` to `.env`; it contains placeholders only.

| Variable | Required? | Meaning |
| --- | --- | --- |
| `DATABASE_PATH` | No | SQLite path. Default: `data/career_coach.sqlite3`. |
| `SQLITE_JOURNAL_MODE` | No | `WAL` locally; Azure's single-replica Azure Files template uses `DELETE`. |
| `GITHUB_TOKEN` | Public repos: no; private repos: yes | Fine-grained, read-only token held only by the server. It also improves API rate limits. |
| `GITHUB_API_URL` | No | GitHub REST origin. Default: `https://api.github.com`. |
| `GITHUB_TIMEOUT_SECONDS` | No | Per-request GitHub timeout. |
| `GITHUB_MAX_FILES` | No | Maximum eligible files read per assessment (default `20`, deliberately bounded for unauthenticated GitHub limits). |
| `GITHUB_MAX_FILE_BYTES` | No | Maximum bytes for one eligible file. |
| `GITHUB_MAX_TOTAL_BYTES` | No | Maximum total inspected bytes. |
| `POLL_INTERVAL_SECONDS` | No | Repository polling cadence. Set to `10` for the demo; default is `60`. |
| `MONITORING_ENABLED` | No | Enables the background polling loop. |
| `OPENAI_API_KEY` | No | Server-only key for optional interpretation. |
| `OPENAI_MODEL` | No | Optional interpretation model. |
| `ENABLE_LLM_EXPLANATIONS` | No | Set `true` only when you want job excerpts and already-validated evidence excerpts sent to OpenAI. |

### Optional server-side integrations

Add a value only to local `.env` or an Azure Key Vault-backed app setting; never commit it to `.env.example`. A value alone does not make a provider active: the matching feature flag must also be enabled.

| Variable | Purpose |
| --- | --- |
| `JSEARCH_API_KEY`, `JSEARCH_API_URL`, `JSEARCH_TIMEOUT_SECONDS` | Optional server-side JSearch discovery. The selected result must still retain its real posting URL and reviewed description. |
| `XAI_API_KEY`, `XAI_API_URL`, `XAI_MODEL`, `ENABLE_XAI_FALLBACK` | Controlled Grok/xAI fallback after an eligible transient OpenAI failure. It cannot alter deterministic evidence. |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_API_URL`, `TELEGRAM_NOTIFICATIONS_ENABLED`, `TELEGRAM_BOT_USERNAME`, `PUBLIC_BASE_URL` | Opt-in webhook, expiring pairing, and automatic Proof Delta alerts. Chat IDs/tokens never enter frontend responses. |
| `AZURE_KEY_VAULT_URL`, `APPLICATIONINSIGHTS_CONNECTION_STRING` | Azure deployment configuration. Use managed identity and Key Vault rather than an Azure client secret. |

For Azure Container Apps, mount the SQLite directory through the platform and set `DATABASE_PATH` to that mounted path. The provided template intentionally restricts the app to one always-on replica; read [docs/azure-deployment.md](docs/azure-deployment.md) before deployment.

Never put a token in the browser, a repository URL, or a commit message. `.env` is ignored by Git.

## Demo a real automatic reassessment

1. Create or choose a **public GitHub repository you control**. Commit and push an initial version with an API route but no SQL-query/test evidence.
2. Start this app with `POLL_INTERVAL_SECONDS=10`.
3. In the dashboard, paste a **real public job or internship posting URL** and its actual requirements. Use a role that explicitly mentions APIs, SQL, and automated testing if those are the planned demo signals.
4. Connect your real repository URL. Show the initial snapshot, commit link, evidence paths/excerpts, and the accurate SQL/testing gap wording.
5. Make a genuine follow-up change in the external demo repository (for example, add a parameterized `SELECT` query and a test with an assertion), then push it:

   ```powershell
   cd "C:\path\to\your-controlled-demo-repository"
   git add .
   git commit -m "Add query and automated test evidence"
   git push
   ```

6. Do not press a manual Analyse button. Wait for the server poll. The dashboard should show a new SHA, an **Automatic reassessment** event, a new snapshot, and a before/after comparison of validated evidence.
7. Poll again with no new commit. The monitor reports no change and history remains at the same number of snapshots.

For a compressed live demo, **Check monitor now** calls the polling/change-detection code path; it does not manually rewrite an assessment.

The fuller judge-facing flow is in [docs/demo-script.md](docs/demo-script.md).

## Evidence and score semantics

The engine uses direct, deterministic source/configuration patterns. It ignores comments for code proof and treats README/package/config signals as weak context where applicable. Before storing an evidence item, it verifies that the path, line range, and excerpt match the inspected file contents.

Statuses are:

- **Demonstrated**: validated direct implementation signal at the inspected commit.
- **Partially demonstrated**: limited or contextual signal; not proof of mastery.
- **Not demonstrated in this inspected scope**: no validated matching evidence was returned in the bounded inspection. This is not proof the student lacks the skill.

The optional fit score is explained in the response and dashboard: required skills weigh 1, preferred skills 0.5; demonstrated = 1, partial = 0.5, missing-in-scope = 0. It is an evidence-traceability aid, not a hiring recommendation or measure of proficiency, authorship, interview performance, or complete experience.

## Privacy and security

- GitHub, OpenAI, xAI, JSearch, and Telegram credentials are server-side environment variables only.
- The backend never executes, imports, installs, clones, or runs inspected repository code.
- GitHub calls use timeouts, bounded retries for transient failures, safe handling for auth/rate-limit errors, and no retry for invalid/authentication requests.
- Safety filters exclude likely secrets, generated files, dependencies, binaries, oversized files, and lock files.
- SQLite stores assessment snapshots and selected validated excerpts; it does not store a full cloned copy of an inspected repository.
- The OpenAI opt-in sends only job title/company, requirement excerpts, statuses, and up to two already-validated evidence excerpts per skill. It never sends keys or uninspected source. xAI receives the same bounded payload only after a retryable OpenAI failure. A missing/failed key produces a controlled deterministic result.
- Telegram receives a short new-commit alert only after a paired repository is automatically reassessed. It never receives job text, source excerpts, GitHub tokens, provider keys, or arbitrary incoming chat text.

## Key API endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Health and non-secret deterministic/LLM status. |
| `POST /api/jobs` | Save real source URL and requirements text. |
| `POST /api/job-search` | Optional server-side JSearch discovery; returned items must be reviewed before saving. |
| `POST /api/repositories` | Real GitHub inspection and initial assessment. |
| `GET /api/repositories/{id}/monitor` | Monitoring state, timestamps, and events. |
| `POST /api/repositories/{id}/monitor/check` | Run change detection now. A new SHA is reassessed automatically. |
| `GET /api/repositories/{id}/history` | Stored snapshot history. |
| `GET /api/assessments/{current}/compare/{previous}` | Evidence/status comparison. |
| `POST /api/repositories/{id}/telegram/pair` | Create an expiring one-time Telegram pairing command. |

See [docs/api-contracts.md](docs/api-contracts.md) for the complete contract, [docs/architecture.md](docs/architecture.md) for data flow, and [docs/decisions.md](docs/decisions.md) for deliberate tradeoffs.

## Known limitations

- Many career sites block automated extraction or render descriptions in client-side JavaScript. The app retains the real URL and supports manual paste rather than pretending fetch succeeded.
- Requirement normalization intentionally supports a conservative catalog. Unrecognized phrases are retained in the job text but are not guessed into a skill claim.
- GitHub's compare endpoint may be unavailable for force-pushes, divergent history, or permissions. The service still reassesses the detected new SHA and reports the comparison limitation.
- A repository scan cannot prove authorship, seniority, production deployment, or competence beyond the visible implementation signals.
- Polling is appropriate for a local hackathon MVP. A deployed production system could optionally add verified GitHub webhooks.
- OpenAI interpretation is optional and disabled by default; it is not required for evidence extraction or automatic reassessment.
- The Telegram feature is an operator/demo pairing feature because this MVP does not yet have end-user authentication. Production needs repository ownership and account authorization checks.
- The Azure SQLite profile is deliberately single-replica. Move to PostgreSQL before horizontally scaling or running multiple writers.
