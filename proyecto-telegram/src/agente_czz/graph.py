"""Ensamblado del grafo del agente de acciones."""

import os

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agente_czz.prompts import SYSTEM_PROMPT
from src.agente_czz.tools import HERRAMIENTAS


def construir_grafo():
    modelo = ChatGoogleGenerativeAI(
        model=os.environ.get("MODELO", "gemini-3.5-flash-lite"),
    )
    return create_agent(
        model=modelo,
        tools=HERRAMIENTAS,
        system_prompt=SYSTEM_PROMPT,
        name="agente_czz",
    )
