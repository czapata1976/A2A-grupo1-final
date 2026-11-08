"""Pruebas del agente expuesto por A2A nativo. Requiere `langgraph dev` corriendo (puerto 2025)."""
import os, uuid, httpx, pytest

BASE = os.environ.get("A2A_VIAJES_URL", "http://127.0.0.1:2025")
GRAPH = os.environ.get("A2A_VIAJES_GRAPH", "agente_bryhan")


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
    assert card["name"] == GRAPH and card["url"].endswith(f"/a2a/{aid}")
    assert isinstance(card.get("skills"), list)


def test_message_send():
    cuerpo = {"jsonrpc": "2.0", "id": "1", "method": "message/send", "params": {"message": {
        "role": "user", "messageId": uuid.uuid4().hex, "contextId": str(uuid.uuid4()),
        "parts": [{"kind": "text", "text": "Preséntate brevemente y dime en qué puedes ayudarme."}]}}}
    r = httpx.post(f"{BASE}/a2a/{assistant_id()}", json=cuerpo, timeout=90).json()
    assert r["result"]["status"]["state"] == "completed"
    assert str(r["result"]).strip() != ""
