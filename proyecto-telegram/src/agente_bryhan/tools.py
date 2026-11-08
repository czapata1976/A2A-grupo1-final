"""Herramientas del agente de Bryhan. Deterministas: no llaman al modelo."""
import json

from langchain_core.tools import tool

CONOCIMIENTOS = json.loads('{"conceptos": [{"nombre": "AI Engineering", "contenido": "Diseño e integración de soluciones de inteligencia artificial aplicadas a procesos empresariales y financieros.", "fuente": "Trayectoria profesional documentada como AI Engineer en banca chilena."}, {"nombre": "Data Science y Machine Learning", "contenido": "Uso de Python, SQL, R, analítica y Machine Learning para trabajar con datos y problemas de negocio.", "fuente": "Experiencia profesional y docente documentada."}, {"nombre": "Automatización inteligente", "contenido": "Evaluación y automatización de procesos mediante Python, RPA, Blue Prism, Power Automate y tecnologías relacionadas.", "fuente": "Experiencia documentada en Inteligencia Operacional e hiperautomatización."}, {"nombre": "Procesamiento documental", "contenido": "Extracción y procesamiento de información documental con soluciones como Azure Document Intelligence y flujos de datos.", "fuente": "Proyecto documentado de automatización del arqueo de contratos de derivados."}, {"nombre": "LLMs, RAG y agentes", "contenido": "Conocimientos en modelos de lenguaje, embeddings, RAG, LangChain, LangGraph, agentes y sistemas multiagente.", "fuente": "Formación y conocimientos profesionales documentados; el nivel debe expresarse conservadoramente cuando no esté especificado."}, {"nombre": "Gobernanza y protección", "contenido": "Consideración de ciberseguridad, gobernanza y protección de datos en el diseño de soluciones.", "fuente": "Formación documentada en estas materias."}], "criterios": ["Comprender el problema de negocio y el proceso actual antes de elegir tecnología.", "No asumir que todo problema requiere inteligencia artificial.", "Evaluar reglas, decisiones, datos disponibles, volumen y restricciones.", "Separar automatización tradicional, procesamiento de datos, Machine Learning, IA generativa y procesamiento documental.", "Considerar integración, seguridad, evaluación, operación y mantenibilidad.", "Explicar beneficios, riesgos, limitaciones y supuestos de forma verificable."], "caso": {"nombre": "Automatización del arqueo de contratos de derivados", "contexto": "Proyecto documentado durante la experiencia de Bryhan en Inteligencia Operacional en Banco Santander Chile.", "aporte_demostrable": "Automatización de un proceso documental y operativo mediante Python, Azure Databricks, Data Lake y Azure Document Intelligence.", "resultado": "La solución redujo significativamente el esfuerzo operativo, los tiempos de procesamiento y el trabajo manual; no se atribuyen métricas específicas porque no están documentadas.", "aprendizaje": "La selección tecnológica debe partir del proceso, los datos, las reglas, los controles y los criterios de éxito, no de asumir que todo requiere IA."}}')


@tool
def consultar_conocimientos(tema: str = "") -> str:
    """Consulta la base de Bryhan: conceptos, criterios o caso. Vacío devuelve todo."""
    clave = tema.lower().strip()
    if not clave:
        return json.dumps(CONOCIMIENTOS, ensure_ascii=False, indent=2)
    if clave not in CONOCIMIENTOS:
        return "Tema no registrado. Usa: conceptos, criterios o caso."
    return json.dumps(CONOCIMIENTOS[clave], ensure_ascii=False, indent=2)


@tool
def comparar_opciones(opciones: list[str], criterios: list[str]) -> str:
    """Compara opciones con criterios explicitos; no inventa datos no entregados."""
    opciones = [str(x).strip() for x in opciones if str(x).strip()]
    criterios = [str(x).strip() for x in criterios if str(x).strip()]
    if len(opciones) < 2:
        return "Se necesitan al menos dos opciones para comparar."
    if not criterios:
        criterios = ["ajuste al objetivo", "costo o esfuerzo", "riesgos", "viabilidad"]
    lineas = ["Matriz de comparacion (completar solo con antecedentes disponibles):"]
    for opcion in opciones:
        lineas.append("\nOpcion: " + opcion)
        lineas.extend("- " + criterio + ": por evaluar" for criterio in criterios)
    lineas.append("\nNo elegir automaticamente: explicar trade-offs y pedir datos faltantes.")
    return "\n".join(lineas)


@tool
def disenar_plan(objetivo: str, contexto: str, restricciones: str = "") -> str:
    """Estructura un plan con diagnostico, diseno, ejecucion, verificacion y ajuste."""
    if not objetivo.strip() or not contexto.strip():
        return "Para disenar el plan se necesitan un objetivo y un contexto."
    return (
        "PLAN BASE\n"
        "Objetivo: " + objetivo.strip() + "\n"
        "Contexto: " + contexto.strip() + "\n"
        "Restricciones: " + (restricciones.strip() or "No informadas") + "\n\n"
        "1. Diagnostico: situacion actual, participantes y resultado esperado.\n"
        "2. Diseno: alternativas, criterios, responsables y riesgos.\n"
        "3. Ejecucion: acciones, dependencias y recursos.\n"
        "4. Verificacion: evidencia observable de avance y exito.\n"
        "5. Ajuste: resultados, aprendizajes y siguiente ciclo."
    )


HERRAMIENTAS = [consultar_conocimientos, comparar_opciones, disenar_plan]
