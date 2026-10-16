from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any

from .errors import AppError, GitHubError
from .llm import LLMInterpreter
from .skills import build_assessment
from .storage import SQLiteStore


class MonitorService:
    """Polling-based change detection. A new GitHub SHA creates at most one snapshot."""

    def __init__(
        self,
        store: SQLiteStore,
        github_client: Any,
        llm_interpreter: LLMInterpreter,
        poll_interval_seconds: int,
        telegram_service: Any | None = None,
    ) -> None:
        self.store = store
        self.github_client = github_client
        self.llm_interpreter = llm_interpreter
        self.poll_interval_seconds = poll_interval_seconds
        self.telegram_service = telegram_service
        self._task: asyncio.Task[None] | None = None
        self._locks: dict[int, asyncio.Lock] = {}

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._poll_forever(), name="career-coach-repository-monitor")

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _poll_forever(self) -> None:
        while True:
            await self.check_all()
            await asyncio.sleep(self.poll_interval_seconds)

    async def check_all(self) -> None:
        if self.telegram_service and hasattr(self.telegram_service, "poll_updates"):
            try:
                await self.telegram_service.poll_updates()
            except Exception:
                pass
        # Deliberately sequential: it bounds GitHub requests and keeps a 24-hour MVP predictable.
        for repository in self.store.monitored_repositories():
            try:
                await self.check_repository(int(repository["id"]), origin="scheduled_poll")
            except Exception:
                # check_repository has already recorded a sanitized error; one repository cannot stop the monitor.
                continue

    @staticmethod
    def _safe_inspection(inspection_result: dict[str, Any]) -> dict[str, Any]:
        inspection = inspection_result.get("inspection", {})
        safe = dict(inspection) if isinstance(inspection, dict) else {}
        files: list[dict[str, Any]] = []
        for item in inspection_result.get("files", []):
            if not isinstance(item, dict):
                continue
            files.append(
                {
                    "path": item.get("path"),
                    "size": item.get("size"),
                    "url": item.get("html_url"),
                    "context_only": bool(item.get("context_only")),
                }
            )
        safe["files"] = files
        return safe

    def _lock_for(self, repository_id: int) -> asyncio.Lock:
        if repository_id not in self._locks:
            self._locks[repository_id] = asyncio.Lock()
        return self._locks[repository_id]

    async def create_assessment_from_inspection(
        self,
        repository_id: int,
        inspection_result: dict[str, Any],
        *,
        trigger: str,
        changed_files: list[dict[str, Any]] | None = None,
        previous_sha: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        repository = self.store.get_repository_with_job(repository_id)
        if not repository or not repository.get("job"):
            raise AppError("repository_not_found", "Repository or its linked job was not found.", 404)
        job = repository["job"]
        sha = inspection_result.get("commit_sha")
        commit_url = inspection_result.get("commit_url")
        if not isinstance(sha, str) or not sha or not isinstance(commit_url, str) or not commit_url:
            raise AppError("github_invalid_response", "GitHub inspection did not include a commit reference.", 502)
        assessment = build_assessment(job, inspection_result, changed_files)
        llm = await self.llm_interpreter.enrich(job, assessment)
        snapshot, created = self.store.create_snapshot(
            repository_id=repository_id,
            commit_sha=sha,
            commit_url=commit_url,
            trigger=trigger,
            assessment=assessment,
            inspection=self._safe_inspection(inspection_result),
            changed_files=changed_files or [],
            llm=llm,
        )
        # An initial/manual scan is also a successful repository check, so both timestamps
        # are meaningful from the first dashboard render.
        self.store.record_check(repository_id, state="active")
        if created:
            event_type, message = {
                "initial_scan": (
                    "initial_assessment_completed",
                    f"Initial evidence assessment completed for commit {sha[:12]}.",
                ),
                "automatic_reassessment": (
                    "automatic_reassessment_completed",
                    f"New commit {sha[:12]} detected and reassessed automatically.",
                ),
            }.get(
                trigger,
                ("manual_assessment_completed", f"Manual evidence assessment completed for commit {sha[:12]}."),
            )
            self.store.record_event(
                repository_id,
                event_type=event_type,
                message=message,
                previous_sha=previous_sha,
                current_sha=sha,
                snapshot_id=int(snapshot["id"]),
                details={"changed_file_count": len(changed_files or []), "trigger": trigger},
            )
            if trigger == "automatic_reassessment" and self.telegram_service is not None:
                try:
                    delivery = await self.telegram_service.notify_reassessment(
                        repository_id=repository_id, snapshot=snapshot, previous_sha=previous_sha
                    )
                    if delivery.get("sent"):
                        self.store.record_event(
                            repository_id,
                            event_type="telegram_notification_sent",
                            message="A paired Telegram chat was notified about the automatic reassessment.",
                            previous_sha=previous_sha,
                            current_sha=sha,
                            snapshot_id=int(snapshot["id"]),
                            details={"trigger": trigger},
                        )
                    elif delivery.get("reason") == "delivery_failed":
                        self.store.record_event(
                            repository_id,
                            event_type="telegram_notification_failed",
                            message="Telegram delivery failed; the automatic assessment remains available in the dashboard.",
                            previous_sha=previous_sha,
                            current_sha=sha,
                            snapshot_id=int(snapshot["id"]),
                            details={"trigger": trigger},
                        )
                except Exception:
                    # Alerts are optional and must never make an assessment or its event disappear.
                    self.store.record_event(
                        repository_id,
                        event_type="telegram_notification_failed",
                        message="Telegram delivery could not be completed; the automatic assessment remains available in the dashboard.",
                        previous_sha=previous_sha,
                        current_sha=sha,
                        snapshot_id=int(snapshot["id"]),
                        details={"trigger": trigger},
                    )
        return snapshot, created

    async def check_repository(self, repository_id: int, *, origin: str = "manual_monitor_check") -> dict[str, Any]:
        """Look up the default-branch SHA and automatically reassess only when it changes."""

        async with self._lock_for(repository_id):
            repository = self.store.get_repository_with_job(repository_id)
            if not repository or not repository.get("job"):
                raise AppError("repository_not_found", "Repository or its linked job was not found.", 404)
            if not repository.get("monitor_enabled"):
                return {"event": "monitor_disabled", "repository_id": repository_id, "message": "Monitoring is disabled."}

            self.store.record_check(repository_id, state="checking")
            if self.telegram_service and hasattr(self.telegram_service, "poll_updates"):
                try:
                    await self.telegram_service.poll_updates()
                except Exception:
                    pass
            try:
                latest = await self.github_client.latest_commit(repository)
                latest_sha = latest.get("sha") if isinstance(latest, dict) else None
                latest_url = latest.get("url") if isinstance(latest, dict) else None
                if not isinstance(latest_sha, str) or not latest_sha:
                    raise GitHubError("github_invalid_response", "GitHub did not provide a current commit SHA.", 502)
                known_sha = repository.get("latest_known_sha")
                if known_sha == latest_sha:
                    self.store.record_check(repository_id, state="active")
                    return {
                        "event": "no_change",
                        "repository_id": repository_id,
                        "commit_sha": latest_sha,
                        "message": "No new commit was detected; no duplicate assessment was created.",
                    }

                changed_files: list[dict[str, Any]] = []
                compare_notice: str | None = None
                if isinstance(known_sha, str) and known_sha:
                    try:
                        compared = await self.github_client.compare_commits(repository, known_sha, latest_sha)
                        if isinstance(compared, list):
                            changed_files = compared
                    except GitHubError as comparison_error:
                        # Reassessment remains correct at the new SHA even if GitHub cannot compare histories.
                        compare_notice = comparison_error.message

                inspection_result = await self.github_client.inspect_repository(
                    str(repository["repository_url"]), ref=latest_sha
                )
                inspected_sha = inspection_result.get("commit_sha") if isinstance(inspection_result, dict) else None
                if inspected_sha != latest_sha:
                    raise GitHubError(
                        "github_commit_mismatch",
                        "GitHub returned a different revision than the detected commit; assessment was not stored.",
                        502,
                    )
                snapshot, created = await self.create_assessment_from_inspection(
                    repository_id,
                    inspection_result,
                    trigger="automatic_reassessment",
                    changed_files=changed_files,
                    previous_sha=known_sha if isinstance(known_sha, str) else None,
                )
                self.store.record_check(repository_id, state="active")
                result = {
                    "event": "reassessed" if created else "duplicate_commit_skipped",
                    "repository_id": repository_id,
                    "previous_sha": known_sha,
                    "commit_sha": latest_sha,
                    "commit_url": latest_url or inspection_result.get("commit_url"),
                    "snapshot_id": snapshot.get("id"),
                    "changed_files": changed_files,
                    "message": "New commit detected and automatic reassessment completed."
                    if created
                    else "This commit already has an assessment; no duplicate was created.",
                }
                if compare_notice:
                    result["compare_limitation"] = compare_notice
                return result
            except AppError as error:
                self.store.record_check(
                    repository_id,
                    state="error",
                    error_code=error.code,
                    error_message=error.message,
                )
                raise
            except Exception as error:
                self.store.record_check(
                    repository_id,
                    state="error",
                    error_code="monitor_unexpected_error",
                    error_message="Repository monitoring encountered an unexpected error and will retry later.",
                )
                raise AppError(
                    "monitor_unexpected_error",
                    "Repository monitoring encountered an unexpected error and will retry later.",
                    502,
                ) from error
