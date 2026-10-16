# SkillPath AI — PPT generation and project handoff

Use this document as the factual source for a hackathon presentation, demo narration, or a prompt to generate slides. It is written for **SkillPath AI**, the W-PS-2 AI Career Coach challenge.

> Presentation rule: distinguish **implemented and tested** functionality from **planned or awaiting live rehearsal** work. Do not claim that Azure, Telegram, JSearch, OpenAI, or xAI were used live unless the team has actually completed that specific test.

---

## 1. One-minute project explanation

**SkillPath AI is an evidence-first AI Career Coach.** It compares the requirements in a real job or internship posting against skills that are demonstrably present in a student's real GitHub repository. Instead of producing a generic resume score, it shows the exact file, line range, excerpt, and commit SHA that support each claim.

The central demo loop is:

```text
Real job posting
  → normalized requirements
  → read-only GitHub inspection
  → validated code evidence and careful gaps
  → student makes a real Git commit
  → automatic SHA detection and reassessment
  → before/after Proof Delta
```

The distinguishing principle is **evidence, not assumptions**:

- A missing signal is labelled **“not demonstrated in this inspected scope.”**
- It is never presented as proof that a student lacks a skill.
- An LLM cannot invent evidence, file paths, line references, or skill status.

---

## 2. The problem being solved

Students often see job descriptions that list many skills but cannot tell whether their public portfolio actually proves those skills to a recruiter. Existing career tools commonly rely on self-reported skills, keyword matching, or static resume feedback.

This creates four practical gaps:

1. **No traceability:** a “match score” rarely explains what in the repository proves the match.
2. **No honest absence handling:** a missing keyword can be incorrectly treated as proof that the candidate lacks a skill.
3. **No change awareness:** a portfolio can improve after feedback, while the report remains static.
4. **No concrete next action:** students may know there is a gap but not what code or project work would generate credible evidence.

SkillPath AI addresses these gaps by treating the GitHub commit history as a living portfolio evidence source.

---

## 3. Product value proposition

### For students

- See what their code actually demonstrates for a target role.
- Understand evidence gaps without receiving an unsupported negative judgment.
- Receive project tasks that could create future proof of a missing requirement.
- See how a real new commit changes the portfolio assessment.

### For judges or mentors

- Verify every shown claim using a repository path, excerpt, line range, and SHA.
- Watch the system reassess automatically after a real repository update.
- Inspect clear technical limits instead of trusting opaque AI output.

### Core differentiator: Proof Delta

**Proof Delta** is the before/after comparison created for two repository commits. It explains:

- which job requirement gained, lost, or kept evidence;
- the old and new assessment status;
- evidence added or removed in changed files;
- the relevant commit SHA and changed-file metadata;
- what the result proves and what it still does not prove.

This makes the product a **career evidence ledger**, not a resume chatbot.

---

## 4. What is implemented in the MVP

| Capability | Status | What it does |
| --- | --- | --- |
| Real job ingestion | Implemented | Saves job title, optional company context, public posting URL, and pasted or fetched description. |
| Requirement normalization | Implemented | Recognizes conservative, directly stated skills and retains source excerpts. |
| JSearch discovery | Implemented, optional | Searches jobs server-side; results must be reviewed and deliberately saved. |
| Real GitHub inspection | Implemented | Uses GitHub REST APIs for metadata, default branch, commit SHA, tree, and bounded text-file reads. |
| Evidence engine | Implemented | Validates file path, line range, and excerpt against inspected contents before display. |
| Assessment snapshots | Implemented | Stores immutable SQLite assessments keyed by repository and commit SHA. |
| Automatic monitoring | Implemented | Polls the default branch, detects a new SHA, compares changes where possible, and reassesses automatically. |
| Proof Delta comparison | Implemented | Shows status transitions and validated evidence differences between snapshots. |
| Vanilla dashboard | Implemented | Same-origin responsive HTML/CSS/JS interface with job, repo, evidence, history, and monitor states. |
| OpenAI explanation | Implemented, opt-in | Adds concise language explanations only after deterministic evidence validation. |
| Grok/xAI fallback | Implemented, opt-in | Runs only after a retryable OpenAI failure and cannot change factual evidence. |
| Telegram alert | Implemented, opt-in | Sends one short post-reassessment alert to a paired chat. |
| Docker/Azure templates | Implemented | Dockerfile, CI, Bicep infrastructure, and a Container Apps deployment guide are present. |

