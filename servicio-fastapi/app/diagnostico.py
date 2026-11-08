"""Diagnóstico local de servidores A2A y tarjetas descubiertas."""

from __future__ import annotations

import asyncio
import json

from app.a2a import ClienteA2A
from app.config import cargar_settings


async def main() -> int:
    settings = cargar_settings(requerir_claves=False)
    cliente = ClienteA2A(
        servidores=settings.servidores_a2a,
        timeout=settings.timeout_a2a,
        timeout_conexion=settings.timeout_conexion_a2a,
        ttl_cache=0,
        max_concurrencia=settings.max_concurrencia_a2a,
        confiar_en_proxy=settings.confiar_en_proxy,
    )
    try:
        agentes = await cliente.descubrir(forzar=True)
        print("Servidores configurados:")
        for servidor in settings.servidores_a2a:
            print(f"  - {servidor}")
        print()
        if not agentes:
            print("No se descubrió ningún agente.")
        for grafo, agente in agentes.items():
            habilidades = ", ".join(agente.habilidades) or "(sin habilidades en la tarjeta)"
            print(f"Agente: {grafo}")
            print(f"  tarjeta:      {agente.nombre_tarjeta}")
            print(f"  assistant_id: {agente.assistant_id}")
            print(f"  servidor:     {agente.base_url}")
            print(f"  descripción:  {agente.descripcion or '(sin descripción)'}")
            print(f"  habilidades:  {habilidades}")
            print()
        if cliente.errores_descubrimiento:
            print("Avisos de descubrimiento:")
            print(json.dumps(cliente.errores_descubrimiento, indent=2, ensure_ascii=False))
        return 0 if agentes else 1
    finally:
        await cliente.cerrar()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
