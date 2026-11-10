"""Apuntes y herramientas del agente de Carlos Zapata · Taller A2A · Grupo 1.

`consultar_mis_apuntes` es la herramienta del taller (mis conocimientos en APUNTES).
`consultar_acciones` entrega datos de mercado del taller: precios simulados, pero coherentes
entre sí (una sola tasa de cambio, una sola fecha de corte y cifras derivadas en lugar de valores
inventados por separado).
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

# Datos simulados del taller. En producción serían APIs reales de mercado.
# Se guarda el precio en la moneda local; los valores en CLP se derivan con TASA_USD_CLP.
TASA_USD_CLP = 968.0
FECHA_CORTE = "2026-11-07"
FUENTE = "datos simulados del taller (no son precios reales de mercado)"

MERCADOS = {
    "US": "NASDAQ/NYSE (Estados Unidos)",
    "CL": "Bolsa de Santiago (Chile)",
}

ACCIONES = {
    ("AAPL", "US"): {"nombre": "Apple Inc.", "moneda_local": "USD", "precio_local": 342.10,
                     "var_pct": 1.24, "volumen": 54_300_000, "rango_52_semanas_local": (281.40, 355.90)},
    ("MSFT", "US"): {"nombre": "Microsoft Corp.", "moneda_local": "USD", "precio_local": 443.05,
                     "var_pct": -0.35, "volumen": 21_800_000, "rango_52_semanas_local": (389.10, 468.20)},
    ("NVDA", "US"): {"nombre": "NVIDIA Corp.", "moneda_local": "USD", "precio_local": 182.40,
                     "var_pct": 2.87, "volumen": 312_500_000, "rango_52_semanas_local": (96.80, 195.60)},
    ("AMZN", "US"): {"nombre": "Amazon.com Inc.", "moneda_local": "USD", "precio_local": 231.75,
                     "var_pct": 0.62, "volumen": 38_400_000, "rango_52_semanas_local": (178.20, 244.90)},
    ("GOOGL", "US"): {"nombre": "Alphabet Inc.", "moneda_local": "USD", "precio_local": 198.60,
                      "var_pct": -0.88, "volumen": 27_100_000, "rango_52_semanas_local": (158.40, 214.30)},
    ("TSLA", "US"): {"nombre": "Tesla Inc.", "moneda_local": "USD", "precio_local": 412.30,
                     "var_pct": -1.94, "volumen": 98_600_000, "rango_52_semanas_local": (182.00, 488.50)},
    ("KO", "US"): {"nombre": "The Coca-Cola Company", "moneda_local": "USD", "precio_local": 71.20,
                   "var_pct": 0.31, "volumen": 12_400_000, "rango_52_semanas_local": (60.10, 73.80)},
    ("SQM-B", "CL"): {"nombre": "Sociedad Química y Minera", "moneda_local": "CLP", "precio_local": 41850.0,
                      "var_pct": 2.10, "volumen": 1_420_000, "rango_52_semanas_local": (32800.0, 46500.0)},
    ("FALABELLA", "CL"): {"nombre": "Falabella S.A.", "moneda_local": "CLP", "precio_local": 3120.5,
                         "var_pct": -1.05, "volumen": 8_900_000, "rango_52_semanas_local": (2680.0, 3560.0)},
    ("CMPC", "CL"): {"nombre": "Empresas CMPC S.A.", "moneda_local": "CLP", "precio_local": 1684.0,
                     "var_pct": 0.48, "volumen": 5_200_000, "rango_52_semanas_local": (1420.0, 1890.0)},
    ("CCU", "CL"): {"nombre": "Compañía Cervecerías Unidas", "moneda_local": "CLP", "precio_local": 5980.0,
                    "var_pct": -0.72, "volumen": 1_100_000, "rango_52_semanas_local": (5210.0, 6540.0)},
    ("BCI", "CL"): {"nombre": "Banco de Crédito e Inversiones", "moneda_local": "CLP", "precio_local": 32450.0,
                    "var_pct": 1.15, "volumen": 2_300_000, "rango_52_semanas_local": (27100.0, 34100.0)},
    ("ANDINA-B", "CL"): {"nombre": "Embotelladora Andina S.A.", "moneda_local": "CLP", "precio_local": 2890.0,
                        "var_pct": 0.00, "volumen": 620_000, "rango_52_semanas_local": (2450.0, 3050.0)},
}


def _mercados_disponibles() -> str:
    return " o ".join(f"{clave} = {nombre}" for clave, nombre in MERCADOS.items())


def _tickers_de(pais: str) -> str:
    return ", ".join(sorted(ticker for (ticker, mercado) in ACCIONES if mercado == pais))


@tool
def consultar_mis_apuntes(tema: str = "") -> str:
    """Consulta mis apuntes: conceptos, criterios o caso. Vacío devuelve todos."""
    clave = tema.lower().strip()
    if not clave:
        return "\n".join(f"{nombre}: {texto}" for nombre, texto in APUNTES.items())
    return APUNTES.get(clave, "No tengo ese tema registrado. Consulta conceptos, criterios o caso.")


@tool
def consultar_acciones(ticker: str, pais: str) -> dict | str:
    """Consulta el precio y los datos de mercado de una acción del taller.

    `ticker` es el código de la acción (ej. AAPL, SQM-B) y `pais` el mercado donde cotiza (US o CL).
    Devuelve precio en moneda local y en CLP con la tasa usada, variación del día, volumen, rango
    de 52 semanas y fecha de corte. Si falta un dato o el ticker no está cubierto, devuelve un texto
    explicando qué falta.
    """
    codigo = (ticker or "").strip().upper()
    mercado = (pais or "").strip().upper()

    if not codigo:
        return "Necesito el ticker de la acción (por ejemplo AAPL o SQM-B). ¿Cuál quieres revisar?"

    if not mercado:
        return (
            f"Para consultar {codigo} necesito el mercado donde cotiza: {_mercados_disponibles()}. "
            "¿En cuál cotiza?"
        )

    if mercado not in MERCADOS:
        return f"No trabajo el mercado {mercado}. Mercados disponibles: {_mercados_disponibles()}."

    datos = ACCIONES.get((codigo, mercado))
    if datos is None:
        otros = sorted(p for (t, p) in ACCIONES if t == codigo)
        if otros:
            return (
                f"{codigo} no cotiza en {mercado}; lo tengo registrado en {', '.join(otros)}. "
                "¿Consulto ese mercado?"
            )
        return f"No tengo {codigo} en {mercado}. Cobertura actual: {_tickers_de(mercado)}."

    en_dolares = datos["moneda_local"] == "USD"
    factor = TASA_USD_CLP if en_dolares else 1.0
    precio_local = datos["precio_local"]
    minimo_local, maximo_local = datos["rango_52_semanas_local"]

    return {
        "ticker": codigo,
        "nombre": datos["nombre"],
        "mercado": MERCADOS[mercado],
        "pais": mercado,
        "moneda_local": datos["moneda_local"],
        "precio_local": precio_local,
        "moneda": "CLP",
        "precio_clp": round(precio_local * factor, 2),
        "tasa_usd_clp": TASA_USD_CLP if en_dolares else None,
        "variacion_dia_pct": datos["var_pct"],
        "volumen": datos["volumen"],
        "rango_52_semanas_clp": {
            "minimo": round(minimo_local * factor, 2),
            "maximo": round(maximo_local * factor, 2),
        },
        "distancia_al_maximo_52s_pct": round((maximo_local - precio_local) / maximo_local * 100, 2),
        "actualizado": FECHA_CORTE,
        "datos_simulados": True,
        "fuente": FUENTE,
    }


# Fundamentales simulados del taller: PER, deuda/patrimonio y márgenes.
# En producción vendrían de los estados financieros y de un proveedor de datos de mercado.
FUENTE_FUNDAMENTALES = "datos simulados del taller (no son cifras reales de mercado)"

FUNDAMENTALES = {
    ("AAPL", "US"): {"per": 31.4, "deuda_patrimonio": 1.87, "margen_bruto_pct": 46.2,
                     "margen_operativo_pct": 31.5, "margen_neto_pct": 26.3},
    ("MSFT", "US"): {"per": 35.2, "deuda_patrimonio": 0.42, "margen_bruto_pct": 69.8,
                     "margen_operativo_pct": 44.6, "margen_neto_pct": 35.9},
    ("NVDA", "US"): {"per": 48.6, "deuda_patrimonio": 0.16, "margen_bruto_pct": 74.9,
                     "margen_operativo_pct": 61.2, "margen_neto_pct": 55.0},
    ("AMZN", "US"): {"per": 41.3, "deuda_patrimonio": 0.58, "margen_bruto_pct": 48.5,
                     "margen_operativo_pct": 11.2, "margen_neto_pct": 9.4},
    ("GOOGL", "US"): {"per": 26.8, "deuda_patrimonio": 0.11, "margen_bruto_pct": 57.9,
                      "margen_operativo_pct": 32.1, "margen_neto_pct": 27.4},
    ("TSLA", "US"): {"per": 72.5, "deuda_patrimonio": 0.18, "margen_bruto_pct": 17.8,
                     "margen_operativo_pct": 9.6, "margen_neto_pct": 7.1},
    ("KO", "US"): {"per": 24.1, "deuda_patrimonio": 1.62, "margen_bruto_pct": 60.3,
                   "margen_operativo_pct": 24.7, "margen_neto_pct": 23.4},
    ("SQM-B", "CL"): {"per": 18.7, "deuda_patrimonio": 0.74, "margen_bruto_pct": 38.2,
                      "margen_operativo_pct": 27.5, "margen_neto_pct": 16.9},
    ("FALABELLA", "CL"): {"per": 12.3, "deuda_patrimonio": 1.05, "margen_bruto_pct": 34.6,
                          "margen_operativo_pct": 8.9, "margen_neto_pct": 4.2},
    ("CMPC", "CL"): {"per": 14.8, "deuda_patrimonio": 0.88, "margen_bruto_pct": 29.4,
                     "margen_operativo_pct": 12.7, "margen_neto_pct": 7.5},
    ("CCU", "CL"): {"per": 16.2, "deuda_patrimonio": 0.61, "margen_bruto_pct": 44.1,
                    "margen_operativo_pct": 12.9, "margen_neto_pct": 8.3},
    ("BCI", "CL"): {"per": 9.4, "deuda_patrimonio": 4.80, "margen_bruto_pct": None,
                    "margen_operativo_pct": 42.1, "margen_neto_pct": 33.8,
                    "nota": "El margen bruto no aplica a bancos; se informan margen operativo y neto."},
    ("ANDINA-B", "CL"): {"per": 15.6, "deuda_patrimonio": 0.52, "margen_bruto_pct": 41.3,
                         "margen_operativo_pct": 14.2, "margen_neto_pct": 9.8},
}


@tool
def consultar_fundamentales(ticker: str, pais: str) -> dict | str:
    """Consulta los fundamentales de una acción del taller.

    `ticker` es el código (ej. AAPL, SQM-B) y `pais` el mercado (US o CL). Devuelve PER, ratio de
    endeudamiento (deuda/patrimonio), margen bruto, operativo y neto, con fecha de corte. Si el
    ticker no está cubierto, devuelve un texto explicando qué falta.
    """
    codigo = (ticker or "").strip().upper()
    mercado = (pais or "").strip().upper()

    if not codigo:
        return "Necesito el ticker de la acción (por ejemplo AAPL o SQM-B). ¿Cuál quieres revisar?"
    if not mercado:
        return (
            f"Para consultar los fundamentales de {codigo} necesito el mercado donde cotiza: "
            f"{_mercados_disponibles()}. ¿En cuál cotiza?"
        )
    if mercado not in MERCADOS:
        return f"No trabajo el mercado {mercado}. Mercados disponibles: {_mercados_disponibles()}."

    datos = FUNDAMENTALES.get((codigo, mercado))
    if datos is None:
        otros = sorted(p for (t, p) in FUNDAMENTALES if t == codigo)
        if otros:
            return f"{codigo} no cotiza en {mercado}; lo tengo registrado en {', '.join(otros)}. ¿Consulto ese mercado?"
        return f"No tengo fundamentales de {codigo} en {mercado}. Cobertura actual: {_tickers_de(mercado)}."

    return dict(
        datos,
        ticker=codigo,
        mercado=MERCADOS[mercado],
        actualizado=FECHA_CORTE,
        datos_simulados=True,
        fuente=FUENTE_FUNDAMENTALES,
    )


@tool
def derivar_a_cumplimiento(motivo: str) -> str:
    """Deriva una revisión de contingencias normativas o tributarias al agente de auditoría.

    Úsala cuando la consulta pida opinar sobre cumplimiento, sanciones, deuda tributaria o
    normativa: esa revisión la realiza el agente de cumplimiento y auditoría (agente_alejandra).
    """
    detalle = (motivo or "").strip() or "Revisión de cumplimiento normativo o tributario"
    return (
        "Esta revisión corresponde al agente de cumplimiento y auditoría (agente_alejandra).\n"
        f"Motivo: {detalle}.\n"
        "Qué hacer: solicitar la revisión indicando la razón social o el nombre de fantasía de la "
        "empresa (no hace falta el RUT). Ese agente consulta SII y CMF, revisa deuda tributaria, "
        "sanciones y normativa aplicable, y entrega el diagnóstico con el siguiente paso."
    )


HERRAMIENTAS = [consultar_mis_apuntes, consultar_acciones, consultar_fundamentales, derivar_a_cumplimiento]
