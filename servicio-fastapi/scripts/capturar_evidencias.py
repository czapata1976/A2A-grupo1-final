"""Captura evidencias reales de la consola web con Playwright.

Requiere el servicio y al menos un agente A2A levantados. Lee la clave desde
servicio-fastapi/.env (API_KEYS) y no la escribe en las capturas ni en el acta.
"""

from __future__ import annotations

import argparse
import json
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
    return None


def _verificar_servicio(url: str, clave: str) -> list[str]:
    with httpx.Client(timeout=90, trust_env=False) as cliente:
        salud = cliente.get(f"{url}/salud")
        if salud.status_code != 200:
            raise RuntimeError(f"El servicio no responde en /salud (HTTP {salud.status_code}).")
        respuesta = cliente.get(f"{url}/v1/agentes", headers={"X-API-Key": clave})
        if respuesta.status_code == 401:
            raise RuntimeError("La clave de API_KEYS fue rechazada por el servicio.")
        if respuesta.status_code != 200:
            raise RuntimeError(f"/v1/agentes devolvió HTTP {respuesta.status_code}: {respuesta.text[:300]}")
        datos = respuesta.json()
        disponibles = [agente["grafo"] for agente in datos.get("agentes", [])]
        if not disponibles:
            errores = datos.get("errores", [])
            detalle = f" Avisos: {'; '.join(errores)}" if errores else ""
            raise RuntimeError(
                "No hay agentes A2A disponibles. Levanta al menos un servidor LangGraph." + detalle
            )
        return disponibles


