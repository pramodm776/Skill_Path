from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - requirements install this in normal use
    load_dotenv = None  # type: ignore[assignment]


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if load_dotenv:
    # Loading a local .env is optional convenience; deployed environments use their own variables.
    load_dotenv(PROJECT_ROOT / ".env", override=False)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int, minimum: int) -> int:
    try:
        parsed = int(value or default)
    except ValueError:
        return default
    return max(parsed, minimum)


def _sqlite_journal_mode(value: str | None) -> str:
    mode = (value or "WAL").strip().upper()
    return mode if mode in {"WAL", "DELETE"} else "WAL"


@dataclass(frozen=True)
class Settings:
    """Runtime configuration. Secrets remain process-local environment values."""

    database_path: str
    github_token: str | None
    github_api_url: str
    github_timeout_seconds: int
    github_max_files: int
    github_max_file_bytes: int
    github_max_total_bytes: int
    poll_interval_seconds: int
    monitoring_enabled: bool
    openai_api_key: str | None
    openai_model: str
    enable_llm_explanations: bool
    # Reserved for opt-in integrations.  Defining a value alone never enables
    # a provider request; the corresponding feature must explicitly opt in.
    xai_api_key: str | None
    xai_api_url: str
    xai_model: str | None
    enable_xai_fallback: bool
    jsearch_api_key: str | None
    jsearch_api_url: str
    jsearch_timeout_seconds: int
    telegram_bot_token: str | None
    telegram_webhook_secret: str | None
    telegram_api_url: str
    telegram_notifications_enabled: bool
    azure_key_vault_url: str | None
    applicationinsights_connection_string: str | None
    public_base_url: str | None = None
    telegram_bot_username: str | None = None
    telegram_pairing_ttl_seconds: int = 600
    telegram_timeout_seconds: int = 12
    sqlite_journal_mode: str = "WAL"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_path=os.getenv(
                "DATABASE_PATH", str(PROJECT_ROOT / "data" / "career_coach.sqlite3")
            ),
            github_token=os.getenv("GITHUB_TOKEN") or None,
            github_api_url=os.getenv("GITHUB_API_URL", "https://api.github.com").rstrip("/"),
            github_timeout_seconds=_as_int(
                os.getenv("GITHUB_TIMEOUT_SECONDS"), default=15, minimum=3
            ),
            github_max_files=_as_int(os.getenv("GITHUB_MAX_FILES"), default=20, minimum=1),
            github_max_file_bytes=_as_int(
                os.getenv("GITHUB_MAX_FILE_BYTES"), default=200_000, minimum=1_024
            ),
            github_max_total_bytes=_as_int(
                os.getenv("GITHUB_MAX_TOTAL_BYTES"), default=1_500_000, minimum=10_000
            ),
            poll_interval_seconds=_as_int(
                os.getenv("POLL_INTERVAL_SECONDS"), default=60, minimum=10
            ),
            monitoring_enabled=_as_bool(os.getenv("MONITORING_ENABLED"), default=True),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            enable_llm_explanations=_as_bool(
                os.getenv("ENABLE_LLM_EXPLANATIONS"), default=False
            ),
            xai_api_key=os.getenv("XAI_API_KEY") or None,
            xai_api_url=os.getenv("XAI_API_URL", "https://api.x.ai/v1").rstrip("/"),
            xai_model=os.getenv("XAI_MODEL") or None,
            enable_xai_fallback=_as_bool(os.getenv("ENABLE_XAI_FALLBACK"), default=False),
            jsearch_api_key=os.getenv("JSEARCH_API_KEY") or None,
            jsearch_api_url=os.getenv(
                "JSEARCH_API_URL", "https://jsearch.p.rapidapi.com"
            ).rstrip("/"),
            jsearch_timeout_seconds=_as_int(
                os.getenv("JSEARCH_TIMEOUT_SECONDS"), default=15, minimum=3
            ),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or None,
            telegram_webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET") or None,
            telegram_api_url=os.getenv("TELEGRAM_API_URL", "https://api.telegram.org").rstrip(
                "/"
            ),
            telegram_notifications_enabled=_as_bool(
                os.getenv("TELEGRAM_NOTIFICATIONS_ENABLED"), default=False
            ),
            # Azure Container Apps injects runtime values from Key Vault.  The
            # app deliberately does not require Azure client secrets locally.
            azure_key_vault_url=os.getenv("AZURE_KEY_VAULT_URL") or None,
            applicationinsights_connection_string=os.getenv(
                "APPLICATIONINSIGHTS_CONNECTION_STRING"
            )
            or None,
            public_base_url=os.getenv("PUBLIC_BASE_URL", "").rstrip("/") or None,
            telegram_bot_username=os.getenv("TELEGRAM_BOT_USERNAME", "").lstrip("@").strip()
            or None,
            telegram_pairing_ttl_seconds=_as_int(
                os.getenv("TELEGRAM_PAIRING_TTL_SECONDS"), default=600, minimum=60
            ),
            telegram_timeout_seconds=_as_int(
                os.getenv("TELEGRAM_TIMEOUT_SECONDS"), default=12, minimum=3
            ),
            sqlite_journal_mode=_sqlite_journal_mode(os.getenv("SQLITE_JOURNAL_MODE")),
        )
