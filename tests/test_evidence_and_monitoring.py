"""Focused evidence and monitoring tests using a local async GitHub double.

These tests intentionally do not execute cloned code or make network calls.  The
fake client has the same asynchronous surface as ``GitHubClient`` so the app's
real ingestion, persistence, monitor, comparison, and error-handling paths are
exercised.
"""

from __future__ import annotations

import asyncio
from copy import deepcopy
import json
import os
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.errors import GitHubError
from backend.skills import build_assessment, extract_job_skills, validate_evidence


INITIAL_SHA = "1" * 40
UPDATED_SHA = "2" * 40
REPOSITORY_URL = "https://github.com/demo/portfolio"


def _settings(tmp_path, *, github_token: str | None = None) -> Settings:
    return Settings(
        database_path=str(tmp_path / "career-coach-test.sqlite3"),
        github_token=github_token,
        github_api_url="https://api.github.invalid",
        github_timeout_seconds=3,
        github_max_files=20,
        github_max_file_bytes=100_000,
        github_max_total_bytes=500_000,
        poll_interval_seconds=10,
        monitoring_enabled=True,
        openai_api_key=None,
        openai_model="test-model",
        enable_llm_explanations=False,
        xai_api_key=None,
        xai_api_url="https://api.x.ai/v1",
        xai_model=None,
        enable_xai_fallback=False,
        jsearch_api_key=None,
        jsearch_api_url="https://jsearch.p.rapidapi.com",
        jsearch_timeout_seconds=3,
        telegram_bot_token=None,
        telegram_webhook_secret=None,
        telegram_api_url="https://api.telegram.org",
        telegram_notifications_enabled=False,
        azure_key_vault_url=None,
        applicationinsights_connection_string=None,
    )


def _inspection(sha: str, source: str) -> dict[str, Any]:
    """Return the shape produced by the real bounded GitHub inspector."""

    return {
        "owner": "demo",
        "name": "portfolio",
        "repository_url": REPOSITORY_URL,
        "default_branch": "main",
        "commit_sha": sha,
        "commit_url": f"{REPOSITORY_URL}/commit/{sha}",
        "commit_date": "2026-10-16T00:00:00Z",
        "files": [
            {
                "path": "src/server.py",
                "content": source,
                "size": len(source.encode("utf-8")),
                "sha": f"blob-{sha[:12]}",
                "html_url": f"{REPOSITORY_URL}/blob/{sha}/src/server.py",
                "context_only": False,
            }
        ],
        "inspection": {
            "inspected_at": "2026-10-16T00:00:00Z",
            "tree_truncated": False,
            "candidate_file_count": 1,
            "inspected_file_count": 1,
            "inspected_byte_count": len(source.encode("utf-8")),
            "max_files": 20,
            "max_file_bytes": 100_000,
            "max_total_bytes": 500_000,
            "skipped": [],
        },
    }


class FakeAsyncGitHubClient:
    """In-memory GitHub API double; it never reaches a network or runs code."""

    def __init__(self, inspections: dict[str, dict[str, Any]]) -> None:
        self.inspections = inspections
        self.current_sha = INITIAL_SHA
        self.inspect_calls: list[tuple[str, str | None]] = []
        self.latest_commit_calls = 0
        self.compare_calls: list[tuple[str, str]] = []
        self.comparisons: dict[tuple[str, str], list[dict[str, str]]] = {}
        self.latest_error: GitHubError | None = None

    async def inspect_repository(self, repository_url: str, ref: str | None = None) -> dict[str, Any]:
        self.inspect_calls.append((repository_url, ref))
        requested_sha = ref or self.current_sha
        try:
            return deepcopy(self.inspections[requested_sha])
        except KeyError as error:  # makes an incorrect reassessment target fail the test loudly
            raise AssertionError(f"No fake inspection was configured for {requested_sha}.") from error

    async def latest_commit(self, repository: dict[str, Any]) -> dict[str, str]:
        self.latest_commit_calls += 1
        if self.latest_error:
            raise self.latest_error
        return {
            "sha": self.current_sha,
            "url": f"{REPOSITORY_URL}/commit/{self.current_sha}",
        }

    async def compare_commits(
        self, repository: dict[str, Any], previous_sha: str, current_sha: str
    ) -> list[dict[str, str]]:
        self.compare_calls.append((previous_sha, current_sha))
        return deepcopy(self.comparisons.get((previous_sha, current_sha), []))


