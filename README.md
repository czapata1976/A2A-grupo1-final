# Grupo 1 · Taller de Implementación · Entrega local reproducible

**Curso:** Certificado Agentic AI · UAI
**Taller:** Implementación y ejecución local
**Grupo:** 1
**Opción:** Servicio FastAPI protegido + consola web de chat + canales Telegram y WhatsApp
**Estado:** implementación local reproducible, suite automatizada aprobada y descubrimiento/manejo de error A2A verificados contra `langgraph dev`; las capturas del recorrido real con modelos quedan pendientes de ejecución con las claves del grupo.


> Esta entrega continúa el **Taller A2A**. No reemplaza los agentes: los reutiliza. El detalle del
> taller anterior se conserva como **Anexo** al final.

## 1. Opción elegida

Se implementaron **dos opciones complementarias** de la consigna:

1. **Servicio FastAPI** con acceso protegido por token, límite de peticiones, sesiones, errores claros,
   trazas A2A y consolidación fiel de respuestas.
2. **Canal de atención web con frontend de chat**, servido por el mismo FastAPI. No es WhatsApp Web ni
   una página estática: la consola habla con la API protegida y muestra la respuesta y la traza.
3. **Canal Telegram** por webhook, usando el mismo orquestador A2A. Telegram no duplica agentes: solo
   es otro punto de entrada al gateway.
4. **Canal WhatsApp** por medio de un puente Node/Baileys en loopback. El puente reenvía los mensajes
   que la cuenta vinculada se envía a sí misma y el gateway responde con el mismo orquestador A2A.

**Problema que resuelve.** Cualquier persona puede hacer una consulta desde el navegador, desde
Telegram o desde WhatsApp y recibir una respuesta de uno o varios agentes, con evidencia de quién
respondió, cuánto tardó y qué contexto usó, sin exponer las claves de los modelos.

**Qué reutiliza del Taller A2A.** Los cuatro agentes, sus prompts, herramientas, grafos y servidores:
`agente_czz`, `agente_bryhan`, `agente_alejandra` y `agente_soluciones_comerciales_marketing`.

**Qué agrega.** `servicio-fastapi/`: gateway, seguridad, orquestador, cliente JSON-RPC, consola web,
canal Telegram, canal WhatsApp (puente Baileys), pruebas, scripts y documentación.

## 2. Integrantes y aportes

| # | Nombre | Agente / grafo | Aporte en esta entrega |
| - | ------ | -------------- | ---------------------- |
| 1 | Carlos Zapata | `agente_czz` | Agente de acciones; diseño e implementación del servicio FastAPI, seguridad, orquestación A2A, consola web, pruebas y documentación de la entrega. |
| 2 | Alejandra Ubilla | `agente_alejandra` | Agente auditor CMF/SII; herramientas, prompt, servidor A2A y consultas de auditoría. |
| 3 | Carlos Monroy | `agente_soluciones_comerciales_marketing` | Agente de ingeniería comercial y marketing; herramientas, prompt, servidor A2A y runtime del notebook. |
| 4 | Bryhan Cortes | `agente_bryhan` | Agente de AI Engineering; herramientas, prompt, servidor A2A y conexión A2A. |

## 3. Inicio rápido

Requisitos: Python 3.12 y una clave de Gemini (`GOOGLE_API_KEY`) para los cuatro agentes. Para el
canal Telegram se necesita un bot de BotFather (`TELEGRAM_TOKEN`) y un túnel HTTPS. El canal WhatsApp
es opcional: requiere Node 22+, `WHATSAPP_HABILITADO=true` y un conector comunitario no oficial
(Baileys).

```powershell
# Terminal 1 · desde la raíz del taller
cd mi-agente-cz
.venv\Scripts\langgraph.exe dev --port 2025

# Terminal 2 · desde la raíz del taller
cd agente-bryhan
.venv\Scripts\langgraph.exe dev --port 2026

# Terminal 3 · desde la raíz del taller
cd servicio-fastapi
.\scripts\iniciar.ps1

# 3) Abrir la consola
# http://127.0.0.1:8000
# La clave está en servicio-fastapi\.env (API_KEYS)
```

