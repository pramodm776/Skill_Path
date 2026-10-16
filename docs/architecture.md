# Architecture

```text
Browser (vanilla HTML, CSS, JavaScript)
   | same-origin JSON requests; no credentials
   v
FastAPI application
   |-- job ingestion and conservative skill normalization
   |-- optional JSearch discovery (review before persistence)
   |-- GitHub REST client (read-only, bounded, retry-aware)
   |-- deterministic evidence engine and reference validator
   |-- SQLite snapshot/history store
   |-- background polling monitor
   |-- optional OpenAI Responses API interpretation layer
   |     `-- controlled xAI fallback only after retryable OpenAI failures
   |         (validated evidence only; never creates citations)
   `-- optional Telegram pairing and automatic-reassessment notification
```

## Data flow

1. A user saves a public posting URL and description. The URL is retained even if the user pasted the text because website extraction failed.
2. Directly mentioned, supported requirement phrases are normalized. The original excerpt and line are stored with every normalized requirement.
3. The user connects a `github.com/owner/repository` URL. The service reads metadata, the default-branch commit, tree, and a bounded set of text files. It does not clone or execute code.
4. Deterministic rules inspect non-comment source/configuration lines. Every candidate excerpt is revalidated against the inspected file contents before it becomes assessment evidence.
5. The first result is an immutable SQLite snapshot keyed by repository and commit SHA.
6. The polling monitor periodically reads the default-branch SHA. For a new SHA, it requests GitHub's compare endpoint where feasible, fetches the exact new revision, produces a fresh snapshot, and records an automatic reassessment event.
7. The browser refreshes status only. It never performs a manual rewrite of the assessment or receives a token.
8. If a paired Telegram integration is enabled, the new automatic snapshot can create one short notification. A uniqueness record prevents duplicate deliveries for the same snapshot.

## Bounded inspection

Default limits are 20 eligible files, 200 KB per file, and 1.5 MB total content. This keeps a typical initial scan plus one new-commit reassessment practical even without a token. Binary files, generated/minified/lock files, dependency and build directories, probable secret files, and unsupported file types are skipped. The snapshot records the limits and skipped-file reasons so scope is visible.

## Optional LLM behavior

The deterministic engine is the source of truth. With both `OPENAI_API_KEY` and `ENABLE_LLM_EXPLANATIONS=true`, the server can send the job title/company, requirement excerpts, statuses, and at most two already-validated excerpts per skill to the OpenAI Responses API for a short secondary interpretation. It does not send API keys, uninspected files, or create evidence with the model. Only a retryable provider/network failure can use an explicitly enabled xAI fallback; authentication and validation failures never fail over. If a key is missing or both providers fail, the app remains in clearly labelled deterministic mode.

## Deployment profile

The Azure path serves the vanilla dashboard and FastAPI API from one Container Apps service. For the hackathon profile it uses one always-on replica and an Azure Files mount for SQLite snapshots. This is intentionally not a multi-replica database design; moving to Azure Database for PostgreSQL is required before horizontal scale. See [azure-deployment.md](azure-deployment.md).
