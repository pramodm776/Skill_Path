from __future__ import annotations

import asyncio
import ipaddress
import re
from contextlib import asynccontextmanager
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import PROJECT_ROOT, Settings
from .errors import AppError
from .github_client import GitHubClient
from .job_search import JSearchClient
from .llm import LLMInterpreter
from .monitor import MonitorService
from .skills import compare_assessments, extract_job_skills
from .storage import SQLiteStore
from .telegram import TelegramService


FRONTEND_DIRECTORY = PROJECT_ROOT / "frontend"
MAX_JOB_DESCRIPTION_CHARS = 50_000
MAX_FETCHED_PAGE_BYTES = 750_000


class JobCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    company: str = Field(min_length=1, max_length=240)
    source_url: str = Field(min_length=8, max_length=2_048)
    description: str = Field(min_length=1, max_length=MAX_JOB_DESCRIPTION_CHARS)


class JobFetchRequest(BaseModel):
    source_url: str = Field(min_length=8, max_length=2_048)


class JobSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=160)
    country: str = Field(default="in", min_length=2, max_length=2)
    location: Optional[str] = Field(default=None, max_length=160)
    date_posted: str = Field(default="all", pattern="^(all|today|3days|week|month)$")


class RepositoryCreateRequest(BaseModel):
    job_id: int = Field(gt=0)
    repository_url: str = Field(min_length=12, max_length=2_048)


class MonitorUpdateRequest(BaseModel):
    enabled: bool


