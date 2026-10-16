"""Shared test fixtures and in-memory test doubles for SkillPath AI.

These fixtures isolate filesystem state, eliminate network requests, and provide
reusable doubles for GitHub API, JSearch, and Telegram integrations.
"""

from __future__ import annotations

from copy import deepcopy
import os
from typing import Any

import pytest
from fastapi import FastAPI

from backend.config import Settings
from backend.errors import GitHubError


INITIAL_SHA = "1" * 40
UPDATED_SHA = "2" * 40
REPOSITORY_URL = "https://github.com/demo/portfolio"


def make_test_settings(tmp_path, **overrides: Any) -> Settings:
    """Create a fully typed Settings instance pointing to a temp SQLite database."""
    values: dict[str, Any] = {
        "database_path": str(tmp_path / "test.sqlite3"),
        "github_token": None,
        "github_api_url": "https://api.github.invalid",
        "github_timeout_seconds": 3,
        "github_max_files": 20,
        "github_max_file_bytes": 100_000,
        "github_max_total_bytes": 500_000,
        "poll_interval_seconds": 10,
        "monitoring_enabled": True,
        "openai_api_key": None,
        "openai_model": "test-model",
        "enable_llm_explanations": False,
        "xai_api_key": None,
        "xai_api_url": "https://api.x.ai/v1",
        "xai_model": None,
        "enable_xai_fallback": False,
        "jsearch_api_key": None,
        "jsearch_api_url": "https://jsearch.p.rapidapi.com",
        "jsearch_timeout_seconds": 3,
        "telegram_bot_token": None,
        "telegram_webhook_secret": None,
        "telegram_api_url": "https://api.telegram.org",
        "telegram_notifications_enabled": False,
        "azure_key_vault_url": None,
        "applicationinsights_connection_string": None,
        "public_base_url": "https://skillpath.example",
        "telegram_bot_username": "SkillPathTestBot",
        "telegram_pairing_ttl_seconds": 600,
        "telegram_timeout_seconds": 3,
        "github_webhook_secret": None,
    }
    values.update(overrides)
    return Settings(**values)


def make_fake_inspection(
    sha: str = INITIAL_SHA,
    source: str = "",
    *,
    path: str = "src/server.py",
    repo_url: str = REPOSITORY_URL,
    owner: str = "demo",
    name: str = "portfolio",
) -> dict[str, Any]:
    """Return the shape produced by the real bounded GitHub inspector."""
    content_bytes = len(source.encode("utf-8"))
    return {
        "owner": owner,
        "name": name,
        "repository_url": repo_url,
        "default_branch": "main",
        "commit_sha": sha,
        "commit_url": f"{repo_url}/commit/{sha}",
        "commit_date": "2026-10-16T00:00:00Z",
        "files": [
            {
                "path": path,
                "content": source,
                "size": content_bytes,
                "sha": f"blob-{sha[:12]}",
                "html_url": f"{repo_url}/blob/{sha}/{path}",
                "context_only": False,
            }
        ],
        "inspection": {
            "inspected_at": "2026-10-16T00:00:00Z",
            "tree_truncated": False,
            "candidate_file_count": 1,
            "inspected_file_count": 1,
            "inspected_byte_count": content_bytes,
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
        except KeyError as error:
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
def isolate_default_app_database(tmp_path_factory):
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


def create_test_app(
    settings: Settings,
    fake_github: FakeAsyncGitHubClient,
    *,
    job_search_client: Any | None = None,
    telegram_service: Any | None = None,
) -> FastAPI:
    """Create a FastAPI application instance wired with test doubles."""
    from backend.main import create_app

    return create_app(
        settings=settings,
        github_client=fake_github,
        job_search_client=job_search_client,
        telegram_service=telegram_service,
        start_monitor=False,
    )
