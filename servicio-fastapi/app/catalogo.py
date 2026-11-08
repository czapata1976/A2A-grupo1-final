"""Catálogo de agentes del Grupo 1 y selección por especialidad."""

from __future__ import annotations

import json
import re
import unicodedata

from app.a2a import AgenteRemoto
from app.config import ConfiguracionInvalida, Settings
from app.errores import SolicitudInvalida

CATALOGO_POR_DEFECTO: dict[str, dict] = {
    "agente_czz": {
        "autor": "Carlos Zapata",
        "especialidad": "análisis de acciones e inversiones",
        "descripcion": (
            "Consulta precios y datos de mercado de acciones de EE.UU. y Chile, "
            "criterios de inversión, riesgo, diversificación y apuntes del autor."
        ),
        "palabras_clave": [
            "accion", "acciones", "invertir", "inversion", "inversiones", "bolsa",
            "ticker", "precio", "per", "dividendo", "portafolio", "rentabilidad",
            "riesgo", "diversificacion", "aapl", "msft", "sqm", "falabella", "mercado",
        ],
    },
    "agente_bryhan": {
        "autor": "Bryhan Cortes",
        "especialidad": "AI Engineering aplicado a procesos empresariales y financieros",
        "descripcion": (
            "Analiza procesos, diseña soluciones de datos e IA, compara alternativas "
            "técnicas y arma planes de trabajo con restricciones y responsables."
        ),
        "palabras_clave": [
            "proceso", "procesos", "automatizar", "automatizacion", "ia", "inteligencia artificial",
            "datos", "plan", "plan de trabajo", "comparar", "alternativas", "solucion",
            "tecnologia", "ingenieria", "flujo", "integracion", "arquitectura",
        ],
    },
    "agente_alejandra": {
        "autor": "Alejandra Ubilla",
        "especialidad": "auditoría de cumplimiento normativo y tributario (CMF y SII)",
        "descripcion": (
            "Audita empresas y fondos: cruza CMF y SII, revisa cumplimiento contable, "
            "concentración, liquidez, ratios y genera checklists de auditoría."
        ),
        "palabras_clave": [
            "auditoria", "auditar", "cumplimiento", "normativo", "normativa", "tributario",
            "tributaria", "impuesto", "impuestos", "sii", "cmf", "rut", "fondo", "fondos",
            "ratios", "liquidez", "concentracion", "contable", "regulacion", "legal",
        ],
    },
    "agente_soluciones_comerciales_marketing": {
        "autor": "Carlos Monroy",
        "especialidad": "ingeniería comercial y marketing",
        "descripcion": (
            "Analiza necesidades comerciales, verifica antecedentes documentales, "
            "compara alternativas y propone soluciones de marketing con pasos concretos."
        ),
        "palabras_clave": [
            "marketing", "comercial", "ventas", "cliente", "clientes", "campana",
            "publicidad", "producto", "propuesta", "mercado objetivo", "segmentacion",
            "precio", "promocion", "canal", "consumidor", "marca",
        ],
    },
}

ORDEN_POR_DEFECTO = tuple(CATALOGO_POR_DEFECTO)


