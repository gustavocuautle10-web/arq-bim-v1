"""
ARQ-BIM V1 — agentes/crew_agente.py
Agente CrewAI OPCIONAL y ligero.
Rol: traducir requerimientos de cliente en texto libre
     → JSON estructurado para los módulos Python deterministas.

IMPORTANTE:
  - Este agente SOLO pre-procesa texto libre de entrada.
  - La lógica normativa y de áreas es 100% determinista en Python.
  - CrewAI nunca toca validador.py ni modifica reglas NTC-CDMX.

Dependencias:
  pip install crewai crewai-tools langchain-openai

Uso en Colab:
  from agentes.crew_agente import procesar_requerimientos_cliente
  datos = procesar_requerimientos_cliente(texto_libre)
  # datos → dict con proyecto, terreno y programa_arquitectonico
"""
from __future__ import annotations

import json
import os
from typing import Optional

# ── Guard de importación — CrewAI es opcional ────────────────────────────────
try:
    from crewai import Agent, Task, Crew, Process
    from langchain_openai import ChatOpenAI
    _CREWAI_DISPONIBLE = True
except ImportError:
    _CREWAI_DISPONIBLE = False


# ─────────────────────────────────────────────────────────────────────────────
#  PROMPTS INTERNOS
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
Eres un asistente especializado en arquitectura y normativa NTC-CDMX.
Tu única función es traducir requerimientos de clientes en texto libre
a un JSON estructurado para el motor ARQ-BIM V1.

REGLAS ESTRICTAS:
1. NUNCA inventes áreas ni dimensiones. Si no se mencionan, omite el campo.
2. NUNCA apliques normativa. Eso lo hace Python de forma determinista.
3. Solo extrae lo que el cliente dice explícitamente.
4. Devuelve ÚNICAMENTE JSON válido, sin texto adicional, sin markdown.

SCHEMA DE SALIDA:
{
  "proyecto": {
    "nombre": "string",
    "clave": "string o vacío",
    "uso_predominante": "vivienda_unifamiliar | vivienda_plurifamiliar | uso_mixto | comercial",
    "orientacion_norte_grados": 0.0
  },
  "terreno": {
    "frente_m": null_o_numero,
    "fondo_m": null_o_numero,
    "restriccion_frontal_m": 0.0,
    "restriccion_lateral_m": 0.0,
    "restriccion_fondo_m": 0.0
  },
  "programa_arquitectonico": [
    {
      "nombre": "string",
      "area_m2": null_o_numero,
      "nivel_id": "PB | N1 | N2 ...",
      "altura_m": null_o_numero,
      "iluminacion_natural": true | false | null,
      "ventilacion_natural": true | false | null,
      "orientacion": "norte | sur | oriente | poniente | no_definida"
    }
  ],
  "notas_adicionales": ["string"]
}
"""

_TASK_DESCRIPTION = """
Analiza el siguiente texto del cliente y extrae los datos del proyecto,
terreno y programa arquitectónico en el JSON estructurado requerido.

TEXTO DEL CLIENTE:
{texto}