Si los agentes aún no tienen `.venv`, sigue `servicio-fastapi/README.md` §4.1. Para los cuatro agentes,
usa 2025, 2026, 2027 y 2028, y ajusta `A2A_SERVIDORES` en `servicio-fastapi/.env`.

Para Telegram:

```powershell
# En servicio-fastapi\.env
# TELEGRAM_TOKEN=token_de_botfather
# TELEGRAM_SECRET=un_secreto_largo

# Con el gateway arriba y un túnel HTTPS al puerto 8000:
.venv\Scripts\python.exe scripts\set_webhook.py --url "https://tu-url.trycloudflare.com"
```

El webhook usa el mismo orquestador A2A que la consola. Comandos: `/agente_czz <consulta>`,
`/paralelo agente_czz,agente_bryhan <consulta>`, `/colaborativo ...` y `/ayuda`.

Para WhatsApp (opcional):

```powershell
# En servicio-fastapi\.env: WHATSAPP_HABILITADO=true y WHATSAPP_SECRET=<secreto de 16+ caracteres>
npm ci --ignore-scripts
# Con el servicio arriba: http://127.0.0.1:8000/whatsapp
```

Detalle completo: [`servicio-fastapi/README.md`](servicio-fastapi/README.md).

## 4. Estructura de la entrega

```text
grupo-1-taller-a2a/
├── README.md                 ← este archivo
├── documento-entrega.md      ← informe de la implementación
├── package.json              ← dependencias del puente WhatsApp (Baileys)
├── servicio-fastapi/         ← API protegida + consola web + Telegram + WhatsApp + pruebas
│   ├── app/  tests/  scripts/  evidencias/
│   ├── whatsapp/             ← puente Node/Baileys (loopback, solo texto)
│   ├── .env.example  requirements.txt  requirements-lock.txt  requirements-evidencias.txt
│   ├── Dockerfile  Procfile
│   └── README.md  SEGURIDAD.md
├── evaluacion/               ← promptfoo: 20 pruebas (contenido, prohibido y rúbrica) + --saltos / --diagrama
├── mi-agente-cz/             ← agente_czz
├── agente-bryhan/            ← agente_bryhan
├── mi-agente-ale/            ← agente_alejandra
└── mi-agente-CM/             ← agente_soluciones_comerciales_marketing
```

## 5. Seguridad y evidencias

- El servicio exige `API_KEYS` en el servidor (`X-API-Key` o `Bearer`), aplica rate limit y no registra
  el texto de las consultas. Las claves de modelo viven solo en los `.env` de los agentes.
- El webhook de Telegram exige `TELEGRAM_SECRET` y el token de BotFather vive solo en `.env`.
- El puente de WhatsApp escucha solo en `127.0.0.1:18081` y exige `WHATSAPP_SECRET`; el panel exige la
  clave del servicio y no se registran números, códigos ni cuerpos de mensajes.
- `.env.example` no contiene secretos; los `.env`, `.venv`, `logs/`, `node_modules/` y
  `whatsapp/.runtime/` están excluidos.
- Pruebas: `cd servicio-fastapi; .venv\Scripts\python.exe -m pytest -q` → **64 aprobadas, 1 omitida**
  (la integración real requiere agentes y claves). `npm run whatsapp:test` → **8 aprobadas**.
- Evidencias: [`servicio-fastapi/evidencias/README.md`](servicio-fastapi/evidencias/README.md).
- Seguridad detallada: [`servicio-fastapi/SEGURIDAD.md`](servicio-fastapi/SEGURIDAD.md).

## 6. Documentos de la entrega

| Documento | Contenido |
| --- | --- |
| `servicio-fastapi/README.md` | Instalación, configuración, API, Telegram, modos, pruebas y despliegue. |
| `servicio-fastapi/SEGURIDAD.md` | Controles, demostración de acceso y riesgos residuales. |
| `servicio-fastapi/evidencias/README.md` | Casos, capturas y checklist de evidencia. |
| `evaluacion/README.md` | Evaluación con promptfoo: cómo correr, leer la tabla y diagnosticar fallos con `--saltos`. |
| `documento-entrega.md` | Informe extendido, resultados y límites. |