def normalizar(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(letra for letra in descompuesto if not unicodedata.combining(letra))


def _contiene(texto: str, clave: str) -> bool:
    if len(clave) <= 4 and clave.isalpha():
        return re.search(rf"\b{re.escape(clave)}\b", texto) is not None
    return clave in texto


class Catalogo:
    def __init__(
        self,
        definiciones: dict[str, dict],
        agente_primario: str,
        max_agentes: int = 4,
    ) -> None:
        self._definiciones = definiciones
        self._primario = agente_primario
        self._max_agentes = max_agentes

    @classmethod
    def desde_settings(cls, settings: Settings) -> Catalogo:
        definiciones = {grafo: dict(datos) for grafo, datos in CATALOGO_POR_DEFECTO.items()}
        if settings.catalogo_json:
            try:
                personalizadas = json.loads(settings.catalogo_json)
            except json.JSONDecodeError as error:
                raise ConfiguracionInvalida("CATALOGO_AGENTES no es JSON válido.") from error
            if not isinstance(personalizadas, dict):
                raise ConfiguracionInvalida("CATALOGO_AGENTES debe ser un objeto JSON.")
            for grafo, datos in personalizadas.items():
                if not isinstance(datos, dict):
                    raise ConfiguracionInvalida(f"El agente {grafo} del catálogo debe ser un objeto.")
                actual = definiciones.setdefault(grafo, {})
                for campo in ("autor", "especialidad", "descripcion"):
                    if campo in datos and not isinstance(datos[campo], str):
                        raise ConfiguracionInvalida(
                            f"El campo {campo} de {grafo} debe ser texto."
                        )
                    if campo in datos:
                        actual[campo] = datos[campo]
                if "palabras_clave" in datos:
                    claves = datos["palabras_clave"]
                    if not isinstance(claves, list) or not all(isinstance(c, str) for c in claves):
                        raise ConfiguracionInvalida(
                            f"palabras_clave de {grafo} debe ser una lista de textos."
                        )
                    actual["palabras_clave"] = claves
        return cls(definiciones, settings.agente_primario, settings.max_agentes_por_consulta)

    def metadatos(self, grafo: str, remoto: AgenteRemoto | None = None) -> dict:
        base = self._definiciones.get(grafo, {})
        descripcion = base.get("descripcion") or (remoto.descripcion if remoto else "") or ""
        especialidad = base.get("especialidad") or (remoto.descripcion if remoto else "") or None
        return {
            "autor": base.get("autor"),
            "especialidad": especialidad,
            "descripcion": descripcion,
            "palabras_clave": base.get("palabras_clave", []),
        }

    def titulo(self, grafo: str, remoto: AgenteRemoto | None = None) -> str:
        autor = self.metadatos(grafo, remoto).get("autor")
        return f"{autor} · {grafo}" if autor else grafo

    def puntuar(self, mensaje: str, disponibles: list[str]) -> dict[str, int]:
        texto = normalizar(mensaje)
        puntajes: dict[str, int] = {}
        for grafo in disponibles:
            claves = [normalizar(clave) for clave in self.metadatos(grafo).get("palabras_clave", [])]
            puntajes[grafo] = sum(len(clave) for clave in claves if _contiene(texto, clave))
        return puntajes

    def elegir(
        self,
        mensaje: str,
        disponibles: list[str],
        modo: str,
        solicitados: list[str] | None,
    ) -> tuple[list[str], str]:
        if not disponibles:
            raise SolicitudInvalida("No hay agentes A2A disponibles para responder.")
        if solicitados:
            desconocidos = [agente for agente in solicitados if agente not in disponibles]
            if desconocidos:
                raise SolicitudInvalida(
                    "Alguno de los agentes solicitados no está disponible.",
                    [
                        f"No disponible: {', '.join(desconocidos)}.",
                        f"Disponibles: {', '.join(disponibles)}.",
                    ],
                )
            if modo == "individual" and len(solicitados) != 1:
                raise SolicitudInvalida("El modo individual necesita exactamente un agente.")
            if modo == "auto" and len(solicitados) > 1:
                raise SolicitudInvalida(
                    "Para consultar varios agentes usa el modo paralelo o colaborativo."
                )
            if len(solicitados) > self._max_agentes:
                raise SolicitudInvalida(
                    f"Se permiten como máximo {self._max_agentes} agentes por consulta."
                )
            return list(solicitados), "agentes indicados por la persona"

        puntajes = self.puntuar(mensaje, disponibles)
        orden = sorted(
            disponibles,
            key=lambda grafo: (
                -puntajes[grafo],
                0 if grafo == self._primario else 1,
                ORDEN_POR_DEFECTO.index(grafo) if grafo in ORDEN_POR_DEFECTO else 99,
                disponibles.index(grafo),
            ),
        )
        detalle = ", ".join(f"{grafo}={puntajes[grafo]}" for grafo in orden[:4])
        if modo in {"auto", "individual"}:
            return [orden[0]], f"mejor coincidencia ({detalle})"
        if modo == "paralelo":
            con_coincidencia = [grafo for grafo in orden if puntajes[grafo] > 0]
            seleccion = (con_coincidencia or orden)[: self._max_agentes]
            return seleccion, f"modo paralelo ({detalle})"
        con_coincidencia = [grafo for grafo in orden if puntajes[grafo] > 0]
        seleccion = (con_coincidencia or orden[:2])[:2]
        return seleccion, f"modo colaborativo ({detalle})"
