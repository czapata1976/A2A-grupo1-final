"""Supervisor del servicio: uvicorn y, si está habilitado, el puente WhatsApp.

Un solo dyno: la API pública escucha en ``$PORT`` y el puente Node/Baileys en
loopback. Si el puente no puede arrancar, la API web sigue disponible y el
panel informa que el canal no responde.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

logger = logging.getLogger("supervisor")


def _puerto_interno(url: str) -> int:
    partes = urlparse(url)
    return partes.port or 18081


def _arrancar_puente(settings, puerto_publico: int) -> subprocess.Popen | None:
    node = shutil.which("node")
    if node is None:
        logger.warning("Node no está instalado; el canal WhatsApp no se iniciará.")
        return None
    script = RAIZ / "whatsapp" / "src" / "main.mjs"
    if not script.is_file():
        logger.warning("No se encontró el puente de WhatsApp en %s.", script)
        return None
    entorno = dict(os.environ)
    entorno.update(
        WHATSAPP_ENABLE_CONNECTION="true",
        WHATSAPP_SECRET=settings.whatsapp_secret,
        WHATSAPP_INTERNAL_PORT=str(_puerto_interno(settings.whatsapp_url_interna)),
        WHATSAPP_BACKEND_URL=f"http://127.0.0.1:{puerto_publico}/whatsapp/mensaje",
        WHATSAPP_TIMEOUT_MS=str(int((settings.timeout_a2a + 30) * 1000)),
    )
    try:
        proceso = subprocess.Popen([node, str(script)], cwd=str(RAIZ), env=entorno)
    except OSError as error:
        logger.warning("No se pudo iniciar el puente de WhatsApp: %s", error)
        return None
    logger.info("Puente de WhatsApp iniciado (pid=%s).", proceso.pid)
    return proceso


def _detener(proceso: subprocess.Popen | None) -> None:
    if proceso is None or proceso.poll() is not None:
        return
    proceso.terminate()
    try:
        proceso.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proceso.kill()
        proceso.wait(timeout=5)


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    from app.config import ConfiguracionInvalida, cargar_settings

    try:
        settings = cargar_settings()
    except ConfiguracionInvalida as error:
        logger.error("Configuración inválida: %s", error)
        return 1

    puerto_publico = int(os.environ.get("PORT", os.environ.get("SERVICIO_PORT", "8000")))
    direccion = os.environ.get("SERVICIO_HOST", "0.0.0.0")
    puente: subprocess.Popen | None = None
    if settings.whatsapp_habilitado:
        puente = _arrancar_puente(settings, puerto_publico)

    import uvicorn

    try:
        uvicorn.run(
            "app.main:crear_app",
            factory=True,
            host=direccion,
            port=puerto_publico,
            workers=1,
            access_log=False,
            log_config=None,
            server_header=False,
            timeout_graceful_shutdown=20,
        )
    finally:
        _detener(puente)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
