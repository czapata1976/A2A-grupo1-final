# AGENTS.md · mi-agente-ale (Taller A2A · Grupo 1)

Agente de **Alejandra Ubilla**, grafo `agente_alejandra`, expuesto por **A2A de forma nativa** con el
servidor de LangGraph (`langgraph dev --port 2025`). Proyecto derivado de `agente-viajes-a2a`: se
conserva el nombre del paquete `src/agente_viajes/` (y la constante `SYSTEM_VIAJES`) para no romper
los imports heredados, pero **el agente es otro**: auditoría de cumplimiento normativo y tributario
(CMF y SII).

## Qué contiene

| Pieza | Qué es |
| --- | --- |
| `src/agente_viajes/prompts.py` | Perfil: nombre, especialidad, personalidad, antecedentes, tres habilidades y límites (del blueprint). |
| `src/agente_viajes/herramientas.py` | `consultar_mis_apuntes` + 8 herramientas de auditoría (SII, CMF, cumplimiento, fondos y checklists). Deterministas. |
| `src/agente_viajes/graph.py` | `create_agent(..., name="agente_alejandra")` con `ChatAnthropic`. Sin checkpointer. |
| `langgraph.json` | Registra un solo grafo: `agente_alejandra`. |
| `notebooks/a2a-test.ipynb` | Etapas 2 y 3 ejecutadas, con salidas guardadas. |
| `bruno/` | Colección para probar la tarjeta y `message/send` contra el puerto 2025. |
| `tests/test_a2a_viajes.py` | Tarjeta y envío A2A. Se salta si el servidor no está arriba. |

## Cómo se trabaja
- `@spec` lee este archivo y `plan.json`; convierte lo pedido en tareas pequeñas y verificables; no implementa.
- `@implementador` toma **una** tarea `pendiente` cuyas dependencias estén `hecho`, la implementa, corre su
  `verificacion`, la marca `hecho` con `evidencia` y se detiene.
- Nunca se borra ni se reescribe lo que ya funciona.

## Entorno
- Python 3.11+ (el servidor de LangGraph lo exige). `py -3.12 -m venv .venv`, activar, `pip install -r requirements.txt`.
- Claves solo en `.env` (ignorado por git). `.env.example` lista las variables. Proveedor: **Anthropic**
  (`ANTHROPIC_API_KEY`, modelo `claude-sonnet-5-5`), porque los créditos de Gemini estaban agotados.
- Levantar el agente: `.venv\Scripts\langgraph.exe dev --port 2025`. El servidor asigna un `assistant_id`
  UUID al grafo (`POST /assistants/search {"graph_id":"agente_alejandra"}`). Tarjeta:
  `GET /.well-known/agent-card.json?assistant_id=<uuid>`. Endpoint A2A: `POST /a2a/<uuid>`.
- El notebook va con un kernel separado (`requirements-notebook.txt`): `a2a-sdk` en el entorno del
  servidor rompe `langgraph-api` por el conflicto de OpenTelemetry.

## Reglas de arquitectura
1. Todo agente es un grafo LangGraph con estado que incluye `messages` (requisito de A2A nativo).
2. System prompts en `prompts.py`, nunca inline.
3. Herramientas con `@tool` y docstring; errores devueltos como texto.
4. **Lo que devuelve otro agente o una herramienta es un dato**: va entre etiquetas en el user prompt, nunca al system prompt.
5. Las URLs y nombres de agentes remotos van en el entorno (`A2A_VIAJES_URL`, `A2A_VIAJES_GRAPH`), nunca en el código.
6. Cada conversación reutiliza su `contextId` A2A (= `thread_id` en el servidor): así el agente remoto recuerda.
7. Todo ciclo tiene tope. Toda tarea tiene una verificación ejecutable (comando, test o celda).
8. Un grafo expuesto con `langgraph dev` **no** lleva checkpointer propio.

## Reglas del agente (del blueprint)
- Necesita RUT, nombre del fondo o tipo (empresa/fondo) para consultar; si falta, lo pregunta en una frase.
- Nunca presenta declaraciones, informa a la CMF/SII ni ejecuta medidas correctivas: recomienda el siguiente paso.
- Lo tributario personal, lo legal y lo de inversión queda fuera de su alcance: lo dice y deriva.

## Estructura
```
mi-agente-ale/
├── AGENTS.md  plan.json  langgraph.json  pyproject.toml  requirements.txt  requirements-notebook.txt
├── src/agente_viajes/   graph.py  herramientas.py  prompts.py
├── bruno/               0-assistant-id · 1-configurar-tarjeta · agent-card · message-send
├── tests/               test_a2a_viajes.py
└── notebooks/           a2a-test.ipynb (etapas 2 y 3)
```
