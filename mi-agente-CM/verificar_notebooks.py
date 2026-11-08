"""Ejecuta las celdas Python de los notebooks del proyecto, incluido `await` de nivel superior.

Uso:  python verificar_notebooks.py            (todos los notebooks de notebooks/)
      python verificar_notebooks.py a2a-test   (solo los que coincidan con el texto)

Necesita el servidor del puerto 2025 arriba y un entorno con a2a-sdk + langchain-google-genai
(requirements-notebook.txt).
"""
import ast
import asyncio
import json
import sys
from pathlib import Path


async def ejecutar(path: Path) -> None:
    namespace = {"__name__": "__main__"}
    print(f"NOTEBOOK {path.name}", flush=True)
    for index, cell in enumerate(json.loads(path.read_text(encoding="utf-8"))["cells"]):
        if cell["cell_type"] != "code":
            continue
        print(f"CELDA {index}", flush=True)
        code = compile("".join(cell["source"]), f"{path}:{index}", "exec",
                       flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        resultado = eval(code, namespace)
        if asyncio.iscoroutine(resultado):
            await resultado
    print("OK", path.name, flush=True)


async def main() -> None:
    raiz = Path(__file__).resolve().parent
    filtro = sys.argv[1] if len(sys.argv) > 1 else ""
    notebooks = sorted(p for p in (raiz / "notebooks").glob("*.ipynb") if filtro in p.name)
    if not notebooks:
        raise SystemExit(f"No hay notebooks en {raiz / 'notebooks'}")
    for path in notebooks:
        await ejecutar(path)


if __name__ == "__main__":
    asyncio.run(main())