---

## 5. What remains before final submission

These are rollout and rehearsal activities, not missing core code.

| Remaining activity | Why it matters | Completion evidence |
| --- | --- | --- |
| Initialize/publish `main` branch | Gives teammates one common Git base. | Remote `main` contains the reviewed commit. |
| Live public-repo walkthrough | Demonstrates real GitHub API access, not only unit tests. | Initial assessment showing real commit SHA and evidence. |
| Real commit reassessment rehearsal | This is the key mandatory problem-statement demo. | New SHA, automatic event, second snapshot, and Proof Delta. |
| Live JSearch test | Validates the team's key and job-search quota. | Reviewed job result is saved with its direct source URL. |
| Optional OpenAI test | Validates secondary explanation with a team key. | Labelled LLM explanation without any new evidence citation. |
| Docker build | Verifies the deployment artifact after Docker Desktop is running. | Successful image build and local container health response. |
| Azure deployment | Produces the public demo endpoint. | Container App health endpoint and browser dashboard. |
| Optional Telegram test | Needs a public HTTPS URL and bot configuration. | One alert after an automatic new-SHA reassessment. |

**Do not say “deployed to Azure” or “Telegram notifications tested” in the PPT until those events are actually completed.**

---

## 6. Architecture

```text
                         Browser dashboard
                   Vanilla HTML + CSS + JavaScript
                           same-origin requests
                                     |
                                     v
                    ┌──────────────────────────┐
                    │   FastAPI application     │
                    │   single backend service  │
                    └────────────┬─────────────┘
       ┌─────────────────────────┼─────────────────────────┐
       v                         v                         v
 Job intake and           GitHub REST client        SQLite persistence
 skill normalization       read-only / bounded       jobs, repositories,
 URL retention             no code execution         snapshots, events
       |                         |                         ^
       └───────────────┐         v                         |
                       │  Deterministic evidence engine ───┘
                       │  path + line + excerpt validation
                       v
              Background monitor
              detects default-branch SHA changes
                       |
                       v
              Automatic reassessment + Proof Delta
                       |
         ┌─────────────┴─────────────┐
         v                           v
 Optional LLM explanation     Optional Telegram alert
 OpenAI primary; xAI fallback short post-reassessment notice
```

### Why one service?

The product intentionally uses one FastAPI service, SQLite, and vanilla web files. This keeps a 24-hour MVP dependable, easy to demo locally, and easy to deploy as one Azure Container App. It avoids unnecessary React, microservices, queues, and agent frameworks.

---

## 7. End-to-end workflow in detail

### Phase A — Job source

1. The user enters a job title, optional company context, public job URL, and description.
2. The application retains the source URL even when it cannot automatically extract a page.
3. Directly mentioned supported requirements are normalized conservatively.
4. Each normalized requirement keeps the original source excerpt.

Manual paste is a deliberate fallback because many job sites are JavaScript-rendered or block automated requests.

### Phase B — Repository inspection

1. The user supplies a `github.com/owner/repository` URL.
2. The backend discovers the repository metadata, default branch, and current commit SHA.
3. It reads a bounded subset of eligible text files using the GitHub REST API.
4. It skips binaries, dependencies, generated/minified files, lock files, oversized files, and likely secret files.
5. It never clones, executes, imports, installs, or runs repository code.

Default inspection bounds:

- Up to 20 eligible files
- Up to 200 KB per file
- Up to 1.5 MB total inspected content

The application stores these bounds and skipped-file reasons with the assessment so its scope is transparent.

### Phase C — Evidence-backed assessment

For every supported job skill, deterministic rules look for appropriate source/configuration signals in non-comment code. Before displaying any evidence, the app verifies that:

