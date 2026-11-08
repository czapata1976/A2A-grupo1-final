# Seguridad del servicio FastAPI

Este documento describe el alcance, los controles implementados y los límites conocidos de la
implementación local. La evaluación principal es local; no se declara el servicio como producción.

## 1. Alcance y activos

| Activo | Dónde vive | Riesgo principal |
| --- | --- | --- |
| Clave de acceso al servicio (`API_KEYS`) | `.env` del servicio y `sessionStorage` del navegador | Uso no autorizado de la API |
| Claves de modelo (`GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`) | `.env` de cada agente | Costo y acceso al proveedor |
| Texto de las consultas y respuestas | En memoria y en la respuesta HTTP | Exposición de datos personales |
| `contextId` A2A | Memoria del servicio y del servidor LangGraph | Continuidad de un hilo |
| Servidores LangGraph | `127.0.0.1:2025-2028` | Acceso directo sin autenticación |
| Token de Telegram | `.env` del servicio | Suplantación del bot y envío de mensajes |
| Secreto del webhook | `.env` del servicio | Updates falsos hacia el webhook |

## 2. Controles implementados

### 2.1 Autenticación del servicio

- `API_KEYS` es obligatoria. Si no hay claves, el servicio **no arranca** (fail closed).
- Se rechazan claves de menos de 12 caracteres y los valores ficticios de `.env.example`.
- Se acepta `X-API-Key: <token>` o `Authorization: Bearer <token>`.
- La comparación usa `secrets.compare_digest` para evitar comparaciones vulnerables a tiempos.
- La respuesta `401` incluye `WWW-Authenticate: Bearer` y un mensaje claro.
- La clave se guarda en `sessionStorage` de la consola web. No se escribe en cookies persistentes,
  en la URL, en `localStorage` ni en el HTML.
- La clave del servicio **no es** una clave de modelo. Las claves de Gemini/Anthropic nunca llegan al
  navegador ni al gateway.

### 2.2 Límite de peticiones

- `RATE_LIMIT_POR_MINUTO` (30 por defecto) se aplica por huella SHA-256 del token e IP.
- Al excederlo: `429` con `Retry-After`.
- El límite vive en memoria. Con varios workers o réplicas no se comparte; para escalar se necesita
  Redis u otro almacén.

### 2.3 Validación de entrada

- Pydantic con `extra="forbid"`: campos desconocidos producen `422`.
- `mensaje`: 1 a 4000 caracteres, se recorta antes de validar.
- `session_id`: solo letras, números, guion y guion bajo; 8 a 64 caracteres. Evita rutas y valores
  arbitrarios en la URL de sesión.
- `agentes`: lista de hasta 4 nombres con patrón `[a-z0-9_]`; se rechazan duplicados.
- `modo`: unión cerrada de cuatro valores.
- No se aceptan URLs, cabeceras de proveedor ni claves de modelo por parte del cliente.

### 2.4 Prevención de SSRF y de destino arbitrario

- Las URLs de los agentes salen exclusivamente de `A2A_SERVIDORES`.
- El cliente no puede elegir una URL: solo elige un `graph_id` que debe existir en el catálogo
  descubierto.
- El endpoint A2A se construye con la URL configurada y el `assistant_id` asignado por el servidor.
- `A2A_SERVIDORES` se valida al arrancar: solo `http`/`https`, sin query ni fragmento.

### 2.5 Secretos y registros

- `.env` está en `.gitignore`; `.env.example` solo tiene valores ficticios.
- No se registra la clave, el token ni el cuerpo de la consulta.
- La auditoría (`logs/auditoria.jsonl`) guarda:
  - `solicitud_id`, hash corto de la sesión, modo, agentes, estado, duración;
  - hash corto del mensaje y su largo;
  - estado por agente, duración, prefijo de `contextId` y código de error.
- Los logs de consola no incluyen el texto de la consulta ni claves.
- Los errores de proveedor se sanitizan y se truncan antes de devolverlos.

### 2.6 Consola web

- Sin scripts de terceros, sin fuentes externas y sin `innerHTML` para datos del servidor.
- Todo texto dinámico se inserta con `textContent`.
- Cabeceras:
  - `Content-Security-Policy` con `default-src 'self'`, `script-src 'self'`, `style-src 'self'`,
    `connect-src 'self'`, `frame-ancestors 'none'`.
  - `X-Content-Type-Options: nosniff`.
  - `X-Frame-Options: DENY`.
  - `Referrer-Policy: no-referrer`.
  - `Permissions-Policy` sin cámara, micrófono ni geolocalización.
- CORS cerrado por defecto. Si se configura `CORS_ORIGINS`, se limita a la lista y no se usan
  credenciales.
- La documentación interactiva se puede desactivar con `DOCS_HABILITADOS=false`; se recomienda en un
  despliegue real.

### 2.7 Manejo de errores

| Código | Código de error | Significado |
| --- | --- | --- |
| `400` | `SOLICITUD_INVALIDA` | Agente desconocido, combinación de modo/agentes inválida. |
| `401` | `NO_AUTORIZADO` | Falta el token o no coincide. |
| `422` | `ENTRADA_INVALIDA` | Cuerpo fuera del esquema. |
| `429` | `LIMITE_ALCANZADO` | Rate limit. |
| `502` | `AGENTES_FALLARON` | Ningún agente pudo responder. |
| `503` | `SIN_AGENTES_DISPONIBLES` | Descubrimiento vacío. |
| `504` | `AGENTES_TIEMPO_AGOTADO` | Timeout de todos los agentes. |

Los errores no incluyen trazas, rutas internas ni claves. Cada uno lleva `solicitud_id` para
correlacionar con el registro.

### 2.8 Canal Telegram

