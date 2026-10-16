from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from .config import Settings
from .errors import AppError


MAX_RESULTS = 12


def _safe_public_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return None
    return candidate


class JSearchClient:
    """Small server-side client for optional job discovery.

    Results are only suggestions. A user must still review a result before the
    normal job-ingestion endpoint persists its returned source URL and text.
    """

    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = settings
        self.transport = transport

    def status(self) -> dict[str, Any]:
        if not self.settings.jsearch_api_key:
            return {
                "available": False,
                "provider": "JSearch",
                "reason": "JSEARCH_API_KEY is not configured; paste a real job posting URL and description instead.",
            }
        return {"available": True, "provider": "JSearch", "max_results": MAX_RESULTS}

    async def search(
        self,
        *,
        query: str,
        country: str,
        location: str | None = None,
        date_posted: str | None = None,
    ) -> dict[str, Any]:
        if not self.settings.jsearch_api_key:
            raise AppError(
                "job_search_unavailable",
                "Job discovery is not configured. Paste a real public job-posting URL and description instead.",
                503,
            )
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
        raw_items = payload.get("data", []) if isinstance(payload, dict) else []
        if not isinstance(raw_items, list):
            raw_items = []
        results: list[dict[str, Any]] = []
        for item in raw_items[:MAX_RESULTS]:
            if not isinstance(item, dict):
                continue
            posting_url = _safe_public_url(item.get("job_apply_link")) or _safe_public_url(
                item.get("job_google_link")
            )
            title = item.get("job_title")
            company = item.get("employer_name")
            description = item.get("job_description")
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
                    "location": item.get("job_city") or item.get("job_country") or "",
                    "posted_at": item.get("job_posted_at_datetime_utc") or "",
                    "employment_type": item.get("job_employment_type") or "",
                }
            )
        return {
            "provider": "JSearch",
            "query": query.strip(),
            "country": country.strip().lower(),
            "results": results,
            "notice": "Review the returned text and source URL before saving. A search result is not persisted or assessed until you save it as a job.",
        }
