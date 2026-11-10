"""Supervisor del servicio: uvicorn y, si está habilitado, el puente WhatsApp.

Un solo dyno: la API pública escucha en ``$PORT`` y el puente Node/Baileys en
loopback. Si el puente no puede arrancar, la API web sigue disponible y el
panel informa que el canal no responde.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

logger = logging.getLogger("supervisor")

# Rotación del log: 2 MB por archivo y 3 copias (máximo ~8 MB en disco).
TAMANO_LOG_BYTES = 2_000_000
COPIAS_LOG = 3

# Niveles de pino (puente Node) a niveles de Python.
NIVELES_PINO = {
    10: logging.DEBUG,
    20: logging.DEBUG,
    30: logging.INFO,
    40: logging.WARNING,
    50: logging.ERROR,
    60: logging.CRITICAL,
}


def _bombear_puente(proceso: subprocess.Popen) -> None:
    """Pasa la salida JSON del puente al log, sin los payloads largos de Baileys."""
    registro = logging.getLogger("puente")
    for linea in proceso.stdout or []:
        texto = linea.rstrip()
        if not texto:
            continue
        try:
            datos = json.loads(texto)
        except (TypeError, ValueError):
            registro.info("%s", texto[:300])
            continue
        try:
            nivel = NIVELES_PINO.get(int(datos.get("level", 30)), logging.INFO)
        except (TypeError, ValueError):
            nivel = logging.INFO
        resumen = str(datos.get("msg", "evento"))
        codigo = datos.get("code")
        if codigo is None:
            nodo = datos.get("fullErrorNode") or {}
            codigo = (nodo.get("attrs") or {}).get("code")
        if codigo is not None:
            resumen = f"{resumen} (code={codigo})"
        registro.log(nivel, "%s", resumen[:300])


def _configurar_registro() -> None:
    """Consola y archivo con rotación, para que el log no crezca sin límite."""
    nivel = os.environ.get("LOG_LEVEL", "INFO").upper()
    formato = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    raiz = logging.getLogger()
    raiz.setLevel(nivel)
    for manejador in list(raiz.handlers):
        raiz.removeHandler(manejador)
    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(formato)
    raiz.addHandler(consola)
    carpeta = RAIZ / "logs"
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = RotatingFileHandler(
        carpeta / "servicio.log",
        maxBytes=TAMANO_LOG_BYTES,
        backupCount=COPIAS_LOG,
        encoding="utf-8",
    )
    archivo.setFormatter(formato)
    raiz.addHandler(archivo)
    # El cliente HTTP interno del panel es muy ruidoso; solo interesan sus errores.
    for ruidoso in ("httpx", "httpcore"):
        logging.getLogger(ruidoso).setLevel(logging.WARNING)


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
    entorno.setdefault("WHATSAPP_LOG_LEVEL", "info")
    try:
        proceso = subprocess.Popen(
            [node, str(script)],
            cwd=str(RAIZ),
            env=entorno,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except OSError as error:
        logger.warning("No se pudo iniciar el puente de WhatsApp: %s", error)
        return None
    threading.Thread(
        target=_bombear_puente, args=(proceso,), daemon=True, name="puente-log"
    ).start()
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
    _configurar_registro()

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
