"""Resume resultados.json de promptfoo en una tabla Markdown legible."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ruta = Path(__file__).with_name("resultados.json")
datos = json.loads(ruta.read_text(encoding="utf-8"))
filas = datos["results"]["results"]

print("| # | Agente | Pregunta | Resultado | Aserciones | ms |")
print("| - | ------ | -------- | --------- | ---------- | -: |")
for i, fila in enumerate(filas, 1):
    caso = fila.get("testCase") or {}
    desc = (caso.get("description") or "").split(" · ")[0]
    agente = desc.replace("agente_", "agente_")
    agente = {
        "agente_czz": "czz",
        "agente_bryhan": "bryhan",
        "agente_alejandra": "alejandra",
        "agente_CM": "CM",
    }.get(desc, desc)
    pregunta = (fila.get("vars") or {}).get("pregunta", "")
    corta = pregunta if len(pregunta) <= 62 else pregunta[:59] + "…"
    estado = "PASS" if fila.get("success") else "FAIL"
    componentes = (fila.get("gradingResult") or {}).get("componentResults") or []
    marcas = []
    for comp in componentes:
        assert_ = comp.get("assertion") or {}
        tipo = assert_.get("type", "?")
        valor = assert_.get("value") or ""
        icono = "✅" if comp.get("pass") else "❌"
        etiqueta = tipo
        if tipo == "llm-rubric":
            etiqueta = f"rubric {comp.get('score', 0):.2f}"
            if not comp.get("pass"):
                etiqueta += f" (umbral {assert_.get('threshold')})"
        elif not comp.get("pass"):
            etiqueta = f"{tipo} '{valor}'"
        marcas.append(f"{icono} {etiqueta}")
    print(
        f"| {i} | {agente} | {corta} | **{estado}** | {' · '.join(marcas)} | "
        f"{fila.get('latencyMs', 0)} |"
    )

print()
print("=== DETALLE DE FALLOS ===")
for i, fila in enumerate(filas, 1):
    if fila.get("success"):
        continue
    caso = fila.get("testCase") or {}
    print(f"\n[{i}] {(caso.get('description') or '').strip()}")
    print(f"    Pregunta: {(fila.get('vars') or {}).get('pregunta', '')}")
    respuesta = (fila.get("response") or {}).get("output", "")
    print(f"    Respuesta: {' '.join(str(respuesta).split())[:600]}")
    for comp in (fila.get("gradingResult") or {}).get("componentResults") or []:
        if comp.get("pass"):
            continue
        assert_ = comp.get("assertion") or {}
        print(f"    ✗ {assert_.get('type')}: {comp.get('reason')}")
        if assert_.get("value") is not None:
            print(f"      esperado/umbral: {assert_.get('value')}")
        if comp.get("score") is not None:
            print(f"      score: {comp.get('score')}")
