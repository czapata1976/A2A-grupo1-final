"""Memoria de contextos A2A por sesión."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class _Sesion:
    contextos: dict[str, str] = field(default_factory=dict)
    visto: float = 0.0


class AlmacenSesiones:
    def __init__(self, ttl: float, max_sesiones: int) -> None:
        self.ttl = ttl
        self.max_sesiones = max_sesiones
        self._datos: dict[str, _Sesion] = {}
        self._lock = asyncio.Lock()

    async def obtener_contexto(self, session_id: str, agente: str) -> str | None:
        async with self._lock:
            self._purgar()
            sesion = self._datos.get(session_id)
            if sesion is None:
                return None
            sesion.visto = time.monotonic()
            return sesion.contextos.get(agente)

    async def guardar_contexto(self, session_id: str, agente: str, context_id: str | None) -> None:
        if not context_id:
            return
        async with self._lock:
            self._purgar()
            if session_id not in self._datos and len(self._datos) >= self.max_sesiones:
                self._expulsar_antigua()
            sesion = self._datos.setdefault(session_id, _Sesion())
            sesion.contextos[agente] = context_id
            sesion.visto = time.monotonic()

    async def limpiar(self, session_id: str) -> bool:
        async with self._lock:
            return self._datos.pop(session_id, None) is not None

    async def contar(self) -> int:
        async with self._lock:
            self._purgar()
            return len(self._datos)

    def _purgar(self) -> None:
        ahora = time.monotonic()
        vencidas = [clave for clave, sesion in self._datos.items() if ahora - sesion.visto > self.ttl]
        for clave in vencidas:
            self._datos.pop(clave, None)

    def _expulsar_antigua(self) -> None:
        if not self._datos:
            return
        clave = min(self._datos, key=lambda item: self._datos[item].visto)
        self._datos.pop(clave, None)
