"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  MÓDULO 2 — Agente de Documentación y Manual de Mantenimiento (PDF)         ║
║  Pipeline ARQ-BIM V1 | Google Colab / GitHub                                ║
║  Autor: Sistema ARQ-BIM – Ing. Gustavo Ángel Cuautle Zimarrón              ║
║  Versión: 1.0  |  2026-11-03                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

Responsabilidades:
  - Leer el JSON "drafted_ARQ-2026-XXX.json" (esquema ARQ-BIM V1).
  - Compilar con ReportLab un PDF formal: Manual de Mantenimiento y Entrega
    de Obra, con estructura profesional lista para carpeta de licencias.
  - Secciones: Datos del Predio, Cuadro de Áreas, Análisis Bioclimático,
    Especificaciones de Materiales + Calendario de Mantenimiento,
    Bloque de Validación (DRO + Cliente).

Integración CrewAI:
  La clase PDFMantenimientoAgent expone el método `run()` que el Crew
  orquestador invoca como Tool, recibiendo el path del JSON y devolviendo
  el path del PDF generado.
"""

import json
import os
from datetime import datetime
from pathlib import Path

# ── ReportLab ────────────────────────────────────────────────────────────────
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether, PageBreak
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("⚠️  ReportLab no disponible. Instala con: pip install reportlab")


# ── Paleta de colores corporativa ARQ-BIM (alineada con Motor Sísmico) ───────
C_AZUL_OSCURO  = colors.HexColor("#1A2744")
C_AZUL_MEDIO   = colors.HexColor("#1E4FA0")
C_AZUL_CLARO   = colors.HexColor("#D6E4F7")
C_GRIS_CLARO   = colors.HexColor("#F2F2F2")
C_GRIS_MEDIO   = colors.HexColor("#CCCCCC")
C_AMARILLO     = colors.HexColor("#FFC107")
C_ROJO         = colors.HexColor("#C0392B")
C_VERDE        = colors.HexColor("#27AE60")
C_NEGRO        = colors.black
C_BLANCO       = colors.white

# ── Comportamiento bioclimático por orientación ───────────────────────────────
BIOCLIMATICO = {
    "SUR": {
        "ganancia_solar": "Alta en invierno (máxima captación solar)",
        "confort_verano": "Requiere aleros o voladizos de protección (ángulo ~55° para Puebla lat. 19°N)",
        "ventilacion":    "Cruzada Norte-Sur, eficiente para extracción de calor",
        "recomendacion":  (
            "Ubicar áreas sociales (Sala-Comedor) con frente al Sur. "
            "Proyectar alero calculado para bloquear el sol de verano (solsticio junio, "
            "ángulo altitud ~74°) y permitir ganancia solar en invierno (solsticio diciembre, "
            "ángulo ~28°). Superficie vidriada 25–40% es óptima."
        ),
    },
    "NORTE": {
        "ganancia_solar": "Mínima (luz difusa todo el año, sin sol directo)",
        "confort_verano": "Excelente — sin radiación solar directa, temperaturas interiores estables",
        "ventilacion":    "Entrada de aire fresco en régimen de ventilación cruzada",
        "recomendacion":  (
            "Óptimo para recámaras: luz homogénea sin deslumbramiento, "
            "temperatura estable. Superficie vidriada recomendada 15–25%. "
            "Evitar exceso de vidrio para no perder calor en invierno."
        ),
    },
    "ESTE": {
        "ganancia_solar": "Moderada — sol de mañana directo (06:00–12:00 h)",
        "confort_verano": "Aceptable — tardes frescas sin radiación directa",
        "ventilacion":    "Vientos de componente este favorecen ventilación matutina",
        "recomendacion":  (
            "Adecuado para cocinas y estudios: iluminación matutina vigoriza "
            "el espacio. Proteger con persianas o celosías para control del deslumbramiento."
        ),
    },
    "OESTE": {
        "ganancia_solar": "Alta vespertina — radiación solar intensa (14:00–19:00 h)",
        "confort_verano": "Problemática — mayor carga térmica en verano",
        "ventilacion":    "Vientos de poniente pueden ser calientes en temporada seca",
        "recomendacion":  (
            "Minimizar superficies vidriadas. Usar masa térmica (muros gruesos), "
            "vegetación o pantallas de protección solar. "
            "Evitar recámaras y áreas de trabajo al Oeste."
        ),
    },
}

# ── Calendario de mantenimiento preventivo ────────────────────────────────────
CALENDARIO_MANTENIMIENTO = [
    # (Frecuencia, Sistema/Componente, Actividad, Responsable)
    ("Semestral", "Impermeabilización",   "Revisión visual de membrana, sellos perimetrales y drenes; aplicar recubrimiento reflectante si presenta grietas o ampollamiento.", "Empresa especializada"),
    ("Semestral", "Cancelería y Vidrios", "Limpieza de marcos de aluminio con detergente neutro; revisión de empaques, burletes y selladores de silicón; lubricar herrajes.", "Propietario / Herrero"),
    ("Semestral", "Instalación Eléctrica","Revisión de tablero general, interruptores termomagnéticos y tierra física; prueba GFCI en baños y cocina.", "Electricista certificado"),
    ("Semestral", "Instalación Hidráulica","Revisión de llaves de paso, válvulas de flotador (tinacos/cisternas), trampa de agua en coladera de patio; verificar presión.", "Plomero"),
    ("Anual",     "Acabados Interiores",  "Revisión de grietas en muros y losas; resane con pasta premezclada; aplicar pintura vinílica en áreas con manchas de humedad.", "Albañil / Propietario"),
    ("Anual",     "Fachada y Exteriores", "Limpieza de fachada con hidrolavadora; revisión de junteado de loseta y adocreto; sellado de fisuras con poliuretano flexible.", "Albañil"),
    ("Anual",     "Estructura",           "Inspección visual de castillos, trabes y losas: sin grietas diagonales, escurrimientos de salitre ni corrosión en varilla expuesta.", "DRO / Perito Estructural"),
    ("Anual",     "Jardín / Drenaje",     "Limpieza de coladeras pluviales, canales y bajadas de agua; verificar que el terreno no acumule agua junto a la cimentación.", "Propietario"),
    ("3 años",    "Impermeabilización",   "Aplicación de nuevo ciclo de impermeabilización completo sobre azotea con limpieza previa, resane de grietas y membrana nueva.", "Empresa especializada"),
    ("5 años",    "Pintura exterior",     "Repintura total de fachada previo lavado a presión y lija de zonas con descascaramiento. Usar pintura elastomérica de alta durabilidad.", "Pintor profesional"),
]


# ═══════════════════════════════════════════════════════════════════════════════
#  CLASE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════
class PDFMantenimientoAgent:
    """
    Agente CrewAI-compatible para generación del Manual de Mantenimiento PDF.

    Uso directo:
        agent = PDFMantenimientoAgent("drafted_ARQ-2026-001.json")
        result = agent.run()

    Uso como CrewAI Tool: ver as_crewai_tool()
    """

    def __init__(self, json_path: str, output_dir: str = "output_pdf"):
        self.json_path  = Path(json_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.datos: dict = {}
        self.styles = None
        self.story:  list = []

    # ── 1. Carga JSON ─────────────────────────────────────────────────────────
    def cargar_json(self) -> bool:
        CAMPOS = ["programa", "terreno", "orientacion", "meta"]
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                self.datos = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ JSON no encontrado: {self.json_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"❌ JSON malformado: {e}")

        faltantes = [c for c in CAMPOS if c not in self.datos]
        if faltantes:
            raise KeyError(f"❌ Campos faltantes: {faltantes}")
        print(f"✅ JSON cargado → {self.json_path.name}")
        return True

    # ── 2. Inicializar estilos ReportLab ─────────────────────────────────────
    def _init_styles(self):
        base = getSampleStyleSheet()
        self.styles = {
            "titulo_doc": ParagraphStyle(
                "titulo_doc", parent=base["Heading1"],
                fontSize=16, textColor=C_BLANCO, alignment=TA_CENTER,
                spaceAfter=4, fontName="Helvetica-Bold"
            ),
            "subtitulo_doc": ParagraphStyle(
                "subtitulo_doc", parent=base["Normal"],
                fontSize=10, textColor=C_BLANCO, alignment=TA_CENTER,
                spaceAfter=2, fontName="Helvetica"
            ),
            "seccion": ParagraphStyle(
                "seccion", parent=base["Heading2"],
                fontSize=11, textColor=C_BLANCO, spaceAfter=4,
                spaceBefore=12, fontName="Helvetica-Bold", leading=14
            ),
            "cuerpo": ParagraphStyle(
                "cuerpo", parent=base["Normal"],
                fontSize=9, textColor=C_NEGRO, spaceAfter=4,
                fontName="Helvetica", leading=13, alignment=TA_JUSTIFY
            ),
            "cuerpo_bold": ParagraphStyle(
                "cuerpo_bold", parent=base["Normal"],
                fontSize=9, textColor=C_NEGRO, spaceAfter=3,
                fontName="Helvetica-Bold", leading=13
            ),
            "pie": ParagraphStyle(
                "pie", parent=base["Normal"],
                fontSize=7.5, textColor=colors.HexColor("#666666"),
                alignment=TA_CENTER, fontName="Helvetica-Oblique"
            ),
            "firma_label": ParagraphStyle(
                "firma_label", parent=base["Normal"],
                fontSize=8, textColor=C_NEGRO, alignment=TA_CENTER,
                fontName="Helvetica-Bold"
            ),
            "firma_sub": ParagraphStyle(
                "firma_sub", parent=base["Normal"],
                fontSize=7.5, textColor=colors.HexColor("#555555"),
                alignment=TA_CENTER, fontName="Helvetica"
            ),
        }

    # ── 3. Helper: encabezado de sección ──────────────────────────────────────
    def _seccion(self, titulo: str, numero: str = ""):
        """Bloque de encabezado de sección con barra azul."""
        label = f"{numero}  {titulo}" if numero else titulo
        t = Table([[Paragraph(label, self.styles["seccion"])]],
                  colWidths=[17.5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_AZUL_OSCURO),
            ("LEFTPADDING",  (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING",   (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ]))
        self.story.append(t)
        self.story.append(Spacer(1, 4))

    def _par(self, texto: str, estilo: str = "cuerpo"):
        self.story.append(Paragraph(texto, self.styles[estilo]))

    def _espacio(self, h: float = 6):
        self.story.append(Spacer(1, h))

    def _hr(self):
        self.story.append(HRFlowable(width="100%", thickness=0.5,
                                      color=C_GRIS_MEDIO, spaceAfter=4))

    # ── 4. Portada ────────────────────────────────────────────────────────────
    def _portada(self):
        meta    = self.datos.get("meta", {})
        terreno = self.datos.get("terreno", {})

        # Caja azul de portada
        titulo_data = [[
            Paragraph(
                "MANUAL DE MANTENIMIENTO<br/>Y ENTREGA DE OBRA",
                self.styles["titulo_doc"]
            )
        ]]
        t_portada = Table(titulo_data, colWidths=[17.5 * cm])
        t_portada.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_AZUL_OSCURO),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 18),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
            ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ]))
        self.story.append(t_portada)
        self.story.append(Spacer(1, 10))

        # Subtítulo proyecto
        sub_data = [[
            Paragraph(
                meta.get("nombre_proyecto", "Proyecto Arquitectónico"),
                self.styles["subtitulo_doc"]
            )
        ]]
        t_sub = Table(sub_data, colWidths=[17.5 * cm])
        t_sub.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_AZUL_MEDIO),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        self.story.append(t_sub)
        self.story.append(Spacer(1, 16))

        # Tabla de datos generales del encabezado
        filas_meta = [
            ["ID Proyecto",     meta.get("id_proyecto", "—"),
             "Fecha",           meta.get("fecha_elaboracion", "—")],
            ["Estado",          meta.get("estado", "DRAFTED"),
             "Versión Esquema", meta.get("version_esquema", "ARQ-BIM-V1")],
            ["Ubicación",       terreno.get("ubicacion", "—"),
             "Normativa",       terreno.get("normativa", "—")],
            ["Elaboró",         meta.get("elaboro", "—"), "", ""],
        ]
        ancho = [3.8 * cm, 5.0 * cm, 3.5 * cm, 5.2 * cm]
        t_meta = Table(filas_meta, colWidths=ancho)
        t_meta.setStyle(TableStyle([
            ("FONTNAME",   (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8.5),
            ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),  # labels
            ("FONTNAME",   (2, 0), (2, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (0, -1), C_AZUL_CLARO),
            ("BACKGROUND", (2, 0), (2, -1), C_AZUL_CLARO),
            ("GRID",       (0, 0), (-1, -1), 0.5, C_GRIS_MEDIO),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [C_BLANCO, C_GRIS_CLARO]),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        self.story.append(t_meta)
        self.story.append(Spacer(1, 8))

    # ── 5. Sección 1: Datos Generales del Predio ──────────────────────────────
    def _sec_datos_predio(self):
        self._seccion("DATOS GENERALES DEL PREDIO", "1.")
        t = self.datos.get("terreno", {})

        self._par(f"<b>Ubicación:</b> {t.get('ubicacion', '—')}")
        self._par(f"<b>Normativa aplicable:</b> {t.get('normativa', '—')}")
        self._espacio(4)

        # Tabla de dimensiones
        filas = [
            ["DIMENSIONES DEL TERRENO", "", "COLINDANCIAS", ""],
            ["Frente:",   f"{t.get('frente_m', '—')} m",
             "Al Norte:", t.get("colindancia_norte", "—")],
            ["Fondo:",    f"{t.get('fondo_m', '—')} m",
             "Al Sur:",   t.get("colindancia_sur", "—")],
            ["Área Total:", f"{t.get('area_total_m2', '—')} m²",
             "Al Este:",  t.get("colindancia_este", "—")],
            ["",          "",
             "Al Oeste:", t.get("colindancia_oeste", "—")],
        ]
        ancho = [3.5 * cm, 4.0 * cm, 3.5 * cm, 6.5 * cm]
        t_predio = Table(filas, colWidths=ancho)
        t_predio.setStyle(TableStyle([
            ("SPAN",       (0, 0), (1, 0)),
            ("SPAN",       (2, 0), (3, 0)),
            ("BACKGROUND", (0, 0), (1, 0), C_AZUL_OSCURO),
            ("BACKGROUND", (2, 0), (3, 0), C_AZUL_MEDIO),
            ("TEXTCOLOR",  (0, 0), (3, 0), C_BLANCO),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME",   (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTNAME",   (2, 1), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8.5),
            ("ALIGN",      (0, 0), (-1, 0), "CENTER"),
            ("GRID",       (0, 0), (-1, -1), 0.5, C_GRIS_MEDIO),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_BLANCO, C_GRIS_CLARO]),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        self.story.append(t_predio)
        self._espacio()

    # ── 6. Sección 2: Cuadro de Áreas ─────────────────────────────────────────
    def _sec_cuadro_areas(self):
        self._seccion("CUADRO DE ÁREAS Y PROGRAMA ARQUITECTÓNICO", "2.")
        programa = self.datos.get("programa", [])

        encab = ["ID", "NOMBRE DEL ESPACIO", "NIVEL", "ÁREA\n(m²)",
                 "TIPO", "IL. NATURAL", "VENT. NATURAL", "ORIENTACIÓN"]
        filas = [encab]
        total = 0.0
        for e in programa:
            area = e.get("area_m2", 0)
            total += area
            filas.append([
                e.get("id", ""),
                e.get("nombre", ""),
                e.get("nivel", ""),
                f"{area:.2f}",
                e.get("tipo", "").capitalize(),
                "✓" if e.get("iluminacion_natural") else "✗",
                "✓" if e.get("ventilacion_natural") else "✗",
                e.get("orientacion", ""),
            ])
        filas.append(["", "TOTAL", "", f"{total:.2f} m²", "", "", "", ""])

        anchos = [1.3*cm, 4.5*cm, 1.5*cm, 1.5*cm, 2.5*cm, 1.6*cm, 1.8*cm, 2.8*cm]
        t_areas = Table(filas, colWidths=anchos, repeatRows=1)
        t_areas.setStyle(TableStyle([
            # Encabezado
            ("BACKGROUND",   (0, 0), (-1, 0), C_AZUL_OSCURO),
            ("TEXTCOLOR",    (0, 0), (-1, 0), C_BLANCO),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
            ("FONTSIZE",     (0, 0), (-1, 0), 7.5),
            # Cuerpo
            ("FONTNAME",     (0, 1), (-1, -2), "Helvetica"),
            ("FONTSIZE",     (0, 1), (-1, -1), 8),
            ("ALIGN",        (3, 1), (3, -1), "RIGHT"),
            ("ALIGN",        (5, 1), (6, -1), "CENTER"),
            ("ROWBACKGROUNDS",(0, 1), (-1, -2), [C_BLANCO, C_GRIS_CLARO]),
            # Fila total
            ("BACKGROUND",   (0, -1), (-1, -1), C_AZUL_CLARO),
            ("FONTNAME",     (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",     (0, -1), (-1, -1), 8.5),
            ("ALIGN",        (3, -1), (3, -1), "RIGHT"),
            # Grid
            ("GRID",         (0, 0), (-1, -1), 0.4, C_GRIS_MEDIO),
            ("TOPPADDING",   (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
            ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ]))
        self.story.append(t_areas)
        self._espacio()

    # ── 7. Sección 3: Análisis Bioclimático ──────────────────────────────────
    def _sec_bioclimatico(self):
        self._seccion("ANÁLISIS BIOCLIMÁTICO Y DE ORIENTACIÓN", "3.")
        orient = self.datos.get("orientacion", {})
        programa = self.datos.get("programa", [])
        frente_card = orient.get("frente_cardinal", "SUR")

        self._par(
            f"El frente del predio está orientado al <b>{frente_card}</b>. "
            f"{orient.get('descripcion', '')}"
        )
        self._espacio(4)

        # Agrupar espacios por orientación
        orient_grupos: dict[str, list] = {}
        for e in programa:
            o = e.get("orientacion", "SUR")
            orient_grupos.setdefault(o, []).append(e)

        for card, espacios in sorted(orient_grupos.items()):
            bio = BIOCLIMATICO.get(card, {})
            nombres = ", ".join(e["nombre"] for e in espacios)
            area_sum = sum(e.get("area_m2", 0) for e in espacios)

            datos_bio = [
                [f"ORIENTACIÓN {card} — {nombres} ({area_sum:.1f} m²)", ""],
                ["Ganancia solar:", bio.get("ganancia_solar", "—")],
                ["Confort en verano:", bio.get("confort_verano", "—")],
                ["Ventilación:", bio.get("ventilacion", "—")],
                ["Recomendación técnica:", bio.get("recomendacion", "—")],
            ]
            anchos = [4.0 * cm, 13.5 * cm]
            t_bio = Table(datos_bio, colWidths=anchos)
            t_bio.setStyle(TableStyle([
                ("SPAN",       (0, 0), (1, 0)),
                ("BACKGROUND", (0, 0), (-1, 0),
                 C_AZUL_MEDIO if card == frente_card else colors.HexColor("#2A9D8F")),
                ("TEXTCOLOR",  (0, 0), (-1, 0), C_BLANCO),
                ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",   (0, 0), (-1, 0), 8.5),
                ("ALIGN",      (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME",   (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE",   (0, 1), (-1, -1), 8),
                ("VALIGN",     (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_BLANCO, C_GRIS_CLARO]),
                ("GRID",       (0, 0), (-1, -1), 0.4, C_GRIS_MEDIO),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            self.story.append(KeepTogether(t_bio))
            self._espacio(6)

    # ── 8. Sección 4: Especificaciones de Materiales ──────────────────────────
    def _sec_materiales(self):
        self._seccion("ESPECIFICACIONES DE MATERIALES Y ACABADOS", "4.")
        mat = self.datos.get("especificaciones_materiales", {})

        if not mat:
            self._par("No se registraron especificaciones de materiales en el JSON.")
        else:
            filas_mat = [["SISTEMA / COMPONENTE", "ESPECIFICACIÓN"]]
            labels = {
                "estructura":           "Estructura",
                "muros":                "Muros",
                "impermeabilizacion":   "Impermeabilización",
                "acabados_interiores":  "Acabados Interiores",
                "canceleria":           "Cancelería y Vidrios",
                "pisos":                "Pisos",
                "fachada":              "Fachada",
            }
            for key, label in labels.items():
                val = mat.get(key)
                if val:
                    filas_mat.append([label, val])

            t_mat = Table(filas_mat, colWidths=[4.5 * cm, 13.0 * cm], repeatRows=1)
            t_mat.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, 0), C_AZUL_OSCURO),
                ("TEXTCOLOR",    (0, 0), (-1, 0), C_BLANCO),
                ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",     (0, 0), (-1, 0), 8.5),
                ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME",     (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTNAME",     (1, 1), (1, -1), "Helvetica"),
                ("FONTSIZE",     (0, 1), (-1, -1), 8),
                ("VALIGN",       (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_BLANCO, C_GRIS_CLARO]),
                ("GRID",         (0, 0), (-1, -1), 0.4, C_GRIS_MEDIO),
                ("TOPPADDING",   (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
                ("LEFTPADDING",  (0, 0), (-1, -1), 6),
            ]))
            self.story.append(t_mat)
        self._espacio()

    # ── 9. Sección 5: Calendario de Mantenimiento Preventivo ──────────────────
    def _sec_mantenimiento(self):
        self._seccion("CALENDARIO DE MANTENIMIENTO PREVENTIVO", "5.")
        self._par(
            "El presente calendario establece las revisiones periódicas mínimas "
            "recomendadas para conservar la integridad de la obra en condiciones óptimas "
            "conforme a la normativa de San Andrés Cholula, Puebla."
        )
        self._espacio(4)

        encab = ["FRECUENCIA", "SISTEMA", "ACTIVIDAD", "RESPONSABLE"]
        filas = [encab] + [list(r) for r in CALENDARIO_MANTENIMIENTO]

        anchos = [2.2*cm, 3.5*cm, 9.0*cm, 2.8*cm]
        t_mant = Table(filas, colWidths=anchos, repeatRows=1)
        t_mant.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), C_AZUL_OSCURO),
            ("TEXTCOLOR",     (0, 0), (-1, 0), C_BLANCO),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 8),
            ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, -1), 7.5),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_BLANCO, C_GRIS_CLARO]),
            # Colorear columna frecuencia por urgencia
            ("BACKGROUND", (0, 1),  (0, 2),  colors.HexColor("#FFF3CD")),  # Semestral
            ("BACKGROUND", (0, 3),  (0, 9),  colors.HexColor("#D4EDDA")),  # Anual
            ("BACKGROUND", (0, 10), (0, 11), colors.HexColor("#F8D7DA")),  # 3-5 años
            ("FONTNAME",   (0, 1),  (0, -1), "Helvetica-Bold"),
            ("GRID",       (0, 0), (-1, -1), 0.4, C_GRIS_MEDIO),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ]))
        self.story.append(t_mant)
        self._espacio()

        # Leyenda de colores
        leyenda = [
            [Paragraph("■ Semestral", ParagraphStyle("l", fontSize=7.5, textColor=colors.HexColor("#856404")))],
            [Paragraph("■ Anual",     ParagraphStyle("l", fontSize=7.5, textColor=colors.HexColor("#155724")))],
            [Paragraph("■ 3–5 años",  ParagraphStyle("l", fontSize=7.5, textColor=colors.HexColor("#721c24")))],
        ]
        t_leyenda = Table([leyenda[0] + leyenda[1] + leyenda[2]],
                          colWidths=[4*cm, 3*cm, 3*cm])
        t_leyenda.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#FFF3CD")),
            ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#D4EDDA")),
            ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#F8D7DA")),
            ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
        ]))
        self.story.append(t_leyenda)

    # ── 10. Sección 6: Bloque de Validación y Firmas ──────────────────────────
    def _sec_firmas(self):
        self.story.append(PageBreak())
        self._seccion("BLOQUE DE VALIDACIÓN Y FIRMAS", "6.")
        meta    = self.datos.get("meta", {})
        terreno = self.datos.get("terreno", {})

        self._par(
            f"El presente <b>Manual de Mantenimiento y Entrega de Obra</b> del proyecto "
            f"<b>{meta.get('nombre_proyecto', '—')}</b> (ID: {meta.get('id_proyecto','—')}) "
            f"ubicado en <b>{terreno.get('ubicacion', '—')}</b>, ha sido elaborado conforme "
            f"al Reglamento de Construcciones Municipal vigente y los requisitos de la "
            f"Dirección de Obras Públicas del municipio de San Andrés Cholula, Puebla."
        )
        self._espacio(8)

        # Tabla de firmas
        firma_vacia = "_" * 42
        filas_firmas = [
            [
                Paragraph(firma_vacia, self.styles["firma_label"]),
                Paragraph(firma_vacia, self.styles["firma_label"]),
            ],
            [
                Paragraph("DIRECTOR RESPONSABLE DE OBRA", self.styles["firma_label"]),
                Paragraph("PROPIETARIO / CLIENTE", self.styles["firma_label"]),
            ],
            [
                Paragraph(meta.get("elaboro", "—"), self.styles["firma_sub"]),
                Paragraph("Nombre del Propietario", self.styles["firma_sub"]),
            ],
            [
                Paragraph("DRO / CSE / Perito Estructural", self.styles["firma_sub"]),
                Paragraph("C.C. / RFC: _______________________", self.styles["firma_sub"]),
            ],
            [
                Paragraph("Cédula Prof. No.: ________________", self.styles["firma_sub"]),
                Paragraph("Teléfono: ________________________", self.styles["firma_sub"]),
            ],
        ]
        t_firmas = Table(filas_firmas, colWidths=[8.75 * cm, 8.75 * cm])
        t_firmas.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LINEABOVE",     (0, 1), (-1, 1), 1, C_AZUL_OSCURO),  # línea de firma
            ("LINEABOVE",     (0, 2), (-1, 2), 0.5, C_GRIS_MEDIO),
            ("BOX",           (0, 0), (-1, -1), 0.5, C_GRIS_MEDIO),
            ("INNERGRID",     (0, 0), (-1, -1), 0.3, C_GRIS_CLARO),
        ]))
        self.story.append(t_firmas)
        self._espacio(14)

        # Sello de validación del sistema
        sello_data = [[
            Paragraph(
                f"✅ Documento generado por Sistema ARQ-BIM V1 | {meta.get('version_esquema','')}<br/>"
                f"Fecha de emisión: {datetime.now().strftime('%d/%m/%Y %H:%M')} h<br/>"
                f"Este documento es válido para carpeta de licencias municipales.",
                self.styles["pie"]
            )
        ]]
        t_sello = Table(sello_data, colWidths=[17.5 * cm])
        t_sello.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_GRIS_CLARO),
            ("BOX",           (0, 0), (-1, -1), 1, C_AZUL_MEDIO),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))
        self.story.append(t_sello)

    # ── 11. Pie de página personalizado ───────────────────────────────────────
    def _pie_pagina(self, canvas, doc):
        meta = self.datos.get("meta", {})
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#666666"))
        y_base = 1.2 * cm
        canvas.drawString(1.5 * cm, y_base,
            f"{meta.get('nombre_proyecto','Proyecto')} | {meta.get('id_proyecto','')} "
            f"| ARQ-BIM V1")
        canvas.drawRightString(
            letter[0] - 1.5 * cm, y_base,
            f"Pág. {doc.page}"
        )
        canvas.line(1.5 * cm, y_base + 5, letter[0] - 1.5 * cm, y_base + 5)
        canvas.restoreState()

    # ── 12. Compilar y exportar PDF ───────────────────────────────────────────
    def compilar_pdf(self) -> str:
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab requerido: pip install reportlab")

        meta     = self.datos.get("meta", {})
        id_proj  = meta.get("id_proyecto", "proyecto")
        out_path = self.output_dir / f"{id_proj}_Manual_Mantenimiento.pdf"

        doc = SimpleDocTemplate(
            str(out_path),
            pagesize=letter,
            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
            leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        )

        self._init_styles()
        self.story = []

        # ── Ensamble del documento ─────────────────────────────────────────────
        self._portada()
        self._sec_datos_predio()
        self._sec_cuadro_areas()
        self._sec_bioclimatico()
        self._sec_materiales()
        self._sec_mantenimiento()
        self._sec_firmas()

        # Compilar
        doc.build(self.story, onFirstPage=self._pie_pagina,
                  onLaterPages=self._pie_pagina)
        print(f"✅ PDF generado → {out_path}")
        return str(out_path)

    # ── 13. Punto de entrada principal ────────────────────────────────────────
    def run(self) -> dict:
        print("\n" + "═" * 60)
        print("  📄  AGENTE PDF MANTENIMIENTO — Iniciando")
        print("═" * 60)
        self.cargar_json()
        pdf_path = self.compilar_pdf()
        resultado = {
            "status":   "✅ Completado",
            "id_proyecto": self.datos["meta"]["id_proyecto"],
            "pdf_path": pdf_path,
        }
        print("\n✅ Agente PDF Mantenimiento finalizado.\n")
        return resultado

    # ── CrewAI Tool wrapper ───────────────────────────────────────────────────
    @staticmethod
    def as_crewai_tool():
        return {
            "nombre": "PDFMantenimientoTool",
            "descripcion": (
                "Lee el JSON ARQ-BIM V1 y genera un Manual de Mantenimiento y "
                "Entrega de Obra en PDF profesional con 6 secciones: Datos del Predio, "
                "Cuadro de Áreas, Análisis Bioclimático, Especificaciones de Materiales, "
                "Calendario de Mantenimiento y Bloque de Validación (DRO/Cliente). "
                "Parámetros: json_path (str), output_dir (str)."
            ),
            "clase": PDFMantenimientoAgent,
        }


# ── Bloque de prueba ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    json_file = sys.argv[1] if len(sys.argv) > 1 else "drafted_ARQ-2026-001.json"
    agent = PDFMantenimientoAgent(json_file, output_dir="output_pdf")
    result = agent.run()
    print(f"PDF: {result['pdf_path']}")
