"""CLI para ejecutar los agentes desde la raíz del proyecto."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent
load_dotenv(RAIZ / ".env")

from src.agentes import listar_agentes, obtener_agente
from src.mensajes import crear_entrada, extraer_texto


def _obtener(nombre: str):
    try:
        return obtener_agente(nombre)
    except KeyError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2) from error


def ejecutar(nombre: str, mensaje: str, saltos: bool = False) -> str:
    grafo = _obtener(nombre)
    entrada = crear_entrada(mensaje)
    if not saltos:
        return extraer_texto(grafo.invoke(entrada))

    estado_final: dict = {}
    for actualizacion in grafo.stream(entrada, stream_mode="updates"):
        for nodo, cambio in actualizacion.items():
            print(f"[nodo] {nodo}")
            if isinstance(cambio, dict):
                estado_final.update(cambio)
    return extraer_texto(estado_final)


def diagrama(nombre: str) -> str:
    if not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = "solo-para-diagrama"
    if not os.environ.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = "solo-para-diagrama"
    grafo = _obtener(nombre)
    return grafo.get_graph().draw_mermaid()


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ejecuta un agente registrado o muestra su diagrama Mermaid.",
    )
    parser.add_argument("agente", help=f"Nombre del agente. Disponibles: {', '.join(listar_agentes())}")
    parser.add_argument("mensaje", nargs="?", help="Mensaje para el agente.")
    parser.add_argument("--saltos", action="store_true", help="Imprime los nodos del grafo.")
    parser.add_argument(
        "--diagrama",
        action="store_true",
        help="Imprime el Mermaid del grafo y no lo ejecuta.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    if args.diagrama:
        try:
            print(diagrama(args.agente))
        except Exception as error:
            print(f"No se pudo generar el diagrama: {error}", file=sys.stderr)
            return 1
        return 0
    if not args.mensaje:
        parser.error("Falta el mensaje: python main.py {agente} \"mensaje\"")
    try:
        print(ejecutar(args.agente, args.mensaje, args.saltos))
    except Exception as error:
        print(f"Error al ejecutar el agente: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
