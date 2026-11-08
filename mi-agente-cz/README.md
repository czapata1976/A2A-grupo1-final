# Taller A2A · Grupo 1 · Agente de Carlos Zapata

**Grupo 1** · Integrantes: **Alejandra Ubilla, Carlos Monroy, Bryhan Cortes y Carlos Zapata.**
**Autor de este agente:** Carlos Zapata · grafo `agente_czz`.
**Dónde corre:** `http://127.0.0.1:2025`.

Este proyecto parte de `agente-viajes-a2a` (el agente de viajes de la clase) y lo transforma en un agente
con el perfil de su autor: **asesor experto en acciones**. Se conserva la carpeta `src/agente_viajes`
por los imports heredados, pero el prompt ya es propio (`SYSTEM_AGENTE`), con método de análisis,
formato de respuesta y límites explícitos.

El agente trabaja con un método fijo: identifica ticker y mercado, obtiene los datos con
`consultar_acciones`, los interpreta (rango de 52 semanas, variación, volumen), los contrasta con los
criterios de `consultar_mis_apuntes` y entrega una decisión condicionada al perfil de riesgo, con
riesgos y regla de salida. Nunca inventa fundamentales que la herramienta no devuelve.

## Blueprint · Agente `agente_czz`

| Qué definir       | Mi agente                                                                                                                                                                                           |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Rol y alcance      | **Hace:** analiza acciones con datos de mercado y criterios fundamentales, compara alternativas y propone un plan de análisis. **No hace:** pagos, ejecución de inversiones, ni asesoría tributaria o legal. |
| Herramientas       | `consultar_mis_apuntes(tema)` — mis conceptos, criterios y un caso. `consultar_acciones(ticker, pais)` — precio en moneda local y en CLP (con tasa explícita), variación, volumen, rango de 52 semanas y fecha de corte. Datos simulados y coherentes entre sí. |
| Autonomía          | **Decide solo:** consultar acciones y mis apuntes sin aprobación previa. **Nunca sin una persona:** ejecutar pagos, compras, ventas o inversiones.                                        |
| Cuándo pide ayuda  | **Pregunta si falta:** el país (el mercado donde cotiza) o el ticker. **Deriva a otro especialista cuando:** la consulta es tributaria o normativa.                                      |
| Dónde se ejecuta   | `http://127.0.0.1:2025` · grafo `agente_czz`                                                                                                                                                   |

## Cómo ejecutar

```powershell
cd mi-agente-cz
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env          # y pega tu GOOGLE_API_KEY
.venv\Scripts\langgraph.exe dev --port 2025
```

Queda disponible en `http://127.0.0.1:2025`:

```powershell
# assistant_id del grafo
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:2025/assistants/search" -ContentType "application/json" -Body '{"graph_id":"agente_czz"}'
# tarjeta del agente (con su assistant_id)
Invoke-RestMethod "http://127.0.0.1:2025/.well-known/agent-card.json?assistant_id=<uuid>"
```

Después, en `notebooks/a2a-test.ipynb`:

1. Kernel: **Python (Taller A2A)** (`taller-a2a`), que apunta a `../venv-notebook`.
2. Primera celda: `LANGGRAPH_URL = "http://127.0.0.1:2025"`.
3. Ejecuta «Encontrar el Id de tu agente» y copia el UUID en `ASSISTANT_ID`.

### Entorno del notebook (`venv-notebook`)

El kernel vive en la raíz del taller, fuera del proyecto, y **no** lleva `langgraph-cli` (por el
conflicto de OpenTelemetry de la nota siguiente). Así se reproduce:

```powershell
cd ..        # raíz del taller
py -3.12 -m venv venv-notebook
.\venv-notebook\Scripts\python.exe -m pip install -r mi-agente-cz\requirements-notebook.txt
.\venv-notebook\Scripts\python.exe -m ipykernel install --user --name taller-a2a --display-name "Python (Taller A2A)"
```

Comprobaciones:

```powershell
.\venv-notebook\Scripts\python.exe -m pip check
.\venv-notebook\Scripts\python.exe -m jupyter kernelspec list   # debe listar taller-a2a
```

El servidor del agente (`langgraph dev --port 2025`) va aparte, con `mi-agente-cz/.venv` y
`requirements.txt`: desde `venv-notebook` no se puede levantar el servidor.

> **Nota de entorno (etapas 2 y 3).** El notebook usa `a2a-sdk` para leer la tarjeta y hablar por A2A.
> Instalarlo en el mismo entorno que `langgraph-cli` **rompe el servidor**: sube `google-api-core`, que exige
> OpenTelemetry ≥ 1.44, mientras que `langgraph-api` fija ≤ 0.63b1. Por eso conviene un entorno aparte solo
> para el kernel del notebook (`a2a-sdk`, `langchain-google-genai`, `langgraph-sdk`, `httpx`, `ipykernel`),
> sin `langgraph-cli`. En este equipo el servidor corre con el entorno del proyecto y el notebook con ese
> kernel separado (kernel `taller-a2a`). Ver `requirements-notebook.txt`.

> **Nota de protocolo.** Las Agent Cards de `langgraph dev` anuncian `protocolVersion 1.0`, pero el endpoint
> responde con el JSON de A2A 0.3 (`kind` en las partes). Con `a2a-sdk` 1.2.2 el envío falla con
> `ParseError: Message type "lf.a2a.v1.Task" has no field named "kind"`. La solución que quedó en el
> notebook es fijar `interfaz.protocol_version = "0.3.0"` en la tarjeta antes de `create_client(...)`: así el
> cliente usa el transporte compatible y el `message/send` funciona.

