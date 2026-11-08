"""Genera notebooks/a2a-test.ipynb del proyecto de Carlos Monroy (etapas 2 y 3 del taller)."""
from pathlib import Path

import nbformat as nbf

raiz = Path(__file__).resolve().parent
nb = nbf.v4.new_notebook()
celdas = []


def md(texto):
    celdas.append(nbf.v4.new_markdown_cell(texto.strip("\n")))


def py(texto):
    celdas.append(nbf.v4.new_code_cell(texto.strip("\n")))


md("""
# Taller A2A · Agente de Carlos Monroy

Grafo `agente_soluciones_comerciales_marketing` (ingeniería comercial y marketing).

- **Etapa 2:** personalidad, conocimientos/skills, memoria por `thread_id`, tarjeta A2A y un envío real.
- **Etapa 3:** el supervisor descubre las dos tarjetas del grupo y elige con quién conversar cada turno.

La primera celda levanta `langgraph dev` en el puerto 2025 si el servidor no está arriba.
Necesita `GOOGLE_API_KEY` en `.env` y un kernel con `a2a-sdk` y `langchain-google-genai`.
""")

py("""
# ── CONFIGURACIÓN BASE ───────────────────────────────────────────────────
import sys
from pathlib import Path

# Funciona desde la raíz del proyecto o desde notebooks/.
carpeta = Path.cwd().resolve()
raiz = next((p for base in (carpeta, *carpeta.parents)
             if (p / "notebook_runtime.py").is_file()), None)
if raiz is None:
    raise RuntimeError("Abre el notebook dentro de mi-agente-CM.")
if str(raiz) not in sys.path:
    sys.path.insert(0, str(raiz))

from notebook_runtime import asegurar_servidor

A2A_URL = asegurar_servidor()
print(f"Servidor disponible: {A2A_URL}")

import json
import os

import httpx
from langgraph_sdk import get_client

A2A_VIAJES_URL = A2A_URL
A2A_VIAJES_GRAPH = os.environ["A2A_VIAJES_GRAPH"]
LANGGRAPH_URL = A2A_URL

# No enviamos claves de LangSmith al servidor local.
lg = get_client(url=LANGGRAPH_URL, api_key=None, timeout=120)


def mostrar(valor):
    print(json.dumps(valor, indent=2, ensure_ascii=False, default=str))


print(A2A_VIAJES_URL, A2A_VIAJES_GRAPH)
""")

md("# Encontrar el Id de tu agente")

py("""
# El servidor asigna un assistant_id (UUID) a cada grafo.
asistentes = await lg.assistants.search(limit=100, response_format="array")
for asistente in asistentes:
    print({
        "name": asistente.get("name"),
        "graph_id": asistente.get("graph_id"),
        "assistant_id": asistente.get("assistant_id"),
    })

propio = next((a for a in asistentes if a.get("graph_id") == A2A_VIAJES_GRAPH), None)
if propio is None:
    raise RuntimeError(f"El servidor no expone {A2A_VIAJES_GRAPH}. Revisa langgraph.json.")

ASSISTANT_ID = propio["assistant_id"]
print("ASSISTANT_ID:", ASSISTANT_ID)
""")

md("# Comunicación directa con el agente")

py("""
OUTPUT_KEY = None  # Ejemplo: "respuesta" si tu grafo no devuelve messages.


def crear_entrada(texto):
    return {"messages": [{"role": "human", "content": texto}]}


def extraer_texto(estado):
    if not isinstance(estado, dict):
        raise ValueError("La salida no es un diccionario; adapta extraer_texto a tu grafo.")
    if estado.get("__interrupt__"):
        raise RuntimeError("Tu grafo quedó pausado: resuelve el interrupt antes de responder.")
    if OUTPUT_KEY:
        contenido = estado[OUTPUT_KEY]
    else:
        mensajes = estado.get("messages", [])
        respuesta = next(
            (m for m in reversed(mensajes)
             if m.get("type", m.get("role")) in ("ai", "assistant")),
            None,
        )
        if respuesta is None:
            raise ValueError("No hay respuesta ai/assistant. Configura OUTPUT_KEY.")
        contenido = respuesta.get("content", "")
    if isinstance(contenido, list):
        contenido = "\\n".join(
            bloque if isinstance(bloque, str) else bloque.get("text", "")
            for bloque in contenido
            if isinstance(bloque, (str, dict))
        )
    if not isinstance(contenido, str) or not contenido.strip():
        raise ValueError("La salida no tiene texto. Adapta extraer_texto a tu agente.")
    return contenido


async def consultar_langgraph(texto, thread_id=None):
    estado = await lg.runs.wait(thread_id, ASSISTANT_ID, input=crear_entrada(texto))
    return extraer_texto(estado)
""")

