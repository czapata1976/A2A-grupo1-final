"""Ejecuta un agente del Grupo 1 y muestra su respuesta, sus pasos o su diagrama.

Uso (desde cualquier carpeta del repositorio):

    python evaluacion\\agente.py --agente agente_czz --pregunta "¿Precio de AAPL en EE.UU.?"
    python evaluacion\\agente.py --agente agente_bryhan --pregunta "..." --saltos
    python evaluacion\\agente.py --agente agente_alejandra --diagrama
    python evaluacion\\agente.py --agente agente_czz --pregunta "..." --json

`--saltos` muestra, paso a paso, qué nodo del grafo se ejecutó, qué herramienta llamó y qué
devolvió: sirve para ver DÓNDE se equivocó el agente en una prueba que falló.
`--diagrama` imprime el grafo en Mermaid (el mismo diagrama de los notebooks del taller).
`--json` devuelve la respuesta y la traza en JSON (lo usa el proveedor de promptfoo).

El script se re-ejecuta solo con el intérprete del `.venv` de cada agente, así que no hace
falta activar el entorno a mano.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# agente -> carpeta, paquete de src, archivo del grafo y modelo por defecto
AGENTES: dict[str, dict] = {
    "agente_czz": {
        "carpeta": "mi-agente-cz",
        "paquete": "agente_viajes",
        "descripcion": "Carlos Zapata · análisis de acciones e inversiones",
    },
    "agente_bryhan": {
        "carpeta": "agente-bryhan",
        "paquete": "agente_bryhan",
        "descripcion": "Bryhan Cortes · AI Engineering aplicado a procesos",
    },
    "agente_alejandra": {
        "carpeta": "mi-agente-ale",
        "paquete": "agente_viajes",
        "descripcion": "Alejandra Ubilla · auditoría CMF y SII",
    },
    "agente_soluciones_comerciales_marketing": {
        "carpeta": "mi-agente-CM",
        "paquete": "agente_viajes",
        "descripcion": "Carlos Monroy · ingeniería comercial y marketing",
    },
}


def _python_del_agente(nombre: str) -> Path:
    return RAIZ / AGENTES[nombre]["carpeta"] / ".venv" / "Scripts" / "python.exe"


def _texto(contenido) -> str:
    """Normaliza el contenido de un mensaje (str o lista de bloques) a texto plano."""
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        partes: list[str] = []
        for bloque in contenido:
            if isinstance(bloque, str):
                partes.append(bloque)
            elif isinstance(bloque, dict):
                if bloque.get("type") == "text" and bloque.get("text"):
                    partes.append(bloque["text"])
        return "\n".join(partes)
    return "" if contenido is None else str(contenido)


def _recortar(texto: str, limite: int = 320) -> str:
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= limite else texto[:limite] + " …"


def _cargar_grafo(nombre: str):
    """Importa el grafo del agente desde su propia carpeta."""
    carpeta = RAIZ / AGENTES[nombre]["carpeta"]
    paquete = AGENTES[nombre]["paquete"]
    if str(carpeta) not in sys.path:
        sys.path.insert(0, str(carpeta))
    os.chdir(carpeta)  # load_dotenv() y langgraph.json se resuelven desde aquí
    modulo = __import__(f"src.{paquete}.graph", fromlist=["graph"])
    return modulo.graph


def _pasos_del_update(update: dict) -> list[dict]:
    """Convierte un update de LangGraph (stream_mode='updates') en pasos legibles."""
    pasos: list[dict] = []
    for nodo, datos in update.items():
        mensajes = (datos or {}).get("messages", []) if isinstance(datos, dict) else []
        for mensaje in mensajes:
            tipo = type(mensaje).__name__
            llamadas = getattr(mensaje, "tool_calls", None) or []
            if llamadas:
                for llamada in llamadas:
                    pasos.append(
                        {
                            "nodo": nodo,
                            "accion": "herramienta",
                            "herramienta": llamada.get("name"),
                            "detalle": _recortar(json.dumps(llamada.get("args", {}), ensure_ascii=False)),
                        }
                    )
            elif tipo == "ToolMessage":
                pasos.append(
                    {
                        "nodo": nodo,
                        "accion": "resultado_herramienta",
                        "herramienta": getattr(mensaje, "name", None),
                        "detalle": _recortar(_texto(getattr(mensaje, "content", ""))),
                    }
                )
            else:
                texto = _texto(getattr(mensaje, "content", ""))
                if texto.strip():
                    pasos.append(
                        {
                            "nodo": nodo,
                            "accion": "respuesta",
                            "detalle": _recortar(texto),
                            "texto": texto,
                        }
                    )
    return pasos


def ejecutar(nombre: str, pregunta: str) -> dict:
    """Invoca el agente y devuelve respuesta, pasos y duración."""
    grafo = _cargar_grafo(nombre)
    inicio = time.perf_counter()
    pasos: list[dict] = []
    respuesta = ""
    numero = 0

    for update in grafo.stream(
        {"messages": [{"role": "user", "content": pregunta}]},
        stream_mode="updates",
    ):
        for paso in _pasos_del_update(update):
            numero += 1
            paso["paso"] = numero
            paso["duracion_ms"] = int((time.perf_counter() - inicio) * 1000)
            if paso["accion"] == "respuesta":
                respuesta = paso.get("texto", paso["detalle"])
            paso.pop("texto", None)
            pasos.append(paso)

    return {
        "agente": nombre,
        "descripcion": AGENTES[nombre]["descripcion"],
        "pregunta": pregunta,
        "respuesta": respuesta,
        "pasos": pasos,
        "herramientas": sorted({p["herramienta"] for p in pasos if p.get("herramienta")}),
        "duracion_ms": int((time.perf_counter() - inicio) * 1000),
        "modelo": os.environ.get("MODELO", "gemini-3.5-flash-lite"),
    }


def _imprimir_saltos(resultado: dict) -> None:
    print(f"AGENTE: {resultado['agente']} · {resultado['descripcion']}")
    print(f"PREGUNTA: {resultado['pregunta']}")
    print(f"MODELO: {resultado['modelo']}")
    print("-" * 78)
    if not resultado["pasos"]:
        print("(el grafo no emitió pasos)")
    for paso in resultado["pasos"]:
        marca = {"herramienta": "→", "resultado_herramienta": "←", "respuesta": "✓"}[paso["accion"]]
        nombre = paso.get("herramienta") or paso["nodo"]
        print(f"[PASO {paso['paso']}] {paso['nodo']:<6} {marca} {nombre}  ({paso['duracion_ms']} ms)")
        print(f"          {paso['detalle']}")
    print("-" * 78)
    print(f"RESPUESTA FINAL ({len(resultado['respuesta'])} caracteres):")
    print(resultado["respuesta"] or "(vacía)")
    print("-" * 78)
    print(f"DURACIÓN: {resultado['duracion_ms']} ms · HERRAMIENTAS: {', '.join(resultado['herramientas']) or 'ninguna'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta un agente del Grupo 1 paso a paso.")
    parser.add_argument("--agente", required=True, choices=sorted(AGENTES), help="Nombre del grafo.")
    parser.add_argument("--pregunta", default="", help="Consulta para el agente.")
    parser.add_argument("--saltos", action="store_true", help="Muestra la traza paso a paso.")
    parser.add_argument("--diagrama", action="store_true", help="Imprime el grafo en Mermaid.")
    parser.add_argument("--json", action="store_true", help="Salida JSON (para promptfoo).")
    args = parser.parse_args()

    # Re-ejecuta con el Python del agente para tener sus dependencias.
    esperado = _python_del_agente(args.agente)
    if esperado.exists() and Path(sys.executable).resolve() != esperado.resolve():
        orden = [str(esperado), str(Path(__file__).resolve()), *sys.argv[1:]]
        entorno = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        return subprocess.call(orden, env=entorno)

    try:
        grafo = _cargar_grafo(args.agente)
        if args.diagrama:
            print(grafo.get_graph().draw_mermaid())
            if not args.pregunta:
                return 0
        if not args.pregunta:
            parser.error("--pregunta es obligatoria salvo que uses solo --diagrama")
        resultado = ejecutar(args.agente, args.pregunta)
    except Exception as error:  # noqa: BLE001 - se reporta tal cual al evaluador
        if args.json:
            print(json.dumps({"agente": args.agente, "respuesta": "", "pasos": [],
                              "error": f"{type(error).__name__}: {error}"}, ensure_ascii=False))
        else:
            print(f"ERROR: {type(error).__name__}: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(resultado, ensure_ascii=False))
    elif args.saltos:
        _imprimir_saltos(resultado)
    else:
        print(resultado["respuesta"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
