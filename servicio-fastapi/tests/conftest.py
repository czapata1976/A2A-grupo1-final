from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import crear_app
from tests.fakes import CLAVE, ClienteFalso


@pytest.fixture
def settings() -> Settings:
    return Settings(
        claves_api=(CLAVE,),
        servidores_a2a=("http://agente-1", "http://agente-2"),
        timeout_a2a=2.0,
        timeout_conexion_a2a=1.0,
        ttl_cache_agentes=0.0,
        limite_por_minuto=1000,
        telegram_token="token-de-prueba",
        telegram_secret="secreto-de-prueba",
        telegram_api_base="http://telegram.fake",
        ruta_auditoria=None,
    )


@pytest.fixture
def cliente_falso() -> ClienteFalso:
    return ClienteFalso()


@pytest.fixture
def cliente_http(settings: Settings, cliente_falso: ClienteFalso):
    app = crear_app(settings=settings, cliente_a2a=cliente_falso)
    with TestClient(app) as cliente:
        yield cliente


@pytest.fixture
def cabeceras() -> dict[str, str]:
    return {"X-API-Key": CLAVE}
