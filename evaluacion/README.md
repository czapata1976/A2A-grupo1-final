# Evaluación con promptfoo · los cuatro agentes del Grupo 1

Evalúa los cuatro agentes de la entrega con **cinco preguntas cada uno** (de fáciles a difíciles) y
tres comprobaciones por prueba:

1. una comprobación mecánica de **contenido esperado** (`icontains` / `icontains-any`),
2. una comprobación mecánica de **contenido prohibido** (`not-icontains`),
3. una **rúbrica** calificada por un segundo modelo (`llm-rubric`): ¿es amable y correcta?

## Archivos

| Archivo | Para qué |
| --- | --- |
| `promptfooconfig.yaml` | Prompts, proveedor, 20 pruebas y aserciones. |
| `providers/provider_agente.py` | Proveedor local: ejecuta el grafo real de cada agente. |
| `agente.py` | Runner con `--saltos` (traza paso a paso) y `--diagrama` (Mermaid). |
| `resumen_resultados.py` | Convierte `resultados.json` en una tabla Markdown. |
| `.env` | Clave del **modelo calificador** (no la de los agentes). Se crea desde `.env.example`. |

## 1. Requisitos

```powershell
npm install -g promptfoo        # versión usada: 0.125.1
cd evaluacion
copy .env.example .env          # y pega GOOGLE_API_KEY / GEMINI_API_KEY
```

Cada agente lee su propia clave desde su carpeta (`mi-agente-cz/.env`, `agente-bryhan/.env`,
`mi-agente-ale/.env`, `mi-agente-CM/.env`). No hace falta levantar `langgraph dev`: el proveedor
importa el grafo directamente con el `.venv` de cada agente.

## 2. Correr y ver

```powershell
cd evaluacion
promptfoo eval --output resultados.json
promptfoo view                  # http://localhost:15500
```

## 3. Cómo leer la tabla

- **Description**: el caso (`agente · n/5 · nivel · tema`).
- **Variables** (`agente`, `pregunta`): lo que recibe el proveedor.
- **Output / columna de cada agente**: la respuesta del agente y el veredicto PASS/FAIL.
- **Assertions / Score**: `15/15 passed`, el puntaje de la rúbrica y el detalle de cada aserción.
- **Latency / Tokens**: milisegundos y consumo; el encabezado resume `5/5 cases` y el % del agente.

Una prueba **pasa** solo si *todas* sus aserciones pasan: contiene lo esperado, no contiene lo
prohibido y la rúbrica llega al umbral (0.7). Si falla una, la celda queda en FAIL y el detalle
muestra qué aserción falló y su razón.

## 4. Cuando una prueba falla: `--saltos` y `--diagrama`

Copia la **misma pregunta** del caso fallido:

```powershell
python evaluacion\agente.py --agente agente_alejandra `
  --pregunta "¿Qué fondo de los que revisas tiene la mayor concentración en un solo emisor?" --saltos
```

`--saltos` imprime cada nodo del grafo (`model`, `tools`), la herramienta llamada con sus
argumentos, lo que devolvió y la respuesta final. Con eso se distingue:

- el agente **no llamó** la herramienta que debía,
- la llamó con **argumentos equivocados** (p. ej. `tema="inmobiliario"` en vez de `"caso"`),
- la herramienta respondió bien y el modelo **redactó mal**,
- el agente respondió bien y la **aserción** era demasiado literal → se corrige el test.

```powershell
python evaluacion\agente.py --agente agente_bryhan --diagrama
```

`--diagrama` imprime el grafo en Mermaid (el mismo de los notebooks), útil para explicar qué nodo
debería haberse ejecutado.

## 5. Resultado de la última corrida

**20/20 aprobadas (100 %)** en la corrida `eval-Ozb` (2026-11-10). La rúbrica de calidad pasó en todos
los casos con score 1,0.

A partir de las corridas anteriores se corrigió lo que la evaluación detectó:

| Hallazgo | Corrección |
| --- | --- |
| `agente_alejandra` no podía enumerar fondos | Nueva herramienta `listar_fondos` |
| `agente_CM` no resolvía temas libres en sus apuntes | `consultar_mis_apuntes` busca por contenido |
| `agente_czz` narraba «procedo a consultar» sin ejecutar | Regla «ejecuta, no anuncies» en el prompt |
| Aserciones demasiado literales | `icontains-any` con sinónimos en las pruebas 18-20 |
| El calificador marcaba 2026 como fecha inválida | La rúbrica declara el contexto temporal del taller |

El detalle se ve con `--saltos` y queda en `resultados.json`.
