"""API FastAPI protegida que orquesta los agentes A2A del Grupo 1."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, Path as FastPath, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.a2a import ClienteA2A
from app.auditoria import Auditor
from app.catalogo import Catalogo
from app.config import Settings, cargar_settings
from app.errores import ErrorServicio
from app.modelos import (
    AgenteInfo,
    ConsultaEntrada,
    ConsultaSalida,
    ListaAgentesSalida,
    PATRON_SESION,
    ReinicioSalida,
    SaludSalida,
)
from app.orquestador import Orquestador
from app.seguridad import ClienteAutenticado, LimitePeticiones, limitar
from app.sesiones import AlmacenSesiones
from app.telegram import router as telegram_router
from app.whatsapp import router as whatsapp_router

logger = logging.getLogger("servicio")
DIRECTORIO_ESTATICO = Path(__file__).resolve().parent / "static"


def _respuesta_error(
    status_code: int,
    codigo: str,
    mensaje: str,
    solicitud_id: str,
    detalles: list[str] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    contenido = {
        "error": {
            "codigo": codigo,
            "mensaje": mensaje,
            "solicitud_id": solicitud_id,
            "detalles": detalles or [],
        }
    }
    cabeceras = {"X-Request-ID": solicitud_id}
    if headers:
        cabeceras.update(headers)
    return JSONResponse(status_code=status_code, content=contenido, headers=cabeceras)


def crear_app(
    settings: Settings | None = None,
    cliente_a2a: ClienteA2A | None = None,
) -> FastAPI:
    settings = settings or cargar_settings()

    logging.basicConfig(
        level=settings.nivel_log,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger().setLevel(settings.nivel_log)

    catalogo = Catalogo.desde_settings(settings)
    sesiones = AlmacenSesiones(settings.ttl_sesion, settings.max_sesiones)
    limite = LimitePeticiones(settings.limite_por_minuto)
    auditor = Auditor(settings.ruta_auditoria)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        cliente = app.state.cliente or ClienteA2A(
            servidores=settings.servidores_a2a,
            timeout=settings.timeout_a2a,
            timeout_conexion=settings.timeout_conexion_a2a,
            ttl_cache=settings.ttl_cache_agentes,
            max_concurrencia=settings.max_concurrencia_a2a,
            confiar_en_proxy=settings.confiar_en_proxy,
        )
        app.state.cliente = cliente
        app.state.orquestador = Orquestador(settings, cliente, catalogo, sesiones, auditor)
        logger.info("Servicio iniciado: %s", settings.resumen())
        try:
            yield
        finally:
            await cliente.cerrar()
            logger.info("Servicio detenido.")

    app = FastAPI(
        title="Agentes A2A · Grupo 1",
        description=(
            "API protegida que descubre los agentes A2A del Grupo 1, consulta uno o varios "
            "y consolida sus aportes sin alterar cifras, unidades ni condiciones."
        ),
        version=settings.version,
        lifespan=lifespan,
        docs_url="/docs" if settings.docs_habilitados else None,
        openapi_url="/openapi.json" if settings.docs_habilitados else None,
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.cliente = cliente_a2a
    app.state.catalogo = catalogo
    app.state.sesiones = sesiones
    app.state.limite = limite
    app.state.auditor = auditor

    if settings.origenes_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.origenes_cors),
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "X-API-Key", "Authorization", "X-Request-ID"],
        )

    @app.middleware("http")
    async def contexto_peticion(request: Request, call_next):
        solicitud_id = uuid4().hex
        request.state.solicitud_id = solicitud_id
        inicio = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Error no controlado en %s %s", request.method, request.url.path)
            raise
        duracion_ms = int((time.perf_counter() - inicio) * 1000)
        response.headers["X-Request-ID"] = solicitud_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        ruta = request.url.path
        if ruta in {"/docs", "/openapi.json"}:
            pass
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
                "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
            )
        if (
            ruta == "/"
            or ruta.startswith("/v1/")
            or ruta.startswith("/whatsapp")
            or ruta == "/salud"
        ):
            response.headers["Cache-Control"] = "no-store"
        elif ruta.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=3600"
        logger.info(
            "%s %s -> %s (%d ms) solicitud_id=%s",
            request.method,
            ruta,
            response.status_code,
            duracion_ms,
            solicitud_id,
        )
        return response

    @app.exception_handler(ErrorServicio)
    async def manejar_error_servicio(request: Request, error: ErrorServicio) -> JSONResponse:
        solicitud_id = getattr(request.state, "solicitud_id", uuid4().hex)
        logger.warning(
            "Error de servicio solicitud_id=%s codigo=%s detalle=%s",
            solicitud_id,
            error.codigo,
            error.mensaje,
        )
        return _respuesta_error(
            error.status_code,
            error.codigo,
            error.mensaje,
            solicitud_id,
            error.detalles,
        )

    @app.exception_handler(RequestValidationError)
    async def manejar_validacion(request: Request, error: RequestValidationError) -> JSONResponse:
        solicitud_id = getattr(request.state, "solicitud_id", uuid4().hex)
        detalles = []
        for item in error.errors():
            ubicacion = ".".join(str(parte) for parte in item.get("loc", ()) if parte != "body")
            detalles.append(f"{ubicacion or 'cuerpo'}: {item.get('msg', 'valor inválido')}")
        return _respuesta_error(
            422,
            "ENTRADA_INVALIDA",
            "La solicitud no cumple el formato esperado. Revisa los campos indicados.",
            solicitud_id,
            detalles,
        )

    @app.exception_handler(StarletteHTTPException)
    async def manejar_http(request: Request, error: StarletteHTTPException) -> JSONResponse:
        solicitud_id = getattr(request.state, "solicitud_id", uuid4().hex)
        codigos = {
            400: "ENTRADA_INVALIDA",
            401: "NO_AUTORIZADO",
            403: "PROHIBIDO",
            404: "NO_ENCONTRADO",
            405: "METODO_NO_PERMITIDO",
            429: "LIMITE_ALCANZADO",
        }
        mensajes = {
            400: "El cuerpo de la solicitud no es JSON válido o está mal codificado.",
            404: "La ruta solicitada no existe.",
            405: "El método no está permitido para esta ruta.",
        }
        return _respuesta_error(
            error.status_code,
            codigos.get(error.status_code, "ERROR_HTTP"),
            mensajes.get(error.status_code, str(error.detail)),
            solicitud_id,
            headers=dict(error.headers or {}),
        )

    @app.exception_handler(Exception)
    async def manejar_inesperado(request: Request, error: Exception) -> JSONResponse:
        solicitud_id = getattr(request.state, "solicitud_id", uuid4().hex)
        logger.exception("Error inesperado solicitud_id=%s", solicitud_id)
        return _respuesta_error(
            500,
            "ERROR_INTERNO",
            "Ocurrió un error interno. Usa el solicitud_id para revisar el registro.",
            solicitud_id,
        )

    @app.get("/", include_in_schema=False)
    async def inicio() -> FileResponse:
        return FileResponse(
            DIRECTORIO_ESTATICO / "index.html",
            media_type="text/html",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/salud", response_model=SaludSalida, tags=["servicio"])
    async def salud() -> SaludSalida:
        return SaludSalida(
            estado="ok",
            servicio="agentes-a2a-grupo-1",
            version=settings.version,
            hora=datetime.now(timezone.utc).isoformat(),
        )

    @app.get("/v1/agentes", response_model=ListaAgentesSalida, tags=["agentes"])
    async def listar_agentes(
        request: Request,
        autenticado: ClienteAutenticado = Depends(limitar),
    ) -> ListaAgentesSalida:
        cliente: ClienteA2A = request.app.state.cliente
        remotos = await cliente.descubrir()
        agentes: list[AgenteInfo] = []
        for grafo, remoto in remotos.items():
            metadatos = catalogo.metadatos(grafo, remoto)
            agentes.append(
                AgenteInfo(
                    grafo=grafo,
                    autor=metadatos.get("autor"),
                    especialidad=metadatos.get("especialidad"),
                    descripcion=metadatos.get("descripcion"),
                    habilidades=remoto.habilidades,
                    disponible=True,
                )
            )
        errores = [
            f"{servidor}: {motivo}"
            for servidor, motivo in cliente.errores_descubrimiento.items()
        ]
        return ListaAgentesSalida(agentes=agentes, errores=errores, total=len(agentes))

    @app.post("/v1/consultas", response_model=ConsultaSalida, tags=["consultas"])
    async def consultar(
        request: Request,
        entrada: ConsultaEntrada,
        autenticado: ClienteAutenticado = Depends(limitar),
    ) -> ConsultaSalida:
        orquestador: Orquestador = request.app.state.orquestador
        solicitud_id = getattr(request.state, "solicitud_id", uuid4().hex)
        return await orquestador.consultar(entrada, solicitud_id, autenticado.huella)

    @app.delete(
        "/v1/sesiones/{session_id}",
        response_model=ReinicioSalida,
        tags=["sesiones"],
    )
    async def reiniciar_sesion(
        request: Request,
        session_id: str = FastPath(pattern=PATRON_SESION.pattern),
        autenticado: ClienteAutenticado = Depends(limitar),
    ) -> ReinicioSalida:
        sesiones: AlmacenSesiones = request.app.state.sesiones
        await sesiones.limpiar(f"{autenticado.huella}:{session_id}")
        return ReinicioSalida(session_id=session_id, estado="reiniciada")

    app.include_router(telegram_router)
    app.include_router(whatsapp_router)

    app.mount("/static", StaticFiles(directory=DIRECTORIO_ESTATICO), name="static")
    return app
