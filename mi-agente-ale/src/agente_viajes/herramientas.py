"""Herramientas del agente auditor. Datos simulados: en producción vendrían de custodios,
administradoras, la CMF (ej. SEIL, informes de valorización) o el SII.

Todas son deterministas: no llaman al modelo y devuelven texto o diccionarios con los datos.
"""
import unicodedata

from langchain_core.tools import tool

FONDOS = {
    "FM Acciones Chile": {"tipo": "accionario", "patrimonio_clp": 45_000_000_000, "ter": 1.8,
                            "rentabilidad_12m": 7.3, "mayor_emisor_pct": 12.5},
    "FM Deuda Privada": {"tipo": "deuda", "patrimonio_clp": 80_000_000_000, "ter": 1.1,
                          "rentabilidad_12m": 5.1, "mayor_emisor_pct": 22.0},
    "FM Inmobiliario": {"tipo": "inmobiliario", "patrimonio_clp": 120_000_000_000, "ter": 2.0,
                         "rentabilidad_12m": 6.8, "mayor_emisor_pct": 35.0},
}

LIMITES_NORMATIVOS = {
    "concentracion_por_emisor_pct": 20.0,   # NCG 365 — límite referencial por emisor
    "liquidez_minima_pct": 5.0,
}


@tool
def consultar_fondo(nombre_fondo: str) -> dict:
    """Devuelve datos del fondo: tipo, patrimonio en CLP, TER, rentabilidad a 12 meses y
    concentración en el mayor emisor (%). Error como texto si el fondo no existe."""
    f = FONDOS.get(nombre_fondo)
    if not f:
        return {"error": f"No se encontró el fondo '{nombre_fondo}'. Fondos disponibles: {list(FONDOS)}"}
    return dict(f, nombre=nombre_fondo)


@tool
def listar_fondos() -> list[dict]:
    """Lista los fondos disponibles con tipo, concentración en el mayor emisor y rentabilidad.

    Sirve para responder "qué fondos revisas" o "cuál tiene la mayor concentración" sin pedir
    nombres: ya devuelve el universo completo de fondos del taller.
    """
    limite = LIMITES_NORMATIVOS["concentracion_por_emisor_pct"]
    return [
        {
            "nombre": nombre,
            "tipo": datos["tipo"],
            "mayor_emisor_pct": datos["mayor_emisor_pct"],
            "rentabilidad_12m_pct": datos["rentabilidad_12m"],
            "cumple_ncg_365": datos["mayor_emisor_pct"] <= limite,
        }
        for nombre, datos in FONDOS.items()
    ]


@tool
def revisar_cumplimiento_normativo(nombre_fondo: str) -> dict:
    """Compara la concentración por emisor del fondo contra el límite normativo (NCG 365, 20%).
    Devuelve si cumple o no, y el margen. Error como texto si el fondo no existe."""
    f = FONDOS.get(nombre_fondo)
    if not f:
        return {"error": f"No se encontró el fondo '{nombre_fondo}'."}
    limite = LIMITES_NORMATIVOS["concentracion_por_emisor_pct"]
    cumple = f["mayor_emisor_pct"] <= limite
    return {
        "nombre": nombre_fondo,
        "mayor_emisor_pct": f["mayor_emisor_pct"],
        "limite_pct": limite,
        "cumple": cumple,
        "margen_pct": round(limite - f["mayor_emisor_pct"], 2),
    }


@tool
def calcular_ratios_fondo(nombre_fondo: str) -> dict:
    """Calcula ratios clave de auditoría del fondo: TER (costo total como % del patrimonio)
    y rentabilidad neta estimada a 12 meses (rentabilidad - TER). Error como texto si no existe."""
    f = FONDOS.get(nombre_fondo)
    if not f:
        return {"error": f"No se encontró el fondo '{nombre_fondo}'."}
    return {
        "nombre": nombre_fondo,
        "ter_pct": f["ter"],
        "rentabilidad_bruta_12m_pct": f["rentabilidad_12m"],
        "rentabilidad_neta_estimada_pct": round(f["rentabilidad_12m"] - f["ter"], 2),
    }


@tool
def generar_checklist_auditoria(tipo_fondo: str) -> list[str]:
    """Genera un checklist de auditoría según el tipo de fondo: 'accionario', 'deuda' o
    'inmobiliario'. Devuelve lista vacía si el tipo no es reconocido."""
    base = [
        "Verificar valorización de cartera vs. custodio",
        "Revisar concentración por emisor vs. límite normativo",
        "Confirmar reglamento interno vigente y firmado por CMF",
    ]
    extra = {
        "accionario": ["Revisar liquidez de posiciones y volumen transado"],
        "deuda": ["Revisar clasificación de riesgo (rating) de cada instrumento"],
        "inmobiliario": ["Revisar tasación independiente de cada activo (vigencia < 12 meses)"],
    }
    if tipo_fondo.lower() not in extra:
        return []
    return base + extra[tipo_fondo.lower()]


