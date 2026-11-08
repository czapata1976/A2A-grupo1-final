"""Preparación compartida de los notebooks y del servidor local."""
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent


def preparar_entorno():
    load_dotenv(ROOT / ".env")
    os.environ.setdefault("A2A_VIAJES_URL", "http://127.0.0.1:2025")
    os.environ.setdefault("A2A_VIAJES_GRAPH", "agente_soluciones_comerciales_marketing")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return os.environ["A2A_VIAJES_URL"].rstrip("/")


def asegurar_servidor(timeout=90):
    """Reutiliza el servidor o inicia langgraph dev local y espera su disponibilidad."""
    url = preparar_entorno()
    with httpx.Client(timeout=2, trust_env=False) as client:
        def disponible():
            try:
                return client.get(f"{url}/ok").status_code == 200
            except httpx.TransportError:
                return False

        if disponible():
            return url
        destino = urlparse(url)
        if destino.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise RuntimeError(f"El servidor remoto {url} no responde. Inícialo antes de continuar.")
        if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
            raise RuntimeError(f"Configura GOOGLE_API_KEY en {ROOT / '.env'}.")
        python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        python = str(python) if python.exists() else sys.executable
        log = ROOT / "langgraph-dev.log"
        with log.open("a", encoding="utf-8") as salida:
            proceso = subprocess.Popen(
                [python, "-m", "langgraph_cli", "dev", "--no-browser", "--no-reload",
                 "--host", destino.hostname, "--port", str(destino.port or 2025)],
                cwd=ROOT, stdout=salida, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        limite = time.monotonic() + timeout
        while time.monotonic() < limite:
            if disponible():
                return url
            if proceso.poll() is not None:
                raise RuntimeError(f"LangGraph terminó con código {proceso.returncode}. Revisa {log}.")
            time.sleep(0.5)
        proceso.terminate()
        raise RuntimeError(f"LangGraph no inició en {timeout}s. Revisa {log}.")


if __name__ == "__main__":
    print(f"Servidor disponible: {asegurar_servidor()}")
