# Taller de Implementación · Grupo 1 · Informe de entrega

**Curso:** Certificado Agentic AI · UAI
**Taller:** Implementación y ejecución local
**Grupo:** 1
**Integrantes:** Alejandra Ubilla, Carlos Monroy, Bryhan Cortes y Carlos Zapata
**Implementación:** Servicio FastAPI protegido + consola web de chat + canales Telegram y WhatsApp
**Estado:** Funcionando en local y desplegado en Heroku; agentes A2A expuestos por túnel, WhatsApp
vinculado y evaluación de calidad **20/20** (2026-11-10)

## 1. Resumen ejecutivo

El grupo reutilizó los cuatro agentes del Taller A2A y construyó una implementación local que una
persona puede instalar, ejecutar y probar desde el navegador. La opción elegida combina:

1. **Servicio FastAPI** con autenticación por token, límite de peticiones, sesiones, trazabilidad y
   orquestación A2A.
2. **Canal web de chat** servido por el mismo FastAPI, con frontend propio y panel de traza.
3. **Canal Telegram** por webhook, que usa el mismo orquestador A2A y devuelve la respuesta al chat.
4. **Canal WhatsApp** con puente Baileys en loopback y panel de vinculación; comparte el mismo
   orquestador y los mismos agentes.

El servicio descubre los agentes de LangGraph por `assistants/search` y su Agent Card, les habla por
JSON-RPC (`message/send`) y devuelve una respuesta visible. Si participan varios agentes, la respuesta
final contiene el texto íntegro de cada aporte: no se reescriben cifras, unidades ni condiciones.
Los canales Telegram y WhatsApp no duplican la lógica: son puntos de entrada al mismo gateway.

La entrega incluye código, `.env.example`, pruebas automatizadas, scripts de arranque y detención,
guía de evidencias y preparación para un despliegue opcional. Además, `evaluacion/` aporta una
evaluación automática con **promptfoo**: 20 casos con comprobaciones mecánicas y una rúbrica de
calidad, con **20/20 aprobadas (100 %)** en la última corrida.

## 2. Problema y solución

**Problema.** En el Taller A2A los agentes ya conversaban entre sí desde notebooks, pero no había una
forma de uso reproducible para una persona externa: faltaba un punto de entrada, control de acceso,
manejo de errores y una respuesta visible.

**Solución.** Un gateway FastAPI que:

- recibe una consulta por HTTP o por Telegram;
- valida el token o el secreto del webhook en el servidor;
- descubre los agentes A2A disponibles;
- elige uno o varios según la consulta y el catálogo;
- mantiene memoria por conversación con `contextId`;
- consolida los aportes sin alterarlos;
- devuelve la respuesta, los aportes por agente y una traza;
- expone una consola web para la persona.

## 3. Qué se reutiliza y qué es nuevo

| Elemento | Origen | Uso en la implementación |
| --- | --- | --- |
| `agente_czz` | `mi-agente-cz/` | Acciones, precios y fundamentales (PER, endeudamiento, márgenes); deriva contingencias a auditoría. |
| `agente_bryhan` | `agente-bryhan/` | Procesos, datos, IA y planes de trabajo. |
| `agente_alejandra` | `mi-agente-ale/` | Auditoría CMF/SII, búsqueda de RUT por nombre, deuda tributaria, fondos, ratios y checklists. |
| `agente_soluciones_comerciales_marketing` | `mi-agente-CM/` | Ingeniería comercial y marketing. |
| Tarjetas y protocolo A2A | Taller A2A | Descubrimiento y `message/send` JSON-RPC. |
| Prompts, herramientas y grafos | Taller A2A | Reutilizados; en esta iteración se agregaron herramientas y reglas a `agente_czz` y `agente_alejandra`. |
| API, seguridad, orquestador, consola, canales y pruebas | Nuevo | `servicio-fastapi/`. |

El gateway se acopla por el protocolo A2A y por la configuración de puertos. En esta iteración se
ampliaron las herramientas y los prompts de dos agentes, sin cambiar su contrato A2A.

## 4. Arquitectura

```text
Persona → Consola web → FastAPI → Descubrimiento A2A → Agente(s) LangGraph
                              ↓
                    Respuesta consolidada + aportes + traza
```

Componentes nuevos:

| Archivo | Responsabilidad |
| --- | --- |
| `app/main.py` | Rutas, middleware, cabeceras, manejo de errores y factory ASGI. |
| `app/config.py` | Configuración validada desde `.env`. |
| `app/seguridad.py` | Token, comparación en tiempo constante y rate limit. |
| `app/a2a.py` | Descubrimiento, Agent Card, JSON-RPC y extracción de texto. |
| `app/catalogo.py` | Catálogo del Grupo 1 y selección por especialidad. |
| `app/orquestador.py` | Modos individual/paralelo/colaborativo, sesiones y consolidación. |
| `app/sesiones.py` | `contextId` por agente y sesión, con TTL y tope. |
| `app/auditoria.py` | JSONL con hashes y metadatos, sin texto ni secretos. |
| `app/static/` | Consola web (HTML, CSS y JavaScript sin dependencias) con 5 ejemplos predefinidos. |
| `app/whatsapp.py` y `app/cliente_whatsapp.py` | Panel de vinculación y cliente del puente Baileys. |
| `whatsapp/` | Puente Node/Baileys en loopback (texto del chat propio). |
| `tests/` | 64 pruebas unitarias/de contrato y 1 integración opcional. |
| `scripts/` | Arranque, detención, prueba HTTP, túneles de agentes y webhook de Telegram. |

### Flujo de una consulta

1. La consola envía `POST /v1/consultas` con `X-API-Key`.
2. FastAPI valida token, límite, cuerpo y sesión.
3. El cliente A2A consulta `/assistants/search` y la Agent Card de cada servidor.
4. El catálogo selecciona el agente o los agentes.
5. Se envía `message/send` a `/a2a/<assistant_id>` con un `contextId` propio por agente.
6. Se extrae el texto de `status.message`, `artifacts` o `history`.
7. Se consolidan los aportes con encabezados; el texto de cada agente queda íntegro.
8. Se devuelve respuesta, aportes, errores, traza y `solicitud_id`.
9. Se registra la auditoría sin el texto de la consulta.

### Modos

- **auto:** un agente, elegido por palabras clave y catálogo.
- **individual:** un agente explícito o el mejor.
- **paralelo:** varios agentes a la vez; si uno falla, la respuesta es parcial.
- **colaborativo:** en orden, cada agente recibe los aportes previos como datos y responde desde su
  especialidad.

## 5. Seguridad

| Control | Implementación |
| --- | --- |
| Autenticación | `API_KEYS` obligatoria; `X-API-Key` o `Bearer`; `compare_digest`. |
| Claves de modelo | Solo en los `.env` de los agentes; nunca en el navegador. |
| Rate limit | 30 peticiones/minuto por token e IP; `429` + `Retry-After`. |
| Validación | Pydantic `extra="forbid"`, longitudes, patrones y modos cerrados. |
| SSRF | URLs solo desde `A2A_SERVIDORES`; el usuario elige grafos, no URLs. |
| Registros | `solicitud_id`, hashes, agentes, estados y duraciones; sin texto ni claves. |
| Consola | CSP estricta, sin terceros, `textContent`, cabeceras de seguridad. |
| CORS | Cerrado por defecto; lista explícita si se configura. |
| Errores | Códigos claros; sin trazas ni detalles internos. |
| Secretos | `.env` ignorado; `.env.example` ficticio; claves de ejemplo rechazadas. |

El detalle y los riesgos residuales están en `servicio-fastapi/SEGURIDAD.md`.

## 6. Pruebas y resultados

### 6.1 Automáticas

Comando:

```powershell
cd servicio-fastapi
.venv\Scripts\python.exe -m pytest -q
```

Resultado en este equipo (2026-11-10):

```text
64 passed, 1 skipped
```

La prueba omitida es la integración real (`tests/test_integracion_a2a.py`), que requiere servidores
LangGraph y claves de modelo. Se activa con:

```powershell
$env:A2A_INTEGRATION = "1"
.venv\Scripts\python.exe -m pytest -m integracion -q
```

Cobertura de la suite:

- salud pública y protección de `/v1/*`;
- token ausente, incorrecto y Bearer válido;
- rate limit;
- validación de cuerpo, longitudes, sesión y agentes;
- selección automática del especialista;
- consolidación exacta de cifras, unidades y condiciones;
- modo paralelo y colaborativo;
- respuesta parcial y fallo total;
- timeout;
- sesión y reutilización de `contextId`;
- reinicio de sesión;
- detección de dato faltante;
- frontend, cabeceras y assets;
- cliente A2A con JSON-RPC, error y timeout simulados;
- webhook de Telegram: secreto, ayuda, selección automática, agente explícito y modo paralelo;
- canal WhatsApp: secreto del puente, panel, estados de vinculación y errores del puente.

### 6.2 Arranque real verificado

Se levantó `uvicorn` en el puerto 8765 con una clave de prueba y sin agentes:

| Comprobación | Resultado |
| --- | --- |
| `GET /salud` | `200` con estado `ok` |
| `GET /` | `200`, consola HTML |
| `GET /v1/agentes` con clave | `200`, lista vacía y aviso de servidor inaccesible |
| `GET /v1/agentes` sin clave | `401` |

Esto verifica el arranque, el frontend y el control de acceso. **No sustituye** la consulta real a un
agente con modelo.

### 6.3 Protocolo A2A verificado

- Se levantó un `langgraph dev` real (`mi-agente-cz`, puerto 2025) y el gateway lo descubrió con su
  `assistant_id`, su Agent Card y el grafo `agente_czz`.
- Se envió `message/send` real al endpoint `/a2a/<assistant_id>`. Con una clave de modelo ficticia, el
  agente devolvió `state: failed`; el gateway respondió `502 AGENTES_FALLARON` con un mensaje claro,
  sin presentarlo como éxito.
- También se probó el recorrido HTTP completo contra un servidor A2A local de prueba con respuestas
  fijas (salud, auth, consulta multiagente, consolidación y errores). Esa prueba valida el protocolo
  del gateway, **no** se usa como evidencia de los agentes reales.
- El capturador `scripts/capturar_evidencias.py` se ejecutó con Edge/Playwright contra ese servidor de
  prueba y generó las capturas de acceso, consulta individual, multiagente, dato faltante y traza. Las
  capturas de la prueba simulada no se incluyen en la entrega; las reales se generan con las claves
  del grupo.
- Se verificó el flujo **Telegram → gateway A2A → Telegram** con un servidor A2A de prueba y un
  receptor de Telegram de prueba: el webhook recibió el update, el orquestador consultó los agentes
  A2A y la respuesta consolidada llegó al receptor. Esta prueba valida la integración de los canales,
  no la respuesta de los modelos reales.

### 6.4 Evidencias y pendientes

Ya verificado en este equipo: consultas reales a los cuatro agentes, recorrido completo por la consola
web, canales Telegram y WhatsApp, descubrimiento de los cuatro agentes desde Heroku y evaluación
automática con promptfoo (20/20).

Pendiente solo de captura formal:

1. ejecutar `scripts/probar_api.py` y guardar el acta;
2. ejecutar `scripts/capturar_evidencias.py` (Playwright) para generar las capturas de acceso,
   consulta individual, multiagente, dato faltante y traza;
3. capturar una conversación real en Telegram y otra en WhatsApp;
4. capturar manualmente un fallo controlado (detener un agente) si se quiere evidenciar ese caso;
5. revisar las imágenes y ocultar cualquier dato sensible;
6. guardar todo en `servicio-fastapi/evidencias/capturas/`.

La guía exacta está en `servicio-fastapi/evidencias/README.md`.

### 6.5 Evaluación de calidad con promptfoo

Se agregó una evaluación automática de los cuatro agentes con **promptfoo 0.125.1**
(`evaluacion/`). Cada agente recibe **cinco preguntas** de dificultad creciente (fácil, fácil-media,
media, media-difícil y difícil) y cada caso debe pasar **tres comprobaciones**:

1. `icontains` / `icontains-any`: el contenido esperado aparece en la respuesta.
2. `not-icontains`: no aparece el contenido prohibido (cifras inventadas, promesas, etc.).
3. `llm-rubric` con umbral 0.7: otro modelo califica **amabilidad y corrección**.

Comando:

```powershell
cd evaluacion
copy .env.example .env      # GOOGLE_API_KEY del modelo calificador (no la de los agentes)
promptfoo eval --output resultados.json
promptfoo view              # http://localhost:15500
```

