"""Proveedor de promptfoo para los agentes A2A del Grupo 1.

promptfoo importa este archivo y llama `call_api(prompt, options, context)` por cada caso.
El agente se elige con `config.agente` del prompt (o con `vars.agente` del test) y la consulta
sale de `vars.pregunta`.

Cada llamada se delega en `evaluacion/agente.py`, que se re-ejecuta con el `.venv` del agente.
Así la evaluación usa exactamente el grafo, el prompt y las herramientas de cada entrega.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
EJECUTOR = Path(__file__).resolve().parents[1] / "agente.py"

AGENTES = {
    "agente_czz",
    "agente_bryhan",
    "agente_alejandra",
    "agente_soluciones_comerciales_marketing",
}


def call_api(prompt: str, options: dict, context: dict) -> dict:
    opciones = options or {}
    variables = (context or {}).get("vars") or {}
    config = opciones.get("config") or {}

    agente = config.get("agente") or variables.get("agente")
    pregunta = variables.get("pregunta") or prompt
    if agente not in AGENTES:
        return {"output": "", "error": f"Agente desconocido: {agente!r}. Usa uno de {sorted(AGENTES)}."}
    if not pregunta or not str(pregunta).strip():
        return {"output": "", "error": "Falta la variable 'pregunta'."}

    orden = [
        sys.executable,
        str(EJECUTOR),
        "--agente", agente,
        "--pregunta", str(pregunta),
        "--json",
    ]
    entorno = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    proceso = subprocess.run(
        orden,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=entorno,
        cwd=str(RAIZ),
        timeout=int(config.get("timeout_s", 300)),
    )

    salida = (proceso.stdout or "").strip()
    # La última línea es el JSON del agente; antes pueden aparecer avisos de librerías.
    datos = None
    for linea in reversed(salida.splitlines()):
        linea = linea.strip()
        if linea.startswith("{"):
            try:
                datos = json.loads(linea)
                break
            except json.JSONDecodeError:
                continue

    if datos is None:
        detalle = (proceso.stderr or salida or "sin salida").strip()[-1200:]
        return {"output": "", "error": f"El agente no devolvió JSON (código {proceso.returncode}): {detalle}"}
    if datos.get("error"):
        return {"output": "", "error": datos["error"]}

    return {
        "output": datos.get("respuesta", ""),
        "metadata": {
            "agente": agente,
            "duracion_ms": datos.get("duracion_ms"),
            "herramientas": datos.get("herramientas", []),
            "pasos": [f"{p['paso']}. {p['nodo']}: {p['accion']}" for p in datos.get("pasos", [])],
        },
    }
