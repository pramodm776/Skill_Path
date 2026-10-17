from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _load(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return fallback


class SQLiteStore:
    """Small persistence layer. Each operation uses a short-lived SQLite connection."""

    def __init__(self, database_path: str, *, journal_mode: str = "WAL"):
        self.database_path = database_path
        self.journal_mode = journal_mode if journal_mode in {"WAL", "DELETE"} else "WAL"
        Path(database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = ${journal_mode};

                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    description TEXT NOT NULL,
                    skills_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS repositories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    repository_url TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    name TEXT NOT NULL,
                    default_branch TEXT NOT NULL,
                    latest_known_sha TEXT,
                    latest_commit_url TEXT,
                    monitor_enabled INTEGER NOT NULL DEFAULT 1,
                    monitor_state TEXT NOT NULL DEFAULT 'idle',
                    last_checked_at TEXT,
                    last_assessed_at TEXT,
                    last_error_code TEXT,
                    last_error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(job_id, repository_url)
                );

                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                    commit_sha TEXT NOT NULL,
                    commit_url TEXT NOT NULL,
                    trigger TEXT NOT NULL,
                    assessed_at TEXT NOT NULL,
                    assessment_json TEXT NOT NULL,
                    inspection_json TEXT NOT NULL,
                    changed_files_json TEXT NOT NULL,
                    llm_json TEXT NOT NULL,
                    UNIQUE(repository_id, commit_sha)
                );

                CREATE TABLE IF NOT EXISTS monitor_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    previous_sha TEXT,
                    current_sha TEXT,
                    snapshot_id INTEGER REFERENCES snapshots(id) ON DELETE SET NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS telegram_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repository_id INTEGER NOT NULL UNIQUE REFERENCES repositories(id) ON DELETE CASCADE,
                    pairing_token_hash TEXT,
                    pairing_expires_at TEXT,
                    chat_id TEXT,
                    active INTEGER NOT NULL DEFAULT 0,
                    last_notified_at TEXT,
                    last_error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS telegram_deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscription_id INTEGER NOT NULL REFERENCES telegram_subscriptions(id) ON DELETE CASCADE,
                    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
                    notification_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    telegram_message_id INTEGER,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(subscription_id, snapshot_id, notification_type)
                );

                CREATE INDEX IF NOT EXISTS idx_snapshots_repository_assessed
                    ON snapshots(repository_id, assessed_at DESC);
                CREATE INDEX IF NOT EXISTS idx_events_repository_created
                    ON monitor_events(repository_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_telegram_subscriptions_pairing
                    ON telegram_subscriptions(pairing_token_hash);
                """.replace("${journal_mode}", self.journal_mode)
            )

    @staticmethod
    def _job(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        item = dict(row)
        item["skills"] = _load(item.pop("skills_json", None), [])
        return item

    @staticmethod
    def _repository(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        item = dict(row)
        item["monitor_enabled"] = bool(item["monitor_enabled"])
        return item

    @staticmethod
    def _snapshot(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        item = dict(row)
        item["assessment"] = _load(item.pop("assessment_json", None), {})
        item["inspection"] = _load(item.pop("inspection_json", None), {})
        item["changed_files"] = _load(item.pop("changed_files_json", None), [])
        item["llm"] = _load(item.pop("llm_json", None), {})
        return item

    @staticmethod
    def _event(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        item = dict(row)
        item["details"] = _load(item.pop("details_json", None), {})
        return item

    @staticmethod
    def _telegram_subscription(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        item = dict(row)
        item["active"] = bool(item["active"])
        return item

    def create_job(
        self,
        *,
        title: str,
        company: str,
        source_url: str,
        description: str,
        skills: list[dict[str, Any]],
    ) -> dict[str, Any]:
        now = utc_now()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO jobs (title, company, source_url, description, skills_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (title, company, source_url, description, _dump(skills), now, now),
            )
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._job(row) or {}

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs ORDER BY id DESC"
            ).fetchall()
        return [self._job(row) or {} for row in rows]

    def get_job(self, job_id: int) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._job(row)

    def update_job(
        self,
        job_id: int,
        *,
        title: str,
        company: str,
        source_url: str,
        description: str,
        skills: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        now = utc_now()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs
                SET title = ?, company = ?, source_url = ?, description = ?,
                    skills_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (title, company, source_url, description, _dump(skills), now, job_id),
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._job(row)

    def delete_job(self, job_id: int) -> bool:
        """Delete a job and cascade to its repositories, snapshots, and events via FK."""
        with self._connection() as connection:
            cursor = connection.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        return cursor.rowcount > 0

    def create_repository(
        self,
        *,
        job_id: int,
        repository_url: str,
        owner: str,
        name: str,
        default_branch: str,
    ) -> dict[str, Any]:
        now = utc_now()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO repositories
                  (job_id, repository_url, owner, name, default_branch, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, repository_url, owner, name, default_branch, now, now),
            )
            row = connection.execute(
                "SELECT * FROM repositories WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return self._repository(row) or {}

    def find_repository(self, job_id: int, repository_url: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM repositories WHERE job_id = ? AND repository_url = ?",
                (job_id, repository_url),
            ).fetchone()
        return self._repository(row)

    def find_repositories_by_full_name(self, owner: str, name: str) -> list[dict[str, Any]]:
        """Return all monitored repositories matching owner/name across all jobs, newest first."""
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM repositories WHERE owner = ? AND name = ? AND monitor_enabled = 1 ORDER BY id DESC",
                (owner, name),
            ).fetchall()
        return [self._repository(row) or {} for row in rows]

    def get_repository(self, repository_id: int) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM repositories WHERE id = ?", (repository_id,)).fetchone()
        return self._repository(row)

    def get_repository_with_job(self, repository_id: int) -> dict[str, Any] | None:
        repository = self.get_repository(repository_id)
        if not repository:
            return None
        repository["job"] = self.get_job(int(repository["job_id"]))
        return repository

    def list_repositories(self, job_id: int | None = None) -> list[dict[str, Any]]:
        with self._connection() as connection:
            if job_id is not None:
                rows = connection.execute(
                    "SELECT * FROM repositories WHERE job_id = ? ORDER BY id DESC",
                    (job_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM repositories ORDER BY id DESC"
                ).fetchall()
        return [self._repository(row) or {} for row in rows]

    def delete_repository(self, repository_id: int) -> bool:
        """Delete a repository and cascade to its snapshots, events, and subscriptions via FK."""
        with self._connection() as connection:
            cursor = connection.execute("DELETE FROM repositories WHERE id = ?", (repository_id,))
        return cursor.rowcount > 0

    def update_repository_metadata(
        self,
        repository_id: int,
        *,
        default_branch: str | None = None,
        owner: str | None = None,
        name: str | None = None,
    ) -> None:
        fields: list[str] = ["updated_at = ?"]
        values: list[Any] = [utc_now()]
        for column, value in (("default_branch", default_branch), ("owner", owner), ("name", name)):
            if value:
                fields.append(f"{column} = ?")
                values.append(value)
        values.append(repository_id)
        with self._connection() as connection:
            connection.execute(f"UPDATE repositories SET {', '.join(fields)} WHERE id = ?", values)

    def record_check(
        self,
        repository_id: int,
        *,
        state: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE repositories
                SET last_checked_at = ?, monitor_state = ?, last_error_code = ?, last_error_message = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (now, state, error_code, error_message, now, repository_id),
            )

    def set_monitor_enabled(self, repository_id: int, enabled: bool) -> None:
        with self._connection() as connection:
            connection.execute(
                "UPDATE repositories SET monitor_enabled = ?, updated_at = ? WHERE id = ?",
                (int(enabled), utc_now(), repository_id),
            )

    def monitored_repositories(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM repositories WHERE monitor_enabled = 1 ORDER BY id DESC"
            ).fetchall()
        return [self._repository(row) or {} for row in rows]

    def create_snapshot(
        self,
        *,
        repository_id: int,
        commit_sha: str,
        commit_url: str,
        trigger: str,
        assessment: dict[str, Any],
        inspection: dict[str, Any],
        changed_files: list[dict[str, Any]],
        llm: dict[str, Any],
        refresh_existing: bool = False,
    ) -> tuple[dict[str, Any], bool]:
        now = utc_now()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO snapshots
                  (repository_id, commit_sha, commit_url, trigger, assessed_at, assessment_json,
                   inspection_json, changed_files_json, llm_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    repository_id,
                    commit_sha,
                    commit_url,
                    trigger,
                    now,
                    _dump(assessment),
                    _dump(inspection),
                    _dump(changed_files),
                    _dump(llm),
                ),
            )
            created = cursor.rowcount == 1
            if not created and refresh_existing:
                connection.execute(
                    """
                    UPDATE snapshots
                    SET assessed_at = ?, assessment_json = ?, inspection_json = ?, llm_json = ?
                    WHERE repository_id = ? AND commit_sha = ?
                    """,
                    (
                        now,
                        _dump(assessment),
                        _dump(inspection),
                        _dump(llm),
                        repository_id,
                        commit_sha,
                    ),
                )
            row = connection.execute(
                "SELECT * FROM snapshots WHERE repository_id = ? AND commit_sha = ?",
                (repository_id, commit_sha),
            ).fetchone()
            if created or refresh_existing:
                connection.execute(
                    """
                    UPDATE repositories
                    SET latest_known_sha = ?, latest_commit_url = ?, last_assessed_at = ?,
                        monitor_state = 'active', last_error_code = NULL, last_error_message = NULL,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (commit_sha, commit_url, now, now, repository_id),
                )
        return self._snapshot(row) or {}, created

    def get_snapshot(self, snapshot_id: int) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
        return self._snapshot(row)

    def latest_snapshot(self, repository_id: int) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM snapshots WHERE repository_id = ? ORDER BY id DESC LIMIT 1",
                (repository_id,),
            ).fetchone()
        return self._snapshot(row)

    def history(self, repository_id: int) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM snapshots WHERE repository_id = ? ORDER BY id DESC", (repository_id,)
            ).fetchall()
        return [self._snapshot(row) or {} for row in rows]

    def get_snapshot_by_sha(self, repository_id: int, commit_sha: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM snapshots WHERE repository_id = ? AND commit_sha = ? LIMIT 1",
                (repository_id, commit_sha),
            ).fetchone()
        return self._snapshot(row)

    def previous_snapshot_for(self, repository_id: int, current_snapshot_id: int) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM snapshots WHERE repository_id = ? AND id < ? ORDER BY id DESC LIMIT 1",
                (repository_id, current_snapshot_id),
            ).fetchone()
        return self._snapshot(row)

    def latest_repository_id_for_full_name(self, owner: str, name: str) -> int | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id FROM repositories WHERE owner = ? AND name = ? AND monitor_enabled = 1 ORDER BY id DESC LIMIT 1",
                (owner, name),
            ).fetchone()
        return int(row["id"]) if row else None

    def record_event(
        self,
        repository_id: int,
        *,
        event_type: str,
        message: str,
        previous_sha: str | None = None,
        current_sha: str | None = None,
        snapshot_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO monitor_events
                  (repository_id, event_type, message, previous_sha, current_sha, snapshot_id,
                   details_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    repository_id,
                    event_type,
                    message,
                    previous_sha,
                    current_sha,
                    snapshot_id,
                    _dump(details or {}),
                    utc_now(),
                ),
            )
            row = connection.execute(
                "SELECT * FROM monitor_events WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return self._event(row) or {}

    def events(self, repository_id: int, limit: int = 12) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM monitor_events WHERE repository_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (repository_id, limit),
            ).fetchall()
        return [self._event(row) or {} for row in rows]

    def telegram_subscription(self, repository_id: int) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM telegram_subscriptions WHERE repository_id = ?", (repository_id,)
            ).fetchone()
            if not row:
                repo = connection.execute(
                    "SELECT owner, name FROM repositories WHERE id = ?", (repository_id,)
                ).fetchone()
                if repo:
                    sibling = connection.execute(
                        """
                        SELECT ts.chat_id FROM telegram_subscriptions ts
                        JOIN repositories r ON ts.repository_id = r.id
                        WHERE r.owner = ? AND r.name = ? AND ts.active = 1 AND ts.chat_id IS NOT NULL
                        LIMIT 1
                        """,
                        (repo["owner"], repo["name"]),
                    ).fetchone()
                    if sibling and sibling["chat_id"]:
                        now = utc_now()
                        connection.execute(
                            """
                            INSERT OR IGNORE INTO telegram_subscriptions
                              (repository_id, pairing_token_hash, pairing_expires_at, chat_id, active,
                               last_notified_at, last_error_message, created_at, updated_at)
                            VALUES (?, NULL, NULL, ?, 1, NULL, NULL, ?, ?)
                            """,
                            (repository_id, sibling["chat_id"], now, now),
                        )
                        row = connection.execute(
                            "SELECT * FROM telegram_subscriptions WHERE repository_id = ?", (repository_id,)
                        ).fetchone()
        return self._telegram_subscription(row)

    def create_telegram_pairing(
        self, *, repository_id: int, token_hash: str, expires_at: str
    ) -> dict[str, Any]:
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO telegram_subscriptions
                  (repository_id, pairing_token_hash, pairing_expires_at, chat_id, active,
                   last_notified_at, last_error_message, created_at, updated_at)
                VALUES (?, ?, ?, NULL, 0, NULL, NULL, ?, ?)
                ON CONFLICT(repository_id) DO UPDATE SET
                  pairing_token_hash = excluded.pairing_token_hash,
                  pairing_expires_at = excluded.pairing_expires_at,
                  chat_id = NULL,
                  active = 0,
                  last_notified_at = NULL,
                  last_error_message = NULL,
                  updated_at = excluded.updated_at
                """,
                (repository_id, token_hash, expires_at, now, now),
            )
            row = connection.execute(
                "SELECT * FROM telegram_subscriptions WHERE repository_id = ?", (repository_id,)
            ).fetchone()
        return self._telegram_subscription(row) or {}

    def consume_telegram_pairing(
        self, *, token_hash: str, chat_id: str, now: str
    ) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM telegram_subscriptions
                WHERE pairing_token_hash = ? AND pairing_expires_at > ? AND active = 0
                """,
                (token_hash, now),
            ).fetchone()
            if row is None:
                return None
            subscription_id = int(row["id"])
            repository_id = int(row["repository_id"])
            repo = connection.execute(
                "SELECT owner, name FROM repositories WHERE id = ?", (repository_id,)
            ).fetchone()
            now_ts = utc_now()
            if repo:
                connection.execute(
                    """
                    UPDATE telegram_subscriptions
                    SET active = 0, updated_at = ?
                    WHERE repository_id IN (
                        SELECT id FROM repositories WHERE owner = ? AND name = ? AND id != ?
                    )
                    """,
                    (now_ts, repo["owner"], repo["name"], repository_id),
                )
            connection.execute(
                """
                UPDATE telegram_subscriptions
                SET pairing_token_hash = NULL, pairing_expires_at = NULL, chat_id = ?, active = 1,
                    last_error_message = NULL, updated_at = ?
                WHERE id = ?
                """,
                (chat_id, now_ts, subscription_id),
            )
            updated = connection.execute(
                "SELECT * FROM telegram_subscriptions WHERE id = ?", (subscription_id,)
            ).fetchone()
        return self._telegram_subscription(updated)

    def deactivate_telegram_chat(self, chat_id: str) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE telegram_subscriptions
                SET active = 0, chat_id = NULL, pairing_token_hash = NULL, pairing_expires_at = NULL,
                    updated_at = ?
                WHERE chat_id = ? AND active = 1
                """,
                (utc_now(), chat_id),
            )
        return cursor.rowcount > 0

    def claim_telegram_delivery(
        self,
        *,
        subscription_id: int,
        snapshot_id: int,
        notification_type: str,
        chat_id: str | None = None,
        owner: str | None = None,
        name: str | None = None,
        commit_sha: str | None = None,
    ) -> bool:
        now = utc_now()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if chat_id and owner and name and commit_sha:
                already_claimed = connection.execute(
                    """
                    SELECT td.id FROM telegram_deliveries td
                    JOIN telegram_subscriptions ts ON td.subscription_id = ts.id
                    JOIN snapshots s ON td.snapshot_id = s.id
                    JOIN repositories r ON s.repository_id = r.id
                    WHERE ts.chat_id = ? AND r.owner = ? AND r.name = ? AND s.commit_sha = ?
                      AND td.notification_type = ? AND td.status IN ('pending', 'sent')
                    LIMIT 1
                    """,
                    (chat_id, owner, name, commit_sha, notification_type),
                ).fetchone()
                if already_claimed is not None:
                    return False

            existing = connection.execute(
                """
                SELECT status FROM telegram_deliveries
                WHERE subscription_id = ? AND snapshot_id = ? AND notification_type = ?
                """,
                (subscription_id, snapshot_id, notification_type),
            ).fetchone()
            if existing is not None:
                if existing["status"] == "failed":
                    cursor = connection.execute(
                        """
                        UPDATE telegram_deliveries
                        SET status = 'pending', error_message = NULL, updated_at = ?
                        WHERE subscription_id = ? AND snapshot_id = ? AND notification_type = ? AND status = 'failed'
                        """,
                        (now, subscription_id, snapshot_id, notification_type),
                    )
                    return cursor.rowcount == 1
                return False

            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO telegram_deliveries
                  (subscription_id, snapshot_id, notification_type, status, telegram_message_id,
                   error_message, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', NULL, NULL, ?, ?)
                """,
                (subscription_id, snapshot_id, notification_type, now, now),
            )
        return cursor.rowcount == 1

    def finish_telegram_delivery(
        self,
        *,
        subscription_id: int,
        snapshot_id: int,
        notification_type: str,
        status: str,
        message_id: int | None,
        error_message: str | None,
    ) -> None:
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE telegram_deliveries
                SET status = ?, telegram_message_id = ?, error_message = ?, updated_at = ?
                WHERE subscription_id = ? AND snapshot_id = ? AND notification_type = ?
                """,
                (status, message_id, error_message, now, subscription_id, snapshot_id, notification_type),
            )
            if status == "sent":
                connection.execute(
                    """
                    UPDATE telegram_subscriptions
                    SET last_notified_at = ?, last_error_message = NULL, updated_at = ?
                    WHERE id = ?
                    """,
                    (now, now, subscription_id),
                )
            elif error_message:
                connection.execute(
                    """
                    UPDATE telegram_subscriptions
                    SET last_error_message = ?, updated_at = ? WHERE id = ?
                    """,
                    (error_message, now, subscription_id),
                )
