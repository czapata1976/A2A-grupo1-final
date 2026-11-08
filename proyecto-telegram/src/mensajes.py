"""Utilidades comunes para invocar grafos y extraer su respuesta."""

from __future__ import annotations


def crear_entrada(texto: str) -> dict:
    return {"messages": [{"role": "user", "content": texto}]}


def _contenido_texto(contenido) -> str:
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        partes = []
        for bloque in contenido:
            if isinstance(bloque, str):
                partes.append(bloque)
            elif isinstance(bloque, dict) and isinstance(bloque.get("text"), str):
                partes.append(bloque["text"])
        return "\n".join(partes)
    return ""


def extraer_texto(estado: dict) -> str:
    if not isinstance(estado, dict):
        raise ValueError("La salida del grafo no es un diccionario.")
    if estado.get("__interrupt__"):
        raise ValueError("El grafo quedó pausado; resuelve el interrupt antes de responder.")
    mensajes = estado.get("messages", [])
    for mensaje in reversed(mensajes):
        if isinstance(mensaje, dict):
            rol = mensaje.get("type", mensaje.get("role"))
            contenido = mensaje.get("content", "")
        else:
            rol = getattr(mensaje, "type", getattr(mensaje, "role", None))
            contenido = getattr(mensaje, "content", "")
        if rol in {"ai", "assistant"}:
            texto = _contenido_texto(contenido)
            if texto.strip():
                return texto.strip()
    raise ValueError("El grafo no devolvió un mensaje ai/assistant con texto.")