py("""
# Verificación 1 · personalidad: nombre, especialidad y tono, sin inventar credenciales.
PREGUNTA = "Preséntate y cuéntame cómo me puedes ayudar."
estado = await lg.runs.wait(None, ASSISTANT_ID, input=crear_entrada(PREGUNTA))
print("\\nRespuesta:")
print(extraer_texto(estado))
""")

py("""
# Verificación 2 · conocimientos y skills: debe consultar los apuntes y aplicar una habilidad.
PREGUNTA_APUNTES = ("Usa el caso de tus apuntes y aplica una de tus habilidades para proponer "
                    "una solución.")
print(">", PREGUNTA_APUNTES, "\\n")
print(await consultar_langgraph(PREGUNTA_APUNTES))
""")

md("# Memoria")

py("""
# Verificación 3 · memoria: el mismo thread_id en los dos turnos.
thread = await lg.threads.create()
thread_id = thread["thread_id"]
print(await consultar_langgraph(
    "Mi objetivo para este taller es dejar el agente de soluciones comerciales funcionando por A2A.",
    thread_id=thread_id))
print()
print(await consultar_langgraph("¿Qué objetivo te acabo de contar?", thread_id=thread_id))
""")

md("""
# Etapa 2 · Agent2Agent

Se descarga la Agent Card del propio agente y se envía un mensaje real por JSON-RPC.
""")

py("""
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.types import Role, SendMessageRequest
from google.protobuf.json_format import MessageToDict

http_a2a = httpx.AsyncClient(timeout=120, trust_env=False)
resolver = A2ACardResolver(http_a2a, A2A_URL)
card_remota = await resolver.get_agent_card(
    http_kwargs={"params": {"assistant_id": ASSISTANT_ID}}
)
print("Ficha descargada:")
mostrar(MessageToDict(card_remota))

# El servidor anuncia protocolVersion 1.0 pero responde con el JSON de A2A 0.3:
# se fija 0.3.0 para que el cliente use el transporte compatible.
for interfaz in card_remota.supported_interfaces:
    interfaz.protocol_version = "0.3.0"

cliente_a2a = await create_client(
    card_remota,
    client_config=ClientConfig(
        httpx_client=http_a2a,
        streaming=False,
        supported_protocol_bindings=["JSONRPC"],
    ),
)
print("Cliente preparado con la Agent Card.")
""")

py("""
# Verificación 4 · un envío real por A2A (JSON-RPC).
from a2a.helpers import get_message_text, get_stream_response_text, new_text_message


async def enviar_a2a(cliente, texto, contexto=None):
    peticion = SendMessageRequest(message=new_text_message(
        texto, role=Role.ROLE_USER, context_id=contexto))
    partes = []
    async for evento in cliente.send_message(peticion):
        fragmento = get_stream_response_text(evento)
        if evento.HasField("task"):
            contexto = evento.task.context_id or contexto
            if not fragmento and evento.task.status.HasField("message"):
                fragmento = get_message_text(evento.task.status.message)
        elif evento.HasField("message"):
            contexto = evento.message.context_id or contexto
        if fragmento:
            partes.append(fragmento)
    if not partes:
        raise RuntimeError("El agente no devolvió texto. Revisa su terminal.")
    return "\\n".join(partes), contexto


respuesta_a2a, contexto_a2a = await enviar_a2a(
    cliente_a2a, "Usa el caso de tus apuntes y aplica una habilidad para proponer una solución.")
print(respuesta_a2a)
""")

md("""
# Etapa 3 · Dos agentes del grupo conversando por A2A

El reto del taller es **evaluar si conviene invertir**. Lo responden dos agentes de dos integrantes,
cada uno en su propio servidor. Un **supervisor** descubre las dos Agent Cards, elige quién responde
cada turno y envía el mensaje por A2A. Cada agente conserva su propio `contextId`, así recuerda lo
que ya conversó.

> Si el segundo servidor no está arriba, la etapa 3 avisa y se detiene ahí: la etapa 2 ya quedó probada.
""")

