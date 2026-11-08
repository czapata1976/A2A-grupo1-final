"""Canal Telegram: recibe updates y consulta el gateway A2A."""

from __future__ import annotations

import logging
import secrets
from uuid import uuid4

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from app.config import Settings
from app.errores import ErrorServicio
from app.modelos import ConsultaEntrada
from app.orquestador import Orquestador

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

MENSAJE_AYUDA = (
    "Hola. Soy el canal Telegram de los agentes A2A del Grupo 1.\n\n"
    "Escríbeme una consulta y elegiré el especialista automáticamente.\n\n"
    "Comandos:\n"
    "/agente_czz <consulta>\n"
    "/agente <nombre> <consulta>\n"
    "/paralelo agente_czz,agente_bryhan <consulta>\n"
    "/colaborativo agente_czz,agente_alejandra <consulta>\n"
    "/ayuda"
)


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


def seleccionar_consulta(texto: str) -> tuple[list[str] | None, str, str]:
    limpio = texto.strip()
    if limpio.startswith("/agente "):
        partes = limpio.split(maxsplit=2)
        if len(partes) >= 3:
            return [partes[1]], "individual", partes[2].strip()
        return None, "auto", limpio

    if limpio.startswith("/"):
        primera, _, resto = limpio.partition(" ")
        comando = primera[1:]
        if comando in {"paralelo", "colaborativo"}:
            partes = resto.split(maxsplit=1)
            if len(partes) == 2:
                agentes = [agente.strip() for agente in partes[0].split(",") if agente.strip()]
                if agentes:
                    return agentes, comando, partes[1].strip()
        if comando.startswith("agente_"):
            return [comando], "individual", resto.strip()

    return None, "auto", limpio


async def enviar_telegram(settings: Settings, chat_id: int, texto: str) -> None:
    if not settings.telegram_token:
        raise RuntimeError("TELEGRAM_TOKEN no configurado.")
    if len(texto) > 4000:
        texto = texto[:3990] + "\n\n(recortado)"
    url = f"{settings.telegram_api_base}/bot{settings.telegram_token}/sendMessage"
    async with httpx.AsyncClient(timeout=30, trust_env=False) as cliente:
        respuesta = await cliente.post(url, json={"chat_id": chat_id, "text": texto})
        respuesta.raise_for_status()


async def procesar_actualizacion(
    orquestador: Orquestador,
    settings: Settings,
    chat_id: int,
    agentes: list[str] | None,
    modo: str,
    texto: str,
) -> None:
    try:
        entrada = ConsultaEntrada(
            mensaje=texto,
            agentes=agentes,
            modo=modo,
            session_id=f"telegram-{chat_id}",
        )
        salida = await orquestador.consultar(
            entrada,
            solicitud_id=uuid4().hex,
            huella="telegram",
        )
        respuesta = salida.respuesta
        if salida.estado == "parcial":
            respuesta = (
                f"{respuesta}\n\n(Respuesta parcial: {'; '.join(salida.errores)})"
            )
    except ErrorServicio as error:
        logger.warning("Telegram: error de servicio %s", error.codigo)
        respuesta = f"No pude responder la consulta: {error.mensaje}"
        if error.detalles:
            respuesta += " " + " ".join(error.detalles)
    except Exception:
        logger.exception("Telegram: error inesperado")
        respuesta = "No pude procesar tu mensaje. Revisa el servicio e intenta nuevamente."

    try:
        await enviar_telegram(settings, chat_id, respuesta)
    except Exception:
        logger.exception("Telegram: no se pudo enviar la respuesta")


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    settings: Settings = request.app.state.settings
    if not settings.telegram_token:
        raise HTTPException(
            status_code=503,
            detail="TELEGRAM_TOKEN no configurado. Agrega el token de BotFather en .env.",
        )
    if not settings.telegram_secret:
        raise HTTPException(
            status_code=503,
            detail="TELEGRAM_SECRET no configurado.",
        )
    recibido = x_telegram_bot_api_secret_token or ""
    if not secrets.compare_digest(
        recibido.encode("utf-8"),
        settings.telegram_secret.encode("utf-8"),
    ):
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

    if texto.lower() in {"/start", "/help", "/ayuda"}:
        background_tasks.add_task(enviar_telegram, settings, chat_id, MENSAJE_AYUDA)
        return {"ok": True, "ayuda": True}

    agentes, modo, texto_limpio = seleccionar_consulta(texto)
    if not texto_limpio:
        background_tasks.add_task(enviar_telegram, settings, chat_id, MENSAJE_AYUDA)
        return {"ok": True, "ayuda": True}

    orquestador: Orquestador = request.app.state.orquestador
    background_tasks.add_task(
        procesar_actualizacion,
        orquestador,
        settings,
        chat_id,
        agentes,
        modo,
        texto_limpio,
    )
    return {"ok": True, "modo": modo, "agentes": agentes or "auto"}
