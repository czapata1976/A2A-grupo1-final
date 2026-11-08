from __future__ import annotations

from fastapi.testclient import TestClient

import app.telegram as telegram_mod
from app.config import Settings
from app.main import crear_app
from tests.fakes import CLAVE, ClienteFalso

SECRETO = "secreto-de-prueba"
CABECERAS = {"X-Telegram-Bot-Api-Secret-Token": SECRETO}


def test_extraer_mensaje() -> None:
    update = {
        "update_id": 1,
        "message": {"message_id": 2, "chat": {"id": 123}, "text": " hola "},
    }
    assert telegram_mod.extraer_mensaje(update) == (123, "hola")
    assert telegram_mod.extraer_mensaje({"update_id": 2}) is None
    assert telegram_mod.extraer_mensaje(
        {"message": {"chat": {"id": 123}, "text": ""}}
    ) is None


def test_seleccionar_consulta() -> None:
    assert telegram_mod.seleccionar_consulta("hola") == (None, "auto", "hola")
    assert telegram_mod.seleccionar_consulta("/agente_czz hola") == (
        ["agente_czz"],
        "individual",
        "hola",
    )
    assert telegram_mod.seleccionar_consulta("/agente agente_bryhan hola") == (
        ["agente_bryhan"],
        "individual",
        "hola",
    )
    assert telegram_mod.seleccionar_consulta(
        "/paralelo agente_czz,agente_bryhan hola"
    ) == (
        ["agente_czz", "agente_bryhan"],
        "paralelo",
        "hola",
    )
    assert telegram_mod.seleccionar_consulta(
        "/colaborativo agente_czz,agente_alejandra hola"
    ) == (
        ["agente_czz", "agente_alejandra"],
        "colaborativo",
        "hola",
    )


def test_webhook_sin_token() -> None:
    settings = Settings(
        claves_api=(CLAVE,),
        telegram_token="",
        telegram_secret="secreto",
        ruta_auditoria=None,
    )
    app = crear_app(settings=settings, cliente_a2a=ClienteFalso())
    with TestClient(app) as cliente:
        respuesta = cliente.post(
            "/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "secreto"},
            json={"update_id": 1},
        )
    assert respuesta.status_code == 503


def test_webhook_con_secreto_incorrecto(cliente_http: TestClient) -> None:
    respuesta = cliente_http.post(
        "/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "otro"},
        json={"update_id": 1},
    )
    assert respuesta.status_code == 403


def test_webhook_ayuda(monkeypatch, cliente_http: TestClient) -> None:
    enviados: list[tuple] = []

    async def falso(settings, chat_id: int, texto: str) -> None:
        enviados.append((chat_id, texto))

    monkeypatch.setattr(telegram_mod, "enviar_telegram", falso)
    respuesta = cliente_http.post(
        "/telegram/webhook",
        headers=CABECERAS,
        json={
            "update_id": 1,
            "message": {"message_id": 2, "chat": {"id": 123}, "text": "/start"},
        },
    )
    assert respuesta.status_code == 200
    assert enviados
    assert "Hola. Soy el canal Telegram" in enviados[0][1]


def test_webhook_consulta_auto(
    monkeypatch,
    cliente_http: TestClient,
    cliente_falso: ClienteFalso,
) -> None:
    enviados: list[tuple] = []

    async def falso(settings, chat_id: int, texto: str) -> None:
        enviados.append((chat_id, texto))

    monkeypatch.setattr(telegram_mod, "enviar_telegram", falso)
    respuesta = cliente_http.post(
        "/telegram/webhook",
        headers=CABECERAS,
        json={
            "update_id": 1,
            "message": {
                "message_id": 2,
                "chat": {"id": 123},
                "text": "¿Cuánto vale AAPL en el mercado US?",
            },
        },
    )
    assert respuesta.status_code == 200
    assert cliente_falso.llamadas[-1]["agente"] == "agente_czz"
    assert enviados
    assert "Respuesta de agente_czz" in enviados[0][1]


def test_webhook_comando_agente(
    monkeypatch,
    cliente_http: TestClient,
    cliente_falso: ClienteFalso,
) -> None:
    enviados: list[tuple] = []

    async def falso(settings, chat_id: int, texto: str) -> None:
        enviados.append((chat_id, texto))

    monkeypatch.setattr(telegram_mod, "enviar_telegram", falso)
    respuesta = cliente_http.post(
        "/telegram/webhook",
        headers=CABECERAS,
        json={
            "update_id": 1,
            "message": {
                "message_id": 2,
                "chat": {"id": 123},
                "text": "/agente_bryhan hola",
            },
        },
    )
    assert respuesta.status_code == 200
    assert cliente_falso.llamadas[-1]["agente"] == "agente_bryhan"
    assert enviados
    assert "Respuesta de agente_bryhan" in enviados[0][1]


def test_webhook_paralelo(
    monkeypatch,
    cliente_http: TestClient,
    cliente_falso: ClienteFalso,
) -> None:
    enviados: list[tuple] = []

    async def falso(settings, chat_id: int, texto: str) -> None:
        enviados.append((chat_id, texto))

    monkeypatch.setattr(telegram_mod, "enviar_telegram", falso)
    respuesta = cliente_http.post(
        "/telegram/webhook",
        headers=CABECERAS,
        json={
            "update_id": 1,
            "message": {
                "message_id": 2,
                "chat": {"id": 123},
                "text": "/paralelo agente_czz,agente_bryhan hola",
            },
        },
    )
    assert respuesta.status_code == 200
    assert [llamada["agente"] for llamada in cliente_falso.llamadas] == [
        "agente_czz",
        "agente_bryhan",
    ]
    assert enviados
    assert "Respuesta de agente_czz" in enviados[0][1]
    assert "Respuesta de agente_bryhan" in enviados[0][1]