1. the path was actually inspected;
2. the line range exists in that file;
3. the displayed excerpt matches the inspected file content;
4. the evidence belongs to the inspected commit SHA.

An assessment includes:

- status: demonstrated, partially demonstrated, or not demonstrated in this inspected scope;
- evidence path, lines, excerpt, SHA, confidence, and limitations;
- gap explanation;
- a future-only evidence task where useful;
- a transparent fit-score calculation and its limitations.

### Phase D — Continuous improvement loop

1. A background monitor polls the default branch at a configured interval.
2. It records the newest GitHub SHA.
3. A duplicate SHA produces no new assessment.
4. A new SHA triggers a GitHub comparison where feasible.
5. The backend inspects the exact new revision and creates a new immutable snapshot.
6. The dashboard shows an automatic reassessment event and Proof Delta.

---

## 8. LLM and “agentic” workflow explanation

### The correct statement

SkillPath AI uses a **bounded, deterministic orchestration workflow**, not an autonomous multi-agent swarm.

The orchestrator coordinates fixed stages:

```text
Requirement normalizer
  → GitHub inspector
  → evidence validator
  → deterministic assessor
  → snapshot store
  → SHA monitor
  → comparison / Proof Delta
  → optional LLM explanation
```

These named stages are system components, not separate autonomous LLM agents that make independent hiring decisions.

### What the LLM does

When enabled, OpenAI receives only:

- job title and company;
- requirement excerpts;
- already-computed assessment statuses;
- at most two already-validated evidence excerpts per skill.

It may create a clearer secondary explanation of existing evidence and future work.

### What the LLM cannot do

- It cannot inspect GitHub itself.
- It cannot create a file path, line reference, or evidence excerpt.
- It cannot change a deterministic status or fit score.
- It cannot see provider keys or an uninspected full repository.
- It cannot turn missing evidence into proof that a student lacks a skill.

OpenAI is the optional primary explanation provider. xAI/Grok is a controlled fallback only after a retryable OpenAI/network failure and only when explicitly configured. If no LLM key is available, the core product stays fully usable in labelled deterministic mode.

### Judge-ready explanation

> “We do not let a language model decide what a repository proves. Our deterministic verifier validates file, line, excerpt, and commit SHA first. The LLM only translates already-validated evidence into clear student guidance.”

---

## 9. Frontend experience

The dashboard is served by FastAPI at `http://127.0.0.1:8000/`. It must not be opened as a standalone `file:///.../index.html` file, because its API and `/static/...` paths require the backend server.

Main user interface areas:

1. **Job source panel:** manual URL/text entry, best-effort page fetch, optional JSearch search.
2. **Repository panel:** GitHub URL entry and initial scan status.
3. **Assessment summary:** evidence-fit score, requirements and scope note.
4. **Skill evidence cards:** status, paths, excerpts, commit information, confidence, limitations, and future evidence contract.
5. **Monitoring panel:** enabled state, last checked/assessed times, latest SHA, events, and safe failures.
6. **History and Proof Delta:** immutable snapshot history and comparison between revisions.
7. **Optional Telegram panel:** safe pairing status and one-time pairing command when configured.

The frontend receives no provider key, GitHub token, Telegram chat ID, or webhook secret.

---

## 10. Data model and API summary

SQLite stores five main categories of data:

| Stored entity | Purpose |
| --- | --- |
| Job | Source URL, title, company, pasted/fetched description, normalized requirements. |
| Repository | GitHub identity, default branch, monitoring settings, latest known SHA and safe state. |
| Snapshot | Immutable assessment for one repository commit SHA. |
| Monitor event | Detection, reassessment, no-change, rate-limit, or safe error events. |
| Telegram subscription/delivery | One-time-code hash, paired state, and deduplicated notification delivery metadata. |

Important API routes:

