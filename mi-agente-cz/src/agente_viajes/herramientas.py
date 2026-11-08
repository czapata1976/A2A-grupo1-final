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


HERRAMIENTAS = [consultar_mis_apuntes, consultar_acciones]
