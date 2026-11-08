from __future__ import annotations

from fastapi.testclient import TestClient


def test_mensaje_vacio_es_invalido(cliente_http: TestClient, cabeceras: dict) -> None:
    respuesta = cliente_http.post(
        "/v1/consultas",
        json={"mensaje": "   ", "agentes": ["agente_czz"], "modo": "individual"},
        headers=cabeceras,
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "ENTRADA_INVALIDA"


def test_campo_extra_es_invalido(cliente_http: TestClient, cabeceras: dict) -> None:
    respuesta = cliente_http.post(
        "/v1/consultas",
        json={"mensaje": "Hola", "campo_no_permitido": True},
        headers=cabeceras,
    )
    assert respuesta.status_code == 422


def test_mensaje_demasiado_largo(cliente_http: TestClient, cabeceras: dict) -> None:
    respuesta = cliente_http.post(
        "/v1/consultas",
        json={"mensaje": "x" * 4001},
        headers=cabeceras,
    )
    assert respuesta.status_code == 422


def test_session_id_invalido(cliente_http: TestClient, cabeceras: dict) -> None:
    respuesta = cliente_http.post(
        "/v1/consultas",
        json={"mensaje": "Hola", "session_id": "../../etc/passwd"},
        headers=cabeceras,
    )
    assert respuesta.status_code == 422


def test_agentes_repetidos_es_invalido(cliente_http: TestClient, cabeceras: dict) -> None:
    respuesta = cliente_http.post(
        "/v1/consultas",
        json={
            "mensaje": "Hola",
            "agentes": ["agente_czz", "agente_czz"],
            "modo": "paralelo",
        },
        headers=cabeceras,
    )
    assert respuesta.status_code == 422


def test_metodo_no_permitido(cliente_http: TestClient) -> None:
    respuesta = cliente_http.get("/v1/consultas")
    assert respuesta.status_code == 405
    assert respuesta.json()["error"]["codigo"] == "METODO_NO_PERMITIDO"


def test_json_malformado_devuelve_error_claro(
    cliente_http: TestClient,
    cabeceras: dict,
) -> None:
    respuesta = cliente_http.post(
        "/v1/consultas",
        content="{esto no es json",
        headers={**cabeceras, "Content-Type": "application/json"},
    )
    assert respuesta.status_code in {400, 422}
    assert respuesta.json()["error"]["codigo"] == "ENTRADA_INVALIDA"
