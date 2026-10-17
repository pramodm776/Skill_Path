from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from .config import Settings
from .errors import AppError
from .skills import compare_assessments
from .storage import SQLiteStore


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _hash_pairing_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_dashboard_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return value.rstrip("/")


class TelegramService:
    """Opt-in Telegram pairing and reassessment notifications.

    This class deliberately stores only a hash of a short-lived pairing token.
    It never forwards evidence excerpts, job text, GitHub tokens, or provider
    credentials to Telegram.
    """

    def __init__(
        self,
        settings: Settings,
        store: SQLiteStore,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.transport = transport
        self._recent_notified_shas: dict[str, str] = {}

    def status(self, repository_id: int | None = None) -> dict[str, Any]:
        configured = bool(
            self.settings.telegram_notifications_enabled
            and self.settings.telegram_bot_token
            and (self.settings.telegram_webhook_secret or self.can_poll())
        )
        if not configured:
            return {
                "available": False,
                "enabled": False,
                "state": "disabled",
                "reason": "Telegram alerts are disabled or not fully configured on the server.",
            }
        result: dict[str, Any] = {
            "available": True,
            "enabled": True,
            "state": "unpaired",
            "bot_username": self.settings.telegram_bot_username,
        }
        if repository_id is None:
            return result
        subscription = self.store.telegram_subscription(repository_id)
        if not subscription:
            return result
        if subscription.get("active"):
            result["state"] = "paired"
            result["last_notified_at"] = subscription.get("last_notified_at")
            result["last_error"] = subscription.get("last_error_message")
        elif subscription.get("pairing_expires_at"):
            result["state"] = "pairing_pending"
            result["pairing_expires_at"] = subscription.get("pairing_expires_at")
        return result

    def _require_configured(self) -> None:
        if not self.status().get("available"):
            raise AppError(
                "telegram_unavailable",
                "Telegram alerts are disabled or not fully configured on the server.",
                503,
            )

    def create_pairing(self, repository_id: int) -> dict[str, Any]:
        self._require_configured()
        token = secrets.token_urlsafe(24)
        expires_at = utc_now() + timedelta(seconds=self.settings.telegram_pairing_ttl_seconds)
        self.store.create_telegram_pairing(
            repository_id=repository_id,
            token_hash=_hash_pairing_token(token),
            expires_at=utc_iso(expires_at),
        )
        start_command = f"/start {token}"
        deep_link = None
        if self.settings.telegram_bot_username:
            deep_link = f"https://t.me/{self.settings.telegram_bot_username}?start={token}"
        return {
            "state": "pairing_pending",
            "expires_at": utc_iso(expires_at),
            "start_command": start_command,
            "deep_link": deep_link,
            "notice": "Pairing is one-time and expires. The token is stored only as a hash on the server.",
        }

    def verify_webhook_secret(self, received: str | None) -> bool:
        expected = self.settings.telegram_webhook_secret
        return bool(expected and received and hmac.compare_digest(expected, received))

    async def _send_message(self, chat_id: str, text: str) -> int | None:
        token = self.settings.telegram_bot_token
        if not token:
            return None
        try:
            async with httpx.AsyncClient(
                base_url=self.settings.telegram_api_url,
                timeout=httpx.Timeout(self.settings.telegram_timeout_seconds),
                follow_redirects=False,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    f"/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": text[:3_500], "disable_web_page_preview": True},
                )
        except httpx.HTTPError:
            return None
        if response.status_code >= 400:
            return None
        try:
            payload = response.json()
        except ValueError:
            return None
        result = payload.get("result") if isinstance(payload, dict) else None
        message_id = result.get("message_id") if isinstance(result, dict) else None
        return message_id if isinstance(message_id, int) else None

    async def handle_webhook_update(self, update: dict[str, Any]) -> dict[str, Any]:
        """Consume only /start or /stop commands; incoming free text is discarded."""

        message = update.get("message") if isinstance(update, dict) else None
        if not isinstance(message, dict):
            return {"handled": False}
        text = message.get("text")
        chat = message.get("chat")
        chat_id = chat.get("id") if isinstance(chat, dict) else None
        if not isinstance(text, str) or not isinstance(chat_id, (int, str)):
            return {"handled": False}
        command = text.strip()
        normalized_chat_id = str(chat_id)
        if command.lower().startswith("/start"):
            parts = command.split(maxsplit=1)
            if len(parts) != 2 or not parts[1] or len(parts[1]) > 128:
                await self._send_message(
                    normalized_chat_id,
                    "SkillPath AI pairing needs a valid one-time code from the dashboard.",
                )
                return {"handled": True, "paired": False}
            subscription = self.store.consume_telegram_pairing(
                token_hash=_hash_pairing_token(parts[1]), chat_id=normalized_chat_id, now=utc_iso(utc_now())
            )
            if not subscription:
                await self._send_message(
                    normalized_chat_id,
                    "That SkillPath AI pairing code is invalid or expired. Create a new pairing code in the dashboard.",
                )
                return {"handled": True, "paired": False}
            await self._send_message(
                normalized_chat_id,
                "SkillPath AI alerts are paired. You will receive a short update after a newly detected commit is automatically reassessed.",
            )
            return {"handled": True, "paired": True, "repository_id": subscription.get("repository_id")}
        if command.lower().split(maxsplit=1)[0].split("@", 1)[0] == "/stop":
            deactivated = self.store.deactivate_telegram_chat(normalized_chat_id)
            await self._send_message(
                normalized_chat_id,
                "SkillPath AI alerts have been stopped for this chat." if deactivated else "No active SkillPath AI alert pairing was found for this chat.",
            )
            return {"handled": True, "stopped": deactivated}
        return {"handled": False}

    @staticmethod
    def _proof_delta_counts(previous_assessment: dict[str, Any], current_assessment: dict[str, Any]) -> dict[str, int]:
        comparison = compare_assessments(previous_assessment, current_assessment)
        rows = comparison.get("requirement_rows")
        if not isinstance(rows, list) or not rows:
            # Fallback if test fixture supplies minimal assessment dict without full skill_assessments
            changes = comparison.get("skill_changes", [])
            return {
                "newly_demonstrated": sum(
                    1
                    for c in changes
                    if c.get("before_status_code") == "not_demonstrated"
                    and c.get("after_status_code") == "demonstrated"
                ),
                "improved": sum(
                    1
                    for c in changes
                    if (
                        c.get("before_status_code") == "partially_demonstrated"
                        and c.get("after_status_code") == "demonstrated"
                    )
                    or (
                        c.get("before_status_code") == "not_demonstrated"
                        and c.get("after_status_code") == "partially_demonstrated"
                    )
                ),
                "regressed": sum(
                    1
                    for c in changes
                    if (
                        c.get("before_status_code") == "demonstrated"
                        and c.get("after_status_code") in {"partially_demonstrated", "not_demonstrated"}
                    )
                    or (
                        c.get("before_status_code") == "partially_demonstrated"
                        and c.get("after_status_code") == "not_demonstrated"
                    )
                ),
                "unchanged": 0,
            }

        newly_demonstrated = 0
        improved = 0
        regressed = 0
        unchanged = 0
        rank = {"not_demonstrated": 0, "partially_demonstrated": 1, "demonstrated": 2}
        for row in rows:
            b_code = str(row.get("before_status_code") or "not_demonstrated")
            a_code = str(row.get("after_status_code") or "not_demonstrated")
            b_rank = rank.get(b_code, 0)
            a_rank = rank.get(a_code, 0)
            added_ev = len(row.get("evidence_added") or [])
            removed_ev = len(row.get("evidence_removed") or [])
            if b_code == "not_demonstrated" and a_code == "demonstrated":
                newly_demonstrated += 1
            elif a_rank > b_rank:
                improved += 1
            elif a_rank < b_rank or (a_rank == b_rank and removed_ev > 0 and added_ev == 0):
                regressed += 1
            else:
                unchanged += 1
        return {
            "newly_demonstrated": newly_demonstrated,
            "improved": improved,
            "regressed": regressed,
            "unchanged": unchanged,
        }

    async def notify_reassessment(
        self,
        *,
        repository_id: int,
        snapshot: dict[str, Any],
        previous_sha: str | None,
    ) -> dict[str, Any]:
        """Send at most one concise alert for an automatic new-SHA snapshot using canonical assessment data."""

        status = self.status(repository_id)
        if not status.get("available") or status.get("state") != "paired":
            return {"sent": False, "reason": status.get("state", "disabled")}
        subscription = self.store.telegram_subscription(repository_id)
        if not subscription or not subscription.get("active") or not subscription.get("chat_id"):
            return {"sent": False, "reason": "unpaired"}

        repo_with_job = self.store.get_repository_with_job(repository_id)
        if not repo_with_job:
            return {"sent": False, "reason": "repository_not_found"}

        owner = str(repo_with_job.get("owner") or "")
        name = str(repo_with_job.get("name") or "")
        branch = str(repo_with_job.get("default_branch") or "main")
        job = repo_with_job.get("job") if isinstance(repo_with_job.get("job"), dict) else {}
        job_title = str(job.get("title") or "Selected Role")

        # If multiple repository rows exist for the same GitHub owner/name, only send the Telegram alert
        # for the canonical latest repository row (or the explicitly paired repository) so old test jobs
        # do not send conflicting 38% scores before the active 73% job is assessed.
        if owner and name and hasattr(self.store, "latest_repository_id_for_full_name"):
            canonical_repo_id = self.store.latest_repository_id_for_full_name(owner, name)
            if canonical_repo_id is not None and canonical_repo_id != repository_id:
                canonical_sub = self.store.telegram_subscription(canonical_repo_id)
                if canonical_sub and canonical_sub.get("active") and canonical_sub.get("chat_id") == subscription.get("chat_id"):
                    return {"sent": False, "reason": "superseded_by_newer_job_repository"}

        snapshot_id = snapshot.get("id")
        if not isinstance(snapshot_id, int):
            return {"sent": False, "reason": "invalid_snapshot"}

        canonical_snapshot = self.store.get_snapshot(snapshot_id) or snapshot
        assessment = canonical_snapshot.get("assessment") if isinstance(canonical_snapshot.get("assessment"), dict) else {}
        if not assessment:
            return {"sent": False, "reason": "invalid_assessment"}

        fit = assessment.get("fit_score") if isinstance(assessment.get("fit_score"), dict) else {}
        score = fit.get("value") if isinstance(fit, dict) else None
        summary = assessment.get("summary") if isinstance(assessment.get("summary"), dict) else {}
        if score is None and not summary:
            return {"sent": False, "reason": "missing_canonical_score"}

        chat_id_str = str(subscription["chat_id"])
        commit_sha_full = str(canonical_snapshot.get("commit_sha", ""))
        if not self.store.claim_telegram_delivery(
            subscription_id=int(subscription["id"]),
            snapshot_id=snapshot_id,
            notification_type="automatic_reassessment",
            chat_id=chat_id_str,
            owner=owner or None,
            name=name or None,
            commit_sha=commit_sha_full or None,
        ):
            return {"sent": False, "reason": "already_notified"}

        demo_total = summary.get("demonstrated", 0) if isinstance(summary, dict) else 0
        part_total = summary.get("partially_demonstrated", 0) if isinstance(summary, dict) else 0
        miss_total = summary.get("not_demonstrated", 0) if isinstance(summary, dict) else 0

        # Retrieve previous snapshot for authentic Proof Delta calculation
        prev_snapshot: dict[str, Any] | None = None
        if previous_sha and hasattr(self.store, "get_snapshot_by_sha"):
            prev_snapshot = self.store.get_snapshot_by_sha(repository_id, previous_sha)
        if prev_snapshot is None and hasattr(self.store, "previous_snapshot_for"):
            prev_snapshot = self.store.previous_snapshot_for(repository_id, snapshot_id)

        sha_short = commit_sha_full[:12] or "new revision"
        repo_label = f"{owner}/{name}" if owner and name else "repository"
        lines = [
            "SkillPath AI — Assessment Update",
            "",
            f"Repository: {repo_label}",
            f"Branch: {branch}",
            f"Commit: {sha_short}",
            f"Job: {job_title}",
            "",
            f"Evidence fit: {score}%" if isinstance(score, (int, float)) else "Evidence fit: Not available",
            f"Demonstrated: {demo_total}",
            f"Partial: {part_total}",
            f"Not demonstrated in inspected scope: {miss_total}",
            "",
            "Proof Delta vs previous commit",
        ]

        if prev_snapshot and isinstance(prev_snapshot.get("assessment"), dict):
            delta = self._proof_delta_counts(prev_snapshot["assessment"], assessment)
            lines.extend([
                f"- Newly demonstrated: {delta['newly_demonstrated']}",
                f"- Improved: {delta['improved']}",
                f"- Regressed: {delta['regressed']}",
                f"- Unchanged: {delta['unchanged']}",
            ])
            prev_sha_short = str(prev_snapshot.get("commit_sha") or previous_sha or "")[:12]
            if prev_sha_short:
                lines.append("")
                lines.append(f"Previous commit: {prev_sha_short}")
        elif previous_sha:
            lines.append("- Baseline comparison unavailable for previous commit.")
            lines.append("")
            lines.append(f"Previous commit: {previous_sha[:12]}")
        else:
            lines.append("- Baseline unavailable (no prior snapshot to compare).")

        dashboard_url = _safe_dashboard_url(self.settings.public_base_url)
        if dashboard_url:
            lines.append("")
            lines.append(f"Dashboard: {dashboard_url}")

        message_id = await self._send_message(chat_id_str, "\n".join(lines))
        if message_id is None:
            self.store.finish_telegram_delivery(
                subscription_id=int(subscription["id"]),
                snapshot_id=snapshot_id,
                notification_type="automatic_reassessment",
                status="failed",
                message_id=None,
                error_message="Telegram delivery failed; the assessment snapshot remains available in the dashboard.",
            )
            return {"sent": False, "reason": "delivery_failed"}
        self._recent_notified_shas[chat_id_str] = commit_sha_full
        self.store.finish_telegram_delivery(
            subscription_id=int(subscription["id"]),
            snapshot_id=snapshot_id,
            notification_type="automatic_reassessment",
            status="sent",
            message_id=message_id,
            error_message=None,
        )
        return {"sent": True}

    def can_poll(self) -> bool:
        return bool(
            self.settings.telegram_notifications_enabled
            and self.settings.telegram_bot_token
            and not self.settings.public_base_url
        )

    async def poll_updates(self) -> int:
        if not self.can_poll():
            return 0
        token = self.settings.telegram_bot_token
        try:
            async with httpx.AsyncClient(
                base_url=self.settings.telegram_api_url,
                timeout=httpx.Timeout(10),
                follow_redirects=False,
                transport=self.transport,
            ) as client:
                response = await client.get(
                    f"/bot{token}/getUpdates",
                    params={"limit": 10, "timeout": 0},
                )
                if response.status_code != 200:
                    return 0
                payload = response.json()
                updates = payload.get("result", [])
                if not isinstance(updates, list) or not updates:
                    return 0
                max_update_id = 0
                for update in updates:
                    update_id = update.get("update_id")
                    if isinstance(update_id, int):
                        max_update_id = max(max_update_id, update_id)
                    await self.handle_webhook_update(update)
                if max_update_id > 0:
                    await client.get(
                        f"/bot{token}/getUpdates",
                        params={"offset": max_update_id + 1, "limit": 1, "timeout": 0},
                    )
                return len(updates)
        except Exception:
            return 0