Recuerda: devuelve ÚNICAMENTE el JSON. Sin explicaciones adicionales.
"""


# ─────────────────────────────────────────────────────────────────────────────
#  AGENTE
# ─────────────────────────────────────────────────────────────────────────────

def _crear_agente_interpretador(llm) -> "Agent":
    return Agent(
        role="Intérprete de Requerimientos Arquitectónicos",
        goal=(
            "Traducir requerimientos de clientes en texto libre "
            "a JSON estructurado para el motor ARQ-BIM V1."
        ),
        backstory=(
            "Especialista en arquitectura y normativa NTC-CDMX. "
            "Extrae datos objetivos sin inventar valores ni aplicar normativa."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
        system_prompt=_SYSTEM_PROMPT,
    )


def _crear_tarea(agente: "Agent", texto: str) -> "Task":
    return Task(
        description=_TASK_DESCRIPTION.format(texto=texto),
        agent=agente,
        expected_output="JSON estructurado según el schema de ARQ-BIM V1.",
    )


# ─────────────────────────────────────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def procesar_requerimientos_cliente(
    texto: str,
    api_key: Optional[str] = None,
    modelo: str = "gpt-4o-mini",
    verbose: bool = False,
) -> dict:
    """
    Traduce texto libre del cliente → dict estructurado para ARQ-BIM V1.

    Parámetros:
        texto    : requerimientos del cliente en lenguaje natural.
        api_key  : OpenAI API key (o leer de variable de entorno OPENAI_API_KEY).
        modelo   : modelo LLM a usar (gpt-4o-mini por defecto — más económico).
        verbose  : mostrar salida del agente en consola.

    Retorna:
        dict con claves: proyecto, terreno, programa_arquitectonico,
                         notas_adicionales.

    Ejemplo:
        texto = '''
            Necesito una casa de un nivel en un terreno de 8x20 metros.
            Quiero sala-comedor grande, dos recámaras, cocina y un baño.
            La fachada da al norte.
        '''
        datos = procesar_requerimientos_cliente(texto)
        espacios = programa_desde_dict(datos["programa_arquitectonico"])
    """
    if not _CREWAI_DISPONIBLE:
        raise ImportError(
            "CrewAI no instalado.\n"
            "Ejecuta: pip install crewai crewai-tools langchain-openai")

    # API Key
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise ValueError(
            "Se requiere OPENAI_API_KEY.\n"
            "En Colab: os.environ['OPENAI_API_KEY'] = 'sk-...'")

    # LLM
    llm = ChatOpenAI(
        model=modelo,
        temperature=0.0,        # determinismo máximo
        api_key=key,
    )

    # Crew
    agente = _crear_agente_interpretador(llm)
    tarea  = _crear_tarea(agente, texto)
    crew   = Crew(
        agents=[agente],
        tasks=[tarea],
        process=Process.sequential,
        verbose=verbose,
    )

    resultado = crew.kickoff()

    # Extraer JSON de la salida
    raw = str(resultado).strip()
    # Limpiar posible markdown
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        datos = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"El agente no devolvió JSON válido.\n"
            f"Salida recibida:\n{raw}\n"
            f"Error: {exc}")

    # Validar claves mínimas
    for clave in ("proyecto", "terreno", "programa_arquitectonico"):
        if clave not in datos:
            datos[clave] = {} if clave != "programa_arquitectonico" else []

    if verbose:
        print("\n[CREW] JSON estructurado extraído:")
        print(json.dumps(datos, ensure_ascii=False, indent=2))

    return datos


# ─────────────────────────────────────────────────────────────────────────────
#  FALLBACK SIN API — parseo básico por palabras clave
#  Útil para demos sin OpenAI key o para pruebas offline.
# ─────────────────────────────────────────────────────────────────────────────

_ESPACIOS_KEYWORDS = {
    "sala":       ("Sala-Comedor",       "sala"),
    "comedor":    ("Sala-Comedor",       "sala"),
    "recámara":   ("Recámara",           "recamara"),
    "recamara":   ("Recámara",           "recamara"),
    "habitación": ("Recámara",           "recamara"),
    "cuarto":     ("Recámara",           "recamara"),
    "cocina":     ("Cocina",             "cocina"),
    "baño":       ("Baño",              "bano"),
    "bano":       ("Baño",              "bano"),
    "sanitario":  ("Baño",              "bano"),
    "estudio":    ("Estudio",           "estudio"),
    "garage":     ("Garage",            "garage"),
    "jardín":     ("Jardín",            "jardin"),
    "patio":      ("Patio",             "patio"),
    "terraza":    ("Terraza",           "terraza"),
    "pasillo":    ("Pasillo",           "pasillo"),
}

_ORIENTACION_KEYWORDS = {
    "norte": "norte", "sur": "sur",
    "oriente": "oriente", "este": "oriente",
    "poniente": "poniente", "oeste": "poniente",
}


def parseo_basico(texto: str) -> dict:
    """
    Parseo sin IA — extrae datos básicos por palabras clave.
    Fallback cuando no hay API key disponible.
    Cobertura limitada; suficiente para demos rápidas.
    """
    import re
    texto_l = texto.lower()

    # Terreno
    frente = fondo = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)", texto)
    if m:
        frente, fondo = float(m.group(1)), float(m.group(2))

    # Orientación fachada
    orientacion = "no_definida"
    for kw, val in _ORIENTACION_KEYWORDS.items():
        if kw in texto_l:
            orientacion = val
            break

    # Uso predominante
    uso = "vivienda_unifamiliar"
    if "plurifamiliar" in texto_l or "departamento" in texto_l:
        uso = "vivienda_plurifamiliar"
    elif "comercial" in texto_l or "local" in texto_l:
        uso = "uso_mixto"

    # Programa arquitectónico
    programa = []
    contadores: dict[str, int] = {}
    palabras = re.findall(r"[a-záéíóúñü]+", texto_l)
    for palabra in palabras:
        if palabra in _ESPACIOS_KEYWORDS:
            nombre_base, clave = _ESPACIOS_KEYWORDS[palabra]
            contadores[clave] = contadores.get(clave, 0) + 1
            # Evitar duplicados consecutivos
            if contadores[clave] == 1 or (
                    clave in ("recamara", "bano") and contadores[clave] <= 3):
                sufijo = (f" {contadores[clave]}"
                          if contadores[clave] > 1 else "")
                programa.append({
                    "nombre":             nombre_base + sufijo,
                    "area_m2":            None,
                    "nivel_id":           "PB",
                    "altura_m":           None,
                    "iluminacion_natural": None,
                    "ventilacion_natural": None,
                    "orientacion":         orientacion
                                           if clave in ("recamara",)
                                           else "no_definida",
                })

    return {
        "proyecto": {
            "nombre":               "Proyecto desde texto libre",
            "clave":                "",
            "uso_predominante":     uso,
            "orientacion_norte_grados": 0.0,
        },
        "terreno": {
            "frente_m":             frente,
            "fondo_m":              fondo,
            "restriccion_frontal_m": 0.0,
            "restriccion_lateral_m": 0.0,
            "restriccion_fondo_m":   0.0,
        },
        "programa_arquitectonico": programa,
        "notas_adicionales": [
            "Parseo básico sin IA — revisar y completar áreas manualmente."
        ],
    }


def interpretar(
    texto: str,
    api_key: Optional[str] = None,
    usar_fallback: bool = True,
    verbose: bool = False,
) -> dict:
    """
    Función unificada: intenta CrewAI primero, cae a parseo básico si falla.

    Uso en Colab:
        from agentes.crew_agente import interpretar
        datos = interpretar(texto_cliente, api_key="sk-...")
        # o sin API:
        datos = interpretar(texto_cliente)  # usa parseo básico
    """
    if _CREWAI_DISPONIBLE and api_key:
        try:
            return procesar_requerimientos_cliente(
                texto, api_key=api_key, verbose=verbose)
        except Exception as exc:
            if verbose:
                print(f"[CREW] Error: {exc}\n→ Usando parseo básico.")

    if usar_fallback:
        if verbose:
            print("[CREW] Usando parseo básico (sin API key).")
        return parseo_basico(texto)

    raise RuntimeError(
        "CrewAI no disponible y fallback desactivado.\n"
        "Pasa usar_fallback=True o proporciona una api_key.")
