## Blueprint · Agente `agente_czz` · Carlos Zapata

**Taller A2A · Grupo 1** — Alejandra Ubilla, Carlos Monroy, Bryhan Cortes y Carlos Zapata.

| Qué definir | Mi agente |
|---|---|
| Rol y alcance | **Hace:** consulta el precio y los datos de mercado de una acción y busca antecedentes en sus apuntes. **No hace:** pagos, ejecución de inversiones, ni asesoría tributaria o legal. |
| Herramientas | `consultar_mis_apuntes(tema)` — mis conceptos, criterios y un caso de mi especialidad. `consultar_acciones(ticker, pais)` — precio en moneda local y en CLP (tasa explícita), variación, volumen y rango de 52 semanas, con fecha de corte (datos simulados). |
| Autonomía | **Decide solo:** consultar acciones y mis apuntes sin aprobación previa. **Nunca sin una persona:** ejecutar pagos, compras, ventas o inversiones. |
| Cuándo pide ayuda | **Pregunta si falta:** el país (el mercado donde cotiza la acción) o el ticker. **Deriva a otro especialista cuando:** la consulta es tributaria o normativa. |
| Dónde se ejecuta | `http://127.0.0.1:2025` · grafo `agente_czz` |

### Del diseño al código
- **Rol y alcance** y **cuándo pide ayuda** → reglas del prompt (`src/agente_viajes/prompts.py`).
- **Herramientas** → lista `HERRAMIENTAS` (`src/agente_viajes/herramientas.py`).
- **Dónde se ejecuta** → `langgraph.json` y el puerto.
- **Rol + herramientas resumidos** → descripción de la tarjeta (etapa 3 del taller).
