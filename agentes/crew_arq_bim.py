"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  ORQUESTADOR CREWAI — Pipeline ARQ-BIM V1                                   ║
║  Archivo: crew_arq_bim.py                                                   ║
║  Autor: Sistema ARQ-BIM – Ing. Gustavo Ángel Cuautle Zimarrón              ║
║  Versión: 1.0  |  2026-11-03                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

Arquitectura de Agentes CrewAI:
─────────────────────────────────────────────────────────────────────────────
  Agente 1 ── ValidadorARQBIM       (capas F1–F5, ya existente en el motor)
  Agente 2 ── VisualControlNet      (NUEVO — Módulo 1: prompts + block plan)
  Agente 3 ── PDFMantenimiento      (NUEVO — Módulo 2: manual PDF)
─────────────────────────────────────────────────────────────────────────────

Flujo de trabajo (secuencial):
  1. JSON de entrada (drafted_ARQ-XXXX.json)
        ↓
  2. ValidadorARQBIM → valida normativa y genera JSON dictaminado
        ↓
  3. VisualControlNetAgent → prompts fotorrealistas + block plan PNG
        ↓
  4. PDFMantenimientoAgent → Manual de Mantenimiento PDF

Notas de integración:
  - Este módulo puede ejecutarse SIN CrewAI instalado (modo standalone).
  - En modo CrewAI real, instalar: pip install crewai crewai-tools
  - En Colab, ejecutar la celda de instalación antes de importar.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# ── Importar agentes del pipeline ─────────────────────────────────────────────
from agente_visual_controlnet import VisualControlNetAgent
from agente_pdf_mantenimiento  import PDFMantenimientoAgent

# ── Intentar importar CrewAI (opcional) ──────────────────────────────────────
try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import tool as crewai_tool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    print("ℹ️  CrewAI no instalado — se usará modo standalone (Pipeline directo)")
    print("   Para instalar: pip install crewai crewai-tools\n")


