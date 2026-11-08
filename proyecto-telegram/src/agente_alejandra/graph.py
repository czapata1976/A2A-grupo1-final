"""Ensamblado del grafo del agente auditor."""

import os

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic

from src.agente_alejandra.prompts import SYSTEM_PROMPT
from src.agente_alejandra.tools import HERRAMIENTAS


def construir_grafo():
    modelo = ChatAnthropic(
        model=os.environ.get("MODELO_ANTHROPIC", "claude-sonnet-5-5"),
    )
    return create_agent(
        model=modelo,
        tools=HERRAMIENTAS,
        system_prompt=SYSTEM_PROMPT,
        name="agente_alejandra",
    )