class FakeJobSearchClient:
    """Server-side discovery double for testing the API route without a provider key."""

    def status(self) -> dict[str, Any]:
        return {"available": True, "provider": "JSearch", "max_results": 12}

    async def search(self, **_: Any) -> dict[str, Any]:
        return {
            "provider": "JSearch",
            "results": [
                {
                    "title": "Python Intern",
                    "company": "Example Careers",
                    "posting_url": "https://jobs.example.org/python-intern",
                    "description": "Required: Python and FastAPI for backend services.",
                }
            ],
            "notice": "Review before saving.",
        }


class FakeTelegramService:
    """Route-level Telegram double; no bot token or external request is involved."""

    def __init__(self) -> None:
        self.updates: list[dict[str, Any]] = []

    def status(self, repository_id: int | None = None) -> dict[str, Any]:
        del repository_id
        return {"available": True, "enabled": True, "state": "unpaired"}

    def create_pairing(self, repository_id: int) -> dict[str, Any]:
        return {
            "state": "pairing_pending",
            "repository_id": repository_id,
            "expires_at": "2026-10-16T00:10:00Z",
            "start_command": "/start one-time-test-code",
            "deep_link": None,
        }

    def verify_webhook_secret(self, received: str | None) -> bool:
        return received == "test-webhook-secret"

    async def handle_webhook_update(self, update: dict[str, Any]) -> dict[str, Any]:
        self.updates.append(update)
        return {"handled": True}

    async def notify_reassessment(self, **_: Any) -> dict[str, Any]:
        return {"sent": False, "reason": "test"}


@pytest.fixture(scope="session", autouse=True)
def _isolate_default_app_database(tmp_path_factory):
    """The module-level FastAPI app is created on import, so keep its DB out of the repo."""

    original = os.environ.get("DATABASE_PATH")
    os.environ["DATABASE_PATH"] = str(
        tmp_path_factory.mktemp("default-app-database") / "bootstrap.sqlite3"
    )
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = original


def _create_app(
    settings: Settings,
    fake_github: FakeAsyncGitHubClient,
    *,
    job_search_client: Any | None = None,
    telegram_service: Any | None = None,
):
    # Delayed import lets the autouse fixture isolate backend.main's module-level app database.
    from backend.main import create_app

    return create_app(
        settings=settings,
        github_client=fake_github,
        job_search_client=job_search_client,
        telegram_service=telegram_service,
        start_monitor=False,
    )


def _create_job_and_repository(client: TestClient) -> tuple[int, dict[str, Any]]:
    job_response = client.post(
        "/api/jobs",
        json={
            "title": "Backend Engineering Intern",
            "company": "Example Careers",
            "source_url": "https://jobs.example.org/backend-intern",
            "description": (
                "Required qualifications include Python and FastAPI for backend services. "
                "Preferred: SQL database experience for reporting features."
            ),
        },
    )
    assert job_response.status_code == 201, job_response.text
    job = job_response.json()["job"]
    assert job["source_url"] == "https://jobs.example.org/backend-intern"

    repository_response = client.post(
        "/api/repositories",
        json={"job_id": job["id"], "repository_url": REPOSITORY_URL},
    )
    assert repository_response.status_code == 201, repository_response.text
    return int(repository_response.json()["repository"]["id"]), repository_response.json()


def _by_key(assessment: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["skill_key"]): item
        for item in assessment["skill_assessments"]
        if isinstance(item, dict)
    }


def test_deterministic_assessment_links_real_evidence_and_labels_absence_carefully() -> None:
    requirements = extract_job_skills(
        "Required qualifications: Python and FastAPI. Preferred: SQL database experience."
    )
    job = {"title": "Backend intern", "company": "Example", "skills": requirements}
    inspected = _inspection(
        INITIAL_SHA,
        "# This comment must not be treated as a FastAPI implementation.\n"
        "from pathlib import Path\n"
        "\n"
        "def read_project_name() -> str:\n"
        "    return Path('README.md').stem\n",
    )

    assessment = build_assessment(job, inspected)
    skills = _by_key(assessment)

    python = skills["python"]
    assert python["status_code"] == "demonstrated"
    assert python["evidence"]
    for evidence in python["evidence"]:
        assert evidence["path"] == "src/server.py"
        assert validate_evidence(evidence, inspected["files"])
    assert any("from pathlib import Path" in evidence["excerpt"] for evidence in python["evidence"])

    fabricated = dict(python["evidence"][0])
    fabricated["excerpt"] = "I have extensive Python mastery."
    assert not validate_evidence(fabricated, inspected["files"])

    fastapi = skills["fastapi"]
    assert fastapi["status_code"] == "not_demonstrated"
    assert fastapi["evidence"] == []
    assert "not demonstrated in this inspected scope" in fastapi["explanation"]
    assert "not proof that the student lacks the skill" in " ".join(fastapi["limitations"])
    assert "not proof that the student lacks the skill" in assessment["scope_notice"]
    assert any(
        item["skill"] == "FastAPI" and item["type"] == "future_recommendation"
        for item in assessment["recommendations"]
    )


