"""Abre un túnel de Cloudflare por cada agente A2A y actualiza la lista de servidores.

Uso (desde la raíz del taller):

    python servicio-fastapi\\scripts\\tuneles_agentes.py
    python servicio-fastapi\\scripts\\tuneles_agentes.py --heroku a2agrupo1
    python servicio-fastapi\\scripts\\tuneles_agentes.py --detener

Qué hace:
  1. Comprueba que cada agente responda en su puerto local (2025-2028).
  2. Abre `cloudflared tunnel --url http://127.0.0.1:<puerto>` para cada uno.
  3. Verifica que la URL pública responda y que el grafo esté publicado.
  4. Guarda las URLs y los PID en `servicio-fastapi/logs/tuneles.json`.
  5. Con `--heroku`, actualiza `A2A_SERVIDORES` (y `A2A_TIMEOUT`) en la app indicada.

La URL de un túnel rápido cambia cada vez que se abre: hay que volver a ejecutar este script
y actualizar Heroku después de cada reinicio. Los canales (web, Telegram y WhatsApp) usan el
gateway, que a su vez consulta estos servidores.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parents[1]
LOGS = RAIZ / "logs"
ARCHIVO = LOGS / "tuneles.json"
PATRON = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

AGENTES = [
    (2025, "agente_czz"),
    (2026, "agente_bryhan"),
    (2027, "agente_alejandra"),
    (2028, "agente_soluciones_comerciales_marketing"),
]


def _cloudflared() -> str:
    ruta = shutil.which("cloudflared")
    if ruta:
        return ruta
    comun = Path(r"C:\Program Files (x86)\cloudflared\cloudflared.exe")
    if comun.exists():
        return str(comun)
    raise SystemExit("No encuentro cloudflared. Instálalo con: winget install Cloudflare.cloudflared")


def _get(url: str, timeout: float = 10.0) -> int:
    with urllib.request.urlopen(url, timeout=timeout) as respuesta:
        return respuesta.status


def _post_json(url: str, cuerpo: dict, timeout: float = 30.0) -> dict:
    datos = json.dumps(cuerpo).encode("utf-8")
    peticion = urllib.request.Request(
        url, data=datos, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def servidor_arriba(puerto: int) -> bool:
    try:
        return _get(f"http://127.0.0.1:{puerto}/ok", timeout=3) == 200
    except Exception:
        return False


def abrir(puerto: int, espera: float = 90.0) -> tuple[str, subprocess.Popen]:
    LOGS.mkdir(parents=True, exist_ok=True)
    log = LOGS / f"cloudflared-{puerto}.log"
    log.unlink(missing_ok=True)
    salida = log.open("w", encoding="utf-8")
    banderas = 0
    if os.name == "nt":
        banderas = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    proceso = subprocess.Popen(
        [_cloudflared(), "tunnel", "--url", f"http://127.0.0.1:{puerto}", "--no-autoupdate"],
        stdout=salida, stderr=subprocess.STDOUT, creationflags=banderas,
    )
    limite = time.monotonic() + espera
    while time.monotonic() < limite:
        if proceso.poll() is not None:
            break
        try:
            encontrada = PATRON.search(log.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            encontrada = None
        if encontrada:
            return encontrada.group(0), proceso
        time.sleep(0.4)
    proceso.terminate()
    raise SystemExit(f"No pude obtener la URL del túnel del puerto {puerto}. Revisa {log}")


def verificar(url: str, grafo: str, intentos: int = 12) -> str:
    """Comprueba que el grafo esté publicado detrás del túnel y devuelve el assistant_id.

    Los túneles rápidos tardan unos segundos en resolver por DNS, así que se reintenta."""
    ultimo: Exception | None = None
    for intento in range(intentos):
        try:
            asistentes = _post_json(f"{url}/assistants/search", {"graph_id": grafo})
            if not asistentes:
                raise RuntimeError(f"{url} no publica el grafo {grafo}")
            aid = asistentes[0]["assistant_id"]
            _get(f"{url}/.well-known/agent-card.json?assistant_id={aid}", timeout=30)
            return aid
        except Exception as error:  # noqa: BLE001 - se reintenta y se informa el último
            ultimo = error
            if intento + 1 < intentos:
                time.sleep(3)
    raise RuntimeError(f"{url}: {ultimo}")


def detener() -> int:
    if not ARCHIVO.exists():
        print("No hay túneles registrados.")
        return 0
    datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
    for puerto, pid in datos.get("pids", {}).items():
        try:
            os.kill(int(pid), signal.SIGTERM)
            print(f"Túnel {puerto} detenido (PID {pid}).")
        except OSError:
            print(f"El túnel {puerto} (PID {pid}) ya no estaba corriendo.")
    ARCHIVO.unlink(missing_ok=True)
    return 0


def _actualizar_heroku(app: str, servidores: list[str], timeout: int) -> int:
    # En Windows el CLI de Heroku es un .cmd: hay que resolver la ruta completa.
    heroku = shutil.which("heroku")
    if not heroku:
        print("No encuentro el CLI de Heroku. Instálalo y ejecuta `heroku login`.")
        return 1
    orden = [
        heroku, "config:set",
        f"A2A_SERVIDORES={','.join(servidores)}",
        f"A2A_TIMEOUT={timeout}",
        "--app", app,
    ]
    print(f"\nActualizando Heroku ({app}) …")
    resultado = subprocess.run(orden, text=True, encoding="utf-8", errors="replace")
    if resultado.returncode != 0:
        print("No pude actualizar Heroku. Revisa `heroku login` y el nombre de la app.")
        return resultado.returncode
    print("Heroku actualizado. Si el catálogo tarda en refrescar: "
          f"heroku restart --app {app}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Túneles Cloudflare para los agentes A2A del Grupo 1.")
    parser.add_argument("--solo", type=int, action="append", help="Puerto a exponer (repetible). Por defecto, todos.")
    parser.add_argument("--heroku", help="App de Heroku donde actualizar A2A_SERVIDORES.")
    parser.add_argument("--timeout", type=int, default=90, help="Segundos de espera de A2A en Heroku.")
    parser.add_argument("--detener", action="store_true", help="Cierra los túneles registrados.")
    parser.add_argument("--reverificar", action="store_true", help="Revisa los túneles ya guardados.")
    args = parser.parse_args()

    if args.detener:
        return detener()

    if args.reverificar:
        if not ARCHIVO.exists():
            raise SystemExit("No hay túneles guardados. Ejecuta el script sin --reverificar.")
        datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
        for grafo, info in datos["por_agente"].items():
            try:
                info["assistant_id"] = verificar(info["url"], grafo)
                info["estado"] = "verificado"
            except Exception as error:  # noqa: BLE001
                info["estado"] = f"sin verificar: {error}"
            print(f"{grafo}: {info['url']} → {info['estado']}", flush=True)
        ARCHIVO.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
        servidores = datos["servidores"]
        print("\nA2A_SERVIDORES=" + ",".join(servidores))
        if args.heroku:
            return _actualizar_heroku(args.heroku, servidores, args.timeout)
        return 0

    agentes = [par for par in AGENTES if not args.solo or par[0] in args.solo]
    faltan = [p for p, _ in agentes if not servidor_arriba(p)]
    if faltan:
        raise SystemExit(
            "Estos agentes no responden en local: "
            + ", ".join(f"{p}" for p in faltan)
            + "\nLevántalos primero con:  .venv\\Scripts\\langgraph.exe dev --port <puerto> --no-browser"
        )

    por_agente: dict[str, dict] = {}
    pids: dict[str, int] = {}
    for puerto, grafo in agentes:
        print(f"Abriendo túnel para {grafo} (puerto {puerto}) …", flush=True)
        url, proceso = abrir(puerto)
        try:
            aid = verificar(url, grafo)
            estado = "verificado"
        except Exception as error:  # noqa: BLE001 - se informa sin cortar el resto
            aid = None
            estado = f"sin verificar: {error}"
        por_agente[grafo] = {"puerto": puerto, "url": url, "assistant_id": aid, "estado": estado}
        pids[str(puerto)] = proceso.pid
        print(f"  {url}  ({estado})", flush=True)

    servidores = [datos["url"] for datos in por_agente.values()]
    ARCHIVO.write_text(
        json.dumps({"servidores": servidores, "por_agente": por_agente, "pids": pids}, indent=2),
        encoding="utf-8",
    )

    print("\nA2A_SERVIDORES=" + ",".join(servidores))
    print(f"Guardado en {ARCHIVO}")

    if args.heroku:
        return _actualizar_heroku(args.heroku, servidores, args.timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