py("""
# ── 3.0 CONFIGURACIÓN ────────────────────────────────────────────────────
from typing import TypedDict
from uuid import uuid4

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

SERVIDORES = {
    "http://127.0.0.1:2025": "Carlos Monroy",
    "http://127.0.0.1:2026": "Compañero del grupo",
}
print("Servidores a descubrir:", list(SERVIDORES))

# La tarjeta es la carta de presentación: de ella depende que el supervisor elija bien.
FICHAS = {
    "agente_soluciones_comerciales_marketing": (
        "Agente de Carlos Monroy. Ingeniería comercial y marketing: analiza necesidades, "
        "verifica antecedentes documentales, compara alternativas y propone soluciones "
        "comerciales con pasos concretos."),
    "agente_czz": (
        "Agente de Carlos Zapata. Análisis de acciones e inversiones: precios de acciones de "
        "EE.UU. y Chile, criterios y apuntes de inversión."),
    "agente_bryhan": (
        "Agente de Bryhan Cortes. AI Engineering aplicado a procesos empresariales y "
        "financieros: analiza procesos, diseña soluciones de datos e IA y arma planes."),
    "agente_alejandra": (
        "Agente de Alejandra Ubilla. Auditoría de cumplimiento normativo y tributario "
        "(CMF y SII) de empresas y fondos de inversión."),
}
""")

py("""
# ── 3.1 DESCUBRIR LOS AGENTES Y PREPARAR UN CLIENTE A2A POR AGENTE ──────
AGENTES = {}  # nombre de la tarjeta -> cliente A2A, contexto propio y ficha

for base, autor in SERVIDORES.items():
    try:
        asistentes = httpx.post(f"{base}/assistants/search", json={"limit": 10},
                                timeout=30, trust_env=False).json()
    except Exception as error:
        print(f"[aviso] {base} no responde: {type(error).__name__}")
        continue
    for asistente in asistentes:
        graph_id = asistente["graph_id"]
        if graph_id in FICHAS:
            httpx.patch(f"{base}/assistants/{asistente['assistant_id']}",
                        json={"name": graph_id, "description": FICHAS[graph_id]},
                        timeout=30, trust_env=False)
        tarjeta = await A2ACardResolver(http_a2a, base).get_agent_card(
            http_kwargs={"params": {"assistant_id": asistente["assistant_id"]}})
        for interfaz in tarjeta.supported_interfaces:
            interfaz.protocol_version = "0.3.0"
            if interfaz.protocol_binding == "JSONRPC":
                interfaz.url = f"{base}/a2a/{asistente['assistant_id']}"
        cliente = await create_client(
            tarjeta,
            client_config=ClientConfig(httpx_client=http_a2a, streaming=False,
                                       supported_protocol_bindings=["JSONRPC"]),
        )
        AGENTES[tarjeta.name] = {
            "cliente": cliente,
            "contexto": str(uuid4()),
            "autor": autor,
            "descripcion": tarjeta.description,
            "url": tarjeta.supported_interfaces[0].url,
        }

print("Agentes A2A disponibles:", list(AGENTES))
for nombre, datos in AGENTES.items():
    print(f"  {nombre:<45} {datos['autor']:<18} {datos['url']}")
if len(AGENTES) < 2:
    raise RuntimeError("La etapa 3 necesita dos servidores arriba (2025 y 2026).")
""")

py("""
# ── 3.2 SUPERVISOR: ELIGE CON QUIÉN CONVERSAR ───────────────────────────
class Decision(BaseModel):
    agente: str = Field(description="Nombre exacto de uno de los agentes del catálogo")
    motivo: str = Field(description="Por qué ese agente responde mejor la consulta")


modelo_router = ChatGoogleGenerativeAI(model=os.environ.get("MODELO", "gemini-3.5-flash-lite"),
                                       temperature=0)
enrutador = modelo_router.with_structured_output(Decision)

PLANTILLA_ROUTER = '''Eres el supervisor de un grupo de agentes que conversan por A2A.
Elige UN agente del catálogo para responder la consulta del usuario.

Catálogo:
{catalogo}

Consulta del usuario:
<consulta>{consulta}</consulta>

Devuelve el nombre exacto del agente y un motivo breve.'''


def catalogo() -> str:
    return "\\n".join(
        f"- {nombre}: {datos['descripcion']} (representa a {datos['autor']})"
        for nombre, datos in AGENTES.items())


print(catalogo())
""")

