"""Canal WhatsApp: entrada desde el puente Baileys y panel del operador.

El puente (Node + Baileys) entrega cada mensaje propio al endpoint interno
`POST /whatsapp/mensaje` y publica su estado en loopback. El panel de esta
aplicación es la única superficie pública; nunca expone el puente.
"""

from __future__ import annotations

import logging
import secrets
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from app.cliente_whatsapp import ClienteWhatsApp
from app.errores import ErrorServicio
from app.modelos import ConsultaEntrada, PATRON_SESION
from app.orquestador import Orquestador
from app.seguridad import ClienteAutenticado, limitar
from app.telegram import seleccionar_consulta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
DIRECTORIO_ESTATICO = Path(__file__).resolve().parent / "static"

MENSAJE_AYUDA = (
    "Hola. Soy el canal WhatsApp de los agentes A2A del Grupo 1.\n\n"
    "Escríbeme una consulta y elegiré el especialista automáticamente.\n\n"
    "Comandos:\n"
    "/agente_czz <consulta>\n"
    "/agente <nombre> <consulta>\n"
    "/paralelo agente_czz,agente_bryhan <consulta>\n"
    "/colaborativo agente_czz,agente_alejandra <consulta>\n"
    "/ayuda"
)

PATRON_TELEFONO = r"^[1-9][0-9]{6,14}$"


class MensajeWhatsApp(BaseModel):
    """Mensaje entregado por el puente local, ya validado en el celular."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    mensaje: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, pattern=PATRON_SESION.pattern)
    request_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{16,64}$")


class ModoVinculacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modo: Literal["code", "qr"]


class TelefonoVinculacion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    telefono: str = Field(pattern=PATRON_TELEFONO)


class RespuestaWhatsApp(BaseModel):
    respuesta: str
    estado: str
    agentes: list[str] = Field(default_factory=list)


def _recortar(texto: str, limite: int) -> str:
    sufijo = "\n\n(recortado)"
    if len(texto) <= limite:
        return texto
    return texto[: max(1, limite - len(sufijo))].rstrip() + sufijo


def _puente(request: Request) -> ClienteWhatsApp:
    settings = request.app.state.settings
    if not (settings.whatsapp_habilitado and settings.whatsapp_secret):
        raise ErrorServicio(
            503,
            "WHATSAPP_NO_HABILITADO",
            "El canal WhatsApp no está habilitado en este despliegue.",
        )
    cliente = getattr(request.app.state, "whatsapp", None)
    if cliente is None:
        cliente = ClienteWhatsApp(
            settings.whatsapp_url_interna,
            settings.whatsapp_secret,
            settings.whatsapp_timeout,
        )
        request.app.state.whatsapp = cliente
    return cliente


@router.post("/mensaje", response_model=RespuestaWhatsApp)
async def mensaje_entrante(request: Request, cuerpo: MensajeWhatsApp) -> RespuestaWhatsApp:
    """Recibe un mensaje del puente, consulta los agentes y devuelve el texto."""

    settings = request.app.state.settings
    if not (settings.whatsapp_habilitado and settings.whatsapp_secret):
        raise HTTPException(
            status_code=503,
            detail="El canal WhatsApp no está habilitado en este despliegue.",
        )
    recibido = request.headers.get("x-whatsapp-secret", "")
    if not secrets.compare_digest(
        recibido.encode("utf-8"),
        settings.whatsapp_secret.encode("utf-8"),
    ):
        raise HTTPException(status_code=403, detail="Secreto de WhatsApp inválido.")

    texto = cuerpo.mensaje.strip()
    if texto.lower() in {"/start", "/help", "/ayuda"}:
        return RespuestaWhatsApp(respuesta=MENSAJE_AYUDA, estado="ok")

    agentes, modo, texto_limpio = seleccionar_consulta(texto)
    if not texto_limpio:
        return RespuestaWhatsApp(respuesta=MENSAJE_AYUDA, estado="ok")

    session_id = cuerpo.session_id or f"wa-{uuid4().hex[:16]}"
    entrada = ConsultaEntrada(
        mensaje=texto_limpio,
        agentes=agentes,
        modo=modo,
        session_id=session_id,
    )
    orquestador: Orquestador = request.app.state.orquestador
    try:
        salida = await orquestador.consultar(
            entrada,
            solicitud_id=cuerpo.request_id or uuid4().hex,
            huella="whatsapp",
        )
    except ErrorServicio as error:
        logger.warning("WhatsApp: error de servicio %s", error.codigo)
        respuesta = f"No pude responder la consulta: {error.mensaje}"
        if error.detalles:
            respuesta += " " + " ".join(error.detalles)
        return RespuestaWhatsApp(
            respuesta=_recortar(respuesta, settings.whatsapp_max_caracteres),
            estado="error",
        )
    except Exception:
        logger.exception("WhatsApp: error inesperado")
        return RespuestaWhatsApp(
            respuesta="No pude procesar tu mensaje. Revisa el servicio e intenta nuevamente.",
            estado="error",
        )

    respuesta = salida.respuesta
    if salida.estado == "parcial":
        respuesta = f"{respuesta}\n\n(Respuesta parcial: {'; '.join(salida.errores)})"
    return RespuestaWhatsApp(
        respuesta=_recortar(respuesta, settings.whatsapp_max_caracteres),
        estado=salida.estado,
        agentes=salida.agentes_consultados,
    )


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
async def panel() -> FileResponse:
    return FileResponse(
        DIRECTORIO_ESTATICO / "whatsapp.html",
        media_type="text/html",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/estado")
async def estado(
    request: Request,
    autenticado: ClienteAutenticado = Depends(limitar),
) -> dict:
    return await _puente(request).estado()


@router.post("/conectar")
async def conectar(
    request: Request,
    autenticado: ClienteAutenticado = Depends(limitar),
) -> dict:
    return await _puente(request).conectar()


@router.post("/desconectar")
async def desconectar(
    request: Request,
    autenticado: ClienteAutenticado = Depends(limitar),
) -> dict:
    return await _puente(request).desconectar()


@router.post("/modo")
async def cambiar_modo(
    request: Request,
    cuerpo: ModoVinculacion,
    autenticado: ClienteAutenticado = Depends(limitar),
) -> dict:
    return await _puente(request).modo(cuerpo.modo)


@router.get("/codigo")
async def consultar_codigo(
    request: Request,
    autenticado: ClienteAutenticado = Depends(limitar),
) -> dict:
    return await _puente(request).codigo()


@router.post("/codigo")
async def solicitar_codigo(
    request: Request,
    cuerpo: TelefonoVinculacion,
    autenticado: ClienteAutenticado = Depends(limitar),
) -> dict:
    return await _puente(request).codigo(cuerpo.telefono)


@router.get("/qr")
async def consultar_qr(
    request: Request,
    autenticado: ClienteAutenticado = Depends(limitar),
) -> dict:
    return await _puente(request).qr()
