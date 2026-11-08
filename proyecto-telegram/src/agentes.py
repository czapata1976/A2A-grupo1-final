"""Registro central de agentes."""

from __future__ import annotations

from functools import lru_cache

from src.agente_alejandra.graph import construir_grafo as construir_alejandra
from src.agente_bryhan.graph import construir_grafo as construir_bryhan
from src.agente_czz.graph import construir_grafo as construir_czz
from src.agente_general.graph import construir_grafo as construir_general
from src.agente_soluciones_comerciales_marketing.graph import (
    construir_grafo as construir_soluciones,
)

_CONSTRUCTORES = {
    "agente_general": construir_general,
    "agente_czz": construir_czz,
    "agente_bryhan": construir_bryhan,
    "agente_alejandra": construir_alejandra,
    "agente_soluciones_comerciales_marketing": construir_soluciones,
}


def listar_agentes() -> tuple[str, ...]:
    return tuple(_CONSTRUCTORES)


@lru_cache(maxsize=None)
def obtener_agente(nombre: str):
    constructor = _CONSTRUCTORES.get(nombre)
    if constructor is None:
        disponibles = ", ".join(_CONSTRUCTORES)
        raise KeyError(f"Agente desconocido: {nombre}. Disponibles: {disponibles}")
    return constructor()