EMPRESAS_SII = {
    "76.123.456-7": {
        "razon_social": "Inversiones del Sur SpA",
        "nombre_fantasia": "Inversiones del Sur",
        "estado_actividad": "vigente",
        "declaraciones_al_dia": True,
        "ultima_declaracion_renta": "2026-04-28",
        "deuda_tributaria_clp": 0,
        "deuda_detalle": [],
        "observaciones": [],
    },
    "77.987.654-3": {
        "razon_social": "Comercial Andina Ltda",
        "nombre_fantasia": "Comercial Andina",
        "estado_actividad": "vigente",
        "declaraciones_al_dia": False,
        "ultima_declaracion_renta": "2025-04-30",
        "deuda_tributaria_clp": 12_480_000,
        "deuda_detalle": [
            "IVA pendiente marzo 2026: $7.480.000",
            "Reajustes e intereses: $5.000.000",
        ],
        "observaciones": ["Atraso en declaración de renta 2026", "IVA pendiente marzo 2026"],
    },
    "78.555.111-2": {
        "razon_social": "Tecnología Pacífico S.A.",
        "nombre_fantasia": "Tecnología Pacífico",
        "estado_actividad": "término de giro",
        "declaraciones_al_dia": True,
        "ultima_declaracion_renta": "2025-04-29",
        "deuda_tributaria_clp": 0,
        "deuda_detalle": [],
        "observaciones": [],
    },
    "79.123.456-8": {
        "razon_social": "Viña Los Andes SpA",
        "nombre_fantasia": "Viña Los Andes",
        "estado_actividad": "vigente",
        "declaraciones_al_dia": False,
        "ultima_declaracion_renta": "2025-04-30",
        "deuda_tributaria_clp": 18_450_000,
        "deuda_detalle": [
            "IVA febrero 2026: $6.300.000",
            "PPM marzo 2026: $4.150.000",
            "Reajustes e intereses: $8.000.000",
        ],
        "observaciones": ["Atraso en declaración de renta 2026"],
    },
}

EMPRESAS_CMF = {
    "76.123.456-7": {"fiscalizada_cmf": False, "normativa_aplicable": [], "sanciones_vigentes": []},
    "77.987.654-3": {"fiscalizada_cmf": True, "normativa_aplicable": ["NCG 461", "Ley de Sociedades Anónimas"],
                      "sanciones_vigentes": ["Multa 2025 por entrega tardía de EEFF"]},
    "78.555.111-2": {"fiscalizada_cmf": True, "normativa_aplicable": ["NCG 461"], "sanciones_vigentes": []},
    "79.123.456-8": {"fiscalizada_cmf": False, "normativa_aplicable": [], "sanciones_vigentes": []},
}


