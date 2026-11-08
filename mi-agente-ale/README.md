# Taller A2A · Grupo 1 · Agente de Alejandra Ubilla

**Grupo 1** · Integrantes: **Alejandra Ubilla, Carlos Monroy, Bryhan Cortes y Carlos Zapata.**
**Autora de este agente:** Alejandra Ubilla · grafo `agente_alejandra`.
**Dónde corre:** `http://127.0.0.1:2025` (local) y, para el grupo, por un túnel de Cloudflare.

Este proyecto parte de `agente-viajes-a2a` y lo transforma en un agente auditor. Se conserva el nombre
del paquete `src/agente_viajes/` (y la constante `SYSTEM_VIAJES`) para no romper los imports heredados;
el agente, sus herramientas y su prompt son propios.

## Blueprint · Agente `agente_alejandra`

| Qué definir | Mi agente |
| --- | --- |
| Rol y alcance | **Hace:** audita cumplimiento normativo y tributario de empresas (cruzando CMF y SII) y de fondos de inversión regulados por la CMF (concentración, liquidez, ratios). **No hace:** no ejecuta acciones correctivas, no presenta declaraciones, no da asesoría tributaria personal, legal o de inversión. |
| Herramientas | `consultar_mis_apuntes` (conceptos, criterios y un caso real de auditoría) · `consultar_sii`, `consultar_cmf`, `verificar_cumplimiento_contable`, `generar_checklist_cumplimiento_empresa` (empresas) · `consultar_fondo`, `revisar_cumplimiento_normativo`, `calcular_ratios_fondo`, `generar_checklist_auditoria` (fondos). |
| Autonomía | **Decide solo:** qué herramienta llamar según la pregunta, cómo interpretar y cruzar los datos devueltos, qué alertas o incumplimientos señalar. **Nunca sin una persona:** no informa a la CMF/SII, no ejecuta medidas correctivas, no contacta a terceros — solo recomienda el siguiente paso. |
| Cuándo pide ayuda | **Pregunta si falta:** RUT de la empresa, nombre del fondo, tipo de empresa (sa/spa/ltda) o tipo de fondo (accionario/deuda/inmobiliario). **Deriva a otro especialista cuando:** le piden asesoría tributaria personal, legal o de inversión. |
| Dónde se ejecuta | `http://127.0.0.1:2025` · grafo `agente_alejandra` |

### Perfil del agente

- **Nombre:** Alejandra
- **Especialidad:** auditoría de cumplimiento normativo y tributario (CMF y SII)
- **Personalidad:** rigurosa, directa y paciente; explica con ejemplos concretos y cita siempre la fuente o norma exacta.
- **Skills:**
  1. Consultar el estado tributario de una empresa en el SII y señalar atrasos u observaciones.
  2. Cruzar datos de la CMF y el SII para determinar si una empresa cumple la normativa.
  3. Generar un checklist de auditoría según el tipo de empresa o de fondo.

## Cómo ejecutar

```powershell
cd mi-agente-ale
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env          # y pega tu GOOGLE_API_KEY
.venv\Scripts\langgraph.exe dev --port 2025
```

El servidor queda en `http://127.0.0.1:2025`:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:2025/assistants/search" -ContentType "application/json" -Body '{"graph_id":"agente_alejandra"}'
Invoke-RestMethod "http://127.0.0.1:2025/.well-known/agent-card.json?assistant_id=<uuid>"
```

Después, `notebooks/a2a-test.ipynb` con un kernel que tenga `a2a-sdk` y `langchain-google-genai`
(`requirements-notebook.txt`), ejecutado de arriba abajo.

> **Nota de entorno.** `a2a-sdk` sube `google-api-core`, que exige OpenTelemetry ≥ 1.44, mientras que
> `langgraph-api` fija ≤ 0.63b1. Por eso el notebook usa un kernel aparte y `requirements.txt` no
> incluye `a2a-sdk`; si se instala en el entorno del servidor, `langgraph dev` deja de arrancar.

> **Nota de protocolo.** La Agent Card anuncia `protocolVersion 1.0` pero el endpoint responde con el
> JSON de A2A 0.3. El notebook fija `interfaz.protocol_version = "0.3.0"` antes de `create_client(...)`.

## Etapa 3 · los dos perfiles conversando

`mi-agente-2` (segundo perfil **Benjamín**, control interno y riesgos operacionales, puerto **2026**)
no se incluye en esta carpeta: el notebook lo espera en `http://127.0.0.1:2026` y, si se reemplaza por
el agente de un compañero, basta actualizar `SERVIDORES` en la etapa 3.

**Resultado de la conversación** (`notebooks/a2a-test.ipynb`): Comercial Andina Ltda con atrasos
tributarios recurrentes. Alejandra propuso un diagnóstico cruzado SII/CMF; Benjamín agregó matriz de
riesgo, contención inmediata y segregación de funciones; el plan final de Alejandra integró ambos
aportes en 4 fases con responsables y plazos.

**Blueprint del segundo perfil (Benjamín):**

| Qué definir | Agente Benjamín |
| --- | --- |
| Rol y alcance | **Hace:** diseña y evalúa controles internos, evalúa riesgo de hallazgos y propone planes de mitigación. **No hace:** no revisa cifras tributarias ni normativa de la CMF/SII (deriva a auditoría). |
| Herramientas | `consultar_mis_apuntes` (conceptos, criterios y un caso de control interno). |
| Autonomía | **Decide solo:** qué control proponer y cómo priorizar un riesgo. **Nunca sin una persona:** no implementa el control, no aprueba el plan de mitigación. |
| Cuándo pide ayuda | **Pregunta si falta:** el proceso o hallazgo a evaluar. **Deriva:** cifras tributarias, SII o CMF. |
| Dónde se ejecuta | `http://127.0.0.1:2026` · grafo `agente_benjamin` |

## Estructura

```
mi-agente-ale/
├── AGENTS.md · plan.json · langgraph.json · requirements.txt · requirements-notebook.txt · .env.example
├── src/agente_viajes/   prompts.py · herramientas.py · graph.py   ← auditoría SII/CMF y fondos
├── bruno/               tarjeta y message/send contra el puerto 2025
├── tests/               test_a2a_viajes.py (se salta si el servidor no está arriba)
└── notebooks/           a2a-test.ipynb (etapas 2 y 3)
```

## Identificación

- **Nombre y apellidos:** Alejandra Ubilla
- **Grupo:** Grupo 1 · Taller A2A
- **Aporte:** diseño del perfil, prompts, herramientas de auditoría (SII/CMF/fondos) y pruebas por notebook/A2A.
