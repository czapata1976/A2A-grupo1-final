"""Modelos de entrada y salida de la API."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Modo = Literal["auto", "individual", "paralelo", "colaborativo"]
EstadoConsulta = Literal["ok", "parcial", "error"]
EstadoAporte = Literal["ok", "error"]

PATRON_SESION = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
PATRON_GRAFO = re.compile(r"^[a-z0-9_]{3,80}$")


class ConsultaEntrada(BaseModel):
    """Solicitud de una persona al servicio."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    mensaje: str = Field(
        min_length=1,
        max_length=4000,
        description="Consulta en lenguaje natural. Máximo 4000 caracteres.",
    )
    agentes: list[str] | None = Field(
        default=None,
        max_length=4,
        description="Grafos A2A a consultar. Si se omite, el servicio elige según la consulta.",
    )
    modo: Modo = Field(
        default="auto",
        description=(
            "auto o individual: un agente; paralelo: todos los elegidos; "
            "colaborativo: los agentes se pasan los aportes en orden."
        ),
    )
    session_id: str | None = Field(
        default=None,
        description="Identificador de conversación (8-64 caracteres alfanuméricos, guion o guion bajo).",
    )

    @field_validator("agentes")
    @classmethod
    def validar_agentes(cls, valor: list[str] | None) -> list[str] | None:
        if valor is None:
            return None
        limpios = [agente.strip() for agente in valor]
        if len(set(limpios)) != len(limpios):
            raise ValueError("No repitas el mismo agente en la lista.")
        invalidos = [agente for agente in limpios if not PATRON_GRAFO.fullmatch(agente)]
        if invalidos:
            raise ValueError(f"Nombre de grafo inválido: {', '.join(invalidos)}.")
        return limpios

    @field_validator("session_id")
    @classmethod
    def validar_sesion(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        if not PATRON_SESION.fullmatch(valor):
            raise ValueError(
                "session_id debe tener entre 8 y 64 caracteres: letras, números, guion o guion bajo."
            )
        return valor


class AporteAgente(BaseModel):
    agente: str
    autor: str | None = None
    especialidad: str | None = None
    estado: EstadoAporte
    respuesta: str | None = None
    error: str | None = None
    codigo_error: str | None = None
    duracion_ms: int = 0
    context_id: str | None = None
    contexto_reutilizado: bool = False


class PasoTraza(BaseModel):
    paso: int
    accion: str
    agente: str | None = None
    detalle: str
    duracion_ms: int | None = None


class ConsultaSalida(BaseModel):
    solicitud_id: str
    session_id: str
    modo: Modo
    agentes_consultados: list[str]
    respuesta: str
    aportes: list[AporteAgente]
    estado: EstadoConsulta
    errores: list[str] = Field(default_factory=list)
    traza: list[PasoTraza] = Field(default_factory=list)
    posible_falta_de_datos: bool = False


class AgenteInfo(BaseModel):
    grafo: str
    autor: str | None = None
    especialidad: str | None = None
    descripcion: str | None = None
    habilidades: list[str] = Field(default_factory=list)
    disponible: bool = True


class ListaAgentesSalida(BaseModel):
    agentes: list[AgenteInfo]
    errores: list[str] = Field(default_factory=list)
    total: int


class ReinicioSalida(BaseModel):
    session_id: str
    estado: Literal["reiniciada"]


class SaludSalida(BaseModel):
    estado: Literal["ok"]
    servicio: str
    version: str
    hora: str
