from __future__ import annotations

import main as cli


class GrafoFalso:
    def get_graph(self):
        return self

    def draw_mermaid(self) -> str:
        return "flowchart TD"

    def invoke(self, entrada: dict) -> dict:
        assert entrada["messages"][0]["content"] == "hola"
        return {"messages": [{"type": "ai", "content": "respuesta falsa"}]}

    def stream(self, entrada: dict, stream_mode: str = "updates"):
        assert stream_mode == "updates"
        yield {"modelo": {"messages": [{"type": "ai", "content": "respuesta falsa"}]}}


def test_ejecutar(monkeypatch) -> None:
    monkeypatch.setattr(cli, "obtener_agente", lambda nombre: GrafoFalso())
    assert cli.ejecutar("agente_general", "hola") == "respuesta falsa"


def test_ejecutar_con_saltos(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "obtener_agente", lambda nombre: GrafoFalso())
    assert cli.ejecutar("agente_general", "hola", saltos=True) == "respuesta falsa"
    assert "[nodo] modelo" in capsys.readouterr().out


def test_diagrama(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "solo-prueba")
    monkeypatch.setattr(cli, "obtener_agente", lambda nombre: GrafoFalso())
    assert cli.diagrama("agente_general") == "flowchart TD"
