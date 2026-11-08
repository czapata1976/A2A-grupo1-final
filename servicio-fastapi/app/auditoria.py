"""Registro de auditoría en JSON Lines, sin secretos ni texto de las consultas."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def hash_corto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


class Auditor:
    def __init__(self, ruta: str | None) -> None:
        self.ruta = Path(ruta) if ruta else None
        self._lock = threading.Lock()
        if self.ruta is not None:
            try:
                self.ruta.parent.mkdir(parents=True, exist_ok=True)
            except OSError as error:
                logger.warning("No se pudo crear la carpeta de auditoría %s: %s", self.ruta.parent, error)
                self.ruta = None

    def registrar(self, evento: dict) -> None:
        if self.ruta is None:
            return
        registro = {
            "ts": datetime.now(timezone.utc).isoformat(),
            **evento,
        }
        try:
            with self._lock:
                with self.ruta.open("a", encoding="utf-8") as archivo:
                    archivo.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")
        except OSError as error:
            logger.warning("No se pudo escribir la auditoría en %s: %s", self.ruta, error)
