from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import crear_app
from tests.fakes import CLAVE, ClienteFalso

SECRETO = "secreto-whatsapp-de-prueba-123456"
CABECERAS = {"X-WhatsApp-Secret": SECRETO}
CLAVE_API = {"X-API-Key": CLAVE}


def _settings(**cambios) -> Settings:
    base = Settings(
        claves_api=(CLAVE,),
        servidores_a2a=("http://agente-1", "http://agente-2"),
        timeout_a2a=2.0,
        timeout_conexion_a2a=1.0,
        ttl_cache_agentes=0.0,
        limite_por_minuto=1000,
        ruta_auditoria=None,
        whatsapp_habilitado=True,
        whatsapp_secret=SECRETO,
        whatsapp_url_interna="http://127.0.0.1:18081",
    )
    return replace(base, **cambios)


class PuenteFalso:
    def __init__(self) -> None:
        self.llamadas: list[str] = []

    async def estado(self) -> dict:
        self.llamadas.append("estado")
        return {"estado": "connected", "modo": "code"}

    async def conectar(self) -> dict:
        self.llamadas.append("conectar")
        return {"estado": "preparing"}

    async def desconectar(self) -> dict:
        self.llamadas.append("desconectar")
        return {"estado": "stopped"}

    async def modo(self, modo: str) -> dict:
        self.llamadas.append(f"modo:{modo}")
        return {"modo": modo}

    async def codigo(self, telefono: str | None = None) -> dict:
        self.llamadas.append(f"codigo:{telefono}")
        return {"codigo": "ABCD1234", "expira_en_ms": 60000}

    async def qr(self) -> dict:
        self.llamadas.append("qr")
        return {"imagen": "data:image/png;base64,AA=="}


def test_mensaje_sin_canal_habilitado() -> None:
    settings = _settings(whatsapp_habilitado=False, whatsapp_secret="")
    app = crear_app(settings=settings, cliente_a2a=ClienteFalso())
    with TestClient(app) as cliente:
        respuesta = cliente.post("/whatsapp/mensaje", headers=CABECERAS, json={"mensaje": "hola"})
    assert respuesta.status_code == 503


def test_mensaje_con_secreto_incorrecto() -> None:
    app = crear_app(settings=_settings(), cliente_a2a=ClienteFalso())
    with TestClient(app) as cliente:
        respuesta = cliente.post(
            "/whatsapp/mensaje",
            headers={"X-WhatsApp-Secret": "otro-secreto"},
            json={"mensaje": "hola"},
        )
    assert respuesta.status_code == 403


def test_mensaje_de_ayuda_no_consulta_agentes() -> None:
    falso = ClienteFalso()
    app = crear_app(settings=_settings(), cliente_a2a=falso)
    with TestClient(app) as cliente:
        respuesta = cliente.post("/whatsapp/mensaje", headers=CABECERAS, json={"mensaje": "/ayuda"})
    assert respuesta.status_code == 200
    assert "canal WhatsApp" in respuesta.json()["respuesta"]
    assert falso.llamadas == []


def test_mensaje_consulta_auto() -> None:
    falso = ClienteFalso()
    app = crear_app(settings=_settings(), cliente_a2a=falso)
    with TestClient(app) as cliente:
        respuesta = cliente.post(
            "/whatsapp/mensaje",
            headers=CABECERAS,
            json={"mensaje": "¿Cuánto vale AAPL?", "session_id": "wa_demo_0001"},
        )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["estado"] == "ok"
    assert datos["respuesta"].startswith("Respuesta de ")
    assert len(datos["agentes"]) == 1
    assert len(falso.llamadas) == 1


def test_mensaje_paralelo_consulta_dos_agentes() -> None:
    falso = ClienteFalso()
    app = crear_app(settings=_settings(), cliente_a2a=falso)
    with TestClient(app) as cliente:
        respuesta = cliente.post(
            "/whatsapp/mensaje",
            headers=CABECERAS,
            json={
                "mensaje": "/paralelo agente_czz,agente_bryhan revisa el portafolio",
                "session_id": "wa_demo_0002",
            },
        )
    assert respuesta.status_code == 200
    assert {llamada["agente"] for llamada in falso.llamadas} == {"agente_czz", "agente_bryhan"}


