from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.mensajes import crear_entrada, extraer_texto


def test_crear_entrada() -> None:
    assert crear_entrada("hola") == {
        "messages": [{"role": "user", "content": "hola"}]
    }


def test_extrae_texto_de_mensaje_dict() -> None:
    estado = {"messages": [{"type": "ai", "content": "respuesta"}]}
    assert extraer_texto(estado) == "respuesta"


def test_extrae_texto_de_bloques() -> None:
    estado = {
        "messages": [
            {"type": "ai", "content": [{"type": "text", "text": "uno"}, {"text": "dos"}]}
        ]
    }
    assert extraer_texto(estado) == "uno\ndos"


def test_extrae_texto_de_objeto() -> None:
    estado = {"messages": [SimpleNamespace(type="assistant", content="objeto")]}
    assert extraer_texto(estado) == "objeto"


def test_falla_sin_mensaje_ai() -> None:
    with pytest.raises(ValueError):
        extraer_texto({"messages": [{"type": "human", "content": "hola"}]})