def test_job_allows_an_unknown_company_but_requires_a_traceable_source_url(tmp_path) -> None:
    initial = _inspection(INITIAL_SHA, "from pathlib import Path\n")
    app = _create_app(_settings(tmp_path), FakeAsyncGitHubClient({INITIAL_SHA: initial}))

    with TestClient(app) as client:
        response = client.post(
            "/api/jobs",
            json={
                "title": "Backend Engineering Intern",
                "source_url": "https://jobs.example.org/backend-intern",
                "description": "Required qualifications include Python and FastAPI for backend services.",
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["job"]["company"] == "Company not specified"

        missing_source = client.post(
            "/api/jobs",
            json={
                "title": "Backend Engineering Intern",
                "description": "Required qualifications include Python and FastAPI for backend services.",
            },
        )
        assert missing_source.status_code == 422


def test_optional_integration_routes_are_server_side_and_webhook_authenticated(tmp_path) -> None:
    initial = _inspection(INITIAL_SHA, "from fastapi import FastAPI\napp = FastAPI()\n")
    fake_github = FakeAsyncGitHubClient({INITIAL_SHA: initial})
    fake_search = FakeJobSearchClient()
    fake_telegram = FakeTelegramService()
    app = _create_app(
        _settings(tmp_path),
        fake_github,
        job_search_client=fake_search,
        telegram_service=fake_telegram,
    )

    with TestClient(app) as client:
        search_response = client.post(
            "/api/job-search",
            json={"query": "python intern", "country": "in", "location": "Pune"},
        )
        assert search_response.status_code == 200
        search_payload = search_response.json()
        assert search_payload["results"][0]["posting_url"] == "https://jobs.example.org/python-intern"
        assert "secret" not in json.dumps(search_payload).lower()

        repository_id, _ = _create_job_and_repository(client)
        pairing_response = client.post(f"/api/repositories/{repository_id}/telegram/pair")
        assert pairing_response.status_code == 201
        assert pairing_response.json()["pairing"]["state"] == "pairing_pending"

        rejected_webhook = client.post("/api/integrations/telegram/webhook", json={"update_id": 1})
        assert rejected_webhook.status_code == 401

        accepted_webhook = client.post(
            "/api/integrations/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
            json={"update_id": 2},
        )
        assert accepted_webhook.status_code == 200
        assert accepted_webhook.json() == {"ok": True}
        assert fake_telegram.updates == [{"update_id": 2}]


def test_fake_github_initial_snapshot_then_scheduled_commit_reassessment(tmp_path) -> None:
    initial = _inspection(
        INITIAL_SHA,
        "from pathlib import Path\n\n"
        "def read_project_name() -> str:\n"
        "    return Path('README.md').stem\n",
    )
    updated = _inspection(
        UPDATED_SHA,
        "from fastapi import FastAPI\n\n"
        "app = FastAPI()\n\n"
        "@app.get('/health')\n"
        "def health() -> dict[str, str]:\n"
        "    return {'status': 'ok'}\n",
    )
    fake_github = FakeAsyncGitHubClient({INITIAL_SHA: initial, UPDATED_SHA: updated})
    fake_github.comparisons[(INITIAL_SHA, UPDATED_SHA)] = [
        {"path": "src/server.py", "status": "modified"}
    ]
    app = _create_app(_settings(tmp_path, github_token="server-only-github-token"), fake_github)

    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        health_payload = health.json()
        assert health_payload["llm"]["mode"] == "deterministic"
        assert health_payload["llm"]["available"] is False
        assert "OPENAI_API_KEY" in health_payload["llm"]["reason"]
        assert "server-only-github-token" not in json.dumps(health_payload)

        repository_id, connected = _create_job_and_repository(client)
        assert connected["created_repository"] is True
        assert connected["created_snapshot"] is True
        initial_snapshot = connected["snapshot"]
        assert initial_snapshot["commit_sha"] == INITIAL_SHA
        assert connected["repository"]["repository_url"] == REPOSITORY_URL
        assert connected["repository"]["last_checked_at"] is not None
        assert fake_github.inspect_calls == [(REPOSITORY_URL, None)]
        assert _by_key(initial_snapshot["assessment"])["fastapi"]["status_code"] == "not_demonstrated"
        assert initial_snapshot["llm"]["available"] is False

        # This calls the scheduler's real check_all path, not the manual scan endpoint.
        fake_github.current_sha = UPDATED_SHA

        async def scheduled_reassessment_and_duplicate_check() -> dict[str, Any]:
            await app.state.monitor.check_all()
            return await app.state.monitor.check_repository(repository_id, origin="scheduled_poll")

        duplicate_result = asyncio.run(scheduled_reassessment_and_duplicate_check())
        assert duplicate_result["event"] == "no_change"
        assert fake_github.inspect_calls == [(REPOSITORY_URL, None), (REPOSITORY_URL, UPDATED_SHA)]
        assert fake_github.compare_calls == [(INITIAL_SHA, UPDATED_SHA)]

        history_response = client.get(f"/api/repositories/{repository_id}/history")
        assert history_response.status_code == 200
        history = history_response.json()["history"]
        assert [item["commit_sha"] for item in history] == [UPDATED_SHA, INITIAL_SHA]
        assert history[0]["trigger"] == "automatic_reassessment"
        assert history[0]["changed_files"] == [{"path": "src/server.py", "status": "modified"}]

        latest_snapshot_id = int(history[0]["id"])
        comparison_response = client.get(
            f"/api/assessments/{latest_snapshot_id}/compare/{initial_snapshot['id']}"
        )
        assert comparison_response.status_code == 200
        comparison = comparison_response.json()
        fastapi_change = next(
            item for item in comparison["skill_changes"] if item["skill_key"] == "fastapi"
        )
        assert fastapi_change["status_changed"] is True
        assert fastapi_change["before_status"] == "not demonstrated in this inspected scope"
        assert fastapi_change["after_status"] == "demonstrated"
        assert any(item["path"] == "src/server.py" for item in fastapi_change["evidence_added"])

        overview_response = client.get(f"/api/repositories/{repository_id}/overview")
        assert overview_response.status_code == 200
        overview = overview_response.json()
        updated_skills = _by_key(overview["latest_snapshot"]["assessment"])
        assert updated_skills["fastapi"]["status_code"] == "demonstrated"
        assert updated_skills["fastapi"]["changed_evidence"]
        assert all(
            item["changed_in_commit"] for item in updated_skills["fastapi"]["changed_evidence"]
        )
        assert overview["events"][0]["event_type"] == "automatic_reassessment_completed"
        assert overview["repository"]["last_checked_at"] is not None
        assert "server-only-github-token" not in json.dumps(overview)


def test_monitor_records_sanitized_github_rate_limit_error(tmp_path) -> None:
    initial = _inspection(
        INITIAL_SHA,
        "from pathlib import Path\n\n"
        "def read_project_name() -> str:\n"
        "    return Path('README.md').stem\n",
    )
    fake_github = FakeAsyncGitHubClient({INITIAL_SHA: initial})
    app = _create_app(_settings(tmp_path), fake_github)

    with TestClient(app) as client:
        repository_id, _ = _create_job_and_repository(client)
        fake_github.latest_error = GitHubError(
            "github_rate_limited",
            "GitHub rate limit reached. The monitor will retry on its next check.",
            429,
        )

        check_response = client.post(f"/api/repositories/{repository_id}/monitor/check")
        assert check_response.status_code == 429
        error = check_response.json()["error"]
        assert error["code"] == "github_rate_limited"
        assert "rate limit" in error["message"].lower()

        monitor_response = client.get(f"/api/repositories/{repository_id}/monitor")
        assert monitor_response.status_code == 200
        monitor = monitor_response.json()["monitor"]
        assert monitor["state"] == "error"
        assert monitor["last_error"]["code"] == "github_rate_limited"
        assert "rate limit" in monitor["last_error"]["message"].lower()


def test_job_and_repository_crud_lifecycle(tmp_path) -> None:
    initial = _inspection(
        INITIAL_SHA,
        "from fastapi import FastAPI\n\napp = FastAPI()\n",
    )
    fake_github = FakeAsyncGitHubClient({INITIAL_SHA: initial})
    app = _create_app(_settings(tmp_path), fake_github)

    with TestClient(app) as client:
        # 1. Verify list_jobs is initially empty
        res = client.get("/api/jobs")
        assert res.status_code == 200
        assert res.json()["jobs"] == []

        # 2. Create a job
        job_res = client.post(
            "/api/jobs",
            json={
                "title": "Backend Intern",
                "company": "Tech Corp",
                "source_url": "https://jobs.example.org/backend-intern",
                "description": "Requires Python and FastAPI for backend services. Docker preferred.",
            },
        )
        assert job_res.status_code == 201
        job = job_res.json()["job"]
        job_id = job["id"]

        # 3. List jobs returns created job
        res = client.get("/api/jobs")
        assert res.status_code == 200
        jobs = res.json()["jobs"]
        assert len(jobs) == 1
        assert jobs[0]["id"] == job_id
        assert jobs[0]["title"] == "Backend Intern"

        # 4. Update job with new title, description, company
        update_res = client.put(
            f"/api/jobs/{job_id}",
            json={
                "title": "Senior Backend Engineer",
                "company": "Tech Global",
                "source_url": "https://jobs.example.org/senior-backend",
                "description": "Expert in Python, FastAPI, and SQL databases required for high throughput.",
            },
        )
        assert update_res.status_code == 200
        updated = update_res.json()["job"]
        assert updated["title"] == "Senior Backend Engineer"
        assert updated["company"] == "Tech Global"
        extracted_skills = {s["key"] for s in updated["skills"]}
        assert "fastapi" in extracted_skills
        assert "sql_databases" in extracted_skills

        # 5. Connect repository to this job
        repo_res = client.post(
            "/api/repositories",
            json={"job_id": job_id, "repository_url": REPOSITORY_URL},
        )
        assert repo_res.status_code == 201
        repo_id = repo_res.json()["repository"]["id"]

        # 6. List repositories filtered by job_id
        list_repo_res = client.get(f"/api/repositories?job_id={job_id}")
        assert list_repo_res.status_code == 200
        repos = list_repo_res.json()["repositories"]
        assert len(repos) == 1
        assert repos[0]["id"] == repo_id

        # 7. List all repositories without job_id
        list_all_res = client.get("/api/repositories")
        assert list_all_res.status_code == 200
        assert len(list_all_res.json()["repositories"]) == 1

        # 8. Delete repository
        del_repo_res = client.delete(f"/api/repositories/{repo_id}")
        assert del_repo_res.status_code == 200
        assert del_repo_res.json() == {"deleted": True, "repository_id": repo_id}

        # Verify repository is gone
        overview_res = client.get(f"/api/repositories/{repo_id}/overview")
        assert overview_res.status_code == 404

        # Verify list repositories is now empty
        list_repo_res2 = client.get(f"/api/repositories?job_id={job_id}")
        assert list_repo_res2.status_code == 200
        assert len(list_repo_res2.json()["repositories"]) == 0

        # Reconnect repository to test cascade delete of job
        repo_res2 = client.post(
            "/api/repositories",
            json={"job_id": job_id, "repository_url": REPOSITORY_URL},
        )
        assert repo_res2.status_code == 201
        repo_id2 = repo_res2.json()["repository"]["id"]

        # 9. Delete job -> cascades to repository and snapshots
        del_job_res = client.delete(f"/api/jobs/{job_id}")
        assert del_job_res.status_code == 200
        assert del_job_res.json() == {"deleted": True, "job_id": job_id}

        # Verify job is gone
        get_job_res = client.get(f"/api/jobs/{job_id}")
        assert get_job_res.status_code == 404

        # Verify repository was cascaded
        overview_res2 = client.get(f"/api/repositories/{repo_id2}/overview")
        assert overview_res2.status_code == 404

        # 10. Non-existent entity checks return 404
        assert client.get("/api/jobs/99999").status_code == 404
        assert client.delete("/api/jobs/99999").status_code == 404
        assert client.delete("/api/repositories/99999").status_code == 404
        assert client.get("/api/repositories?job_id=99999").status_code == 404

