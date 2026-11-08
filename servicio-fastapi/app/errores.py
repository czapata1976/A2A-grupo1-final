"""Errores de dominio que la API traduce a respuestas HTTP claras."""

from __future__ import annotations


class ErrorServicio(Exception):
    def __init__(
        self,
        status_code: int,
        codigo: str,
        mensaje: str,
        detalles: list[str] | None = None,
    ) -> None:
        super().__init__(mensaje)
        self.status_code = status_code
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalles = detalles or []


class SolicitudInvalida(ErrorServicio):
    def __init__(self, mensaje: str, detalles: list[str] | None = None) -> None:
        super().__init__(400, "SOLICITUD_INVALIDA", mensaje, detalles)


class SinAgentesDisponibles(ErrorServicio):
    def __init__(self, mensaje: str, detalles: list[str] | None = None) -> None:
        super().__init__(503, "SIN_AGENTES_DISPONIBLES", mensaje, detalles)


class FalloAgentes(ErrorServicio):
    def __init__(
        self,
        mensaje: str,
        detalles: list[str] | None = None,
        status_code: int = 502,
        codigo: str = "AGENTES_FALLARON",
    ) -> None:
        super().__init__(status_code, codigo, mensaje, detalles)
