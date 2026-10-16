# SkillPath AI Working Rules & Guardrails

These non-negotiable rules govern all development, testing, and AI assistant actions for SkillPath AI.

---

## 1. Security & Secrets Management
- **Server-Side Only Credentials:** Keep all GitHub tokens, OpenAI/xAI API keys, RapidAPI keys, Telegram bot tokens, and webhook secrets strictly server-side in process environment variables.
- **No Secret Leakage:** Never put a token, `.env` value, authorization header, or credential snippet into frontend code, browser responses, logs, test fixtures, screenshots, or documentation.
- **Never Commit Secrets:** Never commit `.env`, `data/*.sqlite3`, generated binary assets, or private tokens to Git.

---

## 2. GitHub Read-Only Boundary
- **Read-Only Inspection:** The GitHub integration is strictly read-only. Never clone, execute, install, or import inspected repository code.
- **Bounded Scanning:** Inspections are bounded (`max_files=20`, `max_file_bytes=200KB`, `max_total_bytes=1.5MB`). Binary, minified, generated, lock, secret, and dependency directories are strictly skipped.
- **Push Webhook Authentication:** The push webhook (`POST /api/integrations/github/webhook`) must verify HMAC `X-Hub-Signature-256` when `GITHUB_WEBHOOK_SECRET` is configured. When unset, it operates safely in open development mode.

---

## 3. Evidence Integrity & Ethical Assessment
- **Deterministic Proof Only:** An evidence citation must resolve to an exact file path, 1-indexed line range, and code excerpt returned by the bounded AST scan. Do not use a filename, README, package manifest, or LLM output alone as proof of a skill.
- **Strict Scope Wording:** Missing evidence must ALWAYS be described as **"not demonstrated in this inspected scope"**, never as a claim or verdict that a student lacks a skill.
- **Commit SHA Anchored:** Every change assessment must be tied to a distinct GitHub commit SHA. Duplicate commits must be suppressed, and automatic snapshots must never be fabricated.

---

## 4. Optional Integrations Boundaries
- **OpenAI & LLM Explanations:** LLM interpretation is strictly opt-in (`ENABLE_LLM_EXPLANATIONS=true` and `OPENAI_API_KEY`). The LLM generates summary context and future growth recommendations only; it cannot alter deterministic statuses, invent citations, or claim skills without proof.
- **Telegram Bot Pairing:** Pairing uses short-lived hashed one-time tokens. Webhook alerts (`POST /api/integrations/telegram/webhook`) contain only commit SHAs, repo links, and fit score summaries—never source code excerpts, evidence snippets, or private keys. The UI and API do not gate bot pairing or repository connection behind mandatory job creation.
- **Job Search Discovery & Source URL Flexibility:** Real-time job discovery runs server-side via Jooble (`JOOBLE_API_KEY`) and JSearch (`JSEARCH_API_KEY`) with concurrent fallback and deduplication. Source posting URLs are optional for manual entry and real-time roles (local benchmark references are auto-assigned when omitted). Candidates prefill the job form for immediate review and assessment.

---

## 5. Architecture & Git Workflow
- **Single Service Constraint:** Keep the application a single FastAPI service plus SQLite and vanilla HTML/CSS/JavaScript. Do not introduce frontend frameworks (React, Vue), TypeScript builds, or microservices.
- **Branching & Pull Requests:** Work on focused, short-lived branches (`feature/<area>-<summary>` or `fix/<area>-<summary>`). Open pull requests into the baseline branch. Never force-push `main` or `feature/skillpath-mvp`.
- **Merge Gate Checks:** Before every merge or pull request, verify:
  ```powershell
  pytest -q
  python -m compileall -q backend
  node --check frontend\script.js
  ```
- **Handoff Coordination:** Review `docs/team-context.md` and `docs/api-contracts.md` when altering any cross-cutting API route or storage interface.
