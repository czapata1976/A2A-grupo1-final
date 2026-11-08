from __future__ import annotations

from fastapi.testclient import TestClient


def test_consola_web_se_sirve(cliente_http: TestClient) -> None:
    respuesta = cliente_http.get("/")
    assert respuesta.status_code == 200
    assert "text/html" in respuesta.headers["content-type"]
    assert "Conecta la consola" in respuesta.text
    assert "API_KEYS=" not in respuesta.text
    assert "GOOGLE_API_KEY" not in respuesta.text
    assert "ANTHROPIC_API_KEY" not in respuesta.text


def test_assets_estaticos(cliente_http: TestClient) -> None:
    js = cliente_http.get("/static/app.js")
    css = cliente_http.get("/static/styles.css")
    assert js.status_code == 200
    assert "application/javascript" in js.headers["content-type"] or "text/javascript" in js.headers["content-type"]
    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert "X-API-Key" in js.text


def test_cabeceras_de_seguridad(cliente_http: TestClient) -> None:
    respuesta = cliente_http.get("/")
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
    assert respuesta.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in respuesta.headers["Content-Security-Policy"]
    assert respuesta.headers["Cache-Control"] == "no-store"
    assert respuesta.headers["X-Request-ID"]


def test_favicon(cliente_http: TestClient) -> None:
    respuesta = cliente_http.get("/favicon.ico")
    assert respuesta.status_code == 204


def test_docs_disponibles(cliente_http: TestClient) -> None:
    respuesta = cliente_http.get("/docs")
    assert respuesta.status_code == 200
    assert "Swagger UI" in respuesta.text


def test_health_no_expone_configuracion(cliente_http: TestClient) -> None:
    respuesta = cliente_http.get("/salud")
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"estado", "servicio", "version", "hora"}
    assert "clave" not in respuesta.text.lower()
