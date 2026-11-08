from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.a2a import (
    ClienteA2A,
    ErrorRespuestaA2A,
    ErrorTiempoA2A,
    _extraer_texto,
)


def test_extrae_texto_de_status_y_artifacts() -> None:
    resultado = {
        "status": {
            "state": "completed",
            "message": {"role": "agent", "parts": [{"kind": "text", "text": "desde estado"}]},
        },
        "artifacts": [
            {"parts": [{"kind": "text", "text": "desde artefacto"}]},
        ],
    }
    texto = _extraer_texto(resultado)
    assert "desde estado" in texto
    assert "desde artefacto" in texto


def test_extrae_texto_del_historial_como_respaldo() -> None:
    resultado = {
        "status": {"state": "completed"},
        "history": [
            {"role": "user", "parts": [{"kind": "text", "text": "pregunta"}]},
            {"role": "agent", "parts": [{"kind": "text", "text": "desde historial"}]},
        ],
    }
    texto = _extraer_texto(resultado)
    assert texto == "desde historial"
    assert "pregunta" not in texto


def test_descubre_y_envia_jsonrpc() -> None:
    peticiones: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/assistants/search":
            return httpx.Response(
                200,
                json=[{"graph_id": "agente_czz", "assistant_id": "aid-1"}],
            )
        if request.url.path == "/.well-known/agent-card.json":
            return httpx.Response(
                200,
                json={
                    "name": "agente_czz",
                    "description": "Acciones",
                    "skills": [{"name": "precios"}],
                },
            )
        if request.url.path == "/a2a/aid-1":
            payload = json.loads(request.content)
            peticiones.append(payload)
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "kind": "task",
                        "contextId": "ctx-1",
                        "status": {
                            "state": "completed",
                            "message": {
                                "role": "agent",
                                "parts": [{"kind": "text", "text": "CLP 3.120,5"}],
                            },
                        },
                    },
                },
            )
        return httpx.Response(404)

    async def flujo() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            cliente = ClienteA2A(
                servidores=("http://test",),
                timeout=2,
                timeout_conexion=2,
                ttl_cache=0,
                http_client=http,
            )
            agentes = await cliente.descubrir(forzar=True)
            assert "agente_czz" in agentes
            agente = agentes["agente_czz"]
            assert agente.assistant_id == "aid-1"
            assert agente.habilidades == ["precios"]
            resultado = await cliente.enviar(agente, "¿Precio?", context_id="ctx-1")
            assert resultado.texto == "CLP 3.120,5"
            assert resultado.context_id == "ctx-1"
            assert peticiones[0]["method"] == "message/send"
            assert peticiones[0]["params"]["message"]["contextId"] == "ctx-1"
            assert peticiones[0]["params"]["message"]["parts"][0]["text"] == "¿Precio?"

    asyncio.run(flujo())


def test_error_jsonrpc_se_propaga() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/assistants/search":
            return httpx.Response(200, json=[{"graph_id": "agente_czz", "assistant_id": "aid-1"}])
        if request.url.path == "/.well-known/agent-card.json":
            return httpx.Response(200, json={"name": "agente_czz"})
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": "1", "error": {"code": -32602, "message": "inválido"}},
        )

    async def flujo() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            cliente = ClienteA2A(
                servidores=("http://test",),
                timeout=2,
                timeout_conexion=2,
                ttl_cache=0,
                http_client=http,
            )
            agentes = await cliente.descubrir(forzar=True)
            with pytest.raises(ErrorRespuestaA2A):
                await cliente.enviar(agentes["agente_czz"], "Hola")

    asyncio.run(flujo())


def test_timeout_se_propaga() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/assistants/search":
            return httpx.Response(200, json=[{"graph_id": "agente_czz", "assistant_id": "aid-1"}])
        if request.url.path == "/.well-known/agent-card.json":
            return httpx.Response(200, json={"name": "agente_czz"})
        raise httpx.ReadTimeout("timeout", request=request)

    async def flujo() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            cliente = ClienteA2A(
                servidores=("http://test",),
                timeout=2,
                timeout_conexion=2,
                ttl_cache=0,
                http_client=http,
            )
            agentes = await cliente.descubrir(forzar=True)
            with pytest.raises(ErrorTiempoA2A):
                await cliente.enviar(agentes["agente_czz"], "Hola")

    asyncio.run(flujo())
