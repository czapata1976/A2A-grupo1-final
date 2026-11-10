"""Cliente HTTP del puente local de WhatsApp (Node/Baileys).

El puente escucha solo en loopback y exige el secreto compartido
`WHATSAPP_SECRET`. Ninguna credencial de WhatsApp viaja por la API pública.
"""

from __future__ import annotations

import logging

import httpx

from app.errores import ErrorServicio

logger = logging.getLogger(__name__)

MENSAJES_ERROR = {
    "operator_authentication_required": "El puente rechazó la credencial del servicio.",
    "connection_not_authorized": "La vinculación no está autorizada en este despliegue.",
    "disconnect_before_new_attempt": "Desconecta el intento anterior antes de iniciar otro.",
    "link_mode_unavailable": "No se puede cambiar el modo de vinculación en este momento.",
    "pairing_not_ready": "WhatsApp todavía no habilitó la solicitud de código.",
    "invalid_phone": "El número debe tener entre 7 y 15 dígitos, sin + ni separadores.",
    "invalid_link_mode": "El modo de vinculación debe ser code o qr.",
    "invalid_input": "La solicitud al puente no tiene el formato esperado.",
    "not_found": "El puente no reconoce la operación solicitada.",
}


class ClienteWhatsApp:
    """Traduce el API interno del puente a errores del servicio."""

    def __init__(self, base_url: str, secreto: str, timeout: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.secreto = secreto
        self.timeout = timeout

    async def _peticion(self, metodo: str, ruta: str, json: dict | None = None) -> dict:
        url = f"{self.base_url}{ruta}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as cliente:
                respuesta = await cliente.request(
                    metodo,
                    url,
                    headers={"X-WhatsApp-Secret": self.secreto},
                    json=json,
                )
        except httpx.HTTPError as error:
            logger.warning("WhatsApp: puente inaccesible (%s)", type(error).__name__)
            raise ErrorServicio(
                503,
                "WHATSAPP_NO_DISPONIBLE",
                "El puente de WhatsApp no responde. Revisa el proceso del canal.",
            ) from error

        if respuesta.status_code == 401:
            raise ErrorServicio(
                503,
                "WHATSAPP_NO_AUTORIZADO",
                "El servicio no está autorizado con el puente de WhatsApp.",
            )

        try:
            datos = respuesta.json()
        except ValueError:
            datos = {}

        if respuesta.status_code >= 400:
            codigo = str(datos.get("error") or "whatsapp_operation_failed")
            mensaje = MENSAJES_ERROR.get(
                codigo,
                "El puente no pudo completar la operación; revisa el estado antes de reintentar.",
            )
            estado = 409 if respuesta.status_code == 409 else 503
            if respuesta.status_code in {400, 422}:
                estado = 422
            raise ErrorServicio(estado, "WHATSAPP_OPERACION_FALLIDA", mensaje, [codigo])

        if not isinstance(datos, dict):
            raise ErrorServicio(
                502,
                "WHATSAPP_RESPUESTA_INVALIDA",
                "El puente devolvió una respuesta que no es un objeto JSON.",
            )
        return datos

    async def estado(self) -> dict:
        return await self._peticion("GET", "/internal/estado")

    async def conectar(self) -> dict:
        return await self._peticion("POST", "/internal/conectar")

    async def desconectar(self) -> dict:
        return await self._peticion("POST", "/internal/desconectar")

    async def modo(self, modo: str) -> dict:
        return await self._peticion("POST", "/internal/modo", {"modo": modo})

    async def codigo(self, telefono: str | None = None) -> dict:
        if telefono is None:
            return await self._peticion("GET", "/internal/codigo")
        return await self._peticion("POST", "/internal/codigo", {"telefono": telefono})

    async def qr(self) -> dict:
        return await self._peticion("GET", "/internal/qr")
