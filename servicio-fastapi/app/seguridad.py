"""Autenticación por token y límite de peticiones."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class ClienteAutenticado:
    huella: str
    ip: str


def _extraer_ip(request: Request, confiar_en_proxy: bool) -> str:
    if confiar_en_proxy:
        reenviado = request.headers.get("X-Forwarded-For", "")
        if reenviado:
            return reenviado.split(",")[0].strip()
    return request.client.host if request.client else "desconocido"


def huella_clave(clave: str) -> str:
    return hashlib.sha256(clave.encode("utf-8")).hexdigest()[:16]


def _clave_valida(clave: str, permitidas: tuple[str, ...]) -> bool:
    valida = False
    presentada = clave.encode("utf-8")
    for permitida in permitidas:
        if secrets.compare_digest(presentada, permitida.encode("utf-8")):
            valida = True
    return valida


async def autenticar(
    request: Request,
    api_key: str | None = Depends(api_key_header),
    credenciales: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> ClienteAutenticado:
    settings = request.app.state.settings
    candidatas: list[str] = []
    if api_key and api_key.strip():
        candidatas.append(api_key.strip())
    if credenciales and credenciales.scheme.lower() == "bearer" and credenciales.credentials.strip():
        candidatas.append(credenciales.credentials.strip())

    for clave in candidatas:
        if _clave_valida(clave, settings.claves_api):
            ip = _extraer_ip(request, settings.confiar_en_proxy)
            return ClienteAutenticado(huella=huella_clave(clave), ip=ip)

    ip = _extraer_ip(request, settings.confiar_en_proxy)
    logger.warning("Acceso rechazado: ip=%s ruta=%s motivo=token_ausente_o_invalido", ip, request.url.path)
    raise HTTPException(
        status_code=401,
        detail=(
            "Acceso no autorizado. Envía una clave válida en X-API-Key "
            "o en Authorization: Bearer <token>."
        ),
        headers={"WWW-Authenticate": "Bearer"},
    )


class LimitePeticiones:
    """Límite de ventana fija por huella de token e IP; vive en memoria."""

    def __init__(self, por_minuto: int) -> None:
        self.por_minuto = por_minuto
        self._buckets: dict[str, tuple[float, int]] = {}
        self._lock = asyncio.Lock()

    async def permitir(self, huella: str, ip: str) -> tuple[bool, int]:
        if self.por_minuto <= 0:
            return True, 0
        ahora = time.monotonic()
        llave = f"{huella}:{ip}"
        async with self._lock:
            inicio, cuenta = self._buckets.get(llave, (ahora, 0))
            if ahora - inicio >= 60.0:
                inicio, cuenta = ahora, 0
            if cuenta >= self.por_minuto:
                espera = max(1, int(60.0 - (ahora - inicio)) + 1)
                return False, espera
            self._buckets[llave] = (inicio, cuenta + 1)
            if len(self._buckets) > 10000:
                self._buckets = {
                    clave: valor
                    for clave, valor in self._buckets.items()
                    if ahora - valor[0] < 120.0
                }
            return True, 0


async def limitar(
    request: Request,
    autenticado: ClienteAutenticado = Depends(autenticar),
) -> ClienteAutenticado:
    limite: LimitePeticiones = request.app.state.limite
    permitido, espera = await limite.permitir(autenticado.huella, autenticado.ip)
    if not permitido:
        logger.warning(
            "Límite alcanzado: ip=%s ruta=%s espera=%ss",
            autenticado.ip,
            request.url.path,
            espera,
        )
        raise HTTPException(
            status_code=429,
            detail="Demasiadas solicitudes. Espera antes de volver a consultar.",
            headers={"Retry-After": str(espera)},
        )
    return autenticado