## 7. Guía de ejecución, pruebas, Telegram, Heroku y GitHub

### 7.1 Qué hace el proyecto

`servicio-fastapi/` es un gateway protegido que descubre los agentes A2A del grupo, consulta uno o
varios y devuelve una respuesta consolidada sin alterar cifras, unidades ni condiciones. Tiene dos
puntos de entrada: la consola web y el webhook de Telegram.

### 7.2 Ejecución local

Terminal 1 y 2, desde la raíz, para dos agentes A2A. Si una carpeta ya tiene `.venv`, omite su
creación e instalación:

```powershell
# Terminal 1
cd mi-agente-cz
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { copy .env.example .env }
notepad .env    # pega GOOGLE_API_KEY
.venv\Scripts\langgraph.exe dev --port 2025
```

```powershell
# Terminal 2
cd agente-bryhan
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { copy .env.example .env }
notepad .env    # pega GOOGLE_API_KEY
.venv\Scripts\langgraph.exe dev --port 2026
```

Para los cuatro agentes, repite el patrón en `mi-agente-ale` (puerto 2027) y `mi-agente-CM`
(puerto 2028); ambos usan `GOOGLE_API_KEY`.

### 7.3 Levantar la API

Si `servicio-fastapi/.venv` ya existe, omite la creación e instalación.

```powershell
# Terminal 3
cd servicio-fastapi
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { copy .env.example .env }
notepad .env    # API_KEYS, A2A_SERVIDORES y, si usas Telegram, TELEGRAM_TOKEN/SECRET
.venv\Scripts\python.exe -m uvicorn app.main:crear_app --factory --host 127.0.0.1 --port 8000
```

Alternativa:

```powershell
cd servicio-fastapi
.\scripts\iniciar.ps1
```

Consola: `http://127.0.0.1:8000` · Docs: `http://127.0.0.1:8000/docs`.

### 7.4 Correr las pruebas

```powershell
cd servicio-fastapi
.venv\Scripts\python.exe -m pytest -q
```

Resultado esperado: **52 aprobadas, 1 omitida**. La integración real se activa con los agentes
arriba:

```powershell
$env:A2A_INTEGRATION = "1"
.venv\Scripts\python.exe -m pytest -m integracion -q
```

### 7.5 Conectar Telegram

En `servicio-fastapi/.env`:

```env
TELEGRAM_TOKEN=token_de_botfather
TELEGRAM_SECRET=un_secreto_largo
TELEGRAM_API_BASE=https://api.telegram.org
```

Con el gateway arriba:

```powershell
# 1) Crear el bot en @BotFather y copiar el token.
# 2) Publicar el puerto 8000 con HTTPS:
cloudflared tunnel --url http://localhost:8000

# 3) Registrar el webhook (el script agrega /telegram/webhook):
cd servicio-fastapi
.venv\Scripts\python.exe scripts\set_webhook.py --url "https://tu-url.trycloudflare.com"
```

Mensajes y comandos:

```text
¿Cuánto vale AAPL en el mercado US?
/agente_czz ¿Cuánto vale AAPL en el mercado US?
/paralelo agente_czz,agente_alejandra revisa acción y cumplimiento
/ayuda
```

Si `TELEGRAM_TOKEN` está vacío, el webhook responde `503`. Si el secreto no coincide, responde `403`.

### 7.6 Desplegar en Heroku

El único componente que se despliega es el gateway (`servicio-fastapi/`), que también sirve el canal
de Telegram. Los servidores A2A deben ser alcanzables públicamente; `127.0.0.1` no funciona desde
Heroku. Si ya los tienes expuestos con HTTPS y autenticación:

