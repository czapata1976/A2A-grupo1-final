"""Configuración del servicio, cargada desde variables de entorno."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

RAIZ_SERVICIO = Path(__file__).resolve().parents[1]


class ConfiguracionInvalida(RuntimeError):
    """Error de configuración que impide arrancar el servicio."""


def _csv(valor: str | None) -> tuple[str, ...]:
    if not valor:
        return ()
    return tuple(parte.strip() for parte in valor.split(",") if parte.strip())


def _booleano(valor: str | None, por_defecto: bool = False) -> bool:
    if valor is None or valor == "":
        return por_defecto
    return valor.strip().lower() in {"1", "true", "si", "sí", "yes", "on"}


def _entero(valor: str | None, por_defecto: int, minimo: int = 0) -> int:
    if valor is None or valor == "":
        return por_defecto
    try:
        numero = int(valor)
    except ValueError as error:
        raise ConfiguracionInvalida(f"Se esperaba un número entero y se recibió {valor!r}.") from error
    if numero < minimo:
        raise ConfiguracionInvalida(f"El valor {numero} debe ser mayor o igual a {minimo}.")
    return numero


def _flotante(valor: str | None, por_defecto: float, minimo: float = 0.0) -> float:
    if valor is None or valor == "":
        return por_defecto
    try:
        numero = float(valor)
    except ValueError as error:
        raise ConfiguracionInvalida(f"Se esperaba un número y se recibió {valor!r}.") from error
    if numero < minimo:
        raise ConfiguracionInvalida(f"El valor {numero} debe ser mayor o igual a {minimo}.")
    return numero


def _normalizar_servidor(valor: str) -> str:
    base = valor.strip().rstrip("/")
    partes = urlparse(base)
    if partes.scheme not in {"http", "https"} or not partes.netloc:
        raise ConfiguracionInvalida(
            f"Servidor A2A inválido: {valor!r}. Usa una URL como http://127.0.0.1:2025."
        )
    if partes.query or partes.fragment:
        raise ConfiguracionInvalida(f"El servidor A2A no debe incluir query ni fragmento: {valor!r}.")
    return base


@dataclass(frozen=True)
class Settings:
    """Configuración inmutable del servicio."""

    claves_api: tuple[str, ...] = ()
    servidores_a2a: tuple[str, ...] = ("http://127.0.0.1:2025", "http://127.0.0.1:2026")
    agente_primario: str = "agente_czz"
    catalogo_json: str | None = None
    timeout_a2a: float = 120.0
    timeout_conexion_a2a: float = 5.0
    ttl_cache_agentes: float = 30.0
    max_concurrencia_a2a: int = 4
    max_agentes_por_consulta: int = 4
    limite_por_minuto: int = 30
    ttl_sesion: float = 21600.0
    max_sesiones: int = 500
    max_contexto_colaborativo: int = 24000
    origenes_cors: tuple[str, ...] = ()
    docs_habilitados: bool = True
    confiar_en_proxy: bool = False
    telegram_token: str = ""
    telegram_secret: str = ""
    telegram_api_base: str = "https://api.telegram.org"
    ruta_auditoria: str | None = "logs/auditoria.jsonl"
    nivel_log: str = "INFO"
    version: str = "1.0.0"

    def resumen(self) -> dict:
        return {
            "version": self.version,
            "servidores_a2a": list(self.servidores_a2a),
            "claves_configuradas": len(self.claves_api),
            "agente_primario": self.agente_primario,
            "limite_por_minuto": self.limite_por_minuto,
            "docs_habilitados": self.docs_habilitados,
            "auditoria": bool(self.ruta_auditoria),
            "telegram_configurado": bool(self.telegram_token and self.telegram_secret),
        }


def cargar_settings(
    requerir_claves: bool = True,
    env_file: str | Path | None = None,
) -> Settings:
    """Lee .env y las variables de entorno y valida lo indispensable."""

    archivo = Path(env_file) if env_file else RAIZ_SERVICIO / ".env"
    if archivo.is_file():
        load_dotenv(archivo, override=False)

    claves = _csv(os.environ.get("API_KEYS"))
    if requerir_claves:
        if not claves:
            raise ConfiguracionInvalida(
                "Falta API_KEYS. Copia .env.example a .env y define una clave de al menos 12 caracteres."
            )
        claves_de_ejemplo = {"cambia-esta-clave", "clave-ficticia-de-ejemplo-0000"}
        debiles = [clave for clave in claves if len(clave) < 12 or clave in claves_de_ejemplo]
        if debiles:
            raise ConfiguracionInvalida(
                "API_KEYS contiene una clave débil o de ejemplo. Usa una clave de al menos 12 caracteres."
            )
        if not all(clave.isascii() for clave in claves):
            raise ConfiguracionInvalida("API_KEYS debe contener solo caracteres ASCII.")

    servidores = tuple(_normalizar_servidor(valor) for valor in _csv(os.environ.get("A2A_SERVIDORES")))
    if not servidores:
        servidores = ("http://127.0.0.1:2025", "http://127.0.0.1:2026")
    if len(set(servidores)) != len(servidores):
        raise ConfiguracionInvalida("A2A_SERVIDORES contiene URLs repetidas.")

    catalogo_json = os.environ.get("CATALOGO_AGENTES") or None
    if catalogo_json:
        try:
            datos = json.loads(catalogo_json)
        except json.JSONDecodeError as error:
            raise ConfiguracionInvalida("CATALOGO_AGENTES no es JSON válido.") from error
        if not isinstance(datos, dict):
            raise ConfiguracionInvalida("CATALOGO_AGENTES debe ser un objeto JSON.")

    ruta_auditoria = os.environ.get("AUDIT_LOG", "logs/auditoria.jsonl").strip()
    if ruta_auditoria:
        ruta = Path(ruta_auditoria)
        if not ruta.is_absolute():
            ruta = RAIZ_SERVICIO / ruta
        ruta_auditoria = str(ruta)
    else:
        ruta_auditoria = None

    origenes_cors = _csv(os.environ.get("CORS_ORIGINS"))
    if "*" in origenes_cors:
        raise ConfiguracionInvalida(
            "CORS_ORIGINS no puede ser '*'. Indica los orígenes permitidos, por ejemplo "
            "http://127.0.0.1:8000."
        )

    telegram_token = (os.environ.get("TELEGRAM_TOKEN") or "").strip()
    telegram_secret = (os.environ.get("TELEGRAM_SECRET") or "").strip()
    telegram_api_base = (os.environ.get("TELEGRAM_API_BASE") or "https://api.telegram.org").strip().rstrip("/")
    if telegram_api_base and not telegram_api_base.startswith(("http://", "https://")):
        raise ConfiguracionInvalida("TELEGRAM_API_BASE debe empezar con http:// o https://.")

    nivel_log = (os.environ.get("LOG_LEVEL") or "INFO").upper()
    if nivel_log not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ConfiguracionInvalida("LOG_LEVEL debe ser DEBUG, INFO, WARNING, ERROR o CRITICAL.")

    return Settings(
        claves_api=claves,
        servidores_a2a=servidores,
        agente_primario=os.environ.get("AGENTE_PRIMARIO") or "agente_czz",
        catalogo_json=catalogo_json,
        timeout_a2a=_flotante(os.environ.get("A2A_TIMEOUT"), 120.0, minimo=1.0),
        timeout_conexion_a2a=_flotante(os.environ.get("A2A_CONNECT_TIMEOUT"), 5.0, minimo=1.0),
        ttl_cache_agentes=_flotante(os.environ.get("A2A_CACHE_TTL"), 30.0, minimo=0.0),
        max_concurrencia_a2a=_entero(os.environ.get("A2A_MAX_CONCURRENCIA"), 4, minimo=1),
        max_agentes_por_consulta=_entero(os.environ.get("MAX_AGENTES_POR_CONSULTA"), 4, minimo=1),
        limite_por_minuto=_entero(os.environ.get("RATE_LIMIT_POR_MINUTO"), 30, minimo=0),
        ttl_sesion=_flotante(os.environ.get("SESION_TTL"), 21600.0, minimo=60.0),
        max_sesiones=_entero(os.environ.get("MAX_SESIONES"), 500, minimo=1),
        max_contexto_colaborativo=_entero(os.environ.get("MAX_CONTEXTO_COLABORATIVO"), 24000, minimo=1000),
        origenes_cors=origenes_cors,
        telegram_token=telegram_token,
        telegram_secret=telegram_secret,
        telegram_api_base=telegram_api_base,
        docs_habilitados=_booleano(os.environ.get("DOCS_HABILITADOS"), True),
        confiar_en_proxy=_booleano(os.environ.get("CONFIAR_EN_PROXY"), False),
        ruta_auditoria=ruta_auditoria,
        nivel_log=nivel_log,
        version=os.environ.get("APP_VERSION") or "1.0.0",
    )
