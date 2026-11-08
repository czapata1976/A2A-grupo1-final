"""Grafo del agente de Carlos Zapata · Taller A2A · Grupo 1.

Asesor experto en acciones: prompt con método explícito y herramientas deterministas
(`consultar_acciones` y `consultar_mis_apuntes`). El `name` debe ser único dentro del grupo.
"""
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agente_viajes.herramientas import HERRAMIENTAS
from src.agente_viajes.prompts import SYSTEM_AGENTE

load_dotenv()

modelo = ChatGoogleGenerativeAI(model=os.environ.get("MODELO", "gemini-3.5-flash-lite"))

graph = create_agent(
    model=modelo,
    tools=HERRAMIENTAS,
    system_prompt=SYSTEM_AGENTE,
    name="agente_czz",
)