def test_mensaje_recorta_respuestas_largas() -> None:
    settings = _settings(whatsapp_max_caracteres=200)
    falso = ClienteFalso(respuestas={"agente_czz": "x" * 900})
    app = crear_app(settings=settings, cliente_a2a=falso)
    with TestClient(app) as cliente:
        respuesta = cliente.post(
            "/whatsapp/mensaje",
            headers=CABECERAS,
            json={"mensaje": "/agente_czz hola", "session_id": "wa_demo_0003"},
        )
    texto = respuesta.json()["respuesta"]
    assert len(texto) <= 200
    assert texto.endswith("(recortado)")


def test_panel_whatsapp_publico_sin_datos() -> None:
    app = crear_app(settings=_settings(), cliente_a2a=ClienteFalso())
    with TestClient(app) as cliente:
        respuesta = cliente.get("/whatsapp")
    assert respuesta.status_code == 200
    assert "Canal WhatsApp" in respuesta.text
    assert respuesta.headers["cache-control"] == "no-store"


def test_estado_sin_canal_habilitado() -> None:
    settings = _settings(whatsapp_habilitado=False, whatsapp_secret="")
    app = crear_app(settings=settings, cliente_a2a=ClienteFalso())
    with TestClient(app) as cliente:
        respuesta = cliente.get("/whatsapp/estado", headers=CLAVE_API)
    assert respuesta.status_code == 503


def test_panel_proxy_requiere_clave() -> None:
    app = crear_app(settings=_settings(), cliente_a2a=ClienteFalso())
    with TestClient(app) as cliente:
        respuesta = cliente.get("/whatsapp/estado")
    assert respuesta.status_code == 401


def test_panel_proxy_delega_en_el_puente() -> None:
    app = crear_app(settings=_settings(), cliente_a2a=ClienteFalso())
    puente = PuenteFalso()
    with TestClient(app) as cliente:
        cliente.app.state.whatsapp = puente
        assert cliente.get("/whatsapp/estado", headers=CLAVE_API).json()["estado"] == "connected"
        assert cliente.post("/whatsapp/conectar", headers=CLAVE_API).status_code == 200
        assert cliente.post("/whatsapp/desconectar", headers=CLAVE_API).status_code == 200
        assert (
            cliente.post("/whatsapp/modo", headers=CLAVE_API, json={"modo": "qr"}).json()["modo"]
            == "qr"
        )
        assert (
            cliente.post(
                "/whatsapp/codigo", headers=CLAVE_API, json={"telefono": "56911112222"}
            ).json()["codigo"]
            == "ABCD1234"
        )
        assert cliente.get("/whatsapp/codigo", headers=CLAVE_API).status_code == 200
        assert (
            cliente.get("/whatsapp/qr", headers=CLAVE_API).json()["imagen"].startswith("data:image/")
        )
    assert puente.llamadas == [
        "estado",
        "conectar",
        "desconectar",
        "modo:qr",
        "codigo:56911112222",
        "codigo:None",
        "qr",
    ]


def test_modo_invalido_es_rechazado() -> None:
    app = crear_app(settings=_settings(), cliente_a2a=ClienteFalso())
    with TestClient(app) as cliente:
        cliente.app.state.whatsapp = PuenteFalso()
        respuesta = cliente.post(
            "/whatsapp/modo", headers=CLAVE_API, json={"modo": "telefono"}
        )
    assert respuesta.status_code == 422


def test_telefono_invalido_es_rechazado() -> None:
    app = crear_app(settings=_settings(), cliente_a2a=ClienteFalso())
    with TestClient(app) as cliente:
        cliente.app.state.whatsapp = PuenteFalso()
        respuesta = cliente.post(
            "/whatsapp/codigo", headers=CLAVE_API, json={"telefono": "+56 9 1111"}
        )
    assert respuesta.status_code == 422
