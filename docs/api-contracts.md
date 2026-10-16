# API contracts

All error responses use this shape:

```json
{
  "error": {
    "code": "machine_readable_code",
    "message": "Safe message for the dashboard",
    "details": null
  }
}
```

| Method and route | Purpose |
| --- | --- |
| `GET /api/health` | Service, monitoring, and non-secret LLM, JSearch, and Telegram availability state. |
| `POST /api/jobs` | Persist `{title, company?, source_url, description}` and directly matched supported requirements. `company` is optional context and is stored as `Company not specified` when omitted; `source_url` remains required for traceability. |
| `GET /api/jobs` | Read all saved jobs ordered newest first. |
| `GET /api/jobs/{id}` | Read a saved job and its retained URL. |
| `PUT /api/jobs/{id}` | Update `{title, company?, source_url, description}` and re-extract required skills. |
| `DELETE /api/jobs/{id}` | Delete job and cascade delete all associated repositories, snapshots, and events. |
| `POST /api/jobs/fetch` | Best-effort, user-triggered public-page text fetch. The client may instead paste text. |
| `POST /api/job-search` | Optional server-side JSearch discovery with `{query, country, location?, date_posted?}`. Results are reviewable suggestions only; none are persisted until `POST /api/jobs`. |
| `POST /api/repositories` | Connect `{job_id, repository_url}`, perform the initial GitHub inspection, and store the first snapshot. |
| `GET /api/repositories` | Read repositories, optionally filtered by `?job_id={id}`. |
| `GET /api/repositories/{id}/overview` | Current job, repository metadata, latest snapshot, and monitoring events. |
| `POST /api/repositories/{id}/scan` | Explicit manual re-scan; duplicate SHA snapshots are not created. |
| `GET /api/repositories/{id}/history` | Summary of immutable snapshots, newest first. |
| `GET /api/repositories/{id}/monitor` | Polling state, timestamps, safe error state, and recent events. |
| `PUT /api/repositories/{id}/monitor` | Enable or pause monitoring with `{enabled}`. |
| `POST /api/repositories/{id}/monitor/check` | Invoke the polling code path immediately for demo/testing; a new SHA is automatically reassessed. |
| `DELETE /api/repositories/{id}` | Disconnect and remove repository, cascading to snapshots, monitor events, and Telegram subscriptions. |
| `GET /api/repositories/{id}/telegram` | Safe Telegram availability/pairing state only. Never returns a chat ID, token, or webhook secret. |
| `POST /api/repositories/{id}/telegram/pair` | Create one expiring `/start` pairing command for an enabled Telegram integration. The server stores only its hash. |
| `POST /api/integrations/telegram/webhook` | Telegram-only webhook. Requires the configured `X-Telegram-Bot-Api-Secret-Token` header and accepts `/start <code>` or `/stop`; free-form messages are discarded. |
| `GET /api/assessments/{id}` | Full stored assessment snapshot. |
| `GET /api/assessments/{current}/compare/{previous}` | Validated evidence and status differences for two snapshots of the same repository. |

## Snapshot semantics

A snapshot has an inspected commit SHA, public commit link, trigger, time, bounded-inspection metadata, changed files where available, deterministic assessment, and optional LLM metadata. SQLite has a uniqueness constraint on `(repository_id, commit_sha)`, so the same SHA cannot create duplicate history entries.

## Provider boundaries

- JSearch receives the search query, country, optional location, and date filter. Its key remains server-side. Returned URLs/text must still be reviewed and deliberately saved as a job.
- OpenAI is optional and receives only job title/company, requirement excerpts, statuses, and up to two already-validated excerpts per skill. xAI may receive the same limited payload only after a retryable OpenAI failure. Neither provider creates evidence, paths, line ranges, or statuses.
- Telegram receives a concise notification only after an automatically detected new SHA creates a snapshot for a paired repository. It does not receive code excerpts, job text, GitHub tokens, provider keys, or chat content beyond `/start` and `/stop` commands.
