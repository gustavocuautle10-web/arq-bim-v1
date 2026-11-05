"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  MÓDULO 1 — Agente de Traducción Visual y Generación ControlNet             ║
║  Pipeline ARQ-BIM V1 | Google Colab / GitHub                                ║
║  Autor: Sistema ARQ-BIM – Ing. Gustavo Ángel Cuautle Zimarrón              ║
║  Versión: 1.0  |  2026-11-03                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

Responsabilidades:
  - Leer el JSON "drafted_ARQ-2026-XXX.json" y extraer programa + geometría.
  - Generar prompts fotorrealistas optimizados (ES/EN) para Google Imagen 3,
    Google Flow o NanoBanana, respetando orientación solar y materiales.
  - Renderizar un Block Plan 2D (ControlNet map) en matplotlib con paleta
    cromática por tipo de espacio y leyenda de orientación solar.

Integración CrewAI:
  La clase VisualControlNetAgent expone el método `run()` que el Crew
  orquestador invoca como Tool, recibiendo el path del JSON y devolviendo
  un dict con {prompts, block_plan_path}.
"""

import json
import os
import textwrap
from pathlib import Path
from typing import Optional

# ── Dependencias de renderizado ──────────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use("Agg")          # Backend sin GUI, compatible con Colab
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️  matplotlib no disponible. Instala con: pip install matplotlib")

# ── Paleta cromática por tipo de espacio (tipo → hex) ───────────────────────
PALETA_TIPO = {
    "social":        "#F4A460",   # Sandy Brown  — Sala, Comedor
    "servicio":      "#90EE90",   # Light Green  — Cocina, Lavandería
    "privado":       "#ADD8E6",   # Light Blue   — Recámaras
    "sanitario":     "#D8BFD8",   # Thistle      — Baños
    "complementario":"#D3D3D3",   # Light Gray   — Estacionamiento, Bodega
    "circulacion":   "#FAFAD2",   # Light Goldenrod — Pasillos, Escaleras
}

# ── Comportamiento solar por orientación cardinal ────────────────────────────
SOLAR_DESCRIPCION = {
    "SUR": {
        "es": "ganancia solar máxima en invierno, iluminación cálida todo el año",
        "en": "maximum winter solar gain, warm year-round natural light",
        "lighting_en": "warm golden morning light streaming from the south, soft diffused glow",
    },
    "NORTE": {
        "es": "luz difusa constante sin deslumbramiento, confort térmico en verano",
        "en": "constant diffused north light, no glare, cool comfort in summer",
        "lighting_en": "cool even north light, soft shadows, no direct sun glare",
    },
    "ESTE": {
        "es": "luz de mañana directa, frescura vespertina",
        "en": "direct morning sunlight, cool afternoons",
        "lighting_en": "bright direct morning sunlight flooding from the east, warm sunrise tones",
    },
    "OESTE": {
        "es": "luz de tarde, radiación solar vespertina intensa",
        "en": "afternoon light, intense western solar radiation",
        "lighting_en": "dramatic warm afternoon light from the west, golden hour tones",
    },
}

# ── Materiales base para prompts (desde especificaciones del proyecto) ────────
MATERIALES_BASE = {
    "pisos_social":    "large-format rectified porcelain tile 60x60 cm, polished finish",
    "pisos_privado":   "wood-look ceramic flooring, warm tones",
    "pisos_sanitario": "matte ceramic tile, white and grey tones",
    "muros":           "smooth plaster walls, matte vinyl paint, clean white finish",
    "canceleria":      "natural aluminum frames with 6 mm tempered glass",
    "techo":           "smooth white painted concrete slab",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  CLASE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════
class VisualControlNetAgent:
    """
    Agente CrewAI-compatible para generación de insumos visuales.

    Uso directo (sin CrewAI):
        agent = VisualControlNetAgent("drafted_ARQ-2026-001.json")
        result = agent.run()
        print(result["prompts"])

    Uso como CrewAI Tool:
        Ver método as_crewai_tool() al final de la clase.
    """

    def __init__(self, json_path: str, output_dir: str = "output_visual"):
        self.json_path  = Path(json_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.datos: dict = {}

    # ── 1. Carga y validación del JSON ───────────────────────────────────────
    def cargar_json(self) -> bool:
        """Carga el archivo JSON y valida los campos mínimos requeridos."""
        CAMPOS_REQUERIDOS = ["programa", "geometria_simplificada", "terreno", "orientacion"]
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                self.datos = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ No se encontró el archivo JSON: {self.json_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"❌ JSON malformado: {e}")

        faltantes = [c for c in CAMPOS_REQUERIDOS if c not in self.datos]
        if faltantes:
            raise KeyError(f"❌ Campos faltantes en el JSON: {faltantes}")

        print(f"✅ JSON cargado → {self.json_path.name} "
              f"| {len(self.datos['programa'])} espacios detectados")
        return True

    # ── 2. Generador de Prompts Fotorrealistas ────────────────────────────────
    def _prompt_espacio(self, espacio: dict) -> dict:
        """
        Genera un dict con prompt ES y EN para un espacio arquitectónico.

        Parámetros considerados:
          - nombre, area_m2, orientacion, superficie_vidriada_pct, nivel
          - tipo de espacio → determina acabados del piso
          - comportamiento solar de la orientación
        """
        nombre    = espacio.get("nombre", "Espacio")
        area      = espacio.get("area_m2", 0)
        orient    = espacio.get("orientacion", "SUR").upper()
        vid_pct   = espacio.get("superficie_vidriada_pct", 20)
        nivel     = espacio.get("nivel", "PB")
        tipo      = espacio.get("tipo", "social")

        solar   = SOLAR_DESCRIPCION.get(orient, SOLAR_DESCRIPCION["SUR"])
        piso_en = MATERIALES_BASE.get(f"pisos_{tipo}", MATERIALES_BASE["pisos_social"])

        # Escala de acristalamiento
        if vid_pct >= 30:
            glass_desc = "floor-to-ceiling glass panels"
        elif vid_pct >= 15:
            glass_desc = "generous window openings with aluminum frames"
        else:
            glass_desc = "standard operable windows with aluminum frames"

        # ── Prompt EN (para Google Imagen 3 / Flow / NanoBanana) ─────────────
        prompt_en = (
            f"Architectural interior photograph of a {nombre.lower()}, "
            f"modern Mexican residential home, {area:.0f} sqm, "
            f"{'ground floor' if nivel == 'PB' else 'upper floor'}, "
            f"{solar['lighting_en']}, "
            f"{glass_desc} facing {orient.lower()}, "
            f"{piso_en}, "
            f"{MATERIALES_BASE['muros']}, {MATERIALES_BASE['canceleria']}, "
            f"{MATERIALES_BASE['techo']}, "
            "minimalist contemporary design, clean lines, "
            "professional architectural photography, 4K, wide angle lens, "
            "no people, natural ventilation, bioclimatic design, "
            "San Andrés Cholula Puebla México context, "
            "photorealistic rendering, high detail"
        )

        # ── Prompt ES (para referencia del proyecto) ──────────────────────────
        prompt_es = (
            f"Fotografía arquitectónica del {nombre} de una casa habitación "
            f"unifamiliar contemporánea, {area:.0f} m², "
            f"{'planta baja' if nivel == 'PB' else 'planta alta'}, "
            f"orientación {orient} con {solar['es']}, "
            f"{glass_desc.replace('floor-to-ceiling', 'vidrio piso-techo')}, "
            f"acabados: {piso_en}, muros aplanados blancos, cancelería de aluminio, "
            "diseño minimalista mexicano, fotografía arquitectónica profesional, "
            "sin personas, diseño bioclimático, San Andrés Cholula Puebla"
        )

        return {
            "id":        espacio.get("id", ""),
            "nombre":    nombre,
            "nivel":     nivel,
            "orientacion": orient,
            "prompt_en": prompt_en,
            "prompt_es": prompt_es,
            # Parámetros sugeridos para Google Flow / NanoBanana
            "parametros_ia": {
                "aspect_ratio":  "16:9",
                "guidance_scale": 7.5,
                "num_inference_steps": 50,
                "seed": int(area * 100),         # Semilla reproducible por espacio
                "negative_prompt": (
                    "people, furniture clutter, dark, blurry, low quality, "
                    "cartoon, illustration, deformed, ugly, bad architecture"
                ),
            }
        }

    def generar_prompts(self) -> list[dict]:
        """Genera prompts para todos los espacios del programa."""
        prompts = []
        for espacio in self.datos.get("programa", []):
            try:
                p = self._prompt_espacio(espacio)
                prompts.append(p)
                print(f"  🖼️  Prompt → [{p['id']}] {p['nombre']} ({p['orientacion']})")
            except Exception as e:
                print(f"  ⚠️  Error en espacio {espacio.get('id','?')}: {e}")
        return prompts

    def exportar_prompts_txt(self, prompts: list[dict]) -> str:
        """Exporta prompts a archivo .txt legible y listo para copiar."""
        out_path = self.output_dir / f"{self.datos['meta']['id_proyecto']}_prompts.txt"
        proyecto = self.datos.get("meta", {}).get("nombre_proyecto", "Proyecto")
        lineas = [
            "=" * 72,
            f"PROMPTS FOTORREALISTAS — {proyecto}",
            f"ID: {self.datos['meta']['id_proyecto']}  |  Fecha: {self.datos['meta']['fecha_elaboracion']}",
            "=" * 72, ""
        ]
        for p in prompts:
            lineas += [
                f"[{p['id']}] {p['nombre']} — Nivel {p['nivel']} | Orientación {p['orientacion']}",
                "-" * 60,
                "▶ PROMPT EN (Google Imagen 3 / NanoBanana):",
                textwrap.fill(p["prompt_en"], width=70),
                "",
                "▶ PROMPT ES (Referencia proyecto):",
                textwrap.fill(p["prompt_es"], width=70),
                "",
                "▶ Parámetros IA sugeridos:",
                f"   Aspect ratio : {p['parametros_ia']['aspect_ratio']}",
                f"   Guidance     : {p['parametros_ia']['guidance_scale']}",
                f"   Steps        : {p['parametros_ia']['num_inference_steps']}",
                f"   Seed         : {p['parametros_ia']['seed']}",
                f"   Negative     : {p['parametros_ia']['negative_prompt']}",
                "=" * 72, ""
            ]
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas))
        print(f"\n✅ Prompts exportados → {out_path}")
        return str(out_path)

    # ── 3. Generador de Block Plan (Mapa ControlNet) ──────────────────────────
    def generar_block_plan(self) -> str:
        """
        Renderiza el plano esquemático 2D en matplotlib.
        Escala automática según dimensiones del terreno.
        Genera archivo PNG listo para usar como ControlNet conditioning image.
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib requerido: pip install matplotlib")

        geometria = self.datos.get("geometria_simplificada", [])
        programa  = self.datos.get("programa", [])
        terreno   = self.datos.get("terreno", {})
        orient    = self.datos.get("orientacion", {})
        meta      = self.datos.get("meta", {})

        # Mapa id → tipo (para colorear)
        tipo_por_id = {e["id"]: e.get("tipo", "social") for e in programa}
        nombre_por_id = {e["id"]: e.get("nombre", "") for e in programa}
        nivel_por_id = {e["id"]: e.get("nivel", "PB") for e in programa}

        # Dimensiones del terreno como marco de referencia
        frente = terreno.get("frente_m", 10)
        fondo  = terreno.get("fondo_m", 20)

        # ── Separar PB y PA ───────────────────────────────────────────────────
        ids_pb = [e["id"] for e in programa if e.get("nivel") == "PB"]
        ids_pa = [e["id"] for e in programa if e.get("nivel") == "PA"]
        tiene_pa = bool(ids_pa)

        n_plantas = 2 if tiene_pa else 1
        fig_w = max(10, frente * 0.9)
        fig_h = max(6, fondo * 0.5) * n_plantas + 2

        fig, axes = plt.subplots(1, n_plantas, figsize=(fig_w * n_plantas * 0.8, fig_h),
                                  facecolor="#F5F5F5")
        if n_plantas == 1:
            axes = [axes]

        # ── Función auxiliar para dibujar una planta ──────────────────────────
        def dibujar_planta(ax, ids_nivel, titulo_planta):
            ax.set_facecolor("#ECECEC")
            ax.set_xlim(-0.5, frente + 0.5)
            ax.set_ylim(-0.5, fondo + 0.5)
            ax.set_aspect("equal")
            ax.set_title(titulo_planta, fontsize=11, fontweight="bold",
                         pad=8, color="#1A2744")

            # Marco del terreno
            terreno_rect = FancyBboxPatch(
                (0, 0), frente, fondo,
                boxstyle="square,pad=0", linewidth=2.5,
                edgecolor="#1A2744", facecolor="white", zorder=1
            )
            ax.add_patch(terreno_rect)

            # Flecha de norte
            ax.annotate("N", xy=(frente - 0.3, fondo - 0.4), fontsize=10,
                        fontweight="bold", color="#1A2744", ha="center")
            ax.annotate("", xy=(frente - 0.3, fondo - 0.1),
                        xytext=(frente - 0.3, fondo - 0.8),
                        arrowprops=dict(arrowstyle="->", color="#1A2744", lw=1.5))

            # Dibuja cada espacio
            for geo in geometria:
                if geo["id"] not in ids_nivel:
                    continue
                x     = geo.get("x", 0)
                y     = geo.get("y", 0)
                ancho = geo.get("ancho", 1)
                prof  = geo.get("fondo", 1)
                tipo  = tipo_por_id.get(geo["id"], "social")
                color = PALETA_TIPO.get(tipo, "#CCCCCC")
                nombre = nombre_por_id.get(geo["id"], geo["id"])

                rect = FancyBboxPatch(
                    (x, y), ancho, prof,
                    boxstyle="square,pad=0.05", linewidth=1.2,
                    edgecolor="#444444", facecolor=color, alpha=0.88, zorder=2
                )
                ax.add_patch(rect)

                # Etiqueta ID + nombre abreviado
                cx, cy = x + ancho / 2, y + prof / 2
                label = f"{geo['id']}\n{nombre[:12]}"
                if ancho >= 2 and prof >= 1.5:
                    ax.text(cx, cy, label, ha="center", va="center",
                            fontsize=7.5, fontweight="bold", color="#1A1A1A",
                            zorder=3, wrap=True,
                            bbox=dict(boxstyle="round,pad=0.1",
                                      facecolor="white", alpha=0.5, edgecolor="none"))

                # Área en m²
                area_txt = f"{ancho * prof:.1f} m²"
                ax.text(cx, cy - prof * 0.28, area_txt, ha="center", va="center",
                        fontsize=6.5, color="#333333", zorder=3)

            # Cotas del terreno
            ax.annotate("", xy=(frente, -0.3), xytext=(0, -0.3),
                        arrowprops=dict(arrowstyle="<->", color="#555555", lw=1))
            ax.text(frente / 2, -0.42, f"{frente:.1f} m",
                    ha="center", va="top", fontsize=8, color="#555555")
            ax.annotate("", xy=(-0.3, fondo), xytext=(-0.3, 0),
                        arrowprops=dict(arrowstyle="<->", color="#555555", lw=1))
            ax.text(-0.42, fondo / 2, f"{fondo:.1f} m",
                    ha="right", va="center", fontsize=8, color="#555555", rotation=90)

            # Orientación del frente
            frente_card = orient.get("frente_cardinal", "SUR")
            ax.text(frente / 2, -0.9, f"← FRENTE {frente_card} →",
                    ha="center", va="top", fontsize=8, color="#C0392B",
                    fontweight="bold")
            ax.set_xticks([])
            ax.set_yticks([])

        # ── Dibujar plantas ───────────────────────────────────────────────────
        dibujar_planta(axes[0], ids_pb, "PLANTA BAJA (PB)")
        if tiene_pa:
            dibujar_planta(axes[1], ids_pa, "PLANTA ALTA (PA)")

        # ── Leyenda ───────────────────────────────────────────────────────────
        handles = [
            mpatches.Patch(facecolor=c, edgecolor="#444", label=t.capitalize())
            for t, c in PALETA_TIPO.items()
            if any(tipo_por_id.get(e["id"]) == t for e in programa)
        ]
        fig.legend(handles=handles, loc="lower center",
                   ncol=min(len(handles), 4),
                   fontsize=8, frameon=True, title="Tipo de Espacio",
                   title_fontsize=9, bbox_to_anchor=(0.5, 0.0))

        # ── Título global ─────────────────────────────────────────────────────
        fig.suptitle(
            f"BLOCK PLAN — MAPA DE CONTROL (ControlNet)\n"
            f"{meta.get('nombre_proyecto','Proyecto')} | {meta.get('id_proyecto','')} "
            f"| {meta.get('fecha_elaboracion','')}",
            fontsize=11, fontweight="bold", color="#1A2744", y=1.02
        )

        plt.tight_layout(rect=[0, 0.08, 1, 1])

        out_path = self.output_dir / f"{meta.get('id_proyecto','proyecto')}_block_plan.png"
        fig.savefig(out_path, dpi=150, bbox_inches="tight",
                    facecolor="#F5F5F5")
        plt.close(fig)
        print(f"✅ Block Plan exportado → {out_path}")
        return str(out_path)

    # ── 4. Punto de entrada principal ─────────────────────────────────────────
    def run(self) -> dict:
        """
        Ejecuta el agente completo.
        Retorna dict compatible con CrewAI TaskOutput.
        """
        print("\n" + "═" * 60)
        print("  🏗️  AGENTE VISUAL CONTROLNET — Iniciando")
        print("═" * 60)
        self.cargar_json()

        print("\n📐 Generando prompts fotorrealistas...")
        prompts = self.generar_prompts()
        txt_path = self.exportar_prompts_txt(prompts)

        print("\n🗺️  Generando Block Plan (ControlNet map)...")
        block_plan_path = self.generar_block_plan()

        resultado = {
            "status":          "✅ Completado",
            "id_proyecto":     self.datos["meta"]["id_proyecto"],
            "total_espacios":  len(prompts),
            "prompts":         prompts,
            "prompts_txt":     txt_path,
            "block_plan_path": block_plan_path,
        }
        print("\n✅ Agente Visual ControlNet finalizado.\n")
        return resultado

    # ── 5. Wrapper CrewAI Tool ────────────────────────────────────────────────
    @staticmethod
    def as_crewai_tool():
        """
        Retorna un dict de configuración para registrar este agente
        como herramienta (Tool) dentro de un Crew de CrewAI.

        Ejemplo de uso en crew.py:
            from agente_visual_controlnet import VisualControlNetAgent
            from crewai_tools import tool

            @tool("VisualControlNetTool")
            def visual_controlnet_tool(json_path: str, output_dir: str = "output_visual") -> str:
                agent = VisualControlNetAgent(json_path, output_dir)
                result = agent.run()
                return str(result)
        """
        return {
            "nombre":      "VisualControlNetTool",
            "descripcion": (
                "Lee el JSON ARQ-BIM V1 de un proyecto y genera: "
                "(1) prompts fotorrealistas por espacio para Google Imagen 3 / Flow / NanoBanana, "
                "(2) un Block Plan 2D (PNG) para uso como ControlNet conditioning image. "
                "Parámetros: json_path (str), output_dir (str)."
            ),
            "clase": VisualControlNetAgent,
        }


# ── Bloque de prueba autónoma ─────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    json_file = sys.argv[1] if len(sys.argv) > 1 else "drafted_ARQ-2026-001.json"
    agent = VisualControlNetAgent(json_file, output_dir="output_visual")
    result = agent.run()
    print(f"\nResumen: {result['total_espacios']} espacios procesados")
    print(f"Prompts: {result['prompts_txt']}")
    print(f"Block Plan: {result['block_plan_path']}")
