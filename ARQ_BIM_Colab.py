"""
╔══════════════════════════════════════════════════════════════════╗
║  ARQ-BIM V1 — Google Colab Entry Point                         ║
║  GitHub + CrewAI + Drafted IA                                   ║
║  Ing. Gustavo Ángel Cuautle Zimarrón                           ║
╚══════════════════════════════════════════════════════════════════╝

Cada sección = una celda independiente en Colab.
Para cambio de cliente: editar solo CELDA 2 o CELDA 2b (texto libre).
"""

# ════════════════════════════════════════════════════════════════
# CELDA 1 — Clonar repo, instalar deps, configurar sys.path
# ════════════════════════════════════════════════════════════════
import os, sys, subprocess

# ── 1a. Clonar repositorio desde GitHub ──────────────────────────
REPO_URL = "https://github.com/TU_USUARIO/arq-bim-v1.git"
REPO_DIR = "/content/arq-bim-v1"

if not os.path.exists(REPO_DIR):
    os.system(f"git clone {REPO_URL} {REPO_DIR}")
    print("✔️  Repositorio clonado.")
else:
    os.system(f"cd {REPO_DIR} && git pull origin main")
    print("✔️  Repositorio actualizado (git pull).")

# ── 1b. Agregar al sys.path ────────────────────────────────────
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)
print(f"✔️  sys.path configurado: {REPO_DIR}")

# ── 1c. Instalar dependencias ──────────────────────────────────
def pip(pkg):
    subprocess.check_call([sys.executable, "-m", "pip",
                           "install", "-q", pkg])

pip("python-docx")
# pip("crewai crewai-tools langchain-openai")  # ← descomentar si usas CrewAI
# pip("ezdxf")           # ← DXF
# pip("ifcopenshell")    # ← IFC
# pip("trimesh")         # ← GLB

# ── 1d. Verificar importación ──────────────────────────────────
try:
    from arq_bim import (
        Proyecto, Nivel, Terreno, Colindancia,
        Espacio, programa_desde_dict,
        ContextoValidacion, ejecutar_validacion,
        imprimir_reporte, exportar_a_drafted,
    )
    print("✔️  ARQ-BIM V1 cargado correctamente.")
except Exception as e:
    print(f"❌  Error: {e}")


# ════════════════════════════════════════════════════════════════
# CELDA 2a — DATOS MANUALES (editar por cliente)
# ════════════════════════════════════════════════════════════════

proyecto = Proyecto(
    nombre           = "Vivienda Cliente",   # ← cambiar
    clave            = "ARQ-2026-001",        # ← cambiar
    uso_predominante = "vivienda_unifamiliar",
    niveles          = [Nivel("PB", 2.50, "habitacional")],
    orientacion_norte= 0.0,
)

terreno = Terreno(
    frente_m             = 8.00,   # ← cambiar
    fondo_m              = 20.00,  # ← cambiar
    restriccion_frontal_m= 3.00,
    restriccion_lateral_m= 1.00,
    restriccion_fondo_m  = 3.00,
    colindancias         = [
        Colindancia("norte",   "Vía pública 8.00 m"),
        Colindancia("sur",     "Predio habitacional"),
        Colindancia("oriente", "Predio habitacional"),
        Colindancia("poniente","Predio habitacional"),
    ],
)

print(f"✔️  Proyecto: {proyecto.nombre}")
print(f"    Terreno : {terreno.frente_m}×{terreno.fondo_m} m  "
      f"│ Área útil: {terreno.area_util_m2:.1f} m²")


# ════════════════════════════════════════════════════════════════
# CELDA 2b — ALTERNATIVA: texto libre del cliente → CrewAI / parseo
# (usar esta celda EN LUGAR de la Celda 2a cuando el cliente
#  entrega requerimientos en lenguaje natural)
# ════════════════════════════════════════════════════════════════

TEXTO_CLIENTE = """
Necesito una casa de un nivel en un terreno de 8 por 20 metros,
con fachada al norte. Quiero una sala-comedor amplia, dos recámaras,
una cocina y un baño. La recámara principal debe dar al norte.
"""

# from agentes.crew_agente import interpretar
# datos = interpretar(
#     TEXTO_CLIENTE,
#     api_key="sk-...",     # ← tu OpenAI key, o dejar vacío para parseo básico
#     verbose=True,
# )
#
# # Construir objetos desde el JSON del agente
# from arq_bim.modelos.proyecto import Proyecto, Nivel
# from arq_bim.modelos.terreno  import Terreno
#
# p = datos["proyecto"]
# t = datos["terreno"]
# proyecto = Proyecto(
#     nombre=p.get("nombre","Proyecto"),
#     clave=p.get("clave",""),
#     uso_predominante=p.get("uso_predominante","vivienda_unifamiliar"),
#     niveles=[Nivel("PB", 2.50, "habitacional")],
#     orientacion_norte=p.get("orientacion_norte_grados", 0.0),
# )
# terreno = Terreno(
#     frente_m=t.get("frente_m") or 8.0,
#     fondo_m=t.get("fondo_m") or 20.0,
#     restriccion_frontal_m=t.get("restriccion_frontal_m", 3.0),
#     restriccion_lateral_m=t.get("restriccion_lateral_m", 1.0),
#     restriccion_fondo_m=t.get("restriccion_fondo_m", 3.0),
# )
# programa_raw = datos["programa_arquitectonico"]
# print("✔️  Datos extraídos por agente.")
# print(f"    Nota: {datos.get('notas_adicionales', [])}")


