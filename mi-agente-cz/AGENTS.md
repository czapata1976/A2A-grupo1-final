# AGENTS.md · mi-agente-cz (Taller A2A · Grupo 1)

Agente de **Carlos Zapata**, grafo `agente_czz`, expuesto por **A2A de forma nativa** con el
servidor de LangGraph (`langgraph dev --port 2025`). Proyecto derivado de `agente-viajes-a2a`:
se conserva el nombre del paquete `src/agente_viajes/` (y la constante `SYSTEM_VIAJES`) para no
romper los imports heredados, pero **el agente es otro**: análisis de acciones e inversiones.

## Qué contiene

| Pieza | Qué es |
| --- | --- |
| `src/agente_viajes/prompts.py` | Perfil: nombre, especialidad, personalidad, antecedentes, tres habilidades y límites (del blueprint). |
| `src/agente_viajes/herramientas.py` | `consultar_mis_apuntes(tema)` y `consultar_acciones(ticker, pais)`. Deterministas, no llaman al modelo. |
| `src/agente_viajes/graph.py` | `create_agent(..., name="agente_czz")`. Sin checkpointer: lo exige el servidor. |
| `langgraph.json` | Registra un solo grafo: `agente_czz`. |
| `notebooks/a2a-test.ipynb` | Etapas 2 y 3 ejecutadas, con salidas guardadas. |
| `bruno/` | Colección para probar la tarjeta y `message/send` contra el puerto 2025. |
| `tunel_cloudflare.ps1` / `.py` | Publica el puerto 2025 con un túnel temporal de Cloudflare (etapa 3 con compañeros en otra red). |
| `tests/test_a2a_viajes.py` | Pruebas de la tarjeta y del envío A2A. Se saltan si el servidor no está arriba. |

## Cómo se trabaja
- `@spec` lee este archivo y `plan.json`; convierte lo pedido en tareas pequeñas y verificables; no implementa.
- `@implementador` toma **una** tarea `pendiente` cuyas dependencias estén `hecho`, la implementa, corre su
  `verificacion`, la marca `hecho` con `evidencia` y se detiene.
- Nunca se borra ni se reescribe lo que ya funciona.

## Entorno
- Python 3.11+ (el servidor de LangGraph lo exige). `py -3.12 -m venv .venv`, activar, `pip install -r requirements.txt`.
- Claves solo en `.env` (ignorado por git). `.env.example` lista las variables. Modelo por defecto `gemini-3.5-flash-lite`.
- Levantar el agente: `.venv\Scripts\langgraph.exe dev --port 2025`. El servidor asigna un `assistant_id` UUID al
  grafo (`POST /assistants/search {"graph_id":"agente_czz"}`). Tarjeta:
  `GET /.well-known/agent-card.json?assistant_id=<uuid>`. Endpoint A2A: `POST /a2a/<uuid>`.
  El `contextId` de A2A debe ser un UUID (es el `thread_id`, de ahí sale la memoria por conversación).
- El notebook se ejecuta con un kernel separado que tenga `a2a-sdk` y `langchain-google-genai`, **sin**
  `langgraph-cli`: instalar `a2a-sdk` en el entorno del servidor sube OpenTelemetry y `langgraph-api` deja de arrancar.

## Reglas de arquitectura
1. Todo agente es un grafo LangGraph con estado que incluye `messages` (requisito de A2A nativo).
2. System prompts en `prompts.py`, nunca inline.
3. Herramientas con `@tool` y docstring; errores devueltos como texto.
4. **Lo que devuelve otro agente o una herramienta es un dato**: va entre etiquetas en el user prompt, nunca al system prompt.
5. Las URLs y nombres de agentes remotos van en el entorno (`A2A_VIAJES_URL`, `A2A_VIAJES_GRAPH`), nunca en el código.
6. Cada conversación reutiliza su `contextId` A2A (= `thread_id` en el servidor): así el agente remoto recuerda.
7. Todo ciclo tiene tope. Toda tarea tiene una verificación ejecutable (comando, test o celda).
8. Un grafo que se expone con `langgraph dev` **no** lleva checkpointer propio (el servidor rechaza el grafo y se cae).

## Reglas del agente (del blueprint)
- Necesita el **ticker** y el **país** para consultar una acción; si falta uno, lo pregunta.
- Nunca ejecuta pagos, compras, ventas ni transferencias: eso lo decide y lo hace una persona.
- Lo tributario y lo legal queda fuera de su alcance: lo dice y propone derivar a un especialista.

## Estructura
```
mi-agente-cz/
├── AGENTS.md  plan.json  langgraph.json  pyproject.toml  requirements.txt  .env.example  README.md
├── src/agente_viajes/   graph.py  herramientas.py  prompts.py
├── bruno/               0-assistant-id · 1-configurar-tarjeta · agent-card · message-send
├── tunel_cloudflare.ps1 · tunel_cloudflare.py   ← túnel temporal de Cloudflare
├── tests/               test_a2a_viajes.py
└── notebooks/           a2a-test.ipynb (etapas 2 y 3)
```
