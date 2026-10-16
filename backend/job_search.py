from __future__ import annotations

import asyncio
import html
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from .config import Settings
from .errors import AppError


MAX_RESULTS = 16


def _safe_public_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return None
    return candidate


def _clean_snippet(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = html.unescape(cleaned)
    return " ".join(cleaned.split())


class JSearchClient:
    """Server-side client for real-time job discovery via Jooble and JSearch.

    Results are only suggestions. A user must still review a result before the
    normal job-ingestion endpoint persists its returned source URL and text.
    """

    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = settings
        self.transport = transport

    def status(self) -> dict[str, Any]:
        providers: list[str] = []
        if self.settings.jooble_api_key:
            providers.append("Jooble")
        if self.settings.jsearch_api_key:
            providers.append("JSearch")
        if not providers:
            return {
                "available": False,
                "provider": "Job Search",
                "reason": "Neither JOOBLE_API_KEY nor JSEARCH_API_KEY is configured; paste job requirements manually.",
            }
        return {
            "available": True,
            "provider": " & ".join(providers),
            "providers": providers,
            "max_results": MAX_RESULTS,
        }

    async def _search_jooble(self, *, query: str, location: str | None = None) -> list[dict[str, Any]]:
        if not self.settings.jooble_api_key:
            return []
        base_url = self.settings.jooble_api_url.rstrip("/")
        api_url = f"{base_url}/{self.settings.jooble_api_key}"
        payload: dict[str, str] = {"keywords": query.strip()}
        if location and location.strip():
            payload["location"] = location.strip()
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.jooble_timeout_seconds),
                follow_redirects=True,
                transport=self.transport,
            ) as client:
                response = await client.post(api_url, json=payload, headers=headers)
        except httpx.HTTPError as error:
            raise AppError("job_search_unavailable", "Jooble job discovery could not be reached.", 502) from error

        if response.status_code in {401, 403}:
            raise AppError("job_search_authentication_failed", "Jooble rejected the configured API key.", 502)
        if response.status_code == 429:
            raise AppError("job_search_rate_limited", "Jooble job discovery is rate-limited.", 429)
        if response.is_error:
            raise AppError("job_search_failed", f"Jooble returned error code {response.status_code}.", 502)

        try:
            data = response.json()
        except ValueError as error:
            raise AppError("job_search_invalid_response", "Jooble returned an unreadable response.", 502) from error

        raw_items = data.get("jobs", []) if isinstance(data, dict) else []
        if not isinstance(raw_items, list):
            raw_items = []

        results: list[dict[str, Any]] = []
        for item in raw_items[:MAX_RESULTS]:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            company = item.get("company")
            snippet = item.get("snippet") or ""
            posting_url = _safe_public_url(item.get("link"))
            if not isinstance(title, str) or not title.strip() or not isinstance(company, str) or not company.strip():
                continue
            clean_desc = _clean_snippet(str(snippet))
            results.append(
                {
                    "title": title.strip()[:240],
                    "company": company.strip()[:240],
                    "posting_url": posting_url,
                    "description": clean_desc[:50_000] if clean_desc else "",
                    "location": item.get("location") or "",
                    "posted_at": item.get("updated") or "",
                    "employment_type": item.get("type") or "",
                    "source": item.get("source") or "Jooble",
                    "provider": "Jooble",
                }
            )
        return results

    async def _search_jsearch(
        self,
        *,
        query: str,
        country: str,
        location: str | None = None,
        date_posted: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self.settings.jsearch_api_key:
            return []
        base_url = self.settings.jsearch_api_url.rstrip("/")
        host = urlparse(base_url).netloc
        if not host:
            raise AppError("job_search_configuration_invalid", "Job discovery is not configured correctly.", 503)
        params: dict[str, str | int] = {
            "query": query.strip(),
            "country": country.strip().lower(),
            "num_pages": 1,
        }
        if location and location.strip():
            params["location"] = location.strip()
        if date_posted and date_posted != "all":
            params["date_posted"] = date_posted
        headers = {
            "X-RapidAPI-Key": self.settings.jsearch_api_key,
            "X-RapidAPI-Host": host,
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                base_url=base_url,
                headers=headers,
                timeout=httpx.Timeout(self.settings.jsearch_timeout_seconds),
                follow_redirects=False,
                transport=self.transport,
            ) as client:
                response = await client.get("/search-v2", params=params)
                if response.status_code == 404:
                    response = await client.get("/search", params=params)
        except httpx.HTTPError as error:
            raise AppError(
                "job_search_unavailable",
                "Job discovery could not be reached. Paste a real job-posting URL and description instead.",
                502,
            ) from error

        if response.status_code in {401, 403}:
            raise AppError(
                "job_search_authentication_failed",
                "Job discovery rejected the server-side provider configuration. Paste a real job-posting URL and description instead.",
                502,
            )
        if response.status_code == 429:
            raise AppError(
                "job_search_rate_limited",
                "Job discovery is rate-limited. Paste a real job-posting URL and description instead.",
                429,
            )
        if response.status_code >= 500:
            raise AppError(
                "job_search_unavailable",
                "Job discovery is temporarily unavailable. Paste a real job-posting URL and description instead.",
                502,
            )
        if response.is_error:
            raise AppError(
                "job_search_failed",
                "Job discovery could not return results. Paste a real job-posting URL and description instead.",
                502,
            )
        try:
            payload = response.json()
        except ValueError as error:
            raise AppError(
                "job_search_invalid_response",
                "Job discovery returned an unreadable response. Paste a real job-posting URL and description instead.",
                502,
            ) from error
        data_field = payload.get("data", []) if isinstance(payload, dict) else []
        if isinstance(data_field, dict):
            raw_items = data_field.get("jobs", [])
        elif isinstance(data_field, list):
            raw_items = data_field
        else:
            raw_items = []
        if not isinstance(raw_items, list):
            raw_items = []
        results: list[dict[str, Any]] = []
        for item in raw_items[:MAX_RESULTS]:
            if not isinstance(item, dict):
                continue
            posting_url = (
                _safe_public_url(item.get("job_apply_link"))
                or _safe_public_url(item.get("link"))
                or _safe_public_url(item.get("job_google_link"))
            )
            title = item.get("job_title") or item.get("title")
            company = item.get("employer_name") or item.get("company")
            description = item.get("job_description") or item.get("description")
            if not isinstance(title, str) or not title.strip() or not isinstance(company, str) or not company.strip():
                continue
            results.append(
                {
                    "title": title.strip()[:240],
                    "company": company.strip()[:240],
                    "posting_url": posting_url,
                    "description": description.strip()[:50_000]
                    if isinstance(description, str) and description.strip()
                    else "",
                    "location": item.get("job_city") or item.get("job_country") or item.get("location") or "",
                    "posted_at": item.get("job_posted_at_datetime_utc") or item.get("posted_at") or "",
                    "employment_type": item.get("job_employment_type") or item.get("employment_type") or "",
                    "source": "RapidAPI",
                    "provider": "JSearch",
                }
            )
        return results

    async def search(
        self,
        *,
        query: str,
        country: str,
        location: str | None = None,
        date_posted: str | None = None,
    ) -> dict[str, Any]:
        has_jooble = bool(self.settings.jooble_api_key)
        has_jsearch = bool(self.settings.jsearch_api_key)

        if not has_jooble and not has_jsearch:
            raise AppError(
                "job_search_unavailable",
                "Job discovery is not configured. Paste a real public job-posting URL and description instead.",
                503,
            )

        results: list[dict[str, Any]] = []
        active_providers: list[str] = []

        if has_jooble and has_jsearch:
            jooble_task = self._search_jooble(query=query, location=location)
            jsearch_task = self._search_jsearch(
                query=query, country=country, location=location, date_posted=date_posted
            )
            outcomes = await asyncio.gather(jooble_task, jsearch_task, return_exceptions=True)
            jooble_res, jsearch_res = outcomes[0], outcomes[1]

            seen_keys: set[tuple[str, str]] = set()
            if isinstance(jooble_res, list) and jooble_res:
                active_providers.append("Jooble")
                for item in jooble_res:
                    key = (item["title"].strip().lower(), item["company"].strip().lower())
                    if key not in seen_keys:
                        seen_keys.add(key)
                        results.append(item)
            if isinstance(jsearch_res, list) and jsearch_res:
                active_providers.append("JSearch")
                for item in jsearch_res:
                    key = (item["title"].strip().lower(), item["company"].strip().lower())
                    if key not in seen_keys:
                        seen_keys.add(key)
                        results.append(item)

            if not results:
                if isinstance(jooble_res, Exception) and isinstance(jsearch_res, Exception):
                    if isinstance(jooble_res, AppError):
                        raise jooble_res
                    if isinstance(jsearch_res, AppError):
                        raise jsearch_res
                    raise AppError("job_search_unavailable", "Job discovery failed across configured providers.", 502)

        elif has_jooble:
            active_providers.append("Jooble")
            results = await self._search_jooble(query=query, location=location)
        else:
            active_providers.append("JSearch")
            results = await self._search_jsearch(
                query=query, country=country, location=location, date_posted=date_posted
            )

        provider_label = " & ".join(active_providers) if active_providers else "Job Search"
        return {
            "provider": provider_label,
            "query": query.strip(),
            "country": country.strip().lower(),
            "results": results[:MAX_RESULTS],
            "notice": "Review the returned text and source URL before saving. A search result is not persisted or assessed until you save it as a job.",
        }
