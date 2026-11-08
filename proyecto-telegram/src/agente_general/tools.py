"""Herramientas deterministas del agente general."""

from langchain_core.tools import tool

APUNTES = {
    "proyecto": (
        "Este proyecto conecta agentes LangGraph con una CLI y con Telegram. "
        "La API recibe actualizaciones por webhook, verifica el secreto y responde en segundo plano."
    ),
    "agentes": (
        "Hay agentes registrados en src/agentes.py. Cada uno tiene su propio prompt, "
        "sus herramientas y un grafo que solo los ensambla."
    ),
}


@tool
def consultar_mis_apuntes(tema: str = "") -> str:
    """Consulta los apuntes del proyecto. Vacío devuelve todos."""
    clave = tema.lower().strip()
    if not clave:
        return "\n".join(f"{nombre}: {texto}" for nombre, texto in APUNTES.items())
    return APUNTES.get(
        clave,
        "No tengo ese tema registrado. Consulta proyecto o agentes.",
    )


HERRAMIENTAS = [consultar_mis_apuntes]
