from __future__ import annotations

from fastapi.testclient import TestClient

from app.a2a import ErrorConexionA2A, ErrorTiempoA2A
from app.config import Settings
from app.main import crear_app
from tests.fakes import ClienteFalso


def _consulta(cliente: TestClient, cabeceras: dict, **cambios) -> dict:
    cuerpo = {
        "mensaje": "Consulta de prueba",
        "agentes": ["agente_czz"],
        "modo": "individual",
        "session_id": "sesion-12345678",
    }
    cuerpo.update(cambios)
    respuesta = cliente.post("/v1/consultas", json=cuerpo, headers=cabeceras)
    return respuesta


def test_individual_conserva_el_texto_del_agente(
    cliente_http: TestClient,
    cliente_falso: ClienteFalso,
    cabeceras: dict,
) -> None:
    texto = "AAPL cotiza en US$ 342,10 con una variación de 1,24%."
    cliente_falso.respuestas["agente_czz"] = texto
    respuesta = _consulta(cliente_http, cabeceras, mensaje="¿Cuánto vale AAPL en US?")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["estado"] == "ok"
    assert datos["respuesta"] == texto
    assert datos["aportes"][0]["respuesta"] == texto
    assert datos["aportes"][0]["context_id"].endswith("…")
    assert datos["aportes"][0]["context_id"] != "ctx-agente_czz-1"


