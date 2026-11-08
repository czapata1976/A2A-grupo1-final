"""API FastAPI con webhook de Telegram."""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")

from src.agentes import listar_agentes, obtener_agente
from src.mensajes import crear_entrada, extraer_texto

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("telegram")

app = FastAPI(
    title="Agentes + Telegram",
    description="API que recibe actualizaciones de Telegram y responde con un agente LangGraph.",
    version="1.0.0",
)


def _token_telegram() -> str:
    return (os.environ.get("TELEGRAM_TOKEN") or "").strip()


def _secreto_telegram() -> str:
    return (os.environ.get("TELEGRAM_SECRET") or "").strip()


def _base_telegram() -> str:
    return (os.environ.get("TELEGRAM_API_BASE") or "https://api.telegram.org").rstrip("/")


def extraer_mensaje(update: dict) -> tuple[int, str] | None:
    mensaje = update.get("message") or update.get("edited_message")
    if not isinstance(mensaje, dict):
        return None
    texto = mensaje.get("text")
    chat = mensaje.get("chat") or {}
    chat_id = chat.get("id") if isinstance(chat, dict) else None
    if not isinstance(texto, str) or not texto.strip() or chat_id is None:
        return None
    return int(chat_id), texto.strip()


def seleccionar_agente(texto: str) -> tuple[str, str]:
    disponibles = listar_agentes()
    predeterminado = (os.environ.get("AGENTE_PREDETERMINADO") or "agente_general").strip()
    if predeterminado not in disponibles:
        predeterminado = disponibles[0]

    if texto.startswith("/agente "):
        partes = texto.split(maxsplit=2)
        if len(partes) >= 3 and partes[1] in disponibles:
            return partes[1], partes[2].strip()

    if texto.startswith("/"):
        primera, _, resto = texto.partition(" ")
        nombre = primera[1:]
        if nombre in disponibles:
            return nombre, resto.strip()

    return predeterminado, texto


def procesar_consulta(nombre: str, texto: str) -> str:
    grafo = obtener_agente(nombre)
    estado = grafo.invoke(crear_entrada(texto))
    return extraer_texto(estado)


async def enviar_telegram(chat_id: int, texto: str) -> None:
    token = _token_telegram()
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN no configurado.")
    if len(texto) > 4000:
        texto = texto[:3990] + "\n\n(recortado)"
    url = f"{_base_telegram()}/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=30, trust_env=False) as cliente:
        respuesta = await cliente.post(
            url,
            json={"chat_id": chat_id, "text": texto},
        )
        respuesta.raise_for_status()


async def procesar_actualizacion(chat_id: int, agente: str, texto: str) -> None:
    try:
        respuesta = await asyncio.to_thread(procesar_consulta, agente, texto)
    except Exception:
        logger.exception("Falló el agente %s", agente)
        respuesta = (
            "No pude procesar tu mensaje. Revisa la configuración del agente "
            "e intenta nuevamente."
        )
    try:
        await enviar_telegram(chat_id, respuesta)
    except Exception:
        logger.exception("No se pudo enviar la respuesta por Telegram")


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "agentes": listar_agentes()}


@app.get("/")
async def inicio() -> dict:
    return {"servicio": "agentes-telegram", "docs": "/docs", "agentes": listar_agentes()}


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    if not _token_telegram():
        raise HTTPException(
            status_code=503,
            detail="TELEGRAM_TOKEN no configurado. Agrega el token de BotFather en .env.",
        )
    secreto = _secreto_telegram()
    if not secreto:
        raise HTTPException(
            status_code=503,
            detail="TELEGRAM_SECRET no configurado.",
        )
    recibido = x_telegram_bot_api_secret_token or ""
    if not secrets.compare_digest(recibido.encode("utf-8"), secreto.encode("utf-8")):
        raise HTTPException(status_code=403, detail="Secreto de Telegram inválido.")

    try:
        update = await request.json()
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail="El cuerpo no es un update JSON válido.",
        ) from error
    if not isinstance(update, dict):
        raise HTTPException(status_code=400, detail="El update debe ser un objeto JSON.")

    mensaje = extraer_mensaje(update)
    if mensaje is None:
        return {"ok": True, "ignorado": True}

    chat_id, texto = mensaje
    agente, texto_agente = seleccionar_agente(texto)
    if not texto_agente:
        return {"ok": True, "ignorado": True, "agente": agente}

    background_tasks.add_task(procesar_actualizacion, chat_id, agente, texto_agente)
    return {"ok": True, "agente": agente}
