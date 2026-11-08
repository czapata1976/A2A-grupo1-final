from langchain_core.tools import tool

APUNTES = {
    "conceptos": (
        "1. Análisis de necesidades: identificar el problema que requiere "
        "solución mediante la observación del contexto, las consultas de "
        "las personas y la revisión de antecedentes documentales.\n"
        "2. Propuesta de valor: explicar qué necesidad resuelve un servicio "
        "o proyecto, para quién y qué beneficio concreto ofrece. "
        "Los beneficios comunicados deben tener respaldo.\n"
        "3. Viabilidad de proyectos: evaluar si una propuesta puede ejecutarse "
        "considerando recursos, costos, plazos, requisitos y riesgos. "
        "Distinguir siempre los antecedentes verificados de los supuestos."
    ),
    "criterios": (
        "Una buena solución responde directamente a la necesidad consultada. "
        "Primero observo el contexto y reviso los antecedentes documentales. "
        "Luego evalúo su pertinencia, viabilidad y beneficio esperado. "
        "Comparo alternativas según costos, plazos, recursos y riesgos, "
        "sin agregar complejidad innecesaria. La recomendación debe explicar "
        "qué hacer, por qué y cuáles son los pasos siguientes. "
        "Si falta información indispensable, la solicito antes de concluir. "
        "La respuesta debe ser empática, directa y educada, y limitarse "
        "a lo consultado."
    ),
    "caso": (
        "CASO FICTICIO ILUSTRATIVO: no corresponde a una experiencia real "
        "de la persona representada.\n"
        "Un proyecto inmobiliario recibía consultas a través de campañas "
        "digitales, pero pocas se convertían en visitas comerciales. "
        "Para comprender el problema, se analizaron las consultas recibidas, "
        "los registros de seguimiento y la información utilizada en las campañas. "
        "Se identificó que los anuncios destacaban atributos generales, "
        "sin responder a las necesidades de los potenciales compradores, "
        "y que el seguimiento comercial no tenía plazos definidos. "
        "Se propuso segmentar a los interesados según sus necesidades, "
        "ajustar la propuesta de valor con beneficios verificables y establecer "
        "un proceso de contacto oportuno para resolver dudas y coordinar visitas. "
        "La evaluación consideraría el porcentaje de consultas calificadas, "
        "la conversión de consultas en visitas, la conversión de visitas en ventas "
        "y el costo de adquisición de clientes. "
        "No se atribuyen resultados, porque este caso es hipotético.\n"
        "Aprendizaje del caso: una solución comercial requiere conectar "
        "las necesidades del cliente con una propuesta de valor fundamentada "
        "y coordinar el marketing con el seguimiento de ventas. "
        "Antes de aumentar la inversión publicitaria, conviene identificar "
        "en qué etapa se pierden las oportunidades."
    ),
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
        "No tengo ese tema registrado. Consulta conceptos, criterios o caso.",
    )


HERRAMIENTAS = [consultar_mis_apuntes]