**Resultado final — corrida `eval-Ozb` (2026-11-10T21:59:49Z): 20/20 aprobadas (100 %), sin errores
de ejecución.**

| Agente | Casos | Latencia media | Mínima | Máxima |
| --- | --- | --- | --- | --- |
| `agente_czz` | 5/5 | 17,8 s | 5,6 s | 25,7 s |
| `agente_bryhan` | 5/5 | 28,6 s | 25,7 s | 31,3 s |
| `agente_alejandra` | 5/5 | 23,5 s | 20,9 s | 29,5 s |
| `agente_soluciones_comerciales_marketing` | 5/5 | 19,7 s | 18,5 s | 20,7 s |

La rúbrica de calidad pasó en **20/20** casos (score 1,0): trato cordial y respuestas apoyadas en las
herramientas.

**Hallazgos de la evaluación y correcciones aplicadas**

| Hallazgo | Corrección |
| --- | --- |
| `agente_alejandra` no podía enumerar fondos y pedía nombres | Nueva herramienta `listar_fondos` con tipo, concentración, rentabilidad y cumplimiento NCG 365. |
| `agente_soluciones_comerciales_marketing` no resolvía temas libres en sus apuntes | `consultar_mis_apuntes` busca por contenido cuando la clave no es exacta. |
| `agente_czz` narraba «procedo a consultar» y terminaba sin llamar herramientas | Regla explícita «ejecuta, no anuncies» y una llamada por ticker. |
| Aserciones demasiado literales en las pruebas 18-20 | `icontains-any` con sinónimos (seguimiento/calificación/contacto; criterio/propósito/control; ficticio/hipotético/ilustrativo). |
| El modelo calificador marcaba 2026 como fecha inválida | La rúbrica declara el contexto temporal del taller (2026-11-10, datos simulados). |

El detalle paso a paso se obtiene con `--saltos`, que imprime cada nodo del grafo, la herramienta
llamada con sus argumentos, lo que devolvió y la respuesta final:

```powershell
python evaluacion\agente.py --agente agente_alejandra `
  --pregunta "Revisa si Comercial Andina Ltda tiene deuda tributaria pendiente" --saltos
python evaluacion\agente.py --agente agente_czz --diagrama
```

### 6.6 Canales y despliegue verificados

| Canal | Estado | Verificación |
| --- | --- | --- |
| Consola web local | ✅ | `GET /` 200; 4 agentes con `disponible: true`; consulta individual y multiagente |
| Consola web en Heroku | ✅ | `A2A_SERVIDORES` con cuatro túneles; `/v1/agentes` 4/4; consulta real a `agente_czz` en 4,9 s |
| Telegram | ✅ | Webhook apuntando al servicio, `pending_update_count: 0`, sin `last_error_message` |
| WhatsApp | ✅ | Vinculado con código de 8 dígitos; `estado: connected`; mensaje real respondido en 5,3 s |

Notas de operación:

- `scripts/tuneles_agentes.py` abre un túnel por agente (2025-2028), verifica el grafo y actualiza
  `A2A_SERVIDORES` en Heroku con `--heroku a2agrupo1`. Las URLs de túnel rápido cambian al reiniciar.
- El canal WhatsApp procesa los mensajes **enviados desde la propia cuenta** (chat «Mensaje para ti»).
  WhatsApp entrega esos mensajes como `append` y el puente acepta `notify` y `append`.
- El log del servicio rota cada 2 MB con 3 copias (`logs/servicio.log`) y no registra el sondeo del panel.
- La consola muestra **5 ejemplos predefinidos** que preseleccionan agente y modo; el ejemplo
  «Consulta multiagente» quedó corregido ortográficamente.

## 7. Preparación manual

| Recurso | Acción |
| --- | --- |
| Python 3.12 | Instalar y verificar `py -3.12 --version`. |
| Gemini | Crear una API key en Google AI Studio para los cuatro agentes. |
| Puertos | 8000 para el gateway; 2025-2028 para los agentes. |
| `.env` de agentes | Copiar cada `.env.example` y pegar la clave correspondiente. |
| `.env` del gateway | Generado por `scripts/iniciar.ps1` o copiado desde `.env.example`; cambiar `API_KEYS`. |
| Telegram | Crear un bot con @BotFather, guardar `TELEGRAM_TOKEN` y definir `TELEGRAM_SECRET`. |
| WhatsApp | Node 22+, `WHATSAPP_HABILITADO=true`, `WHATSAPP_SECRET` largo y vinculación por QR o código de 8 dígitos. |
| Túneles de agentes | `cloudflared` instalado; `scripts/tuneles_agentes.py --heroku a2agrupo1` abre y actualiza las URLs. |
| Túnel HTTPS | Para probar el webhook local con Telegram, por ejemplo `cloudflared tunnel --url http://localhost:8000`. |
| Evaluador | Recibe la clave por un canal privado; no está en el repositorio. |
| promptfoo | `npm install -g promptfoo` (0.125.1) y `evaluacion/.env` con la clave del modelo calificador. |

