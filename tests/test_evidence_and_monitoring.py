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


from tests.conftest import (
    INITIAL_SHA,
    UPDATED_SHA,
    REPOSITORY_URL,
    FakeAsyncGitHubClient,
    FakeJobSearchClient,
    FakeTelegramService,
    create_test_app as _create_app,
    make_fake_inspection as _inspection,
    make_test_settings,
)


def _settings(tmp_path, *, github_token: str | None = None) -> Settings:
    return make_test_settings(
        tmp_path,
        database_path=str(tmp_path / "career-coach-test.sqlite3"),
        github_token=github_token,
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
        assert missing_source.status_code == 201
        assert "skillpath.local" in missing_source.json()["job"]["source_url"]


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


def test_github_webhook_push_triggers_reassessment(tmp_path) -> None:
    """A GitHub push webhook triggers immediate reassessment without waiting for the poll cycle."""
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
    app = _create_app(_settings(tmp_path), fake_github)

    with TestClient(app) as client:
        repository_id, connected = _create_job_and_repository(client)
        assert connected["created_repository"] is True

        # Simulate a GitHub push event with a new commit
        fake_github.current_sha = UPDATED_SHA
        push_payload = {
            "ref": "refs/heads/main",
            "after": UPDATED_SHA,
            "repository": {
                "full_name": "demo/portfolio",
                "html_url": REPOSITORY_URL,
            },
        }
        webhook_response = client.post(
            "/api/integrations/github/webhook",
            json=push_payload,
            headers={"X-GitHub-Event": "push"},
        )
        assert webhook_response.status_code == 200
        webhook_data = webhook_response.json()
        assert webhook_data["ok"] is True
        assert webhook_data["event"] == "push"
        assert webhook_data["repository"] == "demo/portfolio"
        assert webhook_data["reassessed"] == 1
        assert webhook_data["results"][0]["event"] == "reassessed"
        assert webhook_data["results"][0]["commit_sha"] == UPDATED_SHA

        # Verify the snapshot was actually created
        history_response = client.get(f"/api/repositories/{repository_id}/history")
        assert history_response.status_code == 200
        history = history_response.json()["history"]
        assert len(history) == 2
        assert history[0]["commit_sha"] == UPDATED_SHA

        # Test ping event
        ping_response = client.post(
            "/api/integrations/github/webhook",
            json={"zen": "Keep it logically awesome."},
            headers={"X-GitHub-Event": "ping"},
        )
        assert ping_response.status_code == 200
        assert ping_response.json()["event"] == "ping"

        # Test untracked repository
        untracked_response = client.post(
            "/api/integrations/github/webhook",
            json={
                "ref": "refs/heads/main",
                "repository": {"full_name": "unknown/repo"},
            },
            headers={"X-GitHub-Event": "push"},
        )
        assert untracked_response.status_code == 200
        assert untracked_response.json()["reassessed"] == 0

        # Test ignored event type
        issues_response = client.post(
            "/api/integrations/github/webhook",
            json={"action": "opened"},
            headers={"X-GitHub-Event": "issues"},
        )
        assert issues_response.status_code == 200
        assert issues_response.json()["event"] == "issues"


def test_github_webhook_with_signature_verification(tmp_path) -> None:
    """When GITHUB_WEBHOOK_SECRET is set, the webhook rejects unsigned requests."""
    import hashlib
    import hmac as hmac_module
    import json as json_module

    initial = _inspection(INITIAL_SHA, "from pathlib import Path\n")
    fake_github = FakeAsyncGitHubClient({INITIAL_SHA: initial})
    base = _settings(tmp_path)
    # Create settings with webhook secret by replacing the field
    settings_with_secret = Settings(
        **{
            **{f: getattr(base, f) for f in base.__dataclass_fields__},
            "github_webhook_secret": "test-github-secret-123",
        }
    )
    app = _create_app(settings_with_secret, fake_github)

    with TestClient(app) as client:
        # Request without signature should be rejected
        no_sig_response = client.post(
            "/api/integrations/github/webhook",
            json={"zen": "test"},
            headers={"X-GitHub-Event": "ping"},
        )
        assert no_sig_response.status_code == 401

        # Request with wrong signature should be rejected
        wrong_sig_response = client.post(
            "/api/integrations/github/webhook",
            json={"zen": "test"},
            headers={
                "X-GitHub-Event": "ping",
                "X-Hub-Signature-256": "sha256=wrong",
            },
        )
        assert wrong_sig_response.status_code == 401

        # Request with correct signature should succeed
        body = json_module.dumps({"zen": "test"}).encode("utf-8")
        correct_sig = "sha256=" + hmac_module.new(
            b"test-github-secret-123",
            body,
            hashlib.sha256,
        ).hexdigest()
        correct_response = client.post(
            "/api/integrations/github/webhook",
            content=body,
            headers={
                "X-GitHub-Event": "ping",
                "X-Hub-Signature-256": correct_sig,
                "Content-Type": "application/json",
            },
        )
        assert correct_response.status_code == 200
        assert correct_response.json()["event"] == "ping"


def test_git_github_rule_and_enriched_comparison_matrix(tmp_path) -> None:
    """Verify git_github skill detection, contextualized recommendations, and full requirement_rows in comparison."""
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
    app = _create_app(_settings(tmp_path), fake_github)

    with TestClient(app) as client:
        job_res = client.post(
            "/api/jobs",
            json={
                "title": "Software Engineer Intern",
                "company": "Example Corp",
                "source_url": "https://jobs.example.org/swe-intern",
                "description": "Required: Python, FastAPI, automated testing, and version control with Git and GitHub.",
            },
        )
        assert job_res.status_code == 201
        job = job_res.json()["job"]
        skill_keys = {s["key"] for s in job["skills"]}
        assert "git_github" in skill_keys

        # Validate repository metadata endpoint
        val_res = client.get(f"/api/github/validate?repository_url={REPOSITORY_URL}")
        assert val_res.status_code == 200
        assert val_res.json()["valid"] is True
        assert val_res.json()["repository"]["name"] == "portfolio"

        repo_res = client.post(
            "/api/repositories",
            json={"job_id": job["id"], "repository_url": REPOSITORY_URL},
        )
        assert repo_res.status_code == 201
        repo_id = repo_res.json()["repository"]["id"]
        first_snapshot = repo_res.json()["snapshot"]
        skills_map = _by_key(first_snapshot["assessment"])

        # Git and GitHub is now demonstrated via version-controlled source evidence
        assert skills_map["git_github"]["status_code"] == "demonstrated"
        assert len(skills_map["git_github"]["evidence"]) >= 1

        # Contextualized recommendation references inspected file src/server.py
        testing_task = skills_map["automated_testing"]["next_evidence_contract"]["task"]
        assert "src/server.py" in testing_task

        # Advance commit and scan
        fake_github.current_sha = UPDATED_SHA
        scan_res = client.post(f"/api/repositories/{repo_id}/scan")
        assert scan_res.status_code == 200
        second_snapshot = scan_res.json()["snapshot"]

        comp_res = client.get(f"/api/assessments/{second_snapshot['id']}/compare/{first_snapshot['id']}")
        assert comp_res.status_code == 200
        comp = comp_res.json()
        assert "requirement_rows" in comp
        assert len(comp["requirement_rows"]) == len(job["skills"])
        assert any(s["skill_key"] == "fastapi" for s in comp["strengths"])
        assert any(g["skill_key"] == "automated_testing" for g in comp["top_gaps"])


def test_hydrorag_ai_ml_nlp_rag_extraction_and_manual_rescan_refresh(tmp_path) -> None:
    """Verify multi-skill AI/ML/NLP/Deep Learning extraction and HydroRAG code evidence detection."""
    hydrorag_source = (
        "from openai import OpenAI\n"
        "from langchain_chroma import Chroma\n"
        "from langchain_openai import OpenAIEmbeddings\n"
        "from langchain_text_splitters import RecursiveCharacterTextSplitter\n"
        "from langchain_community.document_loaders import PyPDFLoader\n"
        "from rank_bm25 import BM25Okapi\n"
        "\n"
        "def tokenize(text: str) -> list[str]:\n"
        "    return text.lower().split()\n"
        "\n"
        "class RAGEngine:\n"
        "    def __init__(self):\n"
        "        self.openai_client = OpenAI(api_key='test')\n"
        "        self.embeddings = OpenAIEmbeddings(model='text-embedding-3-small')\n"
        "        self.chroma = Chroma(persist_directory='chroma_db', embedding_function=self.embeddings)\n"
        "        self.bm25 = BM25Okapi([[' basil ', ' ph ']])\n"
        "\n"
        "    def dense_search(self, query: str):\n"
        "        return self.chroma.similarity_search_with_relevance_scores(query, k=4)\n"
        "\n"
        "    def bm25_search(self, query: str):\n"
        "        return self.bm25.get_scores(tokenize(query))\n"
        "\n"
        "    def generate_answer(self, query: str):\n"
        "        return self.openai_client.chat.completions.create(model='gpt-4o-mini', messages=[])\n"
    )
    inspected = _inspection(INITIAL_SHA, hydrorag_source)
    fake_github = FakeAsyncGitHubClient({INITIAL_SHA: inspected})
    app = _create_app(_settings(tmp_path), fake_github)

    with TestClient(app) as client:
        # 1. Exact truncated Jooble AI/ML snippet from Job #14
        job_res = client.post(
            "/api/jobs",
            json={
                "title": "AI/ML Engineer",
                "company": "Warrier AI Solutions Pvt Ltd - Zepcruit",
                "city": "Pune",
                "source_url": "https://in.jooble.org/jdp/-8513984833727808877",
                "description": (
                    "About the Role We are looking for a motivated AI/ML Engineer with 1-3 year of experience "
                    "to join our technology team. The ideal candidate should have strong fundamentals in "
                    "Machine Learning and Deep Learning, along with hands-on knowledge of Natural Language Processing (NLP..."
                ),
            },
        )
        assert job_res.status_code == 201
        job = job_res.json()["job"]
        extracted_keys = {s["key"] for s in job["skills"]}
        assert "machine_learning" in extracted_keys
        assert "deep_learning" in extracted_keys
        assert "nlp_text_processing" in extracted_keys

        # 2. Connect HydroRAG and verify multi-skill evidence
        repo_res = client.post(
            "/api/repositories",
            json={"job_id": job["id"], "repository_url": REPOSITORY_URL},
        )
        assert repo_res.status_code == 201
        repo_id = repo_res.json()["repository"]["id"]
        snap = repo_res.json()["snapshot"]
        by_key = _by_key(snap["assessment"])
        assert by_key["machine_learning"]["status_code"] == "demonstrated"
        assert by_key["nlp_text_processing"]["status_code"] == "demonstrated"
        assert by_key["deep_learning"]["status_code"] == "not_demonstrated"
        assert snap["assessment"]["fit_score"]["value"] == 67

        # 3. Update the job to include RAG, Embeddings, and LLM integration, then manual rescan at same SHA
        upd_res = client.put(
            f"/api/jobs/{job['id']}",
            json={
                "title": "AI/ML & RAG Engineer",
                "company": "Warrier AI Solutions",
                "source_url": "https://in.jooble.org/jdp/-8513984833727808877",
                "description": (
                    "Requires Python, Machine Learning, Deep Learning, Natural Language Processing (NLP), "
                    "Retrieval-Augmented Generation (RAG), vector search with Chroma, and OpenAI LLM integration."
                ),
            },
        )
        assert upd_res.status_code == 200
        rescan = client.post(f"/api/repositories/{repo_id}/scan")
        assert rescan.status_code == 200
        refreshed = rescan.json()["snapshot"]
        refreshed_keys = _by_key(refreshed["assessment"])
        assert refreshed_keys["retrieval_augmented_generation"]["status_code"] == "demonstrated"
        assert refreshed_keys["embeddings_vector_search"]["status_code"] == "demonstrated"
        assert refreshed_keys["llm_integration"]["status_code"] == "demonstrated"
        assert refreshed["assessment"]["fit_score"]["value"] >= 80



