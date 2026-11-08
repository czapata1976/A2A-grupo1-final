# Respaldo de la conversación — Taller Agente Auditora

**Fecha:** 18 de octubre de 2026
**Participante:** Alejandra Ubilla

---

## 1. Entorno del proyecto

- Se creó el entorno virtual con **Python 3.12.10** en `agente-viajes-a2a/.venv` y se instalaron las dependencias de `requirements.txt`.
- Se confirmó que no existe ninguna versión real `langgraph 3.2.13` (la versión real instalada es 1.2.16); la confusión venía probablemente de otro dato mencionado en clase.
- Se creó el archivo `.env` (no existía) a partir de `.env.example`.

## 2. Cambio de proveedor del modelo: Gemini → Anthropic

- El agente de viajes usaba `ChatGoogleGenerativeAI` con `gemini-3.5-flash-lite`.
- Al probarlo, falló por `402 RESOURCE_EXHAUSTED`: los créditos prepago de la cuenta de Google AI Studio estaban agotados.
- Con autorización de Alejandra, se cambió el proveedor a **Anthropic** (`ChatAnthropic`, modelo `claude-sonnet-5-5`) en:
  - `src/agente_viajes/graph.py`
  - `src/swarm/graph.py`
  - `requirements.txt` (`langchain-anthropic` en vez de `langchain-google-genai`)
  - `.env` / `.env.example` (`ANTHROPIC_API_KEY` en vez de `GOOGLE_API_KEY`)
- Se probó exitosamente vía notebook y vía servidor (`langgraph dev`).

## 3. Transformación en agente auditor (dentro de `agente-viajes-a2a`, luego revertida)

- Alejandra pidió transformar el agente de viajes en un **agente auditor** especializado en verificar cumplimiento normativo/tributario de empresas (CMF y SII), además de auditoría de fondos de inversión.
- Se diseñaron:
  - Un nuevo `SYSTEM_VIAJES` (prompt) con personalidad de auditora.
  - 8 herramientas nuevas: `consultar_sii`, `consultar_cmf`, `verificar_cumplimiento_contable`, `generar_checklist_cumplimiento_empresa` (empresas) + `consultar_fondo`, `revisar_cumplimiento_normativo`, `calcular_ratios_fondo`, `generar_checklist_auditoria` (fondos), todas con datos simulados.
- Se cuidó que **`src/swarm/` no se modificara** (regla explícita de Alejandra), manteniendo `buscar_vuelos`/`buscar_hoteles` disponibles para ese módulo.

## 4. Aparece la guía oficial del taller (PDF)

Alejandra compartió el PDF *"Laboratorio de Agentes · Taller Práctico A2A"*, que pedía:

1. **Etapa 1 — Diseña:** definir un perfil (NOMBRE, ESPECIALIDAD, PERSONALIDAD, SOBRE_MI, SKILLS), escribir un Blueprint en el README, **copiar el proyecto a una carpeta nueva `mi-agente`** (sin tocar el original), y personalizar 4 archivos (`prompts.py`, `herramientas.py`, `graph.py`, `langgraph.json`).
2. **Etapa 2 — Conecta y pregunta:** levantar el servidor en el puerto 2025, probar personalidad/conocimientos/memoria/tarjeta A2A desde un notebook.
3. **Etapa 3 — Hazlos conversar:** crear un segundo perfil (con un compañero) en el puerto 2026, descubrir ambos agentes y hacerlos resolver un reto juntos en 3 turnos.
4. **Cierre y entrega:** cerrar conexiones, entregar notebooks + blueprint + código, identificación del grupo.

## 5. Trabajo realizado según la guía

- **Perfil de Alejandra:** auditora especializada en cumplimiento normativo y tributario (CMF y SII), personalidad rigurosa/directa/paciente, 3 skills, y una herramienta `consultar_mis_apuntes` (conceptos, criterios, un caso real).
- **`mi-agente/`** creado como copia completa del proyecto base, con su propio venv, dependencias instaladas, grafo renombrado a `agente_alejandra`, servidor en el puerto **2025**.
- **`mi-agente-2/`** creado como segundo perfil **simulado por la misma autora** (no había compañero/a disponible en el momento): "**Benjamín**", especialista en **control interno y gestión de riesgos operacionales**, grafo `agente_benjamin`, servidor en el puerto **2026**.
- Pruebas realizadas y exitosas:
  - Presentación/personalidad del agente.
  - Uso de `consultar_mis_apuntes` (caso real).
  - Memoria entre turnos (mismo `thread_id`).
  - Descarga de la tarjeta A2A.
  - **Conversación de 3 turnos** entre Alejandra y Benjamín resolviendo un caso conjunto (empresa con atrasos tributarios recurrentes): Alejandra propuso diagnóstico SII/CMF, Benjamín agregó matriz de riesgo y segregación de funciones, Alejandra integró todo en un plan final de 4 fases.
