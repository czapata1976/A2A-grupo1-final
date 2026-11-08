from __future__ import annotations

from app.a2a import AgenteRemoto, ResultadoEnvio

CLAVE = "clave-de-prueba-123"


def agente(grafo: str, base: str = "http://agente-1") -> AgenteRemoto:
    return AgenteRemoto(
        grafo=grafo,
        assistant_id=f"aid-{grafo}",
        base_url=base,
        nombre_tarjeta=grafo,
        descripcion=f"Descripción de {grafo}",
        habilidades=[f"habilidad-{grafo}"],
    )


AGENTES = {
    "agente_czz": agente("agente_czz", "http://agente-1"),
    "agente_bryhan": agente("agente_bryhan", "http://agente-2"),
    "agente_alejandra": agente("agente_alejandra", "http://agente-1"),
    "agente_soluciones_comerciales_marketing": agente(
        "agente_soluciones_comerciales_marketing", "http://agente-2"
    ),
}


class ClienteFalso:
    def __init__(
        self,
        agentes: dict[str, AgenteRemoto] | None = None,
        respuestas: dict[str, str] | None = None,
        errores: dict[str, Exception] | None = None,
        error_descubrimiento: Exception | None = None,
    ) -> None:
        self.agentes = agentes if agentes is not None else dict(AGENTES)
        self.respuestas = respuestas or {}
        self.errores = errores or {}
        self.error_descubrimiento = error_descubrimiento
        self.llamadas: list[dict] = []
        self.errores_descubrimiento: dict[str, str] = {}

    async def descubrir(self, forzar: bool = False) -> dict[str, AgenteRemoto]:
        if self.error_descubrimiento is not None:
            raise self.error_descubrimiento
        return dict(self.agentes)

    async def enviar(
        self,
        agente: AgenteRemoto,
        texto: str,
        context_id: str | None = None,
    ) -> ResultadoEnvio:
        self.llamadas.append(
            {"agente": agente.grafo, "texto": texto, "context_id": context_id}
        )
        error = self.errores.get(agente.grafo)
        if error is not None:
            raise error
        respuesta = self.respuestas.get(agente.grafo, f"Respuesta de {agente.grafo}")
        contexto = context_id or f"ctx-{agente.grafo}-{len(self.llamadas)}"
        return ResultadoEnvio(
            texto=respuesta,
            context_id=contexto,
            estado="completed",
            duracion_ms=12,
        )

    async def cerrar(self) -> None:
        return None