def _capturar(pagina, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    pagina.screenshot(path=str(ruta), full_page=False)
    print(f"  captura: {ruta}")


def _enviar(pagina, consulta: str, archivo: Path, timeout_ms: int) -> dict:
    previos_agente = pagina.locator(".mensaje-agente:not(.mensaje-cargando)").count()
    previos_error = pagina.locator(".mensaje-error-sistema").count()
    pagina.fill("#consulta", consulta)
    pagina.click("#btn-enviar")
    try:
        pagina.wait_for_function(
            "() => !document.querySelector('#btn-enviar').disabled",
            timeout=timeout_ms,
        )
    except Exception as error:  # Playwright TimeoutError
        _capturar(pagina, archivo.with_name(archivo.stem + "-timeout.png"))
        return {
            "estado": "timeout",
            "respuesta": str(error),
            "aviso_dato": False,
            "aportes_traza": 0,
        }

    _capturar(pagina, archivo)
    agentes_ahora = pagina.locator(".mensaje-agente:not(.mensaje-cargando)").count()
    errores_ahora = pagina.locator(".mensaje-error-sistema").count()
    if agentes_ahora > previos_agente:
        ultimo = pagina.locator(".mensaje-agente:not(.mensaje-cargando)").last
        texto = ultimo.inner_text()
        aviso_dato = ultimo.locator(".aviso-dato").count() > 0
        aportes_traza = pagina.locator("#traza-aportes .aporte").count()
        return {
            "estado": "ok",
            "respuesta": texto,
            "aviso_dato": aviso_dato,
            "aportes_traza": aportes_traza,
        }
    if errores_ahora > previos_error:
        texto = pagina.locator(".mensaje-error-sistema").last.inner_text()
        return {"estado": "error", "respuesta": texto, "aviso_dato": False, "aportes_traza": 0}
    return {"estado": "desconocido", "respuesta": "", "aviso_dato": False, "aportes_traza": 0}


def _seleccionar_agentes(pagina, grafos: list[str]) -> list[str]:
    pagina.click("#btn-automatico")
    seleccionados = []
    for grafo in grafos:
        localizador = pagina.locator(f'.agente[data-grafo="{grafo}"]')
        if localizador.count() > 0:
            localizador.first.click()
            seleccionados.append(grafo)
    if len(seleccionados) > 1:
        pagina.select_option("#modo", "paralelo")
    return seleccionados


def main() -> int:
    parser = argparse.ArgumentParser(description="Captura evidencias locales de la consola web.")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="URL del servicio.")
    parser.add_argument("--clave", help="Clave API. Si se omite, se lee de .env.")
    parser.add_argument("--env-file", default=str(RAIZ / ".env"), help="Archivo .env.")
    parser.add_argument(
        "--salida",
        default=str(RAIZ / "evidencias" / "capturas"),
        help="Carpeta de capturas y acta.",
    )
    parser.add_argument(
        "--canal",
        choices=["msedge", "chrome", "chromium"],
        default="msedge",
        help="Navegador de Playwright. msedge/chrome usan el navegador instalado.",
    )
    parser.add_argument("--visible", action="store_true", help="Muestra el navegador.")
    parser.add_argument("--timeout", type=int, default=240, help="Timeout por consulta en segundos.")
    args = parser.parse_args()

    clave = _clave(args)
    if not clave:
        print("ERROR: no hay clave. Usa --clave, .env o define API_KEYS.")
        return 2

    url = args.url.rstrip("/")
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    try:
        disponibles = _verificar_servicio(url, clave)
    except Exception as error:
        print(f"ERROR: {error}")
        return 2
    print("Agentes disponibles:", ", ".join(disponibles))

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Falta Playwright. Instala: pip install -r requirements-evidencias.txt")
        return 2

    casos: list[dict] = []
    fecha = datetime.now(timezone.utc).isoformat()
    fallo_fatal: str | None = None

    with sync_playwright() as playwright:
        opciones = {"headless": not args.visible}
        if args.canal != "chromium":
            opciones["channel"] = args.canal
        try:
            navegador = playwright.chromium.launch(**opciones)
        except PlaywrightError as error:
            print(f"ERROR al abrir {args.canal}: {error}")
            if args.canal != "chromium":
                print("Prueba con --canal chromium y ejecuta: python -m playwright install chromium")
            return 3

        contexto = navegador.new_context(viewport={"width": 1500, "height": 950}, locale="es-CL")
        pagina = contexto.new_page()
        try:
            pagina.goto(url, wait_until="domcontentloaded", timeout=30000)
            pagina.wait_for_selector("#panel-acceso:not([hidden])", timeout=15000)
            _capturar(pagina, salida / "01-acceso.png")
            casos.append(
                {
                    "caso": "consola de acceso",
                    "estado": "ok",
                    "resultado": "panel de clave visible",
                    "captura": "01-acceso.png",
                }
            )

            pagina.fill("#clave", "clave-incorrecta-evidencia")
            pagina.click("#btn-conectar")
            pagina.wait_for_selector("#error-acceso:not([hidden])", timeout=20000)
            texto_error = pagina.locator("#error-acceso").inner_text()
            _capturar(pagina, salida / "02-acceso-rechazado.png")
            casos.append(
                {
                    "caso": "acceso rechazado",
                    "estado": "ok",
                    "resultado": texto_error,
                    "esperado": "401 / clave rechazada",
                    "captura": "02-acceso-rechazado.png",
                }
            )

            pagina.fill("#clave", clave)
            pagina.click("#btn-conectar")
            pagina.wait_for_selector("#app:not([hidden])", timeout=60000)
            pagina.wait_for_selector(".agente", timeout=15000)
            _capturar(pagina, salida / "03-consola-conectada.png")
            casos.append(
                {
                    "caso": "acceso permitido",
                    "estado": "ok",
                    "resultado": "consola conectada con agentes",
                    "agentes": disponibles,
                    "captura": "03-consola-conectada.png",
                }
            )

            pagina.click("#btn-automatico")
            pagina.select_option("#modo", "auto")
            resultado = _enviar(
                pagina,
                "¿Cuánto vale AAPL en el mercado US y qué debería revisar antes de invertir?",
                salida / "04-consulta-accion.png",
                args.timeout * 1000,
            )
            casos.append(
                {
                    "caso": "consulta de un agente",
                    "estado": resultado["estado"],
                    "resultado": resultado["respuesta"][:4000],
                    "aviso_dato": resultado["aviso_dato"],
                    "aportes_traza": resultado["aportes_traza"],
                    "captura": "04-consulta-accion.png",
                }
            )

            seleccionados = _seleccionar_agentes(
                pagina,
                ["agente_czz", "agente_alejandra", "agente_bryhan"],
            )
            resultado = _enviar(
                pagina,
                "Evalúa si conviene invertir en Falabella: quiero el dato de mercado, "
                "una revisión de cumplimiento normativo y un plan para automatizar el análisis.",
                salida / "05-consulta-multiagente.png",
                args.timeout * 1000,
            )
            estado_multi = resultado["estado"]
            observacion_multi = ""
            if estado_multi == "ok" and len(seleccionados) > 1 and resultado["aportes_traza"] < 2:
                estado_multi = "revisar"
                observacion_multi = "La traza no muestra al menos dos aportes."
            casos.append(
                {
                    "caso": "consulta multiagente",
                    "estado": estado_multi,
                    "resultado": resultado["respuesta"][:4000],
                    "agentes_seleccionados": seleccionados,
                    "aportes_traza": resultado["aportes_traza"],
                    "observacion": observacion_multi,
                    "captura": "05-consulta-multiagente.png",
                }
            )

            try:
                pagina.locator(".panel-traza").screenshot(
                    path=str(salida / "07-traza-a2a.png")
                )
                print(f"  captura: {salida / '07-traza-a2a.png'}")
            except Exception as error:
                print(f"  aviso: no se pudo capturar la traza: {error}")

            pagina.click("#btn-automatico")
            pagina.select_option("#modo", "auto")
            resultado = _enviar(
                pagina,
                "¿Cuánto vale AAPL?",
                salida / "06-dato-faltante.png",
                args.timeout * 1000,
            )
            estado_falta = resultado["estado"]
            observacion_falta = ""
            if estado_falta == "ok" and not resultado["aviso_dato"]:
                estado_falta = "revisar"
                observacion_falta = (
                    "El agente no mostró una pregunta o aviso de dato faltante en esta ejecución."
                )
            casos.append(
                {
                    "caso": "dato faltante",
                    "estado": estado_falta,
                    "resultado": resultado["respuesta"][:4000],
                    "aviso_dato": resultado["aviso_dato"],
                    "observacion": observacion_falta,
                    "captura": "06-dato-faltante.png",
                }
            )
        except Exception as error:
            fallo_fatal = str(error)
            try:
                _capturar(pagina, salida / "99-error.png")
            except Exception:
                pass
        finally:
            contexto.close()
            navegador.close()

    acta = {
        "entorno": "LOCAL",
        "fecha": fecha,
        "url": url,
        "canal": args.canal,
        "agentes_disponibles": disponibles,
        "clave": "no incluida",
        "fallo_fatal": fallo_fatal,
        "casos": casos,
    }
    (salida / "acta-capturas.json").write_text(
        json.dumps(acta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lineas = [
        "# Acta de capturas",
        "",
        f"- Entorno: **LOCAL**",
        f"- Fecha: `{fecha}`",
        f"- URL: `{url}`",
        f"- Navegador: `{args.canal}`",
        f"- Agentes disponibles: {', '.join(disponibles)}",
        "- Clave: **no incluida**",
        "",
        "| Caso | Estado | Resultado | Observación | Captura |",
        "| --- | --- | --- | --- | --- |",
    ]
    for caso in casos:
        resultado = str(caso.get("resultado", "")).replace("\n", " ")[:220]
        observacion = str(caso.get("observacion", "")).replace("\n", " ")[:220]
        lineas.append(
            f"| {caso.get('caso', '')} | {caso.get('estado', '')} | {resultado} | "
            f"{observacion} | {caso.get('captura', '')} |"
        )
    if fallo_fatal:
        lineas.extend(["", f"**Fallo fatal:** {fallo_fatal}"])
    lineas.extend(
        [
            "",
            "> Revisa las capturas antes de entregarlas: no deben mostrar claves, tokens, `.env` ni datos personales.",
        ]
    )
    (salida / "acta-capturas.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Acta: {salida / 'acta-capturas.md'}")
    print(f"JSON: {salida / 'acta-capturas.json'}")

    if fallo_fatal:
        print(f"Fallo fatal: {fallo_fatal}")
        return 1
    fallos = [caso for caso in casos if caso["estado"] != "ok"]
    if fallos:
        print("Casos no exitosos:")
        for caso in fallos:
            print(f"  - {caso['caso']}: {caso['estado']}")
        return 1
    print("Capturas generadas. Revisa el acta y oculta cualquier dato sensible.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
