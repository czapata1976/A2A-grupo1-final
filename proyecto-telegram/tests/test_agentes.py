from __future__ import annotations

from pathlib import Path

from src.agentes import listar_agentes

RAIZ = Path(__file__).resolve().parents[1]
ESPERADOS = {
    "agente_general",
    "agente_czz",
    "agente_bryhan",
    "agente_alejandra",
    "agente_soluciones_comerciales_marketing",
}


def test_registro_de_agentes() -> None:
    assert set(listar_agentes()) == ESPERADOS


def test_estructura_de_cada_agente() -> None:
    for nombre in ESPERADOS:
        carpeta = RAIZ / "src" / nombre
        assert (carpeta / "graph.py").is_file()
        assert (carpeta / "prompts.py").is_file()
        assert (carpeta / "tools.py").is_file()


def test_prompts_fuera_de_graph() -> None:
    for nombre in ESPERADOS:
        graph = (RAIZ / "src" / nombre / "graph.py").read_text(encoding="utf-8")
        prompts = (RAIZ / "src" / nombre / "prompts.py").read_text(encoding="utf-8")
        tools = (RAIZ / "src" / nombre / "tools.py").read_text(encoding="utf-8")
        assert "SYSTEM_PROMPT =" not in graph
        assert "system_prompt=SYSTEM_PROMPT" in graph
        assert "SYSTEM_PROMPT" in prompts
        assert "HERRAMIENTAS" in tools