# ════════════════════════════════════════════════════════════════
# CELDA 3 — PROGRAMA ARQUITECTÓNICO (editar por cliente)
# ════════════════════════════════════════════════════════════════

programa_raw = [
    {
        "id": "E01", "nombre": "Sala-Comedor",       "area_m2": 15.00,
        "nivel_id": "PB", "iluminacion_natural": True,
        "ventilacion_natural": True, "altura_m": 2.50,
        "orientacion": "sur", "superficie_vidriada_pct": 20.0,
    },
    {
        "id": "E02", "nombre": "Recámara Principal", "area_m2": 8.50,
        "nivel_id": "PB", "iluminacion_natural": True,
        "ventilacion_natural": True, "altura_m": 2.50,
        "orientacion": "norte", "tiene_aislamiento": True,
    },
    {
        "id": "E03", "nombre": "Recámara Secundaria","area_m2": 6.50,
        "nivel_id": "PB", "iluminacion_natural": True,
        "ventilacion_natural": True, "altura_m": 2.50,
        "orientacion": "norte",
    },
    {
        "id": "E04", "nombre": "Cocina",             "area_m2": 4.00,
        "nivel_id": "PB", "iluminacion_natural": True,
        "ventilacion_natural": True, "altura_m": 2.50,
    },
    {
        "id": "E05", "nombre": "Baño",               "area_m2": 3.00,
        "nivel_id": "PB", "iluminacion_natural": False,
        "ventilacion_natural": True, "altura_m": 2.50,
    },
]

espacios   = programa_desde_dict(programa_raw)
relaciones = []

print(f"✔️  Programa: {len(espacios)} espacios")
for e in espacios:
    print(f"    {e.id}  {e.nombre:<24} {e.area_m2:>6.2f} m²")


# ════════════════════════════════════════════════════════════════
# CELDA 4 — VALIDACIÓN + REPORTE CLI
# Opción A: catálogo interno (sin JSON externo)
# Opción B: perfil JSON intercambiable
# ════════════════════════════════════════════════════════════════

ctx = ContextoValidacion(proyecto, terreno, espacios, relaciones)

# Opción A — catálogo interno (default)
resultados = ejecutar_validacion(ctx)

# Opción B — perfil JSON externo (descomentar para usar)
# PERFIL = f"{REPO_DIR}/perfiles/vivienda_unifamiliar.json"
# resultados = ejecutar_validacion(ctx, ruta_perfil=PERFIL)

idx = {e.id: e for e in espacios}
imprimir_reporte(
    resultados,
    titulo=f"REPORTE ARQ-BIM — {proyecto.nombre}",
    espacios_idx=idx,
    mostrar_observaciones=True,
)


# ════════════════════════════════════════════════════════════════
# CELDA 5 — EXPORTAR JSON PARA DRAFTED IA
# ════════════════════════════════════════════════════════════════

RUTA_JSON = f"/content/drafted_{proyecto.clave}.json"

json_str = exportar_a_drafted(
    proyecto, terreno, espacios, relaciones,
    ruta_salida=RUTA_JSON,
    metadata={"cliente": proyecto.nombre, "version": "1.0"},
)

# Descargar archivo desde Colab
from google.colab import files
files.download(RUTA_JSON)
print(f"✔️  JSON descargado → subir a Drafted IA.")


# ════════════════════════════════════════════════════════════════
# CELDA 6 — REPORTE WORD (opcional)
# ════════════════════════════════════════════════════════════════

try:
    from arq_bim.reportes.reporte_cumplimiento import GeneradorReporte
    RUTA_DOCX = f"/content/ReporteARQ_{proyecto.clave}.docx"
    GeneradorReporte(
        proyecto=proyecto, terreno=terreno,
        espacios=espacios, resultados=resultados,
        firmante="Ing. Gustavo Ángel Cuautle Zimarrón",
    ).generar(RUTA_DOCX)
    files.download(RUTA_DOCX)
    print(f"✔️  Word descargado.")
except Exception as ex:
    print(f"⚠️  Word omitido: {ex}")


# ════════════════════════════════════════════════════════════════
# CELDA 7 — COMANDOS GIT (actualizar repo desde PC local)
# ════════════════════════════════════════════════════════════════
"""
── En tu PC local, después de editar cualquier archivo ────────────

# Primera vez:
git init
git remote add origin https://github.com/TU_USUARIO/arq-bim-v1.git
git branch -M main

# Cada actualización:
git add .
git commit -m "descripción del cambio"
git push origin main

# En Colab, para aplicar el cambio:
# → Ejecuta la Celda 1 (git pull) y luego desde Celda 3

── Cambios más comunes ────────────────────────────────────────────

Ajustar área mínima (normativa):
  Archivo: arq_bim/modelos/normativa.py  → CATALOGO_BASE
  O bien:  perfiles/vivienda_unifamiliar.json → parametros

Agregar nuevo espacio al programa:
  Archivo: ARQ_BIM_Colab.py → Celda 3 → programa_raw

Agregar nueva regla:
  Archivo: arq_bim/modelos/normativa.py  → CATALOGO_BASE
  Handler: arq_bim/motores/validador.py  → @handler("NUEVA-ID")

Cambiar perfil de cliente:
  Celda 4 → descomentar Opción B y apuntar a perfiles/uso_mixto.json
"""