## Etapa 3 · los dos agentes del grupo conversando

La etapa 3 necesita **dos** servidores, uno por agente del grupo:

```powershell
# terminal 1 · agente_czz (este proyecto)
cd mi-agente-cz; .venv\Scripts\langgraph.exe dev --port 2025

# terminal 2 · agente_bryhan (proyecto de Bryhan)
cd ..\agente-bryhan; <su entorno>\Scripts\langgraph.exe dev --port 2026
```

El notebook de este proyecto hace el resto: descubre las dos tarjetas, escribe en cada una su ficha
(`PATCH /assistants/<uuid>`), crea un cliente A2A por agente con un `contextId` propio y levanta un
grafo supervisor que elige quién responde cada turno. La conversación queda en tres turnos
`agente_czz → agente_bryhan → agente_czz` sobre el reto del taller.

### Exponer el agente con un túnel de Cloudflare

Cuando el compañero está en otra red, el `127.0.0.1` no le sirve: hay que publicar el puerto 2025 con
un túnel temporal de Cloudflare. El proyecto trae dos scripts equivalentes (`tunel_cloudflare.ps1` para
PowerShell y `tunel_cloudflare.py` para cualquier sistema):

```powershell
# 1. instalar cloudflared (una sola vez)
winget install Cloudflare.cloudflared

# 2. con el servidor del agente ya arriba
.\tunel_cloudflare.ps1                 # o: python tunel_cloudflare.py
```

El script comprueba que `http://127.0.0.1:2025/ok` responda, abre el túnel, espera la URL pública,
verifica la tarjeta a través de ella y la deja guardada en `tunel.url`:

```
Túnel activo: https://algo-random.trycloudflare.com
Estado: agente_czz visible por el túnel
```

Comprobaciones manuales (las mismas que imprime el script):

```powershell
$url = Get-Content .\tunel.url
Invoke-RestMethod -Method Post -Uri "$url/assistants/search" -ContentType "application/json" -Body '{"graph_id":"agente_czz"}'
Invoke-RestMethod "$url/.well-known/agent-card.json?assistant_id=<uuid>"
```

Para que el notebook hable con el agente por la URL pública, exporta la variable antes de abrir el
kernel (o edítala en `SERVIDORES` de la etapa 3):

```powershell
$env:A2A_CZZ_URL = "https://algo-random.trycloudflare.com"
```

Al terminar:

```powershell
.\tunel_cloudflare.ps1 -Detener      # o: python tunel_cloudflare.py --detener
```

Avisos:

- La URL **cambia en cada arranque** y no se versiona (`tunel.url`, `tunel.pid` y `cloudflared*.log`
  están en `.gitignore`).
- La Agent Card anuncia la URL local del servidor. Un cliente remoto debe reescribir
  `supported_interfaces[].url` a la URL del túnel; el notebook de la etapa 3 ya lo hace en la celda de
descubrimiento.
- Cualquiera con la URL puede conversar con el agente mientras el túnel esté abierto: ciérralo al
  terminar y no lo dejes corriendo sin supervisión.
- El túnel solo publica el puerto 2025; el servidor de LangGraph y la `GOOGLE_API_KEY` siguen siendo
  locales.

> El zip **no** incluye `.env` (tiene la clave) ni `.venv` ni `.langgraph_api`. Sí incluye `.env.example`.

## Estructura de los archivos propios

```
mi-agente-cz/
├── src/agente_viajes/prompts.py       ← personalidad, especialidad, SOBRE_MI y las tres skills
├── src/agente_viajes/herramientas.py  ← APUNTES + consultar_mis_apuntes + consultar_acciones
├── src/agente_viajes/graph.py         ← create_agent(..., name="agente_czz")
├── langgraph.json                     ← registra el grafo agente_czz
├── bruno/                             ← tarjeta y message/send contra el puerto 2025
├── tests/test_a2a_viajes.py           ← tarjeta + message/send (se saltan si no hay servidor)
├── tunel_cloudflare.ps1 · .py         ← publica el puerto 2025 con un túnel temporal
└── notebooks/a2a-test.ipynb           ← etapas 2 y 3 ejecutadas
```

## Qué aportó cada persona

| Persona                    | Aporte                                                                                                                                                                                                     |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Carlos Zapata**    | Este agente: blueprint, `prompts.py`, `herramientas.py` (apuntes + `consultar_acciones`), `graph.py` y `langgraph.json` con el grafo `agente_czz`; notebook del taller y documento de entrega. |
| **Alejandra Ubilla** | Agente `agente_alejandra`, especialista en auditoría de cumplimiento normativo y tributario (CMF y SII). Proyecto en `mi-agente-ale/`.                                                                |
| **Bryhan Cortes**    | Agente `agente_bryhan`: su notebook con perfil, herramientas y conversación A2A, y el empaquetado de ese diseño como servidor en el puerto 2026 (`agente-bryhan/`).                                    |
| **Carlos Monroy**    | Agente `agente_soluciones_comerciales_marketing`, especialista en ingeniería comercial y marketing. Proyecto en `mi-agente-CM/`.                                                                       |