```powershell
heroku create a2a-grupo1-gateway
heroku git:remote -a a2a-grupo1-gateway
heroku config:set API_KEYS=... A2A_SERVIDORES=https://agente-czz.example.com,https://agente-bryhan.example.com TELEGRAM_TOKEN=... TELEGRAM_SECRET=... DOCS_HABILITADOS=false
git subtree push --prefix servicio-fastapi heroku main
heroku open
```

No publiques `langgraph dev` sin autenticación: cualquiera podría consultar tus agentes. En local,
mantén el gateway con `API_KEYS` y los túneles bajo tu control.

#### Despliegue del gateway desde la raíz del monorepo (integración GitHub)

La integración de GitHub de Heroku construye la **raíz del repositorio**, no una subcarpeta, y el
dashboard no permite cambiar el stack. Por eso la raíz incluye tres archivos de despliegue y **no**
se usa `heroku.yml` (el build manifest exige el stack `container`):

| Archivo | Contenido | Motivo |
| --- | --- | --- |
| `Procfile` | `uvicorn app.main:crear_app --factory --app-dir servicio-fastapi` | `--app-dir` añade `servicio-fastapi` al `sys.path` sin fijar `PYTHONPATH`. |
| `requirements.txt` | `-r servicio-fastapi/requirements.txt` | Una sola fuente de dependencias. |
| `.python-version` | `3.12` | Evita que el buildpack elija una versión mayor no probada. |

Pasos en el dashboard:

1. **New → Create new app**, nombre `a2a-grupo1-final`, región a elección.
2. **Deploy → Deployment method → GitHub**, autoriza y elige el repositorio y la rama `main`.
3. **Enable Automatic Deploys** y luego **Deploy Branch**.
4. **Settings → Config Vars → Reveal Config Vars** y define:

| Variable | Valor |
| --- | --- |
| `API_KEYS` | Clave propia de 12+ caracteres ASCII (las de ejemplo se rechazan). |
| `A2A_SERVIDORES` | URLs **públicas** de los agentes, separadas por coma. `127.0.0.1` no es alcanzable desde Heroku. |
| `CONFIAR_EN_PROXY` | `true` (Heroku añade `X-Forwarded-For`). |
| `DOCS_HABILITADOS` | `false` para no exponer `/docs` públicamente. |
| `A2A_TIMEOUT` | `25`: el router de Heroku corta la petición a los 30 s, así que conviene responder con un error propio antes. |
| `AUDIT_LOG` | Vacío: el filesystem del dyno es efímero y se pierde en cada reinicio. |
| `TELEGRAM_TOKEN` / `TELEGRAM_SECRET` | Solo si se activa el canal de Telegram. |

Para los agentes locales, `servicio-fastapi/scripts/tuneles_agentes.ps1` abre un túnel de Cloudflare
por puerto, valida `/ok` y escribe `logs/tuneles.json` con el mapa puerto → URL:

```powershell
cd servicio-fastapi
.\scripts\tuneles_agentes.ps1              # imprime el valor de A2A_SERVIDORES
.\scripts\tuneles_agentes.ps1 -Detener     # cierra todos los túneles
```

Las URLs `trycloudflare.com` son temporales: si se reinician los túneles hay que actualizar
`A2A_SERVIDORES` en Heroku.

#### Estado del despliegue (2026-11-08)

| Dato | Valor |
| --- | --- |
| App | `a2agrupo1` (stack `heroku-24`, buildpack `heroku/python`, un dyno web) |
| URL | https://a2agrupo1-225ba991428b.herokuapp.com |
| Origen | Despliegue automático desde `main` de `czapata1976/A2A-grupo1-final` |
| Verificado | `/salud` → `200`; `/v1/agentes` → 4 agentes; `/v1/consultas` → respuesta real en 6 s; `/` → consola web; `/docs` → `404` por `DOCS_HABILITADOS=false` |
| Pendiente | `TELEGRAM_TOKEN` y `TELEGRAM_SECRET` para el canal de Telegram |


Verificación tras el despliegue: `GET https://<app>.herokuapp.com/salud` debe responder `200` y
`/v1/agentes` debe listar los agentes descubiertos por túnel.