- Blueprint y datos de identificación quedaron documentados en `mi-agente/README.md`.

## 6. Corrección importante: revertir el proyecto base

- Se detectó que el `plan.json` del proyecto base (`agente-viajes-a2a`) registra tareas ya "hechas" con evidencia específica (ej. `graph_id: agente_viajes`), y que el profesor dijo que **revisaría los JSON de cada estudiante**.
- Como la guía pedía dejar el proyecto base intacto y personalizar solo la copia, se **revirtió `agente-viajes-a2a`** a su estado original de agente de viajes (`prompts.py`, `herramientas.py`, `graph.py`, `langgraph.json`, `.env`, `README.md`), manteniendo toda la personalización únicamente en `mi-agente` y `mi-agente-2`.
- Se verificó que el proyecto base vuelve a responder como agente de viajes, coherente con `plan.json`.

## 7. Tema del proceso: OpenCode vs. Claude Code

- El profesor insistió mucho en que se usara **OpenCode** (con los agentes `@spec`/`@implementador` definidos en `AGENTS.md`/`.opencode/`), y dijo que revisaría el proceso, no solo el resultado.
- Todo el trabajo de esta conversación se hizo con **Claude Code**, no con OpenCode — se lo advertí explícitamente a Alejandra.
- Se analizaron 3 opciones: (A) instalar y usar OpenCode para rehacer el proceso, (B) ser transparente con el profesor sobre la herramienta usada, (C) usar OpenCode de ahora en más para tareas nuevas. Alejandra no se decidió por una sola; quedó pendiente.
- Se instaló **OpenCode Desktop** (`winget install SST.OpenCodeDesktop`) en su computadora. Se resolvió un error de arranque (`"Database is not empty and has no session table"`) renombrando una base de datos corrupta de un intento anterior (`~/.local/share/opencode/opencode.db`), y la app quedó funcionando.
- Pendiente: configurar una clave de API (Gemini o Anthropic) dentro de OpenCode. Alejandra decidió pausar este paso por cansancio.

## 8. Comunicación con el equipo (4 personas, redes distintas)

- Como los 4 integrantes del grupo están en redes distintas (no la misma sala/wifi), se necesitaba exponer cada agente a internet.
- Se instaló **cloudflared** (`winget install Cloudflare.cloudflared`) y se generaron túneles gratuitos tipo `https://...trycloudflare.com` apuntando al puerto 2025 de `mi-agente`.
- **Importante:** estos túneles son temporales, sin garantía de actividad, y generan una URL nueva cada vez que se reinician — no se guardan en ningún archivo ni se incluyen al entregar el proyecto.
- Se probó: un compañero ya se conectó exitosamente con la primera URL generada. El resto del grupo todavía no había terminado su propio agente.
- Se entregaron dos archivos Word descargables con las instrucciones para el equipo (`instrucciones_equipo.docx` e instrucciones más cortas en `script_verbal_equipo.docx`), además de la versión en Markdown.

## 9. Respaldos realizados

- `Taller agente auditora/respaldo/`: contiene `instrucciones_equipo.docx`, `instrucciones_equipo.md`, `script_verbal_equipo.docx`.
- `Taller agente auditora/respaldo/agente-viajes-a2a-backup-20261018_211853/`: copia completa del proyecto base ya revertido (sin `.venv` ni `.git`).

## 10. Preferencias de comunicación registradas

- Alejandra no es programadora: preferir instrucciones concretas, paso a paso, y hacer las cosas por terminal en vez de pedirle que navegue interfaces complejas de VS Code cuando sea posible.
- Español neutro, sin "vos" ni fraseo rioplatense (no es que quisiera modismos chilenos literales, sino evitar que sonara argentino).

---

## Pendientes al cierre de esta conversación

1. Decidir cómo manejar el tema OpenCode/proceso con el profesor (transparencia, uso futuro, o rehacer con OpenCode).
2. Configurar la clave de API dentro de OpenCode Desktop (Gemini o Anthropic).
3. Terminar de coordinar con los 3 compañeros restantes y repetir el descubrimiento de agentes cuando todos tengan su túnel activo.
4. Levantar un túnel nuevo la próxima vez que se necesite (las URLs de hoy ya no van a funcionar en otra sesión).