- El webhook exige `X-Telegram-Bot-Api-Secret-Token` y lo compara con `TELEGRAM_SECRET` usando
  `secrets.compare_digest` sobre bytes.
- Si falta `TELEGRAM_TOKEN` o `TELEGRAM_SECRET`, responde `503`; no simula una operación exitosa.
- El token de BotFather y el secreto viven solo en `.env` o en config vars; no se registran ni se
  devuelven al usuario.
- La consulta se procesa en segundo plano y la respuesta se envía con `sendMessage`; el texto se
  trunca a 4000 caracteres.
- El webhook usa el mismo orquestador A2A y la misma consolidación fiel que la consola web; no hay
  una segunda lógica de agentes.
- La sesión de Telegram es `telegram-<chat_id>` y queda aislada por la huella del canal en el
  almacén de sesiones.
- Telegram exige una URL HTTPS; en local se usa un túnel temporal y se cierra al terminar.

### 2.9 Aislamiento de la colaboración A2A

- En modo colaborativo, los aportes previos se envían en el **mensaje de usuario**, envueltos en
  `<aporte agente="...">...</aporte>`.
- El prompt indica que son datos, no instrucciones, y que se conserven cifras, unidades y condiciones.
- El texto del usuario nunca se inserta en el system prompt del agente.
- Cada agente mantiene su propio `contextId`; no se comparten hilos entre agentes.

## 3. Demostración de acceso permitido y rechazado

Con el servicio arriba y la clave en `.env`:

```powershell
$base = "http://127.0.0.1:8000"
$clave = (Select-String -Path .env -Pattern '^API_KEYS=').Line.Split('=')[1]

# Permitido
Invoke-RestMethod -Uri "$base/v1/agentes" -Headers @{ "X-API-Key" = $clave }

# Rechazado
try {
    Invoke-RestMethod -Uri "$base/v1/agentes"
} catch {
    "HTTP $([int]$_.Exception.Response.StatusCode)"
}
```

No muestres `$clave` en capturas. Para la evidencia, captura el estado `200` y el `401`, no el valor
de la clave.

## 4. Límites y riesgos residuales

1. **Token compartido.** No hay usuarios, roles ni permisos por persona. Quien tenga la clave puede
   consultar mientras esté vigente. Para producción se recomienda OAuth/OIDC o claves por usuario.
2. **Servidores LangGraph sin autenticación.** `langgraph dev` no valida tokens. El gateway protege
   `/v1/*`, pero un tercero con acceso de red a `127.0.0.1:2025` podría hablar directo con el agente.
   En local está fuera de exposición; en un despliegue deben ir en red privada o detrás de un proxy
   autenticado.
3. **HTTP local.** No hay TLS. Para acceso remoto, usa HTTPS en un proxy inverso.
4. **Rate limit y sesiones en memoria.** No se comparten entre workers; un reinicio limpia sesiones y
   contadores. Es aceptable para la demo local y está declarado.
5. **`sessionStorage`.** La clave está accesible para JavaScript del mismo origen. La CSP y la
   ausencia de terceros reducen el riesgo, pero no lo eliminan. No uses la consola en equipos
   compartidos con extensiones no confiables.
6. **Inyección de prompts.** Los agentes reciben texto del usuario y aportes de otros agentes. Los
   envoltorios y las reglas reducen el riesgo, pero un modelo puede ser manipulado. No hay acciones
   externas: los agentes son de solo lectura y no ejecutan pagos ni envíos.
7. **Veracidad.** El gateway no valida aritmética ni hechos; conserva el texto del agente. La
   revisión de datos es responsabilidad del agente y de la persona.
8. **Heurística de dato faltante.** `posible_falta_de_datos` es una señal, no una garantía. La pregunta
   del agente es la respuesta autoritativa.
9. **Historial de conversación.** Los `contextId` permiten memoria; tras reiniciar el servidor de
   agentes esa memoria se pierde. Inicia una conversación nueva.
10. **Dependencias.** El gateway no instala `a2a-sdk`; usa JSON-RPC directo para evitar el conflicto de
    OpenTelemetry con `langgraph-cli`. Las dependencias se instalan en entornos separados.
11. **Canal Telegram.** El webhook debe ser HTTPS y el túnel local es temporal. Telegram entrega los
    updates al servicio; no hay deduplicación de `update_id`, así que un reintento del proveedor podría
    repetir una consulta. El procesamiento es en memoria y en un solo proceso.
12. **Token y secreto de Telegram.** Quien obtenga `TELEGRAM_TOKEN` puede enviar mensajes como el bot;
    quien obtenga `TELEGRAM_SECRET` puede intentar updates falsos. Trátalos como credenciales y
    rótalos si se filtran.

## 5. Lista de verificación antes de publicar

- [ ] `API_KEYS` es larga, aleatoria y no está en el repositorio.
- [ ] `.env`, `.venv`, `logs/` y `__pycache__/` están fuera de la entrega.
- [ ] `DOCS_HABILITADOS=false` si el servicio no es solo local.
- [ ] `TELEGRAM_TOKEN` y `TELEGRAM_SECRET` son privados, están fuera del repositorio y se rotan si se filtran.
- [ ] El webhook de Telegram usa HTTPS y el mismo `TELEGRAM_SECRET` configurado en `set_webhook.py`.
- [ ] `CORS_ORIGINS` contiene solo orígenes necesarios.
- [ ] Los servidores de agentes están en red privada o detrás de autenticación.
- [ ] HTTPS en el proxy de entrada.
- [ ] Una sola réplica o almacén compartido para sesiones y rate limit.
- [ ] Capturas sin claves, tokens, `.env` ni datos personales.
- [ ] Revisión de que los logs no contienen texto de consultas.