Nota: las sesiones y el caché de agentes viven en memoria, así que el servicio debe quedar en **un
solo dyno** (escala 1) o las peticiones pueden caer en un dyno sin la sesión.

### 7.7 Publicar en GitHub

Desde la raíz, con el remoto y la rama indicados:

```powershell
git init
git add .
git commit -m "Entrega A2A Grupo 1: FastAPI, consola web y Telegram"
git remote add origin https://github.com/czapata1976/A2A-grupo1-final
git branch -M main
git push -u origin main
```

Antes del commit, `git status` no debe mostrar `.env`, `.venv/`, `__pycache__/`, `.langgraph_api/`,
`.pytest_cache/` ni logs. Los `.env.example` sí deben aparecer.

---

# Anexo · Taller A2A (entrega anterior)

> Se conserva como referencia del trabajo anterior. La estructura vigente está en la sección 4 de
> este README y en `servicio-fastapi/`.

**Curso:** Certificado Agentic AI · UAI
**Taller:** Laboratorio de Agentes · Taller práctico A2A
**Grupo:** 1

## 1. Identificación

| # | Nombre y apellidos | Agente / grafo | Puerto | Aporte principal |
| - | ------------------ | -------------- | ------ | ---------------- |
| 1 | Carlos Zapata | `agente_czz` | 2025 | Perfil de análisis de acciones e inversiones, herramientas `consultar_mis_apuntes` y `consultar_acciones`, notebooks de las etapas 2 y 3, supervisor A2A del grupo, scripts de túnel y documento de entrega. |
| 2 | Alejandra Ubilla | `agente_alejandra` | 2025 | Perfil auditor (CMF y SII), nueve herramientas de auditoría de empresas y fondos, notebook de las etapas 2 y 3 y conversación con el segundo perfil `agente_benjamin`. |
| 3 | Carlos Monroy | `agente_soluciones_comerciales_marketing` | 2025 | Perfil de ingeniería comercial y marketing, herramienta `consultar_mis_apuntes`, `notebook_runtime.py`, notebook de las etapas 2 y 3 con supervisor A2A. |
| 4 | Bryhan Cortes | `agente_bryhan` | 2026 | Perfil de AI Engineering aplicado a procesos empresariales y financieros, tres herramientas propias y notebook de conexión A2A con `agente_czz`. |

El material de compañeros incluido corresponde a los cuatro integrantes del **Grupo 1** y está
identificado, con su autor, en el `README.md` de cada carpeta.

## 2. Estructura del entregable

```
grupo-1-taller-a2a/
├── README.md                    ← este archivo (identificación, blueprints y ejecución)
├── documento-entrega.md         ← informe extendido del grupo
├── mi-agente-cz/                ← agente_czz · Carlos Zapata
├── agente-bryhan/               ← agente_bryhan · Bryhan Cortes
├── mi-agente-ale/               ← agente_alejandra · Alejandra Ubilla
└── mi-agente-CM/                ← agente_soluciones_comerciales_marketing · Carlos Monroy
```

El entorno del kernel (`venv-notebook/`) no se incluye: se recrea con los pasos de la sección 5.2.

Cada carpeta incluye:

- `src/agente_viajes/` con `prompts.py`, `herramientas.py` y `graph.py` propios.
- `langgraph.json`, `plan.json`, `.env.example` y `requirements.txt`.
- `notebooks/a2a-test.ipynb` con las celdas ejecutadas y sus resultados.
- `bruno/` con la tarjeta y el `message/send`, y `tests/` con las pruebas A2A.
- `README.md` con el blueprint del agente y sus instrucciones de ejecución.

## 3. Blueprints

### 3.1 `agente_czz` · Carlos Zapata