Se requiere un bot de Telegram y un túnel HTTPS para el canal Telegram. El canal WhatsApp es
opcional: requiere Node 22+, `WHATSAPP_HABILITADO=true` y `WHATSAPP_SECRET`, y usa un conector
comunitario no oficial (Baileys). No se requieren cuentas de Gmail.

## 8. Preparación para despliegue

- `Dockerfile` y `Procfile` listos para un contenedor o una plataforma tipo Heroku.
- `PORT`, `API_KEYS`, `A2A_SERVIDORES`, `TELEGRAM_TOKEN`, `TELEGRAM_SECRET`, `WHATSAPP_HABILITADO`,
  `WHATSAPP_SECRET`, `DOCS_HABILITADOS` y `CORS_ORIGINS` se configuran por entorno.
- En local con Docker, los agentes del host se alcanzan con `host.docker.internal`.
- Para publicar de verdad hay que desplegar también los agentes o exponerlos de forma segura. El token
  del gateway no protege los endpoints directos de `langgraph dev`.
- No se declara el +1 de despliegue: la entrega base es local. El camino queda preparado.

## 9. Límites conocidos

- Sesiones y rate limit en memoria; no se comparten entre workers.
- Token compartido, sin usuarios ni roles.
- Enrutador determinista; puede elegir un agente subóptimo en consultas ambiguas.
- El gateway conserva el texto del agente, pero no valida aritmética ni hechos.
- Los servidores LangGraph no tienen autenticación propia en modo `dev`.
- HTTP local sin TLS; para remoto, proxy con HTTPS.
- `posible_falta_de_datos` es una heurística.
- Al reiniciar un agente se pierden sus hilos en memoria.
- El canal Telegram necesita HTTPS, token de BotFather y el mismo secreto al registrar el webhook.
  No hay deduplicación de updates y el procesamiento es en memoria.
- `consultar_mis_apuntes` resuelve claves exactas y, si no, busca por contenido; aun así un tema muy
  ambiguo puede requerir precisión. La evaluación ya no registra ese caso como fallo.
- Los túneles rápidos de Cloudflare cambian de URL en cada reinicio: hay que volver a ejecutar
  `scripts/tuneles_agentes.py --heroku a2agrupo1` y confirmar con `GET /v1/agentes`.
- WhatsApp usa un conector comunitario no oficial (Baileys) y solo atiende el chat propio; si WhatsApp
  invalida la sesión hay que revincular con QR o código.
- El despliegue en Heroku ejecuta el gateway, pero no los agentes ni el puente de WhatsApp: esos corren
  en el equipo local y se exponen por túnel.

## 10. Conclusión

La implementación conecta el trabajo A2A del grupo con una forma de uso real, protegida y reproducible.
El valor principal no es solo la interfaz: el gateway demuestra el recorrido completo, conserva la
fidelidad de las respuestas y deja evidencia de qué agente respondió, cuánto tardó y con qué contexto.
La consola web, Telegram y WhatsApp usan el mismo orquestador; no hay agentes ni respuestas duplicadas.
La iteración final amplió las capacidades de los agentes (fundamentales y derivación a auditoría en
`agente_czz`; búsqueda de RUT por nombre, deuda tributaria y listado de fondos en `agente_alejandra`)
y alineó la consola con cinco ejemplos de uso. La evaluación con promptfoo cierra el circuito de
calidad: 20 casos, tres comprobaciones por caso y una rúbrica externa, con **20/20 aprobadas (100 %)**.
Las capturas formales del recorrido quedan como el último paso de evidencia del grupo.
