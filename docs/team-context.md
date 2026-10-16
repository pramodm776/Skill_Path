# SkillPath AI — shared team context

Read this before making cross-cutting changes. It is intentionally IDE-neutral: teammates can use Antigravity, Codex, VS Code, or another editor.

## Product and non-negotiable demo

**Product name:** SkillPath AI<br>
**Official challenge:** W-PS-2 — AI Career Coach

The judge-facing loop is:

```text
real job posting -> real GitHub evidence -> accurate gaps
-> meaningful pushed commit -> automatic reassessment -> evidence delta
```

Never describe a missing signal as a missing skill. The required wording is **not demonstrated in this inspected scope**.

## Current architecture

- Vanilla HTML, CSS, and JavaScript dashboard in `frontend/`.
- One FastAPI application in `backend/main.py`.
- Read-only GitHub REST inspection in `backend/github_client.py`; inspected code is never cloned or executed.
- Deterministic evidence verification in `backend/skills.py`.
- SQLite snapshot/history store in `backend/storage.py`.
- Commit-SHA polling and automatic reassessment in `backend/monitor.py`.
- Optional GitHub push webhook in `POST /api/integrations/github/webhook`; when configured, it bypasses the polling cycle and triggers immediate reassessment on push events.
- Optional OpenAI interpretation in `backend/llm.py`; controlled xAI fallback is allowed only for retryable OpenAI failures and may not create evidence, status, or citations.
- Optional JSearch discovery in `backend/job_search.py`; a result must be reviewed and saved through normal job ingestion before it can be assessed.
- Optional Telegram pairing in `backend/telegram.py`; it stores a one-time code hash and may notify only after automatic new-SHA reassessment.

The automatic reassessment flow has automated test coverage. A public repository controlled by the team must still be used for the final live push-to-reassessment rehearsal.

## Delivery decisions

- Keep one backend service; do not introduce React, TypeScript, microservices, or an agent framework for the MVP.
- Treat the current app as a **bounded agentic workflow**, not an autonomous multi-agent swarm. The orchestrator is deterministic and auditable.
- OpenAI is the primary optional reasoning provider. Grok is a controlled fallback only for an eligible provider failure; deterministic evidence extraction remains available if both are unavailable.
- Job-search discovery is optional. The selected job must still retain a real direct posting URL and its returned/pasted description.
- The recommended initial discovery provider is **JSearch** with India-location queries. Keep manual job URL/text ingestion as the reliable fallback. Do not put provider keys in the browser.

## Team ownership boundaries

| Area | Primary files | Guardrail |
| --- | --- | --- |
| GitHub and monitoring | `backend/github_client.py`, `backend/monitor.py`, `backend/storage.py` | Preserve SHA deduplication and read-only access. |
| Assessment | `backend/skills.py`, `backend/llm.py` | Validate every path, line range, and excerpt. |
| API integration | `backend/main.py`, `docs/api-contracts.md` | Update the contract with endpoint changes. |
| Dashboard | `frontend/` | Do not expose keys or bypass server APIs. |
| Tests and demo | `tests/`, `docs/demo-script.md`, `README.md` | Report actual results only. |
| Job discovery / Telegram | `backend/job_search.py`, `backend/telegram.py`, `backend/telegram_setup.py` | Keys and chat IDs never reach frontend responses, logs, or Git. |
| Azure deployment | `Dockerfile`, `infra/`, `docs/azure-deployment.md` | Keep max replicas at one while SQLite is used; use Key Vault in a real deployment. |

## Git workflow

1. Check whether remote `main` exists before starting work. Once initialized, clone `https://github.com/vedantsable56/Skill_Path.git` and pull `main`. Until then, coordinate with the release owner and use the published `feature/skillpath-mvp` baseline; do not initialize or force-push `main` yourself.
2. Create one focused branch, for example `feature/job-discovery` or `feature/telegram-alerts`.
3. Do not edit another teammate's assigned files without first coordinating in the pull request or team chat.
4. Commit small, reviewable changes with a meaningful message. Never commit `.env`, `data/*.sqlite3`, tokens, or generated assets.
5. Open a pull request to `main` after it is initialized. The owner runs the test suite and resolves conflicts before merging.
6. Make a final, meaningful commit in the team-controlled demo repository during rehearsal; SkillPath AI must detect it automatically without the manual Analyse action.

## Merge gate

Run these from the repository root before merging when applicable:

```powershell
python -m pytest -q
python -m compileall -q backend
node --check frontend\script.js
```

Also manually verify the health endpoint and dashboard after changes to startup, API routing, or static assets.

## Secrets and deployment

Use local `.env` only; it is ignored by Git. Expected server-only values include `GITHUB_TOKEN`, `GITHUB_WEBHOOK_SECRET` (only if GitHub webhook is configured), `OPENAI_API_KEY`, `JSEARCH_API_KEY`, `XAI_API_KEY` (only if the Grok fallback is enabled), and Telegram webhook credentials (only if Telegram is enabled). The settings layer may contain placeholders for integrations, but a provider is active only when its feature flag is enabled. Azure deployment uses one Container Apps service plus Azure Files for the hackathon SQLite profile; production should replace that database with PostgreSQL before scale-out. Use Key Vault-backed application secrets and managed identity rather than an Azure client secret.

## Pitch differentiator

SkillPath AI is a **career evidence ledger**, not a résumé chatbot. Its key experience is a **Proof Delta**: after a commit, it identifies exactly which job requirement gained or lost evidence, the changed file/lines and commit SHA, what the result proves, and what it still does not prove.
