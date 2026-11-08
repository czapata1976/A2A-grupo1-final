"""Expone el agente_czz por un túnel temporal de Cloudflare (alternativa a tunel_cloudflare.ps1).

Uso:
    python tunel_cloudflare.py            # puerto 2025
    python tunel_cloudflare.py --port 2025
    python tunel_cloudflare.py --detener

Requiere `cloudflared` en el PATH (winget install Cloudflare.cloudflared) y el servidor de LangGraph
arriba (`langgraph dev --port 2025`). La URL pública se guarda en `tunel.url` y el PID en `tunel.pid`.
"""
from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parent
LOG = RAIZ / "cloudflared.log"
ARCHIVO_URL = RAIZ / "tunel.url"
ARCHIVO_PID = RAIZ / "tunel.pid"
PATRON = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def servidor_arriba(puerto: int) -> bool:
    try:
        return httpx.get(f"http://127.0.0.1:{puerto}/ok", timeout=3).status_code == 200
    except Exception:
        return False


def detener() -> int:
    if ARCHIVO_PID.exists():
        pid = ARCHIVO_PID.read_text(encoding="ascii").strip()
        if pid:
            try:
                os.kill(int(pid), signal.SIGTERM)
                print(f"Túnel detenido (PID {pid}).")
            except OSError:
                print(f"El proceso {pid} ya no estaba corriendo.")
        ARCHIVO_PID.unlink(missing_ok=True)
    ARCHIVO_URL.unlink(missing_ok=True)
    return 0


def abrir(puerto: int, timeout: int) -> int:
    if not servidor_arriba(puerto):
        print(f"No responde http://127.0.0.1:{puerto}/ok")
        print(f"Levanta primero el agente: langgraph dev --port {puerto}")
        return 1

    for archivo in (LOG, ARCHIVO_URL, ARCHIVO_PID):
        archivo.unlink(missing_ok=True)

    print(f"Abriendo el túnel hacia http://127.0.0.1:{puerto} ...")
    with LOG.open("w", encoding="utf-8") as salida:
        proceso = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{puerto}", "--no-autoupdate"],
            stdout=salida, stderr=subprocess.STDOUT,
        )

    url = None
    limite = time.monotonic() + timeout
    while time.monotonic() < limite and url is None:
        if LOG.exists():
            try:
                encontrada = PATRON.search(LOG.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                # cloudflared puede tener el log abierto mientras escribe: se reintenta.
                encontrada = None
            if encontrada:
                url = encontrada.group(0)
                break
        if proceso.poll() is not None:
            break
        time.sleep(0.5)

    if not url:
        print(f"No pude leer la URL pública. Revisa {LOG}")
        proceso.terminate()
        return 1

    ARCHIVO_URL.write_text(url, encoding="ascii")
    ARCHIVO_PID.write_text(str(proceso.pid), encoding="ascii")

    try:
        asistentes = httpx.post(f"{url}/assistants/search", json={"graph_id": "agente_czz"},
                                timeout=30).json()
        aid = asistentes[0]["assistant_id"]
        httpx.get(f"{url}/.well-known/agent-card.json", params={"assistant_id": aid}, timeout=30)
        estado = "agente_czz visible por el túnel"
    except Exception as error:
        estado = f"el túnel abrió, pero el agente todavía no responde: {error}"

    print(f"\nTúnel activo: {url}")
    print(f"PID de cloudflared: {proceso.pid}")
    print(f"Estado: {estado}")
    print(f"\nPara que el notebook use la URL pública:\n  $env:A2A_CZZ_URL = \"{url}\"   (PowerShell)")
    print(f"  export A2A_CZZ_URL={url}     (bash)")
    print("\nAvisos:")
    print("  - La URL cambia cada vez que se abre el túnel; no se guarda en el repositorio.")
    print("  - La tarjeta anuncia la URL local; el cliente remoto debe reescribirla (el notebook lo hace).")
    print("  - Cierra el túnel al terminar:  python tunel_cloudflare.py --detener")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Túnel temporal de Cloudflare para agente_czz")
    parser.add_argument("--port", type=int, default=2025, help="puerto local del servidor (2025)")
    parser.add_argument("--timeout", type=int, default=60, help="segundos de espera de la URL")
    parser.add_argument("--detener", action="store_true", help="cierra el túnel abierto")
    args = parser.parse_args()
    return detener() if args.detener else abrir(args.port, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