def test_auto_elige_al_especialista(
    cliente_http: TestClient,
    cliente_falso: ClienteFalso,
    cabeceras: dict,
) -> None:
    respuesta = _consulta(
        cliente_http,
        cabeceras,
        mensaje="¿Cuánto vale AAPL en el mercado US y qué riesgo tiene?",
        agentes=None,
        modo="auto",
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["agentes_consultados"] == ["agente_czz"]
    assert cliente_falso.llamadas[-1]["agente"] == "agente_czz"


def test_paralelo_conserva_cifras_unidades_y_condiciones(
    cliente_http: TestClient,
    cliente_falso: ClienteFalso,
    cabeceras: dict,
) -> None:
    texto_acciones = "Falabella cotiza en CLP 3.120,5 y la condición es no vender antes de 30 días."
    texto_auditoria = "El fondo mantiene 18,5% de concentración y cumple el límite normativo."
    cliente_falso.respuestas["agente_czz"] = texto_acciones
    cliente_falso.respuestas["agente_alejandra"] = texto_auditoria
    respuesta = _consulta(
        cliente_http,
        cabeceras,
        mensaje="Revisa la acción y el cumplimiento del fondo",
        agentes=["agente_czz", "agente_alejandra"],
        modo="paralelo",
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["estado"] == "ok"
    assert texto_acciones in datos["respuesta"]
    assert texto_auditoria in datos["respuesta"]
    assert "CLP 3.120,5" in datos["respuesta"]
    assert "18,5%" in datos["respuesta"]
    assert "30 días" in datos["respuesta"]
    assert [aporte["agente"] for aporte in datos["aportes"]] == [
        "agente_czz",
        "agente_alejandra",
    ]


def test_colaborativo_entrega_aportes_previos(
    cliente_http: TestClient,
    cliente_falso: ClienteFalso,
    cabeceras: dict,
) -> None:
    cliente_falso.respuestas["agente_czz"] = "El PER es 14,2 y el precio es CLP 3.120,5."
    cliente_falso.respuestas["agente_bryhan"] = "Plan: automatizar la revisión en tres pasos."
    respuesta = _consulta(
        cliente_http,
        cabeceras,
        mensaje="Evalúa la inversión y propone un plan",
        agentes=["agente_czz", "agente_bryhan"],
        modo="colaborativo",
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["estado"] == "ok"
    assert len(cliente_falso.llamadas) == 2
    assert cliente_falso.llamadas[0]["texto"] == "Evalúa la inversión y propone un plan"
    segundo_prompt = cliente_falso.llamadas[1]["texto"]
    assert '<aporte agente="agente_czz">' in segundo_prompt
    assert "El PER es 14,2" in segundo_prompt
    assert "El PER es 14,2 y el precio es CLP 3.120,5." in datos["respuesta"]
    assert "Plan: automatizar la revisión en tres pasos." in datos["respuesta"]


def test_parcial_si_un_agente_falla(
    cliente_http: TestClient,
    cliente_falso: ClienteFalso,
    cabeceras: dict,
) -> None:
    cliente_falso.respuestas["agente_czz"] = "Dato disponible: CLP 3.120,5."
    cliente_falso.errores["agente_bryhan"] = ErrorConexionA2A("sin conexión")
    respuesta = _consulta(
        cliente_http,
        cabeceras,
        agentes=["agente_czz", "agente_bryhan"],
        modo="paralelo",
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["estado"] == "parcial"
    assert "agente_bryhan" in " ".join(datos["errores"])
    assert "CLP 3.120,5" in datos["respuesta"]
    assert any(aporte["estado"] == "error" for aporte in datos["aportes"])


def test_todos_fallan_devuelve_502(
    cliente_http: TestClient,
    cliente_falso: ClienteFalso,
    cabeceras: dict,
) -> None:
    cliente_falso.errores["agente_czz"] = ErrorConexionA2A("sin conexión")
    cliente_falso.errores["agente_bryhan"] = ErrorConexionA2A("sin conexión")
    respuesta = _consulta(
        cliente_http,
        cabeceras,
        agentes=["agente_czz", "agente_bryhan"],
        modo="paralelo",
    )
    assert respuesta.status_code == 502
    cuerpo = respuesta.json()
    assert cuerpo["error"]["codigo"] == "AGENTES_FALLARON"
    assert cuerpo["error"]["detalles"]


def test_timeout_devuelve_504(
    cliente_http: TestClient,
    cliente_falso: ClienteFalso,
    cabeceras: dict,
) -> None:
    cliente_falso.errores["agente_czz"] = ErrorTiempoA2A("tiempo agotado")
    respuesta = _consulta(cliente_http, cabeceras, agentes=["agente_czz"], modo="individual")
    assert respuesta.status_code == 504
    assert respuesta.json()["error"]["codigo"] == "AGENTES_TIEMPO_AGOTADO"


def test_agente_inexistente_devuelve_400(
    cliente_http: TestClient,
    cabeceras: dict,
) -> None:
    respuesta = _consulta(
        cliente_http,
        cabeceras,
        agentes=["agente_fantasma"],
        modo="individual",
    )
    assert respuesta.status_code == 400
    cuerpo = respuesta.json()
    assert cuerpo["error"]["codigo"] == "SOLICITUD_INVALIDA"
    assert "agente_fantasma" in " ".join(cuerpo["error"]["detalles"])


def test_modo_auto_con_varios_agentes_devuelve_400(
    cliente_http: TestClient,
    cabeceras: dict,
) -> None:
    respuesta = _consulta(
        cliente_http,
        cabeceras,
        agentes=["agente_czz", "agente_bryhan"],
        modo="auto",
    )
    assert respuesta.status_code == 400


def test_modo_individual_con_varios_agentes_devuelve_400(
    cliente_http: TestClient,
    cabeceras: dict,
) -> None:
    respuesta = _consulta(
        cliente_http,
        cabeceras,
        agentes=["agente_czz", "agente_bryhan"],
        modo="individual",
    )
    assert respuesta.status_code == 400


def test_sesion_reutiliza_contexto(
    cliente_http: TestClient,
    cliente_falso: ClienteFalso,
    cabeceras: dict,
) -> None:
    primera = _consulta(cliente_http, cabeceras, mensaje="Primer turno")
    assert primera.status_code == 200
    contexto = primera.json()["aportes"][0]["context_id"]
    assert contexto.endswith("…")
    segunda = _consulta(cliente_http, cabeceras, mensaje="Segundo turno")
    assert segunda.status_code == 200
    assert cliente_falso.llamadas[-1]["context_id"] == "ctx-agente_czz-1"


def test_reiniciar_sesion_borra_contexto(
    cliente_http: TestClient,
    cliente_falso: ClienteFalso,
    cabeceras: dict,
) -> None:
    _consulta(cliente_http, cabeceras, mensaje="Primer turno")
    borrado = cliente_http.delete("/v1/sesiones/sesion-12345678", headers=cabeceras)
    assert borrado.status_code == 200
    assert borrado.json()["estado"] == "reiniciada"
    _consulta(cliente_http, cabeceras, mensaje="Turno tras reinicio")
    assert cliente_falso.llamadas[-1]["context_id"] is None


def test_detecta_peticion_de_dato_faltante(
    cliente_http: TestClient,
    cliente_falso: ClienteFalso,
    cabeceras: dict,
) -> None:
    cliente_falso.respuestas["agente_czz"] = (
        "No puedo consultar AAPL sin saber el país (mercado). "
        "¿En qué mercado cotiza? (ej. US, CL)"
    )
    respuesta = _consulta(cliente_http, cabeceras, mensaje="¿Cuánto vale AAPL?")
    assert respuesta.status_code == 200
    assert respuesta.json()["posible_falta_de_datos"] is True


def test_sesion_aislada_por_token() -> None:
    settings = Settings(
        claves_api=("clave-a-123456789", "clave-b-123456789"),
        limite_por_minuto=1000,
        ruta_auditoria=None,
    )
    cliente_falso = ClienteFalso()
    app = crear_app(settings=settings, cliente_a2a=cliente_falso)
    cuerpo = {
        "mensaje": "Hola",
        "agentes": ["agente_czz"],
        "modo": "individual",
        "session_id": "sesion-compartida",
    }
    with TestClient(app) as cliente:
        primera = cliente.post(
            "/v1/consultas",
            json=cuerpo,
            headers={"X-API-Key": "clave-a-123456789"},
        )
        segunda = cliente.post(
            "/v1/consultas",
            json=cuerpo,
            headers={"X-API-Key": "clave-b-123456789"},
        )
    assert primera.status_code == 200
    assert segunda.status_code == 200
    assert cliente_falso.llamadas[0]["context_id"] is None
    assert cliente_falso.llamadas[1]["context_id"] is None
