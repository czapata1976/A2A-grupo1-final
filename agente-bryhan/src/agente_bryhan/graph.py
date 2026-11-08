"""Agente de Bryhan expuesto por A2A nativo con el servidor de LangGraph.

`langgraph dev` lee langgraph.json, levanta este grafo y publica:
  - Agent Card  ->  GET  /.well-known/agent-card.json?assistant_id=<uuid>
  - Endpoint    ->  POST /a2a/<uuid>
"""
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agente_bryhan.herramientas import HERRAMIENTAS
from src.agente_bryhan.prompts import SYSTEM_PROMPT

load_dotenv()

modelo = ChatGoogleGenerativeAI(model=os.environ.get("MODELO", "gemini-3.5-flash-lite"))

graph = create_agent(
    model=modelo,
    tools=HERRAMIENTAS,
    system_prompt=SYSTEM_PROMPT,
    name="agente_bryhan",
)