| Qué definir | Mi agente |
| --- | --- |
| Rol y alcance | **Hace:** consulta el precio y los datos de mercado de una acción y busca antecedentes en sus apuntes. **No hace:** pagos, ejecución de inversiones, ni asesoría tributaria o legal. |
| Herramientas | `consultar_mis_apuntes(tema)` y `consultar_acciones(ticker, pais)`. |
| Autonomía | **Decide solo:** consultar acciones y apuntes sin aprobación previa. **Nunca sin una persona:** ejecutar pagos, compras, ventas o inversiones. |
| Cuándo pide ayuda | **Pregunta si falta:** el país o el ticker. **Deriva:** consultas tributarias o normativas. |
| Dónde se ejecuta | `http://127.0.0.1:2025` · grafo `agente_czz` |

### 3.2 `agente_bryhan` · Bryhan Cortes

| Qué definir | Mi agente |
| --- | --- |
| Rol y alcance | **Hace:** analiza procesos, diseña soluciones de datos e IA, compara alternativas y arma planes de trabajo. **No hace:** no decide por la persona, no ejecuta acciones externas ni reemplaza asesoría regulada. |
| Herramientas | `consultar_conocimientos(tema)`, `comparar_opciones(opciones, criterios)`, `disenar_plan(objetivo, contexto, restricciones)`. |
| Autonomía | **Decide solo:** qué herramienta usar y cómo estructurar el análisis. **Nunca sin una persona:** ejecutar cambios en sistemas, enviar comunicaciones o asumir compromisos. |
| Cuándo pide ayuda | **Pregunta si falta:** un dato que cambie materialmente la respuesta. **Deriva:** temas fuera de su perfil o que exigen asesoría regulada. |
| Dónde se ejecuta | `http://127.0.0.1:2026` · grafo `agente_bryhan` |

### 3.3 `agente_alejandra` · Alejandra Ubilla

| Qué definir | Mi agente |
| --- | --- |
| Rol y alcance | **Hace:** audita cumplimiento normativo y tributario de empresas (cruce CMF/SII) y de fondos (concentración, liquidez, ratios). **No hace:** no ejecuta acciones correctivas, no presenta declaraciones ni da asesoría tributaria, legal o de inversión. |
| Herramientas | `consultar_mis_apuntes`; `consultar_sii`, `consultar_cmf`, `verificar_cumplimiento_contable`, `generar_checklist_cumplimiento_empresa`; `consultar_fondo`, `revisar_cumplimiento_normativo`, `calcular_ratios_fondo`, `generar_checklist_auditoria`. |
| Autonomía | **Decide solo:** qué herramienta llamar, cómo cruzar los datos y qué alertas señalar. **Nunca sin una persona:** informar a la CMF/SII, ejecutar medidas correctivas o contactar a terceros. |
| Cuándo pide ayuda | **Pregunta si falta:** RUT, nombre del fondo, tipo de empresa o tipo de fondo. **Deriva:** asesoría tributaria personal, legal o de inversión. |
| Dónde se ejecuta | `http://127.0.0.1:2025` · grafo `agente_alejandra` |

### 3.4 `agente_soluciones_comerciales_marketing` · Carlos Monroy

| Qué definir | Mi agente |
| --- | --- |
| Rol y alcance | **Hace:** responde consultas y propone soluciones fundamentadas en ingeniería comercial y marketing, con análisis y verificación documental. **No hace:** no aborda temas ajenos a lo consultado ni inventa información, experiencias o credenciales. |
| Herramientas | `consultar_mis_apuntes(tema)` con conceptos, criterios y un caso ficticio ilustrativo. |
| Autonomía | **Decide solo:** cómo organizar la respuesta, analizar antecedentes y presentar alternativas. **Requiere autorización** para enviar mensajes, publicar contenido, modificar documentos o asumir compromisos. |
| Cuándo pide ayuda | **Pregunta si falta** un dato indispensable o el objetivo es ambiguo. **Deriva** cuando la consulta excede su especialidad. |
| Dónde se ejecuta | `http://127.0.0.1:2025` · grafo `agente_soluciones_comerciales_marketing` |

## 4. Evidencia por etapa

