# Proyecto Agentes + Telegram

Proyecto autocontenido con agentes LangGraph, una CLI y una API FastAPI preparada para recibir
mensajes de Telegram por webhook.

> **Este proyecto es independiente del gateway A2A.** Ejecuta copias locales de los agentes en
> `src/`. Si quieres la integración real **Telegram → gateway A2A → agentes A2A**, usa
> `../servicio-fastapi/` y su sección «Canal Telegram».

## 1. Estructura

```text
proyecto-telegram/
├── main.py                 ← CLI
├── api/app.py              ← FastAPI + webhook Telegram
├── src/
│   ├── agentes.py          ← registro de agentes
│   ├── mensajes.py         ← utilidades de entrada/salida
│   ├── agente_general/
│   ├── agente_czz/
│   ├── agente_bryhan/
│   ├── agente_alejandra/
│   └── agente_soluciones_comerciales_marketing/
├── scripts/set_webhook.py
├── tests/
├── .env.example
├── .python-version
├── Procfile
├── requirements.txt
└── AGENTS.md
```

Cada agente cumple la regla `graph.py` + `prompts.py` + `tools.py`: el grafo solo ensambla, los
prompts y reglas viven en `prompts.py`, y las herramientas en `tools.py`.

## 2. Instalación

```powershell
cd proyecto-telegram
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { copy .env.example .env }
notepad .env
```

Completa en `.env`:

```env
GOOGLE_API_KEY=tu_clave_de_gemini
ANTHROPIC_API_KEY=tu_clave_de_anthropic   # solo si usas agente_alejandra
TELEGRAM_TOKEN=
TELEGRAM_SECRET=cambiame
```

- `TELEGRAM_TOKEN` queda vacío hasta crear el bot en BotFather.
- `TELEGRAM_SECRET` puede cambiarse por una cadena aleatoria; debe coincidir con la que se configure
  al registrar el webhook.

## 3. CLI

Desde la raíz:

```powershell
.venv\Scripts\python.exe main.py agente_general "¿Qué puedes hacer?"
```

Agentes disponibles:

- `agente_general`
- `agente_czz` (acciones e inversiones)
- `agente_bryhan` (AI Engineering, procesos, datos e IA)
- `agente_alejandra` (auditoría CMF/SII; usa Anthropic)
- `agente_soluciones_comerciales_marketing` (ingeniería comercial y marketing)

Flags:

```powershell
# Imprime los nodos por los que pasó el grafo
.venv\Scripts\python.exe main.py agente_czz "¿Cuánto vale AAPL en el mercado US?" --saltos

# Imprime el Mermaid sin ejecutar el agente
.venv\Scripts\python.exe main.py agente_bryhan --diagrama
```

`--diagrama` no llama al modelo; si no hay `GOOGLE_API_KEY` usa una clave ficticia solo para construir
la estructura del grafo.

## 4. API

```powershell
.venv\Scripts\python.exe -m uvicorn api.app:app --reload --port 8000
```

Endpoints:

- `GET /health`: estado y agentes registrados.
- `GET /docs`: documentación interactiva.
- `POST /telegram/webhook`: recibe las actualizaciones de Telegram.

El webhook:

- exige el header `X-Telegram-Bot-Api-Secret-Token`;
- compara el secreto con `TELEGRAM_SECRET` en tiempo constante;
- responde `503` si `TELEGRAM_TOKEN` no está configurado;
- procesa la consulta en segundo plano y envía la respuesta con `sendMessage`;
- permite elegir agente con `/agente_czz mensaje` o `/agente agente_czz mensaje`.

## 5. Configurar Telegram

1. En Telegram, abre **@BotFather**, crea un bot con `/newbot` y copia el token.
2. Pon el token en `.env` como `TELEGRAM_TOKEN`.
3. Elige un secreto para el webhook, por ejemplo:
   ```powershell
   $env:TELEGRAM_SECRET = "mi-secreto-largo-y-aleatorio"
   ```
   o edítalo en `.env`.
4. Telegram exige HTTPS para el webhook. Para probar en local, publica el puerto 8000 con un túnel:
   ```powershell
   cloudflared tunnel --url http://localhost:8000
   ```
   Copia la URL `https://...trycloudflare.com`.
5. Registra el webhook:
   ```powershell
   .venv\Scripts\python.exe scripts\set_webhook.py --url "https://...trycloudflare.com"
   ```
   El script agrega `/telegram/webhook`, envía `secret_token` y muestra la respuesta de Telegram.
6. Escríbele al bot. La API recibe el update, ejecuta el agente y responde por Telegram.

Para eliminar el webhook:

```powershell
.venv\Scripts\python.exe scripts\set_webhook.py --delete
```

> El túnel y la URL son temporales. Mantén la terminal del túnel abierta mientras pruebes.
> No publiques el token ni el secreto en capturas o repositorios.

## 6. Pruebas

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Las pruebas usan fakes: no llaman a Gemini ni a Telegram. Cubren:

- registro y estructura de los agentes;
- prompts fuera de `graph.py`;
- extracción de mensajes;
- CLI con y sin `--saltos`/`--diagrama`;
- autenticación del webhook por secreto;
- selección de agente por comando;
- procesamiento en segundo plano y respuesta de error.

## 7. Heroku

Archivos incluidos:

- `Procfile`: `web: uvicorn api.app:app --host 0.0.0.0 --port $PORT`
- `.python-version`: `3.12`
- `requirements.txt`

Comandos de despliegue desde la raíz del monorepo:

```powershell
heroku login
heroku create a2a-grupo1-final
heroku git:remote -a a2a-grupo1-final
heroku config:set GOOGLE_API_KEY=... ANTHROPIC_API_KEY=... MODELO=gemini-3.5-flash-lite MODELO_ANTHROPIC=claude-sonnet-5-5 TELEGRAM_TOKEN=... TELEGRAM_SECRET=... AGENTE_PREDETERMINADO=agente_general
git subtree push --prefix proyecto-telegram heroku main
heroku open
```

Si `proyecto-telegram/` es la raíz del repositorio, usa `git push heroku main` en lugar de
`git subtree push`.

Después del despliegue, registra el webhook con la URL pública de Heroku:

```powershell
.venv\Scripts\python.exe scripts\set_webhook.py --url "https://tu-app.herokuapp.com"
```

## 8. Agregar agentes

1. Crea `src/{nombre_agente}/` con `graph.py`, `prompts.py` y `tools.py`.
2. En `prompts.py` pon el `SYSTEM_PROMPT` y, si hay varios nodos, `PROMPTS_POR_NODO`.
3. En `graph.py` solo construye el modelo y `create_agent(..., name="{nombre_agente}")`.
4. Registra el constructor en `src/agentes.py`.
5. Agrega la prueba de estructura en `tests/test_agentes.py`.

Alejandra (`agente_alejandra`) usa Anthropic; ya está incluida y requiere `ANTHROPIC_API_KEY`.
`langchain-anthropic` está en `requirements.txt`.

## 9. Límites conocidos

- Un solo proceso: las tareas de Telegram se ejecutan en segundo plano en memoria.
- No hay deduplicación de updates; usa `update_id` si necesitas idempotencia.
- El webhook debe ser HTTPS; el túnel local es temporal.
- La API no persiste conversaciones; cada mensaje es independiente salvo la memoria que agregues al
  grafo.
- Los agentes son de solo lectura: no envían correos, no publican ni ejecutan pagos.
