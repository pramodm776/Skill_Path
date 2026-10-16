from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

from .config import Settings


class LLMInterpreter:
    """Optional interpretation only; deterministic evidence remains the source of truth."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        retry_delay_seconds: float = 0.25,
    ) -> None:
        self.settings = settings
        self.transport = transport
        self.retry_delay_seconds = retry_delay_seconds

    def _xai_fallback_available(self) -> bool:
        return bool(
            self.settings.enable_xai_fallback
            and self.settings.xai_api_key
            and self.settings.xai_model
        )

    def status(self) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            return {
                "mode": "deterministic",
                "provider": "OpenAI",
                "available": False,
                "reason": "OPENAI_API_KEY is not configured; deterministic evidence assessment remains available.",
            }
        if not self.settings.enable_llm_explanations:
            return {
                "mode": "deterministic",
                "provider": "OpenAI",
                "available": False,
                "reason": "LLM explanations are disabled. Set ENABLE_LLM_EXPLANATIONS=true to opt in.",
            }
        return {
            "mode": "OpenAI interpretation",
            "provider": "OpenAI",
            "available": True,
            "xai_fallback_available": self._xai_fallback_available(),
        }

    @staticmethod
    def _response_text(payload: dict[str, Any]) -> str | None:
        direct = payload.get("output_text")
        if isinstance(direct, str):
            return direct
        output = payload.get("output")
        if not isinstance(output, list):
            return None
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                    candidate = content.get("text")
                    if isinstance(candidate, str):
                        parts.append(candidate)
        return "\n".join(parts) if parts else None

    @staticmethod
    def _safe_interpretations(text: str | None, assessment: dict[str, Any]) -> dict[str, str]:
        if not text or len(text) > 12_000:
            return {}
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return {}
        if not isinstance(payload, dict):
            return {}
        allowed = {
            str(item.get("skill_key"))
            for item in assessment.get("skill_assessments", [])
            if isinstance(item, dict)
        }
        interpretations: dict[str, str] = {}
        for key, value in payload.items():
            if key not in allowed or not isinstance(value, str):
                continue
            cleaned = " ".join(value.split())
            if 1 <= len(cleaned) <= 400:
                interpretations[key] = cleaned
        return interpretations

    @staticmethod
    def _compact_context(job: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
        compact_items: list[dict[str, Any]] = []
        for item in assessment.get("skill_assessments", []):
            if not isinstance(item, dict):
                continue
            requirement = item.get("job_requirement")
            compact_items.append(
                {
                    "skill_key": item.get("skill_key"),
                    "skill": item.get("skill"),
                    "status": item.get("status"),
                    "job_requirement": requirement.get("source_excerpt", "")
                    if isinstance(requirement, dict)
                    else "",
                    "validated_evidence": [
                        {
                            "path": evidence.get("path"),
                            "lines": f"{evidence.get('start_line')}-{evidence.get('end_line')}",
                            "excerpt": evidence.get("excerpt"),
                        }
                        for evidence in item.get("evidence", [])[:2]
                        if isinstance(evidence, dict)
                    ],
                }
            )
        return {
            "job_title": job.get("title"),
            "company": job.get("company"),
            "skill_assessments": compact_items,
        }

    @staticmethod
    def _body(model: str, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "model": model,
            "store": False,
            "max_output_tokens": 700,
            "instructions": (
                "You are an interpretation helper for an evidence-backed career assessment. "
                "Return only a JSON object mapping each supplied skill_key to one concise, cautious sentence. "
                "Use only the supplied job phrases, statuses, and validated evidence. Do not invent file paths, "
                "line numbers, skills, authorship, proficiency, outcomes, or claims beyond the supplied evidence. "
                "For missing evidence, preserve the phrase 'not demonstrated in this inspected scope'."
            ),
            "input": json.dumps(context, ensure_ascii=False),
        }

    async def _call_provider(
        self, *, endpoint: str, api_key: str, body: dict[str, Any]
    ) -> tuple[str, dict[str, Any] | None]:
        """Return success, transient, or nonretryable without leaking provider details."""

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(20.0),
                follow_redirects=False,
                transport=self.transport,
            ) as client:
                for attempt in range(2):
                    response = await client.post(endpoint, headers=headers, json=body)
                    if response.status_code in {408, 409, 429} or response.status_code >= 500:
                        if attempt == 0:
                            await asyncio.sleep(self.retry_delay_seconds)
                            continue
                        return "transient", None
                    if response.status_code >= 400:
                        return "nonretryable", None
                    try:
                        payload = response.json()
                    except ValueError:
                        return "transient", None
                    return ("success", payload) if isinstance(payload, dict) else ("transient", None)
        except httpx.HTTPError:
            return "transient", None
        return "transient", None

    @staticmethod
    def _apply_interpretations(
        assessment: dict[str, Any], interpretations: dict[str, str]
    ) -> None:
        for item in assessment.get("skill_assessments", []):
            if not isinstance(item, dict):
                continue
            interpretation = interpretations.get(str(item.get("skill_key")))
            if interpretation:
                item["llm_interpretation"] = interpretation

    async def enrich(self, job: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
        """Never let an LLM outage block a factual, citation-validated assessment."""

        initial_status = self.status()
        if not initial_status["available"]:
            return initial_status
        context = self._compact_context(job, assessment)
        openai_outcome, openai_payload = await self._call_provider(
            endpoint="https://api.openai.com/v1/responses",
            api_key=str(self.settings.openai_api_key),
            body=self._body(self.settings.openai_model, context),
        )
        if openai_outcome == "success" and openai_payload is not None:
            interpretations = self._safe_interpretations(self._response_text(openai_payload), assessment)
            self._apply_interpretations(assessment, interpretations)
            return {
                "mode": "OpenAI interpretation",
                "provider": "OpenAI",
                "available": True,
                "sent_to_provider": "Job title/company, requirement excerpts, statuses, and up to two already-validated evidence excerpts per skill. API keys and uninspected files are never sent.",
                "interpreted_skill_count": len(interpretations),
            }
        if openai_outcome == "nonretryable":
            return {
                "mode": "deterministic",
                "provider": "OpenAI",
                "available": False,
                "reason": "OpenAI interpretation was unavailable due to configuration or authentication; deterministic evidence assessment was retained.",
            }
        if self._xai_fallback_available():
            xai_outcome, xai_payload = await self._call_provider(
                endpoint=f"{self.settings.xai_api_url.rstrip('/')}/responses",
                api_key=str(self.settings.xai_api_key),
                body=self._body(str(self.settings.xai_model), context),
            )
            if xai_outcome == "success" and xai_payload is not None:
                interpretations = self._safe_interpretations(self._response_text(xai_payload), assessment)
                self._apply_interpretations(assessment, interpretations)
                return {
                    "mode": "xAI interpretation fallback",
                    "provider": "xAI",
                    "fallback_from": "OpenAI",
                    "available": True,
                    "sent_to_provider": "Job title/company, requirement excerpts, statuses, and up to two already-validated evidence excerpts per skill. API keys and uninspected files are never sent.",
                    "interpreted_skill_count": len(interpretations),
                }
            return {
                "mode": "deterministic",
                "provider": "OpenAI/xAI",
                "available": False,
                "reason": "Optional LLM interpretation was temporarily unavailable; deterministic evidence assessment was retained.",
            }
        return {
            "mode": "deterministic",
            "provider": "OpenAI",
            "available": False,
            "reason": "OpenAI interpretation was temporarily unavailable; deterministic evidence assessment was retained.",
        }
