"""Offline tests for bounded provider integrations and evidence-only safeguards."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

from backend.config import Settings
from backend.job_search import JSearchClient
from backend.llm import LLMInterpreter
from backend.skills import build_assessment, extract_job_skills
from backend.storage import SQLiteStore
from backend.telegram import TelegramService


def _settings(tmp_path, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "database_path": str(tmp_path / "integrations.sqlite3"),
        "github_token": None,
        "github_api_url": "https://api.github.invalid",
        "github_timeout_seconds": 3,
        "github_max_files": 20,
        "github_max_file_bytes": 100_000,
        "github_max_total_bytes": 500_000,
        "poll_interval_seconds": 10,
        "monitoring_enabled": False,
        "openai_api_key": None,
        "openai_model": "test-openai-model",
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
    }
    values.update(overrides)
    return Settings(**values)


def _inspection(source: str) -> dict[str, Any]:
    return {
        "commit_sha": "a" * 40,
        "commit_url": "https://github.com/demo/rag/commit/" + "a" * 40,
        "files": [
            {
                "path": "src/app.py",
                "content": source,
                "size": len(source.encode("utf-8")),
                "html_url": "https://github.com/demo/rag/blob/" + "a" * 40 + "/src/app.py",
                "context_only": False,
            }
        ],
        "inspection": {"inspected_file_count": 1, "skipped": [], "tree_truncated": False},
    }


def _assessment() -> dict[str, Any]:
    return {
        "skill_assessments": [
            {
                "skill_key": "python",
                "skill": "Python",
                "status": "demonstrated",
                "job_requirement": {"source_excerpt": "Python"},
                "evidence": [],
            }
        ]
    }


def test_jsearch_keeps_key_server_side_and_only_returns_reviewable_results(tmp_path) -> None:
    received: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        received["url"] = str(request.url)
        received["headers"] = dict(request.headers)
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "job_title": "Python Intern",
                        "employer_name": "Example Labs",
                        "job_apply_link": "https://jobs.example.test/apply/42",
                        "job_description": "Build Python APIs and write tests.",
                        "job_city": "Pune",
                        "job_country": "IN",
                        "job_employment_type": "INTERN",
                    },
                    {
                        "job_title": "Missing URL",
                        "employer_name": "Example Labs",
                        "job_description": "This result is not selectable.",
                    },
                ]
            },
        )

    secret = "jsearch-server-secret"
    client = JSearchClient(
        _settings(tmp_path, jsearch_api_key=secret), transport=httpx.MockTransport(handler)
    )
    result = asyncio.run(client.search(query="python intern", country="in", location="Pune"))

    assert "num_pages=1" in received["url"]
    assert received["headers"]["x-rapidapi-key"] == secret
    assert result["results"][0]["posting_url"] == "https://jobs.example.test/apply/42"
    assert result["results"][1]["posting_url"] is None
    assert secret not in json.dumps(result)
    assert "not persisted" in result["notice"]


def test_rag_needs_both_retrieval_and_vector_store_source_signals() -> None:
    job = {
        "title": "RAG Engineer",
        "company": "Example",
        "skills": extract_job_skills("Required: RAG, embeddings, and OpenAI API experience."),
    }
    comment_only = _inspection(
        "# RAG uses Chroma and similarity_search with OpenAIEmbeddings\n"
        "def plain_python() -> str:\n"
        "    return 'no retrieval implementation'\n"
    )
    comment_assessment = build_assessment(job, comment_only)
    comment_skills = {item["skill_key"]: item for item in comment_assessment["skill_assessments"]}
    assert comment_skills["retrieval_augmented_generation"]["status_code"] == "not_demonstrated"
    assert comment_skills["embeddings_vector_search"]["status_code"] == "not_demonstrated"
    assert comment_skills["llm_integration"]["status_code"] == "not_demonstrated"

    implemented = _inspection(
        "from langchain_chroma import Chroma\n"
        "from openai import OpenAI\n"
        "\n"
        "vectorstore = Chroma(collection_name='portfolio')\n"
        "retriever = vectorstore.as_retriever()\n"
        "client = OpenAI()\n"
    )
    implemented_assessment = build_assessment(job, implemented)
    implemented_skills = {item["skill_key"]: item for item in implemented_assessment["skill_assessments"]}
    assert implemented_skills["retrieval_augmented_generation"]["status_code"] == "demonstrated"
    assert implemented_skills["embeddings_vector_search"]["status_code"] == "demonstrated"
    assert implemented_skills["llm_integration"]["status_code"] == "demonstrated"
    assert all(
        evidence["path"] == "src/app.py"
        for evidence in implemented_skills["retrieval_augmented_generation"]["evidence"]
    )


def test_llm_uses_xai_only_after_transient_openai_failure(tmp_path) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.host)
        if request.url.host == "api.openai.com":
            return httpx.Response(503, json={"error": "temporary"})
        return httpx.Response(200, json={"output_text": json.dumps({"python": "Validated source supports a Python implementation signal."})})

    openai_secret = "openai-server-secret"
    xai_secret = "xai-server-secret"
    interpreter = LLMInterpreter(
        _settings(
            tmp_path,
            openai_api_key=openai_secret,
            enable_llm_explanations=True,
            xai_api_key=xai_secret,
            xai_model="grok-test",
            enable_xai_fallback=True,
        ),
        transport=httpx.MockTransport(handler),
        retry_delay_seconds=0,
    )
    assessment = _assessment()
    metadata = asyncio.run(interpreter.enrich({"title": "Engineer", "company": "Example"}, assessment))

    assert calls == ["api.openai.com", "api.openai.com", "api.x.ai"]
    assert metadata["provider"] == "xAI"
    assert metadata["fallback_from"] == "OpenAI"
    assert assessment["skill_assessments"][0]["llm_interpretation"].startswith("Validated")
    assert openai_secret not in json.dumps(metadata)
    assert xai_secret not in json.dumps(metadata)


def test_llm_does_not_fallback_after_openai_auth_failure(tmp_path) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.host)
        return httpx.Response(401, json={"error": "invalid key"})

    interpreter = LLMInterpreter(
        _settings(
            tmp_path,
            openai_api_key="openai-server-secret",
            enable_llm_explanations=True,
            xai_api_key="xai-server-secret",
            xai_model="grok-test",
            enable_xai_fallback=True,
        ),
        transport=httpx.MockTransport(handler),
        retry_delay_seconds=0,
    )
    metadata = asyncio.run(interpreter.enrich({"title": "Engineer", "company": "Example"}, _assessment()))

    assert calls == ["api.openai.com"]
    assert metadata["provider"] == "OpenAI"
    assert metadata["available"] is False


def test_telegram_pairing_hashes_code_and_notifies_once_per_snapshot(tmp_path) -> None:
    deliveries: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        deliveries.append(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 99}})

    settings = _settings(
        tmp_path,
        telegram_bot_token="telegram-server-secret",
        telegram_webhook_secret="webhook-server-secret",
        telegram_notifications_enabled=True,
    )
    store = SQLiteStore(settings.database_path)
    job = store.create_job(
        title="Backend intern",
        company="Example",
        source_url="https://jobs.example.test/role",
        description="Required: Python.",
        skills=extract_job_skills("Required: Python."),
    )
    repository = store.create_repository(
        job_id=int(job["id"]),
        repository_url="https://github.com/demo/portfolio",
        owner="demo",
        name="portfolio",
        default_branch="main",
    )
    service = TelegramService(settings, store, transport=httpx.MockTransport(handler))
    pairing = service.create_pairing(int(repository["id"]))
    assert "telegram-server-secret" not in json.dumps(pairing)
    token = pairing["start_command"].split(maxsplit=1)[1]
    raw_subscription = store.telegram_subscription(int(repository["id"]))
    assert raw_subscription is not None
    assert raw_subscription["pairing_token_hash"] != token

    paired = asyncio.run(
        service.handle_webhook_update(
            {"message": {"text": pairing["start_command"], "chat": {"id": 12345}}}
        )
    )
    assert paired["paired"] is True
    public_status = service.status(int(repository["id"]))
    assert public_status["state"] == "paired"
    assert "12345" not in json.dumps(public_status)

    snapshot, created = store.create_snapshot(
        repository_id=int(repository["id"]),
        commit_sha="b" * 40,
        commit_url="https://github.com/demo/portfolio/commit/" + "b" * 40,
        trigger="automatic_reassessment",
        assessment={"fit_score": {"value": 50}, "summary": {"demonstrated": 1}},
        inspection={},
        changed_files=[{"path": "src/app.py", "status": "modified"}],
        llm={},
    )
    assert created is True
    first = asyncio.run(
        service.notify_reassessment(
            repository_id=int(repository["id"]), snapshot=snapshot, previous_sha="a" * 40
        )
    )
    second = asyncio.run(
        service.notify_reassessment(
            repository_id=int(repository["id"]), snapshot=snapshot, previous_sha="a" * 40
        )
    )

    assert first == {"sent": True}
    assert second["reason"] == "already_notified"
    assert len(deliveries) == 2  # Pairing confirmation plus the automatic reassessment alert.
    alert_text = deliveries[-1]["text"]
    assert "Proof Delta" in alert_text
    assert "src/app.py" not in alert_text
    assert "telegram-server-secret" not in alert_text
