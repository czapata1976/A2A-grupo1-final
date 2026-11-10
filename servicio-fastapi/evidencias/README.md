# Evidencias de ejecución local

Esta carpeta reúne el acta JSON que genera `scripts/probar_api.py` y las capturas que debe tomar el
grupo con su propia ejecución. **No se incluyen capturas inventadas**: el estado real de cada caso se
marca abajo.

## 1. Preparación

1. Levanta al menos un agente A2A (idealmente `agente_czz` en 2025 y `agente_bryhan` en 2026).
2. Levanta el servicio:

   ```powershell
   cd servicio-fastapi
   .\scripts\iniciar.ps1
   ```

3. En otra terminal, ejecuta el recorrido HTTP:

   ```powershell
   cd servicio-fastapi
   .venv\Scripts\python.exe scripts\probar_api.py --url http://127.0.0.1:8000
   ```

   El acta queda en `evidencias/ultima-prueba.json`. No contiene la clave.

4. Abre `http://127.0.0.1:8000` y toma las capturas de la sección 3.

### 1.1 Captura automática con Playwright

El proyecto incluye un capturador que abre la consola, prueba el acceso rechazado y permitido, envía
una consulta de un agente, una multiagente y una de dato faltante, y guarda capturas y un acta.

```powershell
cd servicio-fastapi
.venv\Scripts\python.exe -m pip install -r requirements-evidencias.txt
# Con Microsoft Edge instalado (Windows):
.venv\Scripts\python.exe scripts\capturar_evidencias.py --url http://127.0.0.1:8000 --canal msedge

# Alternativa sin Edge: navegador Chromium de Playwright
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe scripts\capturar_evidencias.py --url http://127.0.0.1:8000 --canal chromium
```

- Lee `API_KEYS` desde `.env`; no escribe la clave en las capturas ni en el acta. Prefiere esa vía
  antes que `--clave`, que puede quedar visible en el historial de procesos.
- Requiere al menos un agente A2A levantado.
- Guarda en `evidencias/capturas/`: `01-acceso.png`, `02-acceso-rechazado.png`,
  `03-consola-conectada.png`, `04-consulta-accion.png`, `05-consulta-multiagente.png`,
  `06-dato-faltante.png`, `07-traza-a2a.png`, `acta-capturas.json` y `acta-capturas.md`.
- Si una consulta falla, registra el estado y la captura del error; no la marca como exitosa.
- Revisa las imágenes y oculta cualquier dato sensible antes de entregar.

## 2. Estado de la evidencia

| Evidencia | Estado | Dónde se ve |
| --- | --- | --- |
| Pruebas unitarias de auth, validación, orquestación y A2A | **Verificada** (64 aprobadas, 1 integración omitida) | `pytest -q` |
| Arranque real de FastAPI en local | **Verificada** (salud, frontend y 401 comprobados) | `evidencias/ultima-prueba.json` tras ejecutar el script |
| Descubrimiento y `message/send` contra `langgraph dev` real | **Verificado**; con clave ficticia el agente falla y el gateway devuelve `502` claro | logs de la prueba de protocolo |
| Capturador Playwright (UI, acceso, consultas y traza) | **Verificado** con un servidor A2A de prueba; las capturas reales quedan pendientes | ejecución del capturador |
| Consulta real a un agente con clave de modelo | **Pendiente de ejecución del grupo** | consola web + terminal |
| Consulta multiagente A2A real | **Pendiente de ejecución del grupo** | consola web + panel de traza |
| Dato faltante solicitado por el agente | **Pendiente de ejecución del grupo** | consola web |
| Fallo controlado de agente caído | **Pendiente de ejecución del grupo** | terminal + consola |
| Canal Telegram (webhook → A2A → respuesta) | **Pendiente de ejecución del grupo** | captura de Telegram + log del gateway |

Las capturas deben marcar **LOCAL** y la fecha. No mostrar `API_KEYS`, `.env`, tokens, `contextId`
completos ni datos personales.

## 3. Casos y capturas

### Caso 1 · Acceso permitido

- **Solicitud:** abrir `http://127.0.0.1:8000`, pegar la clave de `.env` y presionar **Conectar**.
- **Resultado esperado:** se ven los agentes descubiertos y el estado «Conectado».
- **Captura:** pantalla de la consola con la lista de agentes. Tapa o recorta la clave.
- **Comando de respaldo:**

  ```powershell
  $clave = (Select-String -Path .env -Pattern '^API_KEYS=').Line.Split('=')[1]
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/agentes" -Headers @{ "X-API-Key" = $clave }
  ```

