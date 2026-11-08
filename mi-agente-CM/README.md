# Taller A2A · Grupo 1 · Agente de Carlos Monroy

**Grupo 1** · Integrantes: **Alejandra Ubilla, Carlos Monroy, Bryhan Cortes y Carlos Zapata.**
**Autor de este agente:** Carlos Monroy · grafo `agente_soluciones_comerciales_marketing`.
**Dónde corre:** `http://127.0.0.1:2025` (local) y, para el grupo, por un túnel de Cloudflare.

Este proyecto parte de `agente-viajes-a2a`. Se conserva el nombre del paquete `src/agente_viajes/`
(y la constante `SYSTEM_VIAJES`) para no romper los imports heredados; el agente es propio:
ingeniería comercial y marketing.

## Blueprint · Agente `agente_soluciones_comerciales_marketing`

El detalle está en `blueprint.md`. Resumen:

| Qué definir | Mi agente |
|-------------|-----------|
| Rol y alcance | **Qué hace:** responde consultas y propone soluciones fundamentadas en ingeniería comercial y marketing, con análisis, observación y verificación documental. **Qué no hace:** no aborda temas ajenos a lo consultado ni inventa información, experiencias o credenciales. |
| Herramientas | `consultar_mis_apuntes(tema)` — conceptos, criterios y un caso ficticio ilustrativo de marketing inmobiliario. No consulta internet ni documentos externos. |
| Autonomía | **Decide solo:** cómo organizar la respuesta, analizar antecedentes y presentar alternativas. **Requiere autorización** para enviar mensajes, publicar contenido, modificar documentos originales o asumir compromisos. |
| Cuándo pide ayuda | **Pregunta si falta** un dato indispensable, el objetivo es ambiguo o hay antecedentes contradictorios. **Deriva** a un especialista cuando la consulta exige una atribución profesional que excede sus capacidades. |
| Dónde se ejecuta | `http://127.0.0.1:2025` · grafo `agente_soluciones_comerciales_marketing` |

### Perfil

- **Nombre:** Agente_soluciones_comerciales_marketing
- **Especialidad:** ingeniería comercial y marketing, con trayectoria en el servicio público y privado.
- **Personalidad:** empático, directo y educado; analítico y abierto a distintas opciones.
- **Habilidades:** analizar antecedentes para identificar necesidades · explicar conceptos y procesos · comparar alternativas con criterios explícitos · verificar documentos y distinguir hechos de supuestos · proponer soluciones concretas con pasos de implementación.

## Cómo ejecutar

```powershell
cd mi-agente-CM
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env          # y pega tu GOOGLE_API_KEY
.venv\Scripts\langgraph.exe dev --port 2025
```

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:2025/assistants/search" -ContentType "application/json" -Body '{"graph_id":"agente_soluciones_comerciales_marketing"}'
Invoke-RestMethod "http://127.0.0.1:2025/.well-known/agent-card.json?assistant_id=<uuid>"
```

Después, `notebooks/a2a-test.ipynb` con un kernel que tenga `a2a-sdk` y `langchain-google-genai`
(`requirements-notebook.txt`), ejecutado de arriba abajo. La primera celda levanta el servidor si no
está disponible (`notebook_runtime.py`, con tope de 90 segundos).

> **Nota de entorno.** `a2a-sdk` sube `google-api-core`, que exige OpenTelemetry ≥ 1.44, mientras que
> `langgraph-api` fija ≤ 0.63b1. Por eso `requirements.txt` no incluye `a2a-sdk`: si se instala en el
> entorno del servidor, `langgraph dev` deja de arrancar.

## Etapas del taller

1. **Etapa 1 · diseño.** `prompts.py` (perfil y límites), `herramientas.py` (`consultar_mis_apuntes`),
   `graph.py` (`create_agent(..., name="agente_soluciones_comerciales_marketing")`) y `langgraph.json`.
2. **Etapa 2 · conexión.** `notebooks/a2a-test.ipynb`: personalidad, conocimientos/skills, memoria por
   `thread_id`, tarjeta A2A y envío `message/send`.
3. **Etapa 3 · conversación.** El mismo notebook descubre los dos servidores del grupo (2025 y 2026),
   escribe la ficha de cada tarjeta, levanta un supervisor que elige con quién conversar y resuelve el
   reto en tres turnos.

## Estructura

```
mi-agente-CM/
├── AGENTS.md · plan.json · langgraph.json · notebook_runtime.py · requirements.txt · .env.example
├── src/agente_viajes/   prompts.py · herramientas.py · graph.py
├── bruno/               tarjeta y message/send contra el puerto 2025
├── tests/               test_a2a_viajes.py (se salta si el servidor no está arriba)
└── notebooks/           a2a-test.ipynb (etapas 2 y 3)
```

El caso de los apuntes es ficticio e ilustrativo; no representa una experiencia real de la persona.
La entrega excluye `.env` y credenciales personales: cada integrante crea su `.env` desde `.env.example`.
