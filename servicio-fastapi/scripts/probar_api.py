"""Prueba el recorrido HTTP y guarda un acta JSON para las evidencias."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import dotenv_values

RAIZ = Path(__file__).resolve().parents[1]


def _clave(args: argparse.Namespace) -> str | None:
    if args.clave:
        return args.clave
    archivo = Path(args.env_file)
    if archivo.is_file():
        valores = dotenv_values(archivo)
        claves = [parte.strip() for parte in (valores.get("API_KEYS") or "").split(",") if parte.strip()]
        if claves:
            return claves[0]
    claves = [parte.strip() for parte in (os.environ.get("API_KEYS") or "").split(",") if parte.strip()]
    return claves[0] if claves else None


def _json_seguro(respuesta: httpx.Response):
    try:
        return respuesta.json()
    except ValueError:
        return respuesta.text[:2000]


def _registrar(
    resultados: list[dict],
    caso: str,
    metodo: str,
    ruta: str,
    respuesta: httpx.Response,
    extra: dict | None = None,
) -> None:
    entrada = {
        "caso": caso,
        "metodo": metodo,
        "ruta": ruta,
        "status": respuesta.status_code,
        "cuerpo": _json_seguro(respuesta),
    }
    if extra:
        entrada.update(extra)
    resultados.append(entrada)
    print(f"[{respuesta.status_code}] {caso}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba el servicio FastAPI del Grupo 1.")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="URL base del servicio.")
    parser.add_argument("--clave", help="Clave API. Si se omite, se lee de .env o del entorno.")
    parser.add_argument("--env-file", default=str(RAIZ / ".env"), help="Archivo .env con API_KEYS.")
    parser.add_argument("--consulta", help="Consulta a enviar al agente.")
    parser.add_argument("--agentes", help="Grafos separados por coma. Si se omite, se elige uno.")
    parser.add_argument("--modo", choices=["auto", "individual", "paralelo", "colaborativo"])
    parser.add_argument(
        "--salida",
        default=str(RAIZ / "evidencias" / "ultima-prueba.json"),
        help="Ruta del acta JSON. Usa '-' para no guardar.",
    )
    args = parser.parse_args()

    clave = _clave(args)
    if not clave:
        print("ERROR: no hay clave API. Usa --clave, .env o la variable API_KEYS.")
        return 2

    url = args.url.rstrip("/")
    resultados: list[dict] = []
    cabeceras = {"X-API-Key": clave}
    fecha = datetime.now(timezone.utc).isoformat()

    with httpx.Client(timeout=240, trust_env=False) as cliente:
        salud = cliente.get(f"{url}/salud")
        _registrar(resultados, "salud pública", "GET", "/salud", salud)

        agentes_sin_clave = cliente.get(f"{url}/v1/agentes")
        _registrar(
            resultados,
            "acceso rechazado sin clave",
            "GET",
            "/v1/agentes",
            agentes_sin_clave,
            {"esperado": 401},
        )

        agentes = cliente.get(f"{url}/v1/agentes", headers=cabeceras)
        _registrar(
            resultados,
            "acceso permitido con clave",
            "GET",
            "/v1/agentes",
            agentes,
            {"esperado": 200},
        )

        disponibles = []
        if agentes.status_code == 200:
            disponibles = [agente["grafo"] for agente in agentes.json().get("agentes", [])]
        if args.agentes:
            seleccion = [parte.strip() for parte in args.agentes.split(",") if parte.strip()]
        elif "agente_czz" in disponibles:
            seleccion = ["agente_czz"]
        elif disponibles:
            seleccion = [disponibles[0]]
        else:
            seleccion = []

        if args.consulta:
            consulta = args.consulta
        elif seleccion and seleccion == ["agente_czz"]:
            consulta = "¿Cuánto vale AAPL en el mercado US y qué debería revisar antes de invertir?"
        else:
            consulta = "Preséntate y cuéntame cómo puedes ayudar."

        modo = args.modo or ("individual" if len(seleccion) <= 1 else "paralelo")
        cuerpo = {
            "mensaje": consulta,
            "modo": modo,
            "session_id": "evidencia-1234",
        }
        if seleccion:
            cuerpo["agentes"] = seleccion

        consulta_con_clave = cliente.post(f"{url}/v1/consultas", json=cuerpo, headers=cabeceras)
        _registrar(
            resultados,
            "consulta autorizada",
            "POST",
            "/v1/consultas",
            consulta_con_clave,
            {"esperado": 200, "solicitud": cuerpo},
        )

        consulta_sin_clave = cliente.post(f"{url}/v1/consultas", json=cuerpo)
        _registrar(
            resultados,
            "consulta rechazada sin clave",
            "POST",
            "/v1/consultas",
            consulta_sin_clave,
            {"esperado": 401, "solicitud": cuerpo},
        )

        invalida = cliente.post(
            f"{url}/v1/consultas",
            json={"mensaje": "", "session_id": "../../fuera"},
            headers=cabeceras,
        )
        _registrar(
            resultados,
            "entrada inválida",
            "POST",
            "/v1/consultas",
            invalida,
            {"esperado": 422},
        )

        frontend = cliente.get(f"{url}/")
        _registrar(resultados, "consola web", "GET", "/", frontend)

    acta = {
        "entorno": "LOCAL",
        "fecha": fecha,
        "url": url,
        "consulta": consulta,
        "agentes": seleccion,
        "modo": modo,
        "clave": "no incluida",
        "resultados": resultados,
    }
    if args.salida and args.salida != "-":
        salida = Path(args.salida)
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(json.dumps(acta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Acta guardada en: {salida}")

    esperados = {
        "salud pública": 200,
        "acceso rechazado sin clave": 401,
        "acceso permitido con clave": 200,
        "consulta autorizada": 200,
        "consulta rechazada sin clave": 401,
        "entrada inválida": 422,
        "consola web": 200,
    }
    fallos = [
        resultado
        for resultado in resultados
        if resultado["caso"] in esperados and resultado["status"] != esperados[resultado["caso"]]
    ]
    if fallos:
        print("Casos con estado inesperado:")
        for fallo in fallos:
            print(f"  - {fallo['caso']}: {fallo['status']} (esperado {esperados[fallo['caso']]})")
        return 1
    print("Todos los casos esperados respondieron con el estado correcto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