# ═══════════════════════════════════════════════════════════════════════════════
#  MODO STANDALONE (sin CrewAI) — Pipeline directo
# ═══════════════════════════════════════════════════════════════════════════════
class PipelineARQBIMStandalone:
    """
    Orquestador standalone para Google Colab.
    Ejecuta los agentes en secuencia sin necesidad de CrewAI instalado.
    Ideal para desarrollo, pruebas y entornos con restricciones de paquetes.
    """

    def __init__(self, json_path: str, output_base: str = "output_arqbim"):
        self.json_path   = Path(json_path)
        self.output_base = Path(output_base)
        self.ts          = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.resultados  = {}

    def _banner(self, texto: str):
        sep = "═" * 65
        print(f"\n{sep}")
        print(f"  🏗️  {texto}")
        print(sep)

    def run(self) -> dict:
        """
        Ejecuta el pipeline completo:
          1. Validación básica del JSON
          2. Agente Visual ControlNet
          3. Agente PDF Mantenimiento
        """
        self._banner("PIPELINE ARQ-BIM V1 — Iniciando")
        print(f"  📂  JSON de entrada : {self.json_path}")
        print(f"  📁  Directorio base : {self.output_base}\n")

        # ── Verificar que el JSON existe ──────────────────────────────────────
        if not self.json_path.exists():
            raise FileNotFoundError(f"❌ No se encontró: {self.json_path}")

        # ── Paso 1: Validación rápida de campos mínimos ───────────────────────
        self._banner("PASO 1 — Validación del JSON ARQ-BIM V1")
        self._validar_json()

        # ── Paso 2: Agente Visual ControlNet ─────────────────────────────────
        self._banner("PASO 2 — Agente Visual ControlNet (Prompts + Block Plan)")
        dir_visual = self.output_base / "visual"
        agente_visual = VisualControlNetAgent(str(self.json_path), str(dir_visual))
        self.resultados["visual"] = agente_visual.run()

        # ── Paso 3: Agente PDF Mantenimiento ─────────────────────────────────
        self._banner("PASO 3 — Agente PDF Manual de Mantenimiento")
        dir_pdf = self.output_base / "pdf"
        agente_pdf = PDFMantenimientoAgent(str(self.json_path), str(dir_pdf))
        self.resultados["pdf"] = agente_pdf.run()

        # ── Reporte final ─────────────────────────────────────────────────────
        self._reporte_final()
        return self.resultados

    def _validar_json(self):
        """Validación mínima de estructura del JSON ARQ-BIM V1."""
        CAMPOS = ["meta", "terreno", "orientacion", "programa", "geometria_simplificada"]
        try:
            with open(self.json_path, encoding="utf-8") as f:
                datos = json.load(f)
        except Exception as e:
            raise ValueError(f"❌ Error leyendo JSON: {e}")

        faltantes = [c for c in CAMPOS if c not in datos]
        if faltantes:
            print(f"  ⚠️  Campos faltantes: {faltantes} — se continuará con defaults")
        else:
            meta = datos.get("meta", {})
            print(f"  ✅ JSON válido: {meta.get('id_proyecto','—')} "
                  f"| {meta.get('nombre_proyecto','—')}")
            print(f"  📋 Espacios en programa: {len(datos.get('programa', []))}")
            print(f"  🗺️  Polígonos en geometría: {len(datos.get('geometria_simplificada', []))}")

    def _reporte_final(self):
        """Imprime el resumen de salidas generadas."""
        sep = "─" * 65
        print(f"\n{'═' * 65}")
        print("  ✅  PIPELINE ARQ-BIM V1 — COMPLETADO")
        print(f"{'═' * 65}")
        v = self.resultados.get("visual", {})
        p = self.resultados.get("pdf", {})
        print(f"\n  📐 Agente Visual ControlNet:")
        print(f"     Espacios procesados : {v.get('total_espacios', '—')}")
        print(f"     Prompts TXT         : {v.get('prompts_txt', '—')}")
        print(f"     Block Plan PNG      : {v.get('block_plan_path', '—')}")
        print(f"\n  📄 Agente PDF Mantenimiento:")
        print(f"     Manual PDF          : {p.get('pdf_path', '—')}")
        print(f"\n  Timestamp : {self.ts}")
        print(sep + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
#  MODO CREWAI (si está instalado)
# ═══════════════════════════════════════════════════════════════════════════════
class CrewARQBIM:
    """
    Orquestador CrewAI para el pipeline ARQ-BIM V1.
    Requiere: pip install crewai crewai-tools

    Registra los agentes como Tools de CrewAI y construye un Crew
    con proceso secuencial para garantizar el orden de ejecución.
    """

    def __init__(self, json_path: str, output_base: str = "output_arqbim"):
        if not CREWAI_AVAILABLE:
            raise ImportError(
                "CrewAI no está instalado. "
                "Usa PipelineARQBIMStandalone para modo sin CrewAI."
            )
        self.json_path   = json_path
        self.output_base = output_base

    def _build_tools(self):
        """Construye los CrewAI Tools a partir de los agentes del pipeline."""
        json_path   = self.json_path
        output_base = self.output_base

        @crewai_tool("VisualControlNetTool")
        def visual_controlnet_tool(json_path: str = json_path,
                                   output_dir: str = f"{output_base}/visual") -> str:
            """
            Genera prompts fotorrealistas para Google Imagen 3/Flow/NanoBanana
            y un Block Plan 2D (ControlNet map) a partir del JSON ARQ-BIM V1.
            """
            agent = VisualControlNetAgent(json_path, output_dir)
            result = agent.run()
            return json.dumps(result, ensure_ascii=False, indent=2)

        @crewai_tool("PDFMantenimientoTool")
        def pdf_mantenimiento_tool(json_path: str = json_path,
                                   output_dir: str = f"{output_base}/pdf") -> str:
            """
            Genera el Manual de Mantenimiento y Entrega de Obra en PDF profesional
            con 6 secciones listas para carpeta de licencias municipales.
            """
            agent = PDFMantenimientoAgent(json_path, output_dir)
            result = agent.run()
            return json.dumps(result, ensure_ascii=False, indent=2)

        return visual_controlnet_tool, pdf_mantenimiento_tool

    def build_crew(self) -> "Crew":
        """
        Construye y retorna el Crew de CrewAI con los 2 agentes especializados.

        Agente 1: Especialista en Visualización Arquitectónica
          → Genera prompts e insumos visuales
        Agente 2: Especialista en Documentación Técnica
          → Genera el Manual PDF
        """
        visual_tool, pdf_tool = self._build_tools()

        # ── Agente 1: Especialista Visual ─────────────────────────────────────
        agente_visual = Agent(
            role="Especialista en Visualización Arquitectónica BIM",
            goal=(
                "Leer el JSON ARQ-BIM del proyecto y generar todos los insumos "
                "visuales necesarios: prompts fotorrealistas para IA generativa "
                "y el Block Plan 2D como mapa de control ControlNet."
            ),
            backstory=(
                "Eres un arquitecto BIM con experiencia en renderizado fotorrealista "
                "y diseño bioclimático para clima mexicano. Dominas Google Imagen 3, "
                "NanoBanana, ControlNet y la normativa de San Andrés Cholula. "
                "Tu trabajo garantiza que los renders respeten la distribución espacial "
                "y el comportamiento solar del proyecto."
            ),
            tools=[visual_tool],
            verbose=True,
            allow_delegation=False,
        )

        # ── Agente 2: Especialista en Documentación ────────────────────────────
        agente_doc = Agent(
            role="Especialista en Documentación Técnica y Licencias de Construcción",
            goal=(
                "Transformar los datos del JSON ARQ-BIM V1 en un Manual de "
                "Mantenimiento y Entrega de Obra en PDF, listo para carpeta "
                "de licencias municipales y firma del DRO."
            ),
            backstory=(
                "Eres un perito en documentación para licencias de construcción "
                "en Puebla, México. Conoces los requisitos del Reglamento de "
                "Construcciones de San Andrés Cholula y produces documentos "
                "con la estructura exigida por la Dirección de Obras Públicas."
            ),
            tools=[pdf_tool],
            verbose=True,
            allow_delegation=False,
        )

        # ── Tareas ─────────────────────────────────────────────────────────────
        tarea_visual = Task(
            description=(
                f"Procesar el archivo JSON '{self.json_path}' para generar: "
                "(1) prompts fotorrealistas por espacio con parámetros para Google Imagen 3 / Flow / NanoBanana, "
                "(2) Block Plan 2D en PNG como ControlNet conditioning image. "
                "Usar la herramienta VisualControlNetTool. "
                "Retornar el path del PNG y el archivo TXT de prompts."
            ),
            agent=agente_visual,
            expected_output=(
                "JSON con status, total_espacios, paths de prompts_txt y block_plan_path."
            ),
        )

        tarea_pdf = Task(
            description=(
                f"Compilar el Manual de Mantenimiento y Entrega de Obra en PDF "
                f"a partir del archivo JSON '{self.json_path}'. "
                "Incluir: Datos del Predio, Cuadro de Áreas, Análisis Bioclimático, "
                "Especificaciones de Materiales, Calendario Preventivo y Bloque de Firmas. "
                "Usar la herramienta PDFMantenimientoTool."
            ),
            agent=agente_doc,
            expected_output=(
                "JSON con status e id_proyecto y pdf_path del Manual generado."
            ),
            context=[tarea_visual],  # El PDF puede mencionar el Block Plan
        )

        # ── Crew secuencial ───────────────────────────────────────────────────
        crew = Crew(
            agents=[agente_visual, agente_doc],
            tasks=[tarea_visual, tarea_pdf],
            process=Process.sequential,
            verbose=True,
        )
        return crew

    def run(self) -> dict:
        """Ejecuta el Crew completo."""
        crew   = self.build_crew()
        result = crew.kickoff()
        return {"crew_result": str(result)}


# ═══════════════════════════════════════════════════════════════════════════════
#  PUNTO DE ENTRADA — Selección automática de modo
# ═══════════════════════════════════════════════════════════════════════════════
def run_pipeline(json_path: str, output_base: str = "output_arqbim",
                 forzar_standalone: bool = False) -> dict:
    """
    Función principal de entrada al pipeline ARQ-BIM V1.

    Selecciona automáticamente:
      - Modo CrewAI si está instalado y forzar_standalone=False
      - Modo Standalone en caso contrario

    Args:
        json_path         : Ruta al JSON drafted_ARQ-XXXX.json
        output_base       : Carpeta raíz de salidas
        forzar_standalone : True para omitir CrewAI aunque esté instalado

    Returns:
        dict con resultados de ambos agentes
    """
    if CREWAI_AVAILABLE and not forzar_standalone:
        print("🤖 Modo CrewAI detectado — usando orquestador inteligente")
        orquestador = CrewARQBIM(json_path, output_base)
    else:
        print("⚙️  Modo Standalone — Pipeline directo (sin CrewAI)")
        orquestador = PipelineARQBIMStandalone(json_path, output_base)

    return orquestador.run()


# ── Bloque __main__ ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    JSON_FILE   = sys.argv[1] if len(sys.argv) > 1 else "drafted_ARQ-2026-001.json"
    OUTPUT_BASE = sys.argv[2] if len(sys.argv) > 2 else "output_arqbim"

    resultados = run_pipeline(
        json_path=JSON_FILE,
        output_base=OUTPUT_BASE,
        forzar_standalone=True  # Cambiar a False para usar CrewAI
    )
