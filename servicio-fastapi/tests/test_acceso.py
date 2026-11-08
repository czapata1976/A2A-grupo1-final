from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import crear_app
from tests.fakes import CLAVE, ClienteFalso


def test_salud_es_publica(cliente_http: TestClient) -> None:
    respuesta = cliente_http.get("/salud")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ok"


def test_consulta_sin_clave_es_rechazada(cliente_http: TestClient) -> None:
    respuesta = cliente_http.post(
        "/v1/consultas",
        json={"mensaje": "Hola", "agentes": ["agente_czz"], "modo": "individual"},
    )
    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["codigo"] == "NO_AUTORIZADO"
    assert "WWW-Authenticate" in respuesta.headers


def test_consulta_con_clave_incorrecta_es_rechazada(cliente_http: TestClient) -> None:
    respuesta = cliente_http.post(
        "/v1/consultas",
        json={"mensaje": "Hola", "agentes": ["agente_czz"], "modo": "individual"},
        headers={"X-API-Key": "clave-equivocada-123"},
    )
    assert respuesta.status_code == 401


def test_bearer_valido(cliente_http: TestClient) -> None:
    respuesta = cliente_http.get(
        "/v1/agentes",
        headers={"Authorization": f"Bearer {CLAVE}"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["total"] == 4


def test_agentes_protegidos(cliente_http: TestClient) -> None:
    sin_clave = cliente_http.get("/v1/agentes")
    assert sin_clave.status_code == 401
    con_clave = cliente_http.get("/v1/agentes", headers={"X-API-Key": CLAVE})
    assert con_clave.status_code == 200
    grafos = {agente["grafo"] for agente in con_clave.json()["agentes"]}
    assert "agente_czz" in grafos
    assert "agente_bryhan" in grafos


def test_limite_por_minuto() -> None:
    settings = Settings(
        claves_api=(CLAVE,),
        limite_por_minuto=1,
        ruta_auditoria=None,
    )
    app = crear_app(settings=settings, cliente_a2a=ClienteFalso())
    with TestClient(app) as cliente:
        primera = cliente.get("/v1/agentes", headers={"X-API-Key": CLAVE})
        segunda = cliente.get("/v1/agentes", headers={"X-API-Key": CLAVE})
    assert primera.status_code == 200
    assert segunda.status_code == 429
    assert segunda.json()["error"]["codigo"] == "LIMITE_ALCANZADO"
    assert "Retry-After" in segunda.headers


def test_error_inesperado_no_expone_detalles() -> None:
    settings = Settings(
        claves_api=(CLAVE,),
        ruta_auditoria=None,
    )
    cliente_falso = ClienteFalso(error_descubrimiento=RuntimeError("secreto interno"))
    app = crear_app(settings=settings, cliente_a2a=cliente_falso)
    with TestClient(app, raise_server_exceptions=False) as cliente:
        respuesta = cliente.get("/v1/agentes", headers={"X-API-Key": CLAVE})
    assert respuesta.status_code == 500
    cuerpo = respuesta.json()
    assert cuerpo["error"]["codigo"] == "ERROR_INTERNO"
    assert "secreto interno" not in cuerpo["error"]["mensaje"]
    assert "Traceback" not in str(cuerpo)
