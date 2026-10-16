"""Explicit operator-only Telegram webhook setup for a deployed SkillPath AI instance.

Run this after setting server-side Telegram values and PUBLIC_BASE_URL. It never
prints a token, webhook secret, or full bot API URL.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from urllib.parse import urlparse

import httpx

from .config import Settings


def _public_base_url(value: str | None) -> str:
    parsed = urlparse(value or "")
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("PUBLIC_BASE_URL must be an HTTPS URL before a Telegram webhook can be configured.")
    return (value or "").rstrip("/")


async def run(action: str) -> int:
    settings = Settings.from_env()
    if not settings.telegram_bot_token:
        print("TELEGRAM_BOT_TOKEN is not configured.", file=sys.stderr)
        return 2
    if action == "set" and not settings.telegram_webhook_secret:
        print("TELEGRAM_WEBHOOK_SECRET is not configured.", file=sys.stderr)
        return 2
    try:
        base_url = _public_base_url(settings.public_base_url) if action == "set" else ""
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    method = "setWebhook" if action == "set" else "deleteWebhook"
    payload: dict[str, object] = {"drop_pending_updates": False}
    if action == "set":
        payload.update(
            {
                "url": f"{base_url}/api/integrations/telegram/webhook",
                "secret_token": settings.telegram_webhook_secret,
                "allowed_updates": ["message"],
            }
        )
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(settings.telegram_timeout_seconds)) as client:
            response = await client.post(
                f"{settings.telegram_api_url}/bot{settings.telegram_bot_token}/{method}", json=payload
            )
    except httpx.HTTPError:
        print("Telegram could not be reached. Check network access and try again.", file=sys.stderr)
        return 1
    if response.status_code >= 400:
        print(f"Telegram rejected the webhook request (HTTP {response.status_code}).", file=sys.stderr)
        return 1
    try:
        data = response.json()
    except ValueError:
        print("Telegram returned an unreadable webhook response.", file=sys.stderr)
        return 1
    if not isinstance(data, dict) or not data.get("ok"):
        print("Telegram did not confirm the webhook change.", file=sys.stderr)
        return 1
    print("Telegram webhook configured." if action == "set" else "Telegram webhook removed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure the deployed SkillPath AI Telegram webhook.")
    parser.add_argument("action", choices=("set", "delete"))
    arguments = parser.parse_args()
    return asyncio.run(run(arguments.action))


if __name__ == "__main__":
    raise SystemExit(main())
