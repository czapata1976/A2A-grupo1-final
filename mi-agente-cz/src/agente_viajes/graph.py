"""Grafo del agente de Carlos Zapata · Taller A2A · Grupo 1.

Conserva los imports y la configuración del modelo del proyecto original; lo único propio es el
`name` del agente, que debe ser único dentro del grupo (`agente_alejandra`, `agente_bryhan`, ...).
"""
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agente_viajes.herramientas import HERRAMIENTAS
from src.agente_viajes.prompts import SYSTEM_VIAJES

load_dotenv()

modelo = ChatGoogleGenerativeAI(model=os.environ.get("MODELO", "gemini-3.5-flash-lite"))

graph = create_agent(
    model=modelo,
    tools=HERRAMIENTAS,
    system_prompt=SYSTEM_VIAJES,
    name="agente_czz",
)
