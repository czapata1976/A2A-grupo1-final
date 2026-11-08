"""Pruebas del agente agente_czz expuesto por A2A nativo.

Requiere `langgraph dev --port 2025` corriendo. Si no hay servidor, las pruebas se saltan.
"""
import os
import uuid

import httpx
import pytest

BASE = os.environ.get("A2A_VIAJES_URL", "http://127.0.0.1:2025")
GRAPH = os.environ.get("A2A_VIAJES_GRAPH", "agente_czz")


def assistant_id() -> str:
    """El servidor identifica cada grafo con un assistant_id UUID; se obtiene buscando por graph_id."""
    r = httpx.post(f"{BASE}/assistants/search", json={"graph_id": GRAPH}, timeout=10).json()
    return r[0]["assistant_id"]


def _servidor_arriba():
    try:
        return httpx.get(f"{BASE}/ok", timeout=3).status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _servidor_arriba(), reason="langgraph dev no está corriendo")


def test_agent_card():
    aid = assistant_id()
    card = httpx.get(f"{BASE}/.well-known/agent-card.json", params={"assistant_id": aid}, timeout=10).json()
    assert card["name"] == GRAPH
    assert card["url"].endswith(f"/a2a/{aid}")
    assert isinstance(card.get("skills"), list)


def test_message_send():
    cuerpo = {"jsonrpc": "2.0", "id": "1", "method": "message/send", "params": {"message": {
        "role": "user", "messageId": uuid.uuid4().hex, "contextId": str(uuid.uuid4()),
        "parts": [{"kind": "text", "text": "¿Cuánto vale AAPL en el mercado US?"}]}}}
    r = httpx.post(f"{BASE}/a2a/{assistant_id()}", json=cuerpo, timeout=90).json()
    assert r["result"]["status"]["state"] == "completed"
    # El agente debe traer el precio simulado de la herramienta consultar_acciones (342,10 USD).
    assert "342" in str(r["result"])
