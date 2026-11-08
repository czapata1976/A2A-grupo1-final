"""Apuntes y herramientas del agente de Carlos Zapata · Taller A2A · Grupo 1.

`consultar_mis_apuntes` es la herramienta del taller (mis conocimientos en APUNTES).
`consultar_acciones` es la herramienta extra de la especialidad: datos de mercado simulados.
"""
from langchain_core.tools import tool

APUNTES = {
    "conceptos": (
        "PER: compara el precio de la acción con la utilidad por acción. Un PER alto sugiere expectativas "
        "de crecimiento; uno bajo puede indicar subvaloración o riesgo. "
        "Riesgo: concentrar todo en un solo papel multiplica la volatilidad del portafolio. "
        "Diversificación: repartir entre sectores y mercados reduce el riesgo sin bajar necesariamente "
        "la rentabilidad esperada."
    ),
    "criterios": (
        "Evalúo una decisión de inversión con cuatro criterios: (1) el precio tiene sentido frente a las "
        "utilidades (PER y comparables), (2) el riesgo es entendible y está acotado, (3) la posición queda "
        "diversificada y (4) hay un motivo escrito para entrar y para salir. Si falta uno de los cuatro, "
        "no es una decisión: es una apuesta."
    ),
    "caso": (
        "Caso de estudio (material del curso): una empresa con buenos fundamentos y un PER razonable "
        "arrastraba una observación tributaria pendiente. Lo aprendido: el análisis financiero no basta; "
        "hay que revisar el cumplimiento normativo antes de invertir, y por eso conviene cruzar la mirada "
        "financiera con la de un especialista en cumplimiento."
    ),
}

# Datos simulados del taller: en producción serían APIs reales de mercado.
ACCIONES = {
    ("AAPL", "US"): {"nombre": "Apple Inc.", "mercado": "NASDAQ", "precio": 331250.0, "moneda": "CLP",
                     "precio_local": 342.10, "moneda_local": "USD", "var_pct": 1.24},
    ("MSFT", "US"): {"nombre": "Microsoft Corp.", "mercado": "NASDAQ", "precio": 428900.0, "moneda": "CLP",
                     "precio_local": 443.05, "moneda_local": "USD", "var_pct": -0.35},
    ("SQM-B", "CL"): {"nombre": "Sociedad Química y Minera", "mercado": "Bolsa de Santiago",
                      "precio": 41850.0, "moneda": "CLP", "precio_local": 41850.0, "moneda_local": "CLP",
                      "var_pct": 2.10},
    ("FALABELLA", "CL"): {"nombre": "Falabella S.A.", "mercado": "Bolsa de Santiago", "precio": 3120.5,
                          "moneda": "CLP", "precio_local": 3120.5, "moneda_local": "CLP", "var_pct": -1.05},
}


@tool
def consultar_mis_apuntes(tema: str = "") -> str:
    """Consulta mis apuntes: conceptos, criterios o caso. Vacío devuelve todos."""
    clave = tema.lower().strip()
    if not clave:
        return "\n".join(f"{nombre}: {texto}" for nombre, texto in APUNTES.items())
    return APUNTES.get(clave, "No tengo ese tema registrado. Consulta conceptos, criterios o caso.")


@tool
def consultar_acciones(ticker: str, pais: str) -> dict | str:
    """Consulta el precio y los datos de mercado de una acción.

    `ticker` es el código de la acción (ej. AAPL, SQM-B) y `pais` el mercado donde cotiza (ej. US, CL).
    Devuelve nombre, mercado, precio en CLP, variación del día y el precio en moneda local.
    Si falta el país o no hay dato para ese ticker, devuelve un texto pidiendo o explicando lo que falta.
    """
    if not pais or not pais.strip():
        return f"No puedo consultar {ticker.upper()} sin saber el país (mercado). ¿En qué mercado cotiza? (ej. US, CL)"
    datos = ACCIONES.get((ticker.upper(), pais.upper()))
    if datos is None:
        disponibles = ", ".join(sorted(t for t, _ in ACCIONES))
        return f"No tengo datos de {ticker.upper()} en el mercado {pais.upper()}. Tickers disponibles: {disponibles}."
    return dict(datos, ticker=ticker.upper(), pais=pais.upper())


HERRAMIENTAS = [consultar_mis_apuntes, consultar_acciones]