py("""
# ── 3.3 NODOS: EL SUPERVISOR Y LA LLAMADA A2A AL AGENTE ELEGIDO ─────────
class EstadoReunion(TypedDict):
    consulta: str
    agente: str
    motivo: str
    respuesta_final: str


async def nodo_supervisor(estado: EstadoReunion) -> dict:
    decision = await enrutador.ainvoke(
        PLANTILLA_ROUTER.format(catalogo=catalogo(), consulta=estado["consulta"]))
    agente = decision.agente if decision.agente in AGENTES else next(iter(AGENTES))
    print(f"[supervisor] -> {agente} · {decision.motivo}")
    return {"agente": agente, "motivo": decision.motivo}


async def nodo_agente_remoto(estado: EstadoReunion) -> dict:
    datos = AGENTES[estado["agente"]]
    peticion = SendMessageRequest(
        message=new_text_message(estado["consulta"], context_id=datos["contexto"],
                                 role=Role.ROLE_USER))
    partes = []
    async for evento in datos["cliente"].send_message(peticion):
        texto = get_stream_response_text(evento)
        if not texto and evento.HasField("task") and evento.task.status.HasField("message"):
            texto = get_message_text(evento.task.status.message)
        if texto:
            partes.append(texto)
    respuesta = "\\n".join(partes) or "(el agente no devolvió texto)"
    print(f"[{estado['agente']}] respondió {len(respuesta)} caracteres")
    return {"respuesta_final": respuesta}


print("Nodos listos: supervisor y agente_remoto.")
""")

py("""
# ── 3.4 GRAFO DEL SUPERVISOR ────────────────────────────────────────────
def construir_reunion():
    flujo = StateGraph(EstadoReunion)
    flujo.add_node("supervisor", nodo_supervisor)
    flujo.add_node("agente_remoto", nodo_agente_remoto)
    flujo.add_edge(START, "supervisor")
    flujo.add_edge("supervisor", "agente_remoto")
    flujo.add_edge("agente_remoto", END)
    return flujo.compile()


reunion = construir_reunion()
print(reunion.get_graph().draw_mermaid())
""")

py("""
# ── 3.5 CONVERSACIÓN DE TRES TURNOS SOBRE EL RETO DEL TALLER ────────────
TURNOS = [
    "Reto del taller: evaluar si conviene invertir en Falabella. ¿Qué datos y qué criterios "
    "debería revisar antes de decidir?",
    "Soy estudiante y quiero automatizar ese análisis con IA: ¿cómo diseñaría el proceso y qué "
    "debería evitar?",
    "Con todo lo anterior, dame el criterio final: ¿cuándo conviene invertir y cuándo no?",
]

historial = []
for numero, consulta in enumerate(TURNOS, 1):
    print("=" * 78)
    print(f"TURNO {numero} · usuario: {consulta}")
    salida = await reunion.ainvoke(
        {"consulta": consulta, "agente": "", "motivo": "", "respuesta_final": ""})
    print(f"\\n[respuesta de {salida['agente']}]\\n{salida['respuesta_final']}\\n")
    historial.append(salida)

print("=" * 78)
print("Conversación cerrada. Un contextId por agente:",
      {nombre: datos["contexto"][:8] + "…" for nombre, datos in AGENTES.items()})
""")

md("""
## Cierre

Se liberan los clientes A2A y el cliente HTTP. Ejecutar esta celda al terminar.
""")

py("""
for datos in AGENTES.values():
    await datos["cliente"].close()
for nombre in ("cliente_a2a",):
    if nombre in globals():
        await globals()[nombre].close()
await http_a2a.aclose()
print("Conexiones cerradas.")
""")

nb.cells = celdas
nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
destino = raiz / "notebooks" / "a2a-test.ipynb"
nbf.write(nb, destino)
print(f"creado {destino}")
