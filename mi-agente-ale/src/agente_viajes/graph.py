"""Agente auditor (antes: agente de viajes) · se expone por A2A de forma NATIVA con el servidor
de LangGraph.

No hay código de servidor aquí. `langgraph dev` (o un deploy de LangGraph Platform) lee
`langgraph.json`, levanta este grafo y publica automáticamente:
  · la Agent Card  →  GET  /.well-known/agent-card.json?assistant_id=agente_alejandra
  · el endpoint    →  POST /a2a/agente_alejandra   (message/send, message/stream, tasks/get, tasks/cancel)

Requisito único: el estado del grafo debe tener la clave `messages` (MessagesState la trae).
El `contextId` de A2A se convierte en `thread_id`: la memoria por conversación viene gratis.
"""
import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent

from src.agente_viajes.herramientas import HERRAMIENTAS
from src.agente_viajes.prompts import SYSTEM_VIAJES

load_dotenv()

modelo = ChatAnthropic(model=os.environ.get("MODELO", "claude-sonnet-5-5"))

# Agente ReAct (LangChain 1.x): el modelo decide qué herramienta llamar, la llama, lee el resultado y responde.
# Su estado tiene la clave `messages`: eso es lo único que A2A necesita para mapear sus `parts` de texto.
graph = create_agent(
    model=modelo,
    tools=HERRAMIENTAS,
    system_prompt=SYSTEM_VIAJES,
    name="agente_alejandra",
)
