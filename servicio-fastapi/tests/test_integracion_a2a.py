from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.config import ConfiguracionInvalida, cargar_settings
from app.main import crear_app

pytestmark = pytest.mark.integracion

if os.environ.get("A2A_INTEGRATION") != "1":
    pytest.skip(
        "Prueba de integración desactivada. Usa A2A_INTEGRATION=1 con los servidores A2A arriba.",
        allow_module_level=True,
    )


def test_recorrido_real_por_a2a() -> None:
    try:
        settings = cargar_settings()
    except ConfiguracionInvalida as error:
        pytest.skip(f"Falta configuración para la prueba real: {error}")

    app = crear_app(settings=settings)
    with TestClient(app) as cliente:
        cabeceras = {"X-API-Key": settings.claves_api[0]}
        agentes = cliente.get("/v1/agentes", headers=cabeceras)
        assert agentes.status_code == 200
        disponibles = [agente["grafo"] for agente in agentes.json()["agentes"]]
        if not disponibles:
            pytest.skip("No hay agentes A2A levantados en A2A_SERVIDORES.")

        grafo = "agente_czz" if "agente_czz" in disponibles else disponibles[0]
        respuesta = cliente.post(
            "/v1/consultas",
            headers=cabeceras,
            json={
                "mensaje": "Preséntate y cuéntame cómo puedes ayudar.",
                "agentes": [grafo],
                "modo": "individual",
                "session_id": "integracion-1234",
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["estado"] == "ok"
        assert datos["respuesta"].strip()
        assert datos["aportes"][0]["agente"] == grafo
