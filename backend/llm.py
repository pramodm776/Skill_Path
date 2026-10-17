from __future__ import annotations

import asyncio
import hashlib
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
        self._cache: dict[str, dict[str, Any]] = {}

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
            "model": self.settings.openai_model,
            "available": True,
            "xai_fallback_available": self._xai_fallback_available(),
        }

    @staticmethod
    def _strip_code_fences(text: str | None) -> str | None:
        if not text:
            return None
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return cleaned

    @staticmethod
    def _response_text(payload: dict[str, Any]) -> str | None:
        direct = payload.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return LLMInterpreter._strip_code_fences(direct)
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
        return LLMInterpreter._strip_code_fences("\n".join(parts)) if parts else None

    @staticmethod
    def _safe_interpretations(text: str | None, assessment: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
        if not text or len(text) > 16_000:
            return {}, {}
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return {}, {}
        if not isinstance(payload, dict):
            return {}, {}
        allowed = {
            str(item.get("skill_key"))
            for item in assessment.get("skill_assessments", [])
            if isinstance(item, dict)
        }
        interpretations: dict[str, str] = {}
        next_tasks: dict[str, str] = {}
        for key, value in payload.items():
            if key not in allowed:
                continue
            if isinstance(value, str):
                cleaned = " ".join(value.split())
                if 1 <= len(cleaned) <= 450:
                    interpretations[key] = cleaned
            elif isinstance(value, dict):
                interp = value.get("interpretation") or value.get("summary")
                if isinstance(interp, str):
                    cleaned = " ".join(interp.split())
                    if 1 <= len(cleaned) <= 450:
                        interpretations[key] = cleaned
                task = value.get("next_task") or value.get("recommendation")
                if isinstance(task, str):
                    cleaned_task = " ".join(task.split())
                    if 10 <= len(cleaned_task) <= 450:
                        next_tasks[key] = cleaned_task
        return interpretations, next_tasks

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
        assessment: dict[str, Any],
        interpretations: dict[str, str],
        next_tasks: dict[str, str] | None = None,
    ) -> None:
        next_tasks = next_tasks or {}
        for item in assessment.get("skill_assessments", []):
            if not isinstance(item, dict):
                continue
            key = str(item.get("skill_key"))
            interpretation = interpretations.get(key)
            if interpretation:
                item["llm_interpretation"] = interpretation
            task_override = next_tasks.get(key)
            if task_override and item.get("status_code") != "demonstrated":
                if isinstance(item.get("next_evidence_contract"), dict):
                    item["next_evidence_contract"]["llm_suggestion"] = task_override

    async def enrich(self, job: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
        """Never let an LLM outage block a factual, citation-validated assessment."""

        initial_status = self.status()
        if not initial_status["available"]:
            return initial_status
        context = self._compact_context(job, assessment)
        cache_key = hashlib.sha256(
            json.dumps(
                {"model": self.settings.openai_model, "sha": assessment.get("inspected_commit_sha"), "ctx": context},
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            self._apply_interpretations(
                assessment, cached.get("interpretations", {}), cached.get("next_tasks", {})
            )
            meta = dict(cached["meta"])
            meta["cached"] = True
            return meta

        openai_outcome, openai_payload = await self._call_provider(
            endpoint="https://api.openai.com/v1/responses",
            api_key=str(self.settings.openai_api_key),
            body=self._body(self.settings.openai_model, context),
        )
        if openai_outcome == "success" and openai_payload is not None:
            interpretations, next_tasks = self._safe_interpretations(self._response_text(openai_payload), assessment)
            self._apply_interpretations(assessment, interpretations, next_tasks)
            usage = openai_payload.get("usage") if isinstance(openai_payload.get("usage"), dict) else {}
            meta = {
                "mode": "OpenAI interpretation",
                "provider": "OpenAI",
                "model": self.settings.openai_model,
                "available": True,
                "cached": False,
                "sent_to_provider": "Job title/company, requirement excerpts, statuses, and up to two already-validated evidence excerpts per skill. API keys and uninspected files are never sent.",
                "interpreted_skill_count": len(interpretations),
                "tokens_used": usage.get("total_tokens") if isinstance(usage, dict) else None,
            }
            if interpretations:
                self._cache[cache_key] = {"interpretations": interpretations, "next_tasks": next_tasks, "meta": meta}
            return meta
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
                interpretations, next_tasks = self._safe_interpretations(self._response_text(xai_payload), assessment)
                self._apply_interpretations(assessment, interpretations, next_tasks)
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
