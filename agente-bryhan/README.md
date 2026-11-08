# Agente Bryhan - Entregable 1

## Identificación

- Integrante: Bryhan Cortes
- Grupo: trabajo individual
- Curso: Certificado Agentic AI, UAI

## Aporte

Bryhan Cortes definió la personalidad, los conocimientos, las tres habilidades, las herramientas y la configuración del agente.

## Ejecución

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Completar GOOGLE_API_KEY en .env.
.venv\Scripts\langgraph.exe dev --port 2025
```

El grafo se llama `agente_bryhan` y queda disponible en `http://127.0.0.1:2025`.

El servidor permanece activo en la terminal hasta presionar `Ctrl+C`.

## Blueprint

El blueprint de la entrega se proporciona como `blueprint.md` en la raíz del paquete, fuera de esta carpeta.

## Notebook

- `notebooks/a2a-test.ipynb`: pruebas del agente y sección de conexión A2A.
