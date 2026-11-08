from __future__ import annotations

from fastapi.testclient import TestClient

import api.app as api

SECRETO = "secreto-de-prueba"
TOKEN = "123456:token-falso"
CABECERAS = {"X-Telegram-Bot-Api-Secret-Token": SECRETO}


def _cliente(monkeypatch) -> TestClient:
    monkeypatch.setenv("TELEGRAM_TOKEN", TOKEN)
    monkeypatch.setenv("TELEGRAM_SECRET", SECRETO)
    monkeypatch.setenv("AGENTE_PREDETERMINADO", "agente_general")
    return TestClient(api.app)


def test_health(monkeypatch) -> None:
    with _cliente(monkeypatch) as cliente:
        respuesta = cliente.get("/health")
    assert respuesta.status_code == 200
    assert "agente_general" in respuesta.json()["agentes"]


def test_webhook_sin_token(monkeypatch) -> None:
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.setenv("TELEGRAM_SECRET", SECRETO)
    with TestClient(api.app) as cliente:
        respuesta = cliente.post("/telegram/webhook", headers=CABECERAS, json={})
    assert respuesta.status_code == 503


def test_webhook_con_secreto_incorrecto(monkeypatch) -> None:
    with _cliente(monkeypatch) as cliente:
        respuesta = cliente.post(
            "/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "otro"},
            json={},
        )
    assert respuesta.status_code == 403


def test_webhook_ignora_update_sin_texto(monkeypatch) -> None:
    with _cliente(monkeypatch) as cliente:
        respuesta = cliente.post(
            "/telegram/webhook",
            headers=CABECERAS,
            json={"update_id": 1},
        )
    assert respuesta.status_code == 200
    assert respuesta.json()["ignorado"] is True


def test_webhook_procesa_y_elige_agente(monkeypatch) -> None:
    llamadas: list[tuple] = []

    async def falso(chat_id: int, agente: str, texto: str) -> None:
        llamadas.append((chat_id, agente, texto))

    monkeypatch.setattr(api, "procesar_actualizacion", falso)
    with _cliente(monkeypatch) as cliente:
        respuesta = cliente.post(
            "/telegram/webhook",
            headers=CABECERAS,
            json={
                "update_id": 1,
                "message": {"message_id": 2, "chat": {"id": 123}, "text": "hola"},
            },
        )
    assert respuesta.status_code == 200
    assert respuesta.json()["agente"] == "agente_general"
    assert llamadas == [(123, "agente_general", "hola")]


def test_webhook_permite_elegir_agente(monkeypatch) -> None:
    llamadas: list[tuple] = []

    async def falso(chat_id: int, agente: str, texto: str) -> None:
        llamadas.append((chat_id, agente, texto))

    monkeypatch.setattr(api, "procesar_actualizacion", falso)
    with _cliente(monkeypatch) as cliente:
        respuesta = cliente.post(
            "/telegram/webhook",
            headers=CABECERAS,
            json={
                "update_id": 1,
                "message": {"message_id": 2, "chat": {"id": 123}, "text": "/agente_czz hola"},
            },
        )
    assert respuesta.status_code == 200
    assert llamadas == [(123, "agente_czz", "hola")]


def test_seleccionar_agente(monkeypatch) -> None:
    monkeypatch.setenv("AGENTE_PREDETERMINADO", "agente_general")
    assert api.seleccionar_agente("hola") == ("agente_general", "hola")
    assert api.seleccionar_agente("/agente_czz hola") == ("agente_czz", "hola")
    assert api.seleccionar_agente("/agente agente_bryhan hola") == ("agente_bryhan", "hola")
