"""Configura o elimina el webhook del canal Telegram del gateway A2A."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")


def _url_webhook(url: str) -> str:
    limpia = url.strip().rstrip("/")
    if not limpia.endswith("/telegram/webhook"):
        limpia += "/telegram/webhook"
    return limpia


def _datos(respuesta: httpx.Response) -> dict:
    if respuesta.headers.get("content-type", "").startswith("application/json"):
        return respuesta.json()
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Configura el webhook de Telegram.")
    parser.add_argument("--url", help="URL pública del gateway o URL completa del webhook.")
    parser.add_argument("--token", help="Token de BotFather. Si se omite, se lee de .env.")
    parser.add_argument("--secret", help="Secreto del webhook. Si se omite, se lee de .env.")
    parser.add_argument("--delete", action="store_true", help="Elimina el webhook.")
    args = parser.parse_args()

    token = (args.token or os.environ.get("TELEGRAM_TOKEN") or "").strip()
    secreto = (args.secret or os.environ.get("TELEGRAM_SECRET") or "").strip()
    base = (os.environ.get("TELEGRAM_API_BASE") or "https://api.telegram.org").rstrip("/")
    if not token:
        print("ERROR: falta TELEGRAM_TOKEN.")
        return 2

    if args.delete:
        respuesta = httpx.post(f"{base}/bot{token}/deleteWebhook", timeout=30)
        datos = _datos(respuesta)
        print("deleteWebhook:", respuesta.status_code, "ok:", datos.get("ok"), datos.get("description", ""))
        return 0 if respuesta.is_success else 1

    if not args.url:
        print("ERROR: falta --url (por ejemplo, la URL de un túnel HTTPS).")
        return 2
    if not secreto:
        print("ERROR: falta TELEGRAM_SECRET.")
        return 2

    url = _url_webhook(args.url)
    respuesta = httpx.post(
        f"{base}/bot{token}/setWebhook",
        json={
            "url": url,
            "secret_token": secreto,
            "allowed_updates": ["message", "edited_message"],
        },
        timeout=30,
    )
    datos = _datos(respuesta)
    print("setWebhook:", respuesta.status_code, "ok:", datos.get("ok"))
    print("URL:", url)
    if datos.get("description"):
        print("Descripción:", datos["description"])
    return 0 if respuesta.is_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
