"""Cliente A2A por JSON-RPC, sin depender de a2a-sdk."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

ESTADOS_ERROR_TEXTO = {
    "failed",
    "failure",
    "canceled",
    "cancelled",
    "rejected",
    "error",
    "task_state_failed",
    "task_state_canceled",
    "task_state_rejected",
}
ESTADOS_ERROR_NUMERO = {4, 5, 7}


class ErrorA2A(RuntimeError):
    """Error al comunicarse con un agente remoto."""

    codigo = "ERROR_A2A"

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class ErrorConexionA2A(ErrorA2A):
    codigo = "AGENTE_INALCANZABLE"


class ErrorTiempoA2A(ErrorA2A):
    codigo = "AGENTE_TIEMPO_AGOTADO"


class ErrorRespuestaA2A(ErrorA2A):
    codigo = "AGENTE_RESPUESTA_INVALIDA"


class ErrorAgenteNoDisponible(ErrorA2A):
    codigo = "AGENTE_NO_DISPONIBLE"


@dataclass
class AgenteRemoto:
    grafo: str
    assistant_id: str
    base_url: str
    nombre_tarjeta: str
    descripcion: str = ""
    habilidades: list[str] = field(default_factory=list)


@dataclass
class ResultadoEnvio:
    texto: str
    context_id: str | None
    estado: str | None
    duracion_ms: int


class ClienteA2A:
    def __init__(
        self,
        servidores: tuple[str, ...],
        timeout: float = 120.0,
        timeout_conexion: float = 5.0,
        ttl_cache: float = 30.0,
        max_concurrencia: int = 4,
        confiar_en_proxy: bool = False,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.servidores = servidores
        self.timeout = timeout
        self.timeout_conexion = timeout_conexion
        self.ttl_cache = ttl_cache
        self.errores_descubrimiento: dict[str, str] = {}
        self._http = http_client or httpx.AsyncClient(
            follow_redirects=True,
            trust_env=confiar_en_proxy,
        )
        self._propio = http_client is None
        self._semaforo = asyncio.Semaphore(max_concurrencia)
        self._lock_descubrimiento = asyncio.Lock()
        self._cache: dict[str, AgenteRemoto] = {}
        self._cache_ts = 0.0

    async def descubrir(self, forzar: bool = False) -> dict[str, AgenteRemoto]:
        async with self._lock_descubrimiento:
            if (
                not forzar
                and self._cache
                and (time.monotonic() - self._cache_ts) < self.ttl_cache
            ):
                return dict(self._cache)

            agentes: dict[str, AgenteRemoto] = {}
            errores: dict[str, str] = {}
            for base in self.servidores:
                try:
                    respuesta = await self._http.post(
                        f"{base}/assistants/search",
                        json={"limit": 100},
                        timeout=httpx.Timeout(self.timeout_conexion),
                    )
                    respuesta.raise_for_status()
                    asistentes = respuesta.json()
                except httpx.ConnectError:
                    errores[base] = "servidor inaccesible (¿está levantado?)"
                    logger.warning("Descubrimiento: no se pudo conectar con %s", base)
                    continue
                except httpx.TimeoutException:
                    errores[base] = "tiempo de conexión agotado"
                    logger.warning("Descubrimiento: %s no respondió a tiempo", base)
                    continue
                except httpx.HTTPError as error:
                    errores[base] = f"error HTTP ({type(error).__name__})"
                    logger.warning("Descubrimiento: %s no respondió (%s)", base, type(error).__name__)
                    continue
                except ValueError:
                    errores[base] = "respuesta JSON inválida"
                    logger.warning("Descubrimiento: %s devolvió JSON inválido", base)
                    continue

                if isinstance(asistentes, dict):
                    asistentes = (
                        asistentes.get("assistants")
                        or asistentes.get("data")
                        or asistentes.get("items")
                        or []
                    )
                if not isinstance(asistentes, list):
                    errores[base] = "formato de asistentes inesperado"
                    continue

                for asistente in asistentes:
                    if not isinstance(asistente, dict):
                        continue
                    grafo = asistente.get("graph_id") or asistente.get("name")
                    assistant_id = asistente.get("assistant_id")
                    if not grafo or not assistant_id:
                        continue
                    if grafo in agentes:
                        errores[f"{base}:{grafo}"] = "grafo repetido; se conserva el primero"
                        continue
                    tarjeta = await self._leer_tarjeta(base, str(assistant_id), grafo)
                    nombre = tarjeta.get("name") or grafo
                    descripcion = tarjeta.get("description") or ""
                    habilidades: list[str] = []
                    for habilidad in tarjeta.get("skills") or []:
                        if isinstance(habilidad, dict):
                            nombre_habilidad = habilidad.get("name") or habilidad.get("id")
                            if nombre_habilidad:
                                habilidades.append(str(nombre_habilidad))
                    agentes[grafo] = AgenteRemoto(
                        grafo=grafo,
                        assistant_id=str(assistant_id),
                        base_url=base,
                        nombre_tarjeta=str(nombre),
                        descripcion=str(descripcion),
                        habilidades=habilidades,
                    )

            self._cache = agentes
            self._cache_ts = time.monotonic()
            self.errores_descubrimiento = errores
            return dict(agentes)

    async def _leer_tarjeta(self, base: str, assistant_id: str, grafo: str) -> dict:
        try:
            respuesta = await self._http.get(
                f"{base}/.well-known/agent-card.json",
                params={"assistant_id": assistant_id},
                timeout=httpx.Timeout(self.timeout_conexion),
            )
            respuesta.raise_for_status()
            tarjeta = respuesta.json()
            return tarjeta if isinstance(tarjeta, dict) else {}
        except (httpx.HTTPError, ValueError) as error:
            self.errores_descubrimiento[f"{base}:{grafo}:tarjeta"] = type(error).__name__
            logger.warning("No se pudo leer la tarjeta de %s en %s", grafo, base)
            return {}

    async def enviar(
        self,
        agente: AgenteRemoto,
        texto: str,
        context_id: str | None = None,
    ) -> ResultadoEnvio:
        mensaje: dict = {
            "role": "user",
            "messageId": uuid.uuid4().hex,
            "parts": [{"kind": "text", "text": texto}],
        }
        if context_id:
            mensaje["contextId"] = context_id
        payload = {
            "jsonrpc": "2.0",
            "id": uuid.uuid4().hex,
            "method": "message/send",
            "params": {"message": mensaje},
        }

        inicio = time.perf_counter()
        async with self._semaforo:
            try:
                respuesta = await self._http.post(
                    f"{agente.base_url}/a2a/{agente.assistant_id}",
                    json=payload,
                    timeout=httpx.Timeout(self.timeout, connect=self.timeout_conexion),
                )
            except httpx.TimeoutException as error:
                raise ErrorTiempoA2A(
                    f"El agente {agente.grafo} agotó el tiempo de espera ({self.timeout:.0f}s)."
                ) from error
            except httpx.HTTPError as error:
                raise ErrorConexionA2A(
                    f"No se pudo conectar con el agente {agente.grafo}."
                ) from error

        duracion_ms = int((time.perf_counter() - inicio) * 1000)
        if respuesta.status_code == 404:
            raise ErrorAgenteNoDisponible(
                f"El agente {agente.grafo} no está expuesto en {agente.base_url}. "
                "Revisa que el servidor siga arriba y vuelve a intentarlo."
            )
        if respuesta.status_code in {401, 403}:
            raise ErrorRespuestaA2A(
                f"El agente {agente.grafo} rechazó la solicitud (HTTP {respuesta.status_code})."
            )
        if respuesta.status_code == 429:
            raise ErrorRespuestaA2A(
                f"El agente {agente.grafo} está limitando solicitudes (HTTP 429)."
            )
        if respuesta.status_code >= 500:
            raise ErrorRespuestaA2A(
                f"El agente {agente.grafo} falló (HTTP {respuesta.status_code})."
            )
        if respuesta.status_code >= 400:
            raise ErrorRespuestaA2A(
                f"El agente {agente.grafo} rechazó la solicitud (HTTP {respuesta.status_code})."
            )

        try:
            datos = respuesta.json()
        except ValueError as error:
            raise ErrorRespuestaA2A(
                f"El agente {agente.grafo} devolvió una respuesta que no es JSON."
            ) from error
        if not isinstance(datos, dict):
            raise ErrorRespuestaA2A(f"El agente {agente.grafo} devolvió un JSON inesperado.")

        error_a2a = datos.get("error")
        if error_a2a:
            if isinstance(error_a2a, dict):
                codigo = error_a2a.get("code", "sin código")
                detalle = str(error_a2a.get("message", ""))[:300]
            else:
                codigo = "sin código"
                detalle = str(error_a2a)[:300]
            raise ErrorRespuestaA2A(
                f"El agente {agente.grafo} devolvió un error A2A ({codigo}): {detalle}"
            )

        resultado = datos.get("result")
        if not isinstance(resultado, dict):
            raise ErrorRespuestaA2A(
                f"El agente {agente.grafo} no devolvió un resultado A2A válido."
            )

        estado_objeto = resultado.get("status")
        estado = estado_objeto.get("state") if isinstance(estado_objeto, dict) else None
        if isinstance(estado, str) and estado.lower() in ESTADOS_ERROR_TEXTO:
            raise ErrorRespuestaA2A(
                f"El agente {agente.grafo} no completó la tarea (estado: {estado})."
            )
        if isinstance(estado, int) and estado in ESTADOS_ERROR_NUMERO:
            raise ErrorRespuestaA2A(
                f"El agente {agente.grafo} no completó la tarea (estado: {estado})."
            )

        texto_respuesta = _extraer_texto(resultado)
        if not texto_respuesta:
            raise ErrorRespuestaA2A(
                f"El agente {agente.grafo} no devolvió texto. Revisa la terminal del servidor."
            )

        contexto = (
            resultado.get("contextId")
            or resultado.get("context_id")
            or context_id
        )
        return ResultadoEnvio(
            texto=texto_respuesta,
            context_id=str(contexto) if contexto else None,
            estado=str(estado) if estado is not None else None,
            duracion_ms=duracion_ms,
        )

    async def cerrar(self) -> None:
        if self._propio:
            await self._http.aclose()


def _textos_de(objeto: dict | None) -> list[str]:
    if not isinstance(objeto, dict):
        return []
    partes = objeto.get("parts")
    if not isinstance(partes, list):
        contenido = objeto.get("content")
        if isinstance(contenido, str) and contenido.strip():
            return [contenido.strip()]
        if isinstance(contenido, list):
            partes = contenido
        else:
            return []
    textos: list[str] = []
    for parte in partes:
        if isinstance(parte, str):
            if parte.strip():
                textos.append(parte.strip())
        elif isinstance(parte, dict):
            texto = parte.get("text")
            if isinstance(texto, str) and texto.strip():
                textos.append(texto.strip())
    return textos


def _extraer_texto(resultado: dict) -> str:
    partes: list[str] = []
    if resultado.get("kind") == "message":
        partes.extend(_textos_de(resultado))
    estado = resultado.get("status") or {}
    if isinstance(estado, dict):
        partes.extend(_textos_de(estado.get("message")))
    for artefacto in resultado.get("artifacts") or []:
        partes.extend(_textos_de(artefacto))
    if not partes:
        historial = resultado.get("history") or []
        if isinstance(historial, list):
            for mensaje in reversed(historial):
                if not isinstance(mensaje, dict):
                    continue
                rol = str(mensaje.get("role", mensaje.get("type", ""))).lower()
                if rol in {"agent", "assistant", "model", "ai"}:
                    partes.extend(_textos_de(mensaje))
                    if partes:
                        break
    vistos: set[str] = set()
    limpios: list[str] = []
    for texto in partes:
        if texto not in vistos:
            vistos.add(texto)
            limpios.append(texto)
    return "\n".join(limpios).strip()
