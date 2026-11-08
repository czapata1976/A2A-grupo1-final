from __future__ import annotations

import asyncio

import api.app as api


def test_extraer_mensaje() -> None:
    update = {
        "update_id": 1,
        "message": {"message_id": 2, "chat": {"id": 123}, "text": " hola "},
    }
    assert api.extraer_mensaje(update) == (123, "hola")
    assert api.extraer_mensaje({"update_id": 2}) is None
    assert api.extraer_mensaje(
        {"message": {"message_id": 3, "chat": {"id": 123}, "text": ""}}
    ) is None


def test_procesar_actualizacion_envia(monkeypatch) -> None:
    enviados: list[tuple] = []

    def consulta(agente: str, texto: str) -> str:
        return f"{agente}: {texto}"

    async def enviar(chat_id: int, texto: str) -> None:
        enviados.append((chat_id, texto))

    monkeypatch.setattr(api, "procesar_consulta", consulta)
    monkeypatch.setattr(api, "enviar_telegram", enviar)
    asyncio.run(api.procesar_actualizacion(123, "agente_general", "hola"))
    assert enviados == [(123, "agente_general: hola")]


def test_procesar_actualizacion_reporta_error(monkeypatch) -> None:
    enviados: list[tuple] = []

    def consulta(agente: str, texto: str) -> str:
        raise RuntimeError("fallo simulado")

    async def enviar(chat_id: int, texto: str) -> None:
        enviados.append((chat_id, texto))

    monkeypatch.setattr(api, "procesar_consulta", consulta)
    monkeypatch.setattr(api, "enviar_telegram", enviar)
    asyncio.run(api.procesar_actualizacion(123, "agente_general", "hola"))
    assert enviados
    assert "No pude procesar" in enviados[0][1]