def _normalizar_nombre(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", (texto or "").lower())
    return "".join(letra for letra in descompuesto if not unicodedata.combining(letra)).strip()


@tool
def buscar_rut_empresa(nombre: str) -> dict | str:
    """Busca el RUT de una empresa por su razón social o nombre de fantasía (datos simulados).

    Devuelve el RUT, la razón social, el estado de actividad y la deuda tributaria vigente.
    Si hay varias coincidencias, devuelve la lista para que se elija una. Nunca se debe pedir
    el RUT a la persona: esta herramienta lo resuelve a partir del nombre.
    """
    clave = _normalizar_nombre(nombre)
    if not clave:
        return "Necesito la razón social o el nombre de fantasía de la empresa."
    coincidencias = []
    for rut, datos in EMPRESAS_SII.items():
        textos = [_normalizar_nombre(datos["razon_social"]), _normalizar_nombre(datos.get("nombre_fantasia", ""))]
        if any(texto and (clave in texto or texto in clave) for texto in textos):
            coincidencias.append(
                {
                    "rut": rut,
                    "razon_social": datos["razon_social"],
                    "nombre_fantasia": datos.get("nombre_fantasia"),
                    "estado_actividad": datos["estado_actividad"],
                    "declaraciones_al_dia": datos["declaraciones_al_dia"],
                    "deuda_tributaria_clp": datos["deuda_tributaria_clp"],
                }
            )
    if not coincidencias:
        disponibles = ", ".join(datos["razon_social"] for datos in EMPRESAS_SII.values())
        return f"No encontré '{nombre}'. Empresas disponibles: {disponibles}."
    if len(coincidencias) > 1:
        return {
            "coincidencias": coincidencias,
            "mensaje": "Hay varias empresas que coinciden. Indica cuál revisar.",
        }
    return coincidencias[0]


@tool
def consultar_sii(rut_empresa: str) -> dict:
    """Consulta el estado tributario de una empresa en el SII por su RUT (formato 12.345.678-9):
    estado de actividad, si las declaraciones están al día, fecha de la última declaración de renta
    y observaciones vigentes. Error como texto si el RUT no existe (datos simulados)."""
    e = EMPRESAS_SII.get(rut_empresa)
    if not e:
        return {"error": f"No se encontró el RUT '{rut_empresa}' en el SII (simulado)."}
    return dict(e, rut=rut_empresa)


@tool
def consultar_cmf(rut_empresa: str) -> dict:
    """Consulta si una empresa está fiscalizada por la CMF por su RUT, qué normativa le aplica
    y si tiene sanciones vigentes. Error como texto si el RUT no existe (datos simulados)."""
    e = EMPRESAS_CMF.get(rut_empresa)
    if not e:
        return {"error": f"No se encontró el RUT '{rut_empresa}' en la CMF (simulado)."}
    return dict(e, rut=rut_empresa)


@tool
def verificar_cumplimiento_contable(rut_empresa: str) -> dict:
    """Cruza los datos del SII y la CMF de una empresa (por RUT) para determinar si su
    administración y registros contables cumplen con las normas: declaraciones al día, sin
    sanciones vigentes y sin observaciones pendientes. Devuelve si cumple, las alertas detectadas
    y la normativa aplicable. Error como texto si el RUT no existe en ninguna de las dos fuentes."""
    sii = EMPRESAS_SII.get(rut_empresa)
    cmf = EMPRESAS_CMF.get(rut_empresa)
    if not sii and not cmf:
        return {"error": f"No se encontró el RUT '{rut_empresa}' en SII ni en CMF."}
    alertas = []
    if sii and not sii["declaraciones_al_dia"]:
        alertas.append("Declaraciones tributarias atrasadas (SII).")
    if sii and sii.get("deuda_tributaria_clp"):
        alertas.append(f"Deuda tributaria vigente: ${sii['deuda_tributaria_clp']:,.0f} CLP.".replace(",", "."))
    if sii:
        alertas.extend(sii["observaciones"])
    if cmf:
        alertas.extend(cmf["sanciones_vigentes"])
    return {
        "rut": rut_empresa,
        "cumple": len(alertas) == 0,
        "alertas": alertas,
        "deuda_tributaria_clp": sii["deuda_tributaria_clp"] if sii else 0,
        "normativa_aplicable": cmf["normativa_aplicable"] if cmf else [],
    }


@tool
def generar_checklist_cumplimiento_empresa(tipo_empresa: str) -> list[str]:
    """Genera un checklist de auditoría de cumplimiento administrativo y contable según el tipo
    de empresa: 'sa' (sociedad anónima), 'spa' o 'ltda'. Devuelve lista vacía si el tipo no es
    reconocido."""
    base = [
        "Verificar declaraciones tributarias al día en el SII",
        "Revisar sanciones o alertas vigentes en la CMF",
        "Confirmar actas de directorio/junta de accionistas vigentes",
    ]
    extra = {
        "sa": ["Revisar entrega oportuna de Estados Financieros a la CMF (NCG 461)"],
        "spa": ["Revisar registro de accionistas y pactos actualizados"],
        "ltda": ["Revisar modificaciones societarias inscritas en el Conservador de Comercio"],
    }
    if tipo_empresa.lower() not in extra:
        return []
    return base + extra[tipo_empresa.lower()]


APUNTES = {
    "conceptos": ("Tres conceptos clave de mi especialidad: (1) Concentración por emisor (NCG 365): "
                  "ningún instrumento de un mismo emisor puede superar el 20% del patrimonio de un "
                  "fondo. (2) Declaración al día: una empresa está al día cuando no tiene atrasos en "
                  "renta ni IVA ante el SII. (3) Fiscalización CMF: una sociedad anónima siempre está "
                  "fiscalizada por la CMF; una SpA o Ltda, solo si capta ahorro público o emite deuda."),
    "criterios": ("Evalúo una buena auditoría por: que cruce al menos dos fuentes independientes "
                  "(ej. SII y CMF) antes de concluir; que distinga un hallazgo confirmado por una "
                  "herramienta de una sugerencia mía; y que termine siempre con un siguiente paso "
                  "concreto, no solo con un diagnóstico."),
    "caso": ("Un caso real del tipo que reviso: un fondo de deuda con concentración en un solo emisor "
             "al 22% (2 puntos sobre el límite de la NCG 365). El aprendizaje fue que el exceso puede "
             "ser pasivo (por un rescate de otros aportantes) y no necesariamente una compra activa; "
             "por eso siempre pido la fecha en que se originó el exceso antes de calificarlo como "
             "incumplimiento grave."),
}


@tool
def consultar_mis_apuntes(tema: str = "") -> str:
    """Consulta mis apuntes: conceptos, criterios o caso. Vacío devuelve todos."""
    clave = tema.lower().strip()
    if not clave:
        return "\n".join(
            f"{nombre}: {texto}" for nombre, texto in APUNTES.items()
        )
    return APUNTES.get(
        clave,
        "No tengo ese tema registrado. Consulta conceptos, criterios o caso."
    )


HERRAMIENTAS = [buscar_rut_empresa, listar_fondos, consultar_fondo, revisar_cumplimiento_normativo,
                calcular_ratios_fondo, generar_checklist_auditoria, consultar_sii, consultar_cmf,
                verificar_cumplimiento_contable, generar_checklist_cumplimiento_empresa,
                consultar_mis_apuntes]