class PageTextExtractor(HTMLParser):
    """Minimal, dependency-free extraction for user-triggered job-page fetches."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg", "canvas"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg", "canvas"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            cleaned = " ".join(data.split())
            if cleaned:
                self.parts.append(cleaned)

    def text(self) -> str:
        return "\n".join(self.parts)[:MAX_JOB_DESCRIPTION_CHARS]


def validate_public_http_url(value: str, *, label: str) -> str:
    raw = value.strip()
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise AppError("invalid_url", f"{label} must be a complete http or https URL.", 422)
    if parsed.username or parsed.password:
        raise AppError("invalid_url", f"{label} must not contain credentials.", 422)
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise AppError("invalid_url", f"{label} must point to a public host.", 422)
    try:
        address = ipaddress.ip_address(host)
        if not address.is_global:
            raise AppError("invalid_url", f"{label} must point to a public host.", 422)
    except ValueError:
        pass
    return raw


async def fetch_job_text(source_url: str) -> dict[str, str]:
    source_url = validate_public_http_url(source_url, label="Job posting URL")
    headers = {"User-Agent": "skillpath-ai-mvp/1.0 (+manual-job-text-fetch)"}
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(12.0), follow_redirects=True, max_redirects=3, headers=headers
        ) as client:
            async with client.stream("GET", source_url) as response:
                if response.status_code >= 400:
                    raise AppError(
                        "job_fetch_failed",
                        "The job page could not be fetched. Paste the job description manually; the source URL will still be retained.",
                        502,
                    )
                final_url = str(response.url)
                validate_public_http_url(final_url, label="Redirected job posting URL")
                content_type = response.headers.get("content-type", "").lower()
                if "html" not in content_type and "text" not in content_type:
                    raise AppError(
                        "job_fetch_unsupported_content",
                        "The job page did not return readable text. Paste the job description manually; the source URL will still be retained.",
                        422,
                    )
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_FETCHED_PAGE_BYTES:
                        raise AppError(
                            "job_fetch_too_large",
                            "The job page is too large to fetch safely. Paste the job description manually.",
                            422,
                        )
                    chunks.append(chunk)
    except AppError:
        raise
    except httpx.HTTPError as error:
        raise AppError(
            "job_fetch_failed",
            "The job page could not be fetched. Paste the job description manually; the source URL will still be retained.",
            502,
        ) from error
    parser = PageTextExtractor()
    parser.feed(b"".join(chunks).decode("utf-8", errors="replace"))
    text = parser.text()
    if len(text) < 80:
        raise AppError(
            "job_fetch_no_text",
            "The job page did not expose enough readable text. Paste the job description manually; the source URL will still be retained.",
            422,
        )
    return {"source_url": source_url, "resolved_url": final_url, "description": text}


def _public_repository(repository: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "id",
        "job_id",
        "repository_url",
        "owner",
        "name",
        "default_branch",
        "latest_known_sha",
        "latest_commit_url",
        "monitor_enabled",
        "monitor_state",
        "last_checked_at",
        "last_assessed_at",
        "last_error_code",
        "last_error_message",
        "created_at",
        "updated_at",
    )
    return {field: repository.get(field) for field in fields}


def _history_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    assessment = snapshot.get("assessment", {})
    summary = assessment.get("summary", {}) if isinstance(assessment, dict) else {}
    fit_score = assessment.get("fit_score", {}) if isinstance(assessment, dict) else {}
    return {
        "id": snapshot.get("id"),
        "commit_sha": snapshot.get("commit_sha"),
        "commit_url": snapshot.get("commit_url"),
        "trigger": snapshot.get("trigger"),
        "assessed_at": snapshot.get("assessed_at"),
        "fit_score": fit_score.get("value") if isinstance(fit_score, dict) else None,
        "summary": summary,
        "changed_files": snapshot.get("changed_files", []),
    }


def create_app(
    *,
    settings: Settings | None = None,
    store: SQLiteStore | None = None,
    github_client: Any | None = None,
    job_search_client: Any | None = None,
    telegram_service: Any | None = None,
    start_monitor: bool = True,
) -> FastAPI:
    settings = settings or Settings.from_env()
    store = store or SQLiteStore(settings.database_path, journal_mode=settings.sqlite_journal_mode)
    github_client = github_client or GitHubClient(settings)
    llm_interpreter = LLMInterpreter(settings)
    job_search_client = job_search_client or JSearchClient(settings)
    telegram_service = telegram_service or TelegramService(settings, store)
    monitor = MonitorService(
        store,
        github_client,
        llm_interpreter,
        settings.poll_interval_seconds,
        telegram_service=telegram_service,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if start_monitor and settings.monitoring_enabled:
            await monitor.start()
        yield
        await monitor.stop()

    app = FastAPI(
        title="SkillPath AI",
        version="1.0.0",
        description="Evidence-backed GitHub skill assessment with automatic commit reassessment.",
        lifespan=lifespan,
    )
    app.state.store = store
    app.state.monitor = monitor
    app.state.settings = settings
    app.state.job_search_client = job_search_client
    app.state.telegram_service = telegram_service

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, error: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"error": {"code": error.code, "message": error.message, "details": error.details}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_request",
                    "message": "Check the submitted fields and try again.",
                    "details": error.errors(),
                }
            },
        )

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "SkillPath AI",
            "monitoring_enabled": bool(settings.monitoring_enabled and start_monitor),
            "llm": llm_interpreter.status(),
            "job_search": job_search_client.status(),
            "telegram": telegram_service.status(),
        }

    @app.post("/api/jobs", status_code=201)
    async def create_job(payload: JobCreateRequest) -> dict[str, Any]:
        source_url = validate_public_http_url(payload.source_url, label="Job posting URL")
        description = payload.description.strip()
        if len(description) < 30:
            raise AppError(
                "job_description_too_short",
                "Paste enough job-description text to identify real requirements; the source URL will be retained.",
                422,
            )
        skills = extract_job_skills(description)
        job = store.create_job(
            title=payload.title.strip(),
            company=payload.company.strip(),
            source_url=source_url,
            description=description,
            skills=skills,
        )
        warning = None
        if not skills:
            warning = (
                "No supported skill phrases were extracted from the provided description. The URL and description were retained, "
                "but add explicit skill requirements before connecting a repository."
            )
        return {"job": job, "warning": warning}

    @app.post("/api/jobs/fetch")
    async def fetch_job_description(payload: JobFetchRequest) -> dict[str, str]:
        return await fetch_job_text(payload.source_url)

    @app.post("/api/job-search")
    async def search_jobs(payload: JobSearchRequest) -> dict[str, Any]:
        return await job_search_client.search(
            query=payload.query,
            country=payload.country,
            location=payload.location,
            date_posted=payload.date_posted,
        )

    @app.get("/api/jobs/{job_id}")
    async def get_job(job_id: int) -> dict[str, Any]:
        job = store.get_job(job_id)
        if not job:
            raise AppError("job_not_found", "Job was not found.", 404)
        return {"job": job}

    @app.post("/api/repositories", status_code=201)
    async def connect_repository(payload: RepositoryCreateRequest) -> dict[str, Any]:
        job = store.get_job(payload.job_id)
        if not job:
            raise AppError("job_not_found", "Create or select a job before connecting a repository.", 404)
        if not job.get("skills"):
            raise AppError(
                "no_supported_job_skills",
                "No supported skills were extracted from this job description. Add explicit requirements before assessment.",
                422,
            )
        inspection = await github_client.inspect_repository(payload.repository_url)
        repository_url = inspection.get("repository_url")
        owner = inspection.get("owner")
        name = inspection.get("name")
        default_branch = inspection.get("default_branch")
        if not all(isinstance(value, str) and value for value in (repository_url, owner, name, default_branch)):
            raise AppError("github_invalid_response", "GitHub inspection did not include repository metadata.", 502)
        repository = store.find_repository(payload.job_id, repository_url)
        created_repository = repository is None
        if repository is None:
            repository = store.create_repository(
                job_id=payload.job_id,
                repository_url=repository_url,
                owner=owner,
                name=name,
                default_branch=default_branch,
            )
            snapshot, created_snapshot = await monitor.create_assessment_from_inspection(
                int(repository["id"]), inspection, trigger="initial_scan"
            )
            repository = store.get_repository(int(repository["id"])) or repository
        else:
            store.update_repository_metadata(
                int(repository["id"]), owner=owner, name=name, default_branch=default_branch
            )
            known_sha = repository.get("latest_known_sha")
            changed_files: list[dict[str, Any]] = []
            if isinstance(known_sha, str) and known_sha and known_sha != inspection.get("commit_sha"):
                try:
                    comparison = await github_client.compare_commits(repository, known_sha, inspection["commit_sha"])
                    if isinstance(comparison, list):
                        changed_files = comparison
                except AppError:
                    pass
            snapshot, created_snapshot = await monitor.create_assessment_from_inspection(
                int(repository["id"]),
                inspection,
                trigger="manual_scan",
                changed_files=changed_files,
                previous_sha=known_sha if isinstance(known_sha, str) else None,
            )
            repository = store.get_repository(int(repository["id"])) or repository
        return {
            "repository": _public_repository(repository),
            "snapshot": snapshot,
            "created_repository": created_repository,
            "created_snapshot": created_snapshot,
            "message": "Repository connected and initial evidence assessment completed."
            if created_repository
            else "Repository was already connected; the current revision was checked without duplicating an assessment.",
        }

    @app.get("/api/repositories/{repository_id}/overview")
    async def repository_overview(repository_id: int) -> dict[str, Any]:
        repository = store.get_repository_with_job(repository_id)
        if not repository:
            raise AppError("repository_not_found", "Repository was not found.", 404)
        snapshot = store.latest_snapshot(repository_id)
        return {
            "repository": _public_repository(repository),
            "job": repository.get("job"),
            "latest_snapshot": snapshot,
            "events": store.events(repository_id),
            "llm": llm_interpreter.status(),
            "telegram": telegram_service.status(repository_id),
        }

    @app.post("/api/repositories/{repository_id}/scan")
    async def manually_scan_repository(repository_id: int) -> dict[str, Any]:
        repository = store.get_repository_with_job(repository_id)
        if not repository:
            raise AppError("repository_not_found", "Repository was not found.", 404)
        inspection = await github_client.inspect_repository(str(repository["repository_url"]))
        known_sha = repository.get("latest_known_sha")
        changed_files: list[dict[str, Any]] = []
        if isinstance(known_sha, str) and known_sha and known_sha != inspection.get("commit_sha"):
            try:
                candidate = await github_client.compare_commits(repository, known_sha, inspection["commit_sha"])
                if isinstance(candidate, list):
                    changed_files = candidate
            except AppError:
                pass
        snapshot, created = await monitor.create_assessment_from_inspection(
            repository_id,
            inspection,
            trigger="manual_scan",
            changed_files=changed_files,
            previous_sha=known_sha if isinstance(known_sha, str) else None,
        )
        return {
            "snapshot": snapshot,
            "created_snapshot": created,
            "message": "Manual scan completed." if created else "This commit already has an assessment; no duplicate was created.",
        }

    @app.get("/api/repositories/{repository_id}/history")
    async def repository_history(repository_id: int) -> dict[str, Any]:
        if not store.get_repository(repository_id):
            raise AppError("repository_not_found", "Repository was not found.", 404)
        snapshots = store.history(repository_id)
        return {"history": [_history_summary(snapshot) for snapshot in snapshots]}

    @app.get("/api/repositories/{repository_id}/monitor")
    async def monitoring_status(repository_id: int) -> dict[str, Any]:
        repository = store.get_repository(repository_id)
        if not repository:
            raise AppError("repository_not_found", "Repository was not found.", 404)
        return {
            "repository_id": repository_id,
            "monitor": {
                "enabled": repository.get("monitor_enabled"),
                "state": repository.get("monitor_state"),
                "poll_interval_seconds": settings.poll_interval_seconds,
                "last_checked_at": repository.get("last_checked_at"),
                "last_assessed_at": repository.get("last_assessed_at"),
                "last_error": {
                    "code": repository.get("last_error_code"),
                    "message": repository.get("last_error_message"),
                }
                if repository.get("last_error_code")
                else None,
            },
            "events": store.events(repository_id),
        }

    @app.put("/api/repositories/{repository_id}/monitor")
    async def update_monitor(repository_id: int, payload: MonitorUpdateRequest) -> dict[str, Any]:
        if not store.get_repository(repository_id):
            raise AppError("repository_not_found", "Repository was not found.", 404)
        store.set_monitor_enabled(repository_id, payload.enabled)
        return await monitoring_status(repository_id)

    @app.post("/api/repositories/{repository_id}/monitor/check")
    async def monitor_check(repository_id: int) -> dict[str, Any]:
        result = await monitor.check_repository(repository_id, origin="manual_monitor_check")
        return {"result": result, "monitor": await monitoring_status(repository_id)}

    @app.get("/api/repositories/{repository_id}/telegram")
    async def telegram_status(repository_id: int) -> dict[str, Any]:
        if not store.get_repository(repository_id):
            raise AppError("repository_not_found", "Repository was not found.", 404)
        return {"repository_id": repository_id, "telegram": telegram_service.status(repository_id)}

    @app.post("/api/repositories/{repository_id}/telegram/pair", status_code=201)
    async def create_telegram_pairing(repository_id: int) -> dict[str, Any]:
        if not store.get_repository(repository_id):
            raise AppError("repository_not_found", "Repository was not found.", 404)
        return {"repository_id": repository_id, "pairing": telegram_service.create_pairing(repository_id)}

    @app.post("/api/integrations/telegram/webhook")
    async def telegram_webhook(
        request: Request,
        x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
    ) -> dict[str, bool]:
        if not telegram_service.verify_webhook_secret(x_telegram_bot_api_secret_token):
            raise AppError("telegram_webhook_unauthorized", "Telegram webhook authentication failed.", 401)
        try:
            update = await request.json()
        except ValueError as error:
            raise AppError("invalid_telegram_update", "Telegram sent an invalid webhook update.", 422) from error
        if not isinstance(update, dict):
            raise AppError("invalid_telegram_update", "Telegram sent an invalid webhook update.", 422)
        await telegram_service.handle_webhook_update(update)
        return {"ok": True}

    @app.get("/api/assessments/{snapshot_id}")
    async def get_assessment(snapshot_id: int) -> dict[str, Any]:
        snapshot = store.get_snapshot(snapshot_id)
        if not snapshot:
            raise AppError("assessment_not_found", "Assessment snapshot was not found.", 404)
        repository = store.get_repository_with_job(int(snapshot["repository_id"]))
        return {"snapshot": snapshot, "repository": _public_repository(repository or {}), "job": (repository or {}).get("job")}

    @app.get("/api/assessments/{snapshot_id}/compare/{previous_snapshot_id}")
    async def compare_snapshot(snapshot_id: int, previous_snapshot_id: int) -> dict[str, Any]:
        current = store.get_snapshot(snapshot_id)
        previous = store.get_snapshot(previous_snapshot_id)
        if not current or not previous:
            raise AppError("assessment_not_found", "One or both assessment snapshots were not found.", 404)
        if current["repository_id"] != previous["repository_id"]:
            raise AppError("assessment_repository_mismatch", "Only snapshots for the same repository can be compared.", 422)
        comparison = compare_assessments(previous["assessment"], current["assessment"])
        comparison.update(
            {
                "previous_snapshot": _history_summary(previous),
                "current_snapshot": _history_summary(current),
                "changed_files": current.get("changed_files", []),
            }
        )
        return comparison

    if FRONTEND_DIRECTORY.exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIRECTORY)), name="static")

        @app.get("/", include_in_schema=False)
        async def dashboard() -> FileResponse:
            return FileResponse(FRONTEND_DIRECTORY / "index.html")

    return app


app = create_app()