### Caso 2 · Acceso rechazado

- **Solicitud:** en la consola, ingresar una clave incorrecta; o ejecutar la petición sin cabecera.
- **Resultado esperado:** `401` con mensaje «Acceso no autorizado»; la consola no muestra agentes.
- **Captura:** error visible en la consola y/o terminal con `HTTP 401`. No mostrar la clave real.
- **Comando:**

  ```powershell
  try {
      Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/agentes"
  } catch {
      "HTTP $([int]$_.Exception.Response.StatusCode)"
  }
  ```

### Caso 3 · Un agente con cifra y unidad

- **Solicitud:** `¿Cuánto vale AAPL en el mercado US y qué debería revisar antes de invertir?`
- **Agente:** `agente_czz`.
- **Resultado esperado:** respuesta con el precio, la moneda y una variación; sin alterar cifras.
- **Captura:** burbuja de respuesta y panel de traza con `agente_czz`, duración y `contextId` abreviado.

### Caso 4 · Varios agentes A2A

- **Solicitud:** `Evalúa si conviene invertir en Falabella: quiero el dato de mercado, una revisión de cumplimiento normativo y un plan para automatizar el análisis.`
- **Modo:** `paralelo` o `colaborativo`, con `agente_czz` + `agente_alejandra` + `agente_bryhan` si están
  disponibles.
- **Resultado esperado:** respuesta consolidada con encabezados por agente y el texto íntegro de cada
  aporte; cifras, unidades y condiciones conservadas.
- **Captura:** respuesta y panel de traza con los tres aportes y sus tiempos.

### Caso 5 · Dato faltante

- **Solicitud:** `¿Cuánto vale AAPL?`
- **Resultado esperado:** el agente pide el mercado/país antes de concluir; la consola muestra
  «El agente pidió un dato faltante».
- **Captura:** pregunta del agente y aviso de dato faltante.

### Caso 6 · Entrada inválida o agente caído

- **Solicitud inválida:** enviar `mensaje` vacío por API.
- **Resultado esperado:** `422 ENTRADA_INVALIDA` con detalles de los campos.
- **Agente caído:** detener un servidor con `Ctrl+C` y consultar solo ese agente.
- **Resultado esperado:** `502` con mensaje claro; si es una consulta paralela, `estado: parcial` y el
  aporte del agente caído marcado como error.
- **Captura:** terminal con el código y la consola con el mensaje. No mostrar claves.

### Caso 7 · Canal Telegram

- **Preparación:** `TELEGRAM_TOKEN` y `TELEGRAM_SECRET` en `servicio-fastapi/.env`; servicio y agentes
  arriba; webhook registrado con `scripts/set_webhook.py` y una URL HTTPS.
- **Solicitud:** desde Telegram, envía `¿Cuánto vale AAPL en el mercado US?`.
- **Resultado esperado:** el bot responde con el aporte del agente A2A; en el log del gateway se ve
  `POST /telegram/webhook` y la consulta A2A.
- **Captura:** pantalla de Telegram con la pregunta y la respuesta, más el log del gateway.
  No muestres el token ni el secreto.
- **Opcional multiagente:** envía `/paralelo agente_czz,agente_alejandra revisa acción y cumplimiento`.
  La respuesta debe contener los dos aportes íntegros.

## 4. Plantilla de acta por caso

Copia esta tabla en el informe o en una captura de texto:

| Campo | Valor |
| --- | --- |
| Entorno y fecha | LOCAL · AAAA-MM-DD HH:MM |
| Solicitud | … |
| Resultado esperado | … |
| Resultado obtenido | … |
| Evidencia | `01-acceso-permitido.png`, `02-consulta-aapl.png`, … |
| Observaciones | diferencias, errores, límites o pasos pendientes |

## 5. Checklist antes de entregar

- [ ] El acta `ultima-prueba.json` se generó con el servicio real y agentes reales.
- [ ] Hay captura de acceso permitido y de acceso rechazado.
- [ ] Hay captura de una consulta con cifra/unidad visible.
- [ ] Hay captura de una consulta con varios agentes y su traza A2A.
- [ ] Hay captura de un dato faltante solicitado por el agente.
- [ ] Se ve el código de error claro en un fallo controlado.
- [ ] Ninguna captura muestra claves, tokens, `.env` ni datos privados.
- [ ] Las capturas están rotuladas como LOCAL y con fecha.
- [ ] Se distinguen los casos probados de los pendientes.