| Etapa | Qué se puede revisar | Dónde |
| --- | --- | --- |
| 1 · Diseña | Blueprint, personalidad, apuntes, tres skills, herramientas, `graph.py` y `langgraph.json` | `README.md` y `src/agente_viajes/` de cada proyecto |
| 2 · Prueba | Personalidad, conocimientos y skills, memoria y tarjeta + `message/send` por A2A | `notebooks/a2a-test.ipynb` de cada proyecto (celdas ejecutadas) |
| 3 · Conversación | `agente_czz` ↔ `agente_bryhan` con supervisor y tres turnos | `mi-agente-cz/notebooks/a2a-test.ipynb` |
| 3 · Conversación | `agente_alejandra` ↔ `agente_benjamin` (A → B → A) | `mi-agente-ale/notebooks/a2a-test.ipynb` |
| 3 · Conversación | `agente_bryhan` ↔ `agente_czz` (A → B → A) | `agente-bryhan/notebooks/a2a-test.ipynb` |
| 3 · Conversación | Supervisor de Carlos Monroy con dos agentes | `mi-agente-CM/notebooks/a2a-test.ipynb` |

## 5. Cómo ejecutar

Requisitos: Python 3.12 y una clave de Gemini (`GOOGLE_API_KEY`) para los cuatro agentes.

### 5.1 Entorno del servidor (uno por agente)

```powershell
cd mi-agente-cz
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { copy .env.example .env }          # completar GOOGLE_API_KEY
.venv\Scripts\langgraph.exe dev --port 2025
```

Repetir en `agente-bryhan` (puerto 2026) y en `mi-agente-ale` / `mi-agente-CM` (puerto 2025).
La etapa 3 necesita **dos** servidores en puertos distintos, por ejemplo `agente_czz` en 2025 y
`agente_bryhan` en 2026.

### 5.2 Kernel de los notebooks

Los notebooks se ejecutan con el kernel **Python (Taller A2A)**. Se crea aparte porque `a2a-sdk` y
`langgraph-cli` no conviven (conflicto de OpenTelemetry):

```powershell
cd <raíz del taller>
py -3.12 -m venv venv-notebook
venv-notebook\Scripts\python.exe -m pip install -r mi-agente-cz\requirements-notebook.txt
venv-notebook\Scripts\python.exe -m pip install -r mi-agente-ale\requirements-notebook.txt
venv-notebook\Scripts\python.exe -m ipykernel install --user --name taller-a2a --display-name "Python (Taller A2A)"
```

### 5.3 Orden sugerido

1. Levantar los dos servidores que se van a usar.
2. Abrir el notebook del proyecto y ejecutarlo de arriba abajo.
3. Cerrar las conexiones con la última celda y detener los servidores con `Ctrl+C`.

### 5.4 Pruebas automáticas

```powershell
# con el servidor del agente arriba
cd mi-agente-cz; .venv\Scripts\python.exe -m pytest tests -q
```

Cada suite apunta por defecto a su puerto y a su grafo, y se salta si el servidor no está corriendo.

## 6. Notas técnicas

- **Sin claves en la entrega.** Cada proyecto trae `.env.example`; el `.env` real no se incluye.
- **Protocolo A2A.** Las tarjetas anuncian `protocolVersion 1.0`, pero el endpoint responde con el
  JSON de A2A 0.3. Los notebooks fijan `protocol_version = "0.3.0"` antes de `create_client(...)`.
- **Estado en memoria.** `langgraph dev` recrea los asistentes al reiniciar, así que el
  `assistant_id` y los `contextId` se obtienen de nuevo en cada sesión.
- **Túnel opcional.** `mi-agente-cz/tunel_cloudflare.ps1` y `.py` publican el puerto 2025 con una URL
  temporal; no se versiona la URL ni se conservan los logs.

## 7. Autoría

- **Proyecto base:** `agente-viajes-a2a`, entregado en el curso como punto de partida.
- **Aportes propios:** perfiles, prompts, herramientas, grafos, notebooks, pruebas y documentación de
  cada integrante, identificados en el `README.md` de su carpeta.
- **Material de compañeros:** los cuatro agentes del Grupo 1 se incluyen completos; los cruces A2A
  (quién conversó con quién) están descritos en la sección 4.