| Route | Purpose |
| --- | --- |
| `GET /api/health` | Non-secret service and integration availability state. |
| `POST /api/jobs` | Save a real source URL and requirements text. |
| `POST /api/job-search` | Optional server-side JSearch discovery. |
| `POST /api/repositories` | Inspect a GitHub repository and create initial snapshot. |
| `GET /api/repositories/{id}/monitor` | Read polling status and events. |
| `POST /api/repositories/{id}/monitor/check` | Run the same monitor detection path immediately. |
| `GET /api/repositories/{id}/history` | Read immutable assessment history. |
| `GET /api/assessments/{current}/compare/{previous}` | Return Proof Delta. |
| `POST /api/repositories/{id}/telegram/pair` | Start an optional expiring Telegram pairing. |

All errors use one consistent safe JSON shape with a machine-readable code and user-safe message.

---

## 11. Security, privacy, and responsible-AI guardrails

### Credential safety

- GitHub, JSearch, OpenAI, xAI, Telegram, and Azure values exist only in environment variables or Azure secret configuration.
- `.env` is ignored by Git.
- The browser never receives a credential, request authorization header, Telegram chat ID, or webhook secret.

### Repository safety

- The GitHub integration is read-only.
- No inspected repository code is cloned or executed.
- Likely secret files and unsafe/generated paths are excluded from inspection.

### Evidence safety

- Candidate evidence is validated against actual inspected file content.
- Comments alone do not prove an implementation skill.
- Missing evidence uses bounded-scope wording, not a personal judgment.

### LLM privacy boundary

- LLM use is opt-in.
- The model sees only compact, already-validated context.
- It never receives keys or a complete uninspected repository.
- A missing/failed key produces a controlled deterministic outcome.

### Telegram safety

- Pairing codes are short-lived and only a hash is stored.
- Incoming free text is discarded; only `/start` and `/stop` are handled.
- Alerts omit source excerpts, job text, and all credentials.

---

## 12. Technology stack

| Layer | Technology | Why it is used |
| --- | --- | --- |
| Frontend | HTML, CSS, vanilla JavaScript | Meets fixed stack; fast, dependency-free demo UI. |
| Backend | Python + FastAPI | Typed API endpoints, async HTTP, static frontend serving. |
| Persistence | SQLite | Lightweight immutable snapshot history for hackathon scope. |
| GitHub access | GitHub REST API + `httpx` | Real repository and commit data; no repository execution. |
| Job discovery | JSearch/RapidAPI, optional | India-friendly discovery; manual source ingestion remains valid. |
| AI explanation | OpenAI Responses API, optional | Clear interpretation of evidence already verified. |
| Fallback | xAI/Grok, optional | Controlled fallback only after eligible transient primary failure. |
| Alerts | Telegram Bot API, optional | Short automatic commit-reassessment notifications. |
| Container | Docker | Portable application package. |
| Cloud | Azure Container Apps + Azure Files | Same-origin service and single-replica SQLite hackathon profile. |
| Infrastructure | Bicep | Repeatable Azure deployment template. |
| CI | GitHub Actions | Python tests and frontend syntax validation. |

---

## 13. Testing and current evidence of quality

The current test suite has run successfully with:

```text
10 passed
```

Covered behavior includes:

- real-source URL retention;
- validated path/line/excerpt evidence;
- fabricated-evidence rejection;
- correct bounded-scope wording for missing evidence;
- comment-only implementation claims not counting as proof;
- initial assessment followed by scheduled new-SHA reassessment;
- changed-file storage and evidence comparison;
- duplicate SHA suppression;
- safe GitHub rate-limit state;
- JSearch server-side key isolation and review-before-save behavior;
- OpenAI retry / xAI fallback rules;
- Telegram one-time pairing, webhook authentication, and delivery deduplication.

Also verified:

- Python backend/test compilation;
- JavaScript syntax;
- frontend element-reference check;
- Bicep template compilation;
- tracked-source credential-pattern scan.

Avoid unsupported claims such as model accuracy percentages, reduced hiring time, number of students helped, or live provider/deployment success before those are measured.

---

## 14. Known limitations and honest roadmap

### Current MVP limitations

- Job sites may block extraction or render descriptions client-side; manual text paste remains the truthful fallback.
- The requirement catalog is intentionally conservative and does not guess unknown skill phrases.
- GitHub compare data can be unavailable for force-pushes, divergent histories, or permissions; the new SHA can still be reassessed with that limitation recorded.
- Repository evidence cannot prove authorship, seniority, production quality, interview readiness, or complete professional ability.
- Polling is appropriate for the MVP but is less immediate than verified GitHub webhooks.
- Telegram pairing is an operator/demo feature; production needs user accounts and repository-ownership authorization.
- SQLite and a one-replica Container App are not suitable for horizontal multi-writer scale.

### Production roadmap

1. Add authenticated users and GitHub OAuth repository authorization.
2. Replace polling with verified GitHub webhooks where appropriate.
3. Move SQLite history to PostgreSQL before multi-replica deployment.
4. Add role-specific skill catalogs with reviewable provenance.
5. Add portfolio-to-requirement trend analytics while preserving evidence traceability.
6. Add evaluator feedback loops without allowing LLM outputs to become unverified evidence.

---

## 15. Suggested 12-slide presentation structure

| Slide | Title | Key message | Suggested visual |
| --- | --- | --- | --- |
| 1 | SkillPath AI | Evidence, not assumptions. | Logo/title with the one-line value proposition. |
| 2 | The student portfolio gap | Students cannot see what their code actually proves for a role. | Problem journey: job description → uncertainty. |
| 3 | Our solution | A living evidence ledger tied to real GitHub commits. | Product loop. |
| 4 | Core user journey | Job URL → repository → evidence → commit → Proof Delta. | Five-step timeline. |
| 5 | Evidence, not keyword claims | Every claim has a path, line, excerpt, and SHA. | Sample evidence card mockup/screenshot. |
| 6 | Automatic reassessment | A new default-branch commit creates a new immutable snapshot. | Before/after SHA and Proof Delta. |
| 7 | Bounded agentic workflow | Deterministic orchestration; LLM explains but does not decide facts. | Architecture diagram from section 6. |
| 8 | Product experience | Job intake, skill evidence, monitor state, history. | Dashboard screenshots. |
| 9 | Responsible AI and security | Server-side keys, no code execution, careful absence wording. | Shield/guardrail diagram. |
| 10 | Technology and deployment | FastAPI + vanilla JS + SQLite + GitHub + Azure Container Apps. | Concise stack diagram. |
| 11 | Validation and demo proof | Ten automated tests plus real push-to-reassessment rehearsal. | Test checklist and live demo screenshots. |
| 12 | Impact and roadmap | More actionable portfolio improvement with trustworthy evidence. | Roadmap: MVP → webhooks/auth/PostgreSQL. |

### Recommended slide tone

- Use a clean dark/navy or white/blue technical style.
- Use screenshots of the actual dashboard and a real GitHub commit rather than generic AI art.
- Use concise statements; the evidence and automatic update are the strongest visuals.
- Do not fill slides with code or long paragraphs.

---

## 16. Demo narration script

Use this short narration during the live product section:

> “I start with a real posting and retain its source URL. SkillPath AI extracts only requirements that are directly present in the description. Next, it inspects a real GitHub repository through read-only APIs. For every demonstrated skill, I can open the exact file, line range, excerpt, and commit SHA. If evidence is missing, the system says only that it was not demonstrated in this bounded inspection; it does not make a claim about the student. Now I push a real code improvement to the repository’s default branch. The monitor detects the new SHA, reassesses automatically, stores a new immutable snapshot, and shows the Proof Delta—the exact evidence that changed.”

For the LLM question:

> “The LLM is optional and secondary. It improves the explanation of validated evidence, but it cannot create citations, statuses, or hiring conclusions. The deterministic verifier remains the source of truth.”

---

## 17. Copy-ready prompt for ChatGPT PPT generation

Copy the text below into ChatGPT when asking it to create slide content or a presentation outline. Add screenshots only after the team completes the live walkthrough.

```text
Create a polished 12-slide hackathon presentation for a project named “SkillPath AI”.

Project: SkillPath AI is an evidence-first AI Career Coach. It compares requirements from a real public job or internship posting with evidence found in a real GitHub repository. It does not generate a generic resume score. For every demonstrated requirement, it shows a validated file path, line range, excerpt, and inspected commit SHA. Missing evidence must be described exactly as “not demonstrated in this inspected scope,” never as proof the student lacks a skill.

Core live loop:
real job posting → normalized requirements → read-only GitHub inspection → validated code evidence and careful gaps → real pushed commit → automatic new-SHA detection → automatic reassessment → before/after Proof Delta.

Proof Delta compares two immutable commit snapshots and shows which requirement gained or lost evidence, old/new status, changed evidence, commit SHA, and limitations.

Architecture: vanilla HTML/CSS/JavaScript dashboard; a single Python FastAPI service; SQLite snapshot history; GitHub REST API; deterministic evidence validation; background polling monitor; optional JSearch discovery; optional OpenAI explanation with controlled Grok/xAI fallback; optional Telegram notification; Docker and Azure Container Apps deployment templates.

Important AI boundary: this is a bounded deterministic orchestration workflow, not an autonomous multi-agent swarm. The LLM is optional and only explains already-validated evidence. It cannot inspect GitHub, create file/line citations, change a skill status, or make hiring decisions.

Security: all provider keys remain server-side; the app never executes repository code; likely secrets/binaries/dependencies/generated files are skipped; the browser receives no keys.

Validation: ten automated tests have passed for evidence validation, missing-evidence wording, new-SHA reassessment, duplicate suppression, rate-limit handling, JSearch key isolation, controlled LLM fallback, Telegram webhook/delivery protections, and optional company with required source traceability. Do not invent performance metrics, user counts, accuracy values, or claim that Azure/Telegram/live providers are deployed/tested unless screenshots prove it.

Make slides technical, visually clean, and concise. Include: problem, solution, user loop, evidence card concept, Proof Delta, architecture, bounded agentic workflow, security, stack/deployment, validation, roadmap, and a closing impact slide. Suggest actual dashboard and GitHub commit screenshots for the product/demo slides. Do not use exaggerated AI claims.
```

---

## 18. Source folder map

```text
hackathon-project/
├── frontend/
│   ├── index.html                 # dashboard structure
│   ├── style.css                  # responsive visual system
│   └── script.js                  # API calls and dashboard state
├── backend/
│   ├── main.py                    # FastAPI routes and static serving
│   ├── github_client.py           # read-only GitHub REST inspection
│   ├── skills.py                  # deterministic evidence and comparisons
│   ├── monitor.py                 # SHA polling and automatic reassessment
│   ├── storage.py                 # SQLite snapshots and event history
│   ├── llm.py                     # optional controlled interpretation
│   ├── job_search.py              # optional JSearch integration
│   ├── telegram.py                # optional Telegram pairing/alerting
│   └── telegram_setup.py          # operator webhook setup utility
├── tests/
│   ├── test_evidence_and_monitoring.py
│   └── test_optional_integrations.py
├── infra/
│   ├── foundation.bicep           # Azure foundation resources
│   └── app.bicep                  # Azure Container App profile
├── docs/
│   ├── architecture.md
│   ├── api-contracts.md
│   ├── decisions.md
│   ├── demo-script.md
│   ├── azure-deployment.md
│   ├── team-context.md
│   ├── ppt-generation-context.md  # this document
│   └── antigravity-handoff.md     # IDE-neutral implementation handoff
├── Dockerfile
├── .env.example                   # placeholders only
├── requirements.txt
└── README.md
```

---

## 19. Team handoff checklist

1. Never commit `.env`, provider keys, SQLite database files, or generated local assets.
2. Use a focused Git branch per task and a pull request into `main` once the remote main base is initialized.
3. Run `python -m pytest -q` and `node --check frontend\script.js` before merging.
4. Do not alter evidence wording, SHA deduplication, or line/excerpt validation without updating tests and documentation.
5. Rehearse the real new-commit automatic reassessment before presenting.
6. Capture screenshots only after verifying that displayed job URLs, commit SHAs, evidence paths, and timestamps are real.

For developer coordination, read `docs/team-context.md`. For local setup and exact deployment commands, read `README.md` and `docs/azure-deployment.md`.
