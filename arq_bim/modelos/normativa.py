"""
ARQ-BIM V1 — modelos/normativa.py
Catálogo de reglas agnóstico: puede cargarse desde Python o desde JSON externo.
CAPAS: normativa | confort | energia | funcionalidad | diseno
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

CAPAS_ORDEN = ["normativa", "confort", "energia", "funcionalidad", "diseno"]

ENCABEZADO_CAPA = {
    "normativa":     "1. NORMATIVA  (NTC-CDMX)",
    "confort":       "2. CONFORT",
    "energia":       "3. EFICIENCIA ENERGÉTICA  (NOM-020)",
    "funcionalidad": "4. FUNCIONALIDAD",
    "diseno":        "5. CRITERIOS ARQ-BIM",
}


@dataclass
class ReglaNormativa:
    id: str
    capa: str
    fuente: str
    apartado: str
    descripcion: str
    parametros: dict[str, Any]  = field(default_factory=dict)
    palabras_clave: list[str]   = field(default_factory=list)
    uso_aplica: list[str]       = field(default_factory=list)
    activa: bool                = True
    version_fuente: str         = "2023"

    def aplica_a(self, uso: str) -> bool:
        return not self.uso_aplica or uso in self.uso_aplica

    def to_dict(self) -> dict:
        return vars(self)


def catalogo_desde_json(ruta: str | Path) -> list[ReglaNormativa]:
    """
    Carga el catálogo desde un perfil JSON intercambiable.
    Compatible con perfiles/vivienda_unifamiliar.json, uso_mixto.json, etc.
    """
    with open(ruta, encoding="utf-8") as f:
        data = json.load(f)
    return [
        ReglaNormativa(
            id=r["id"],
            capa=r["capa"],
            fuente=r["fuente"],
            apartado=r["apartado"],
            descripcion=r["descripcion"],
            parametros=r.get("parametros", {}),
            palabras_clave=r.get("palabras_clave", []),
            uso_aplica=r.get("uso_aplica", []),
            activa=r.get("activa", True),
            version_fuente=r.get("version_fuente", "2023"),
        )
        for r in data.get("reglas", [])
        if r.get("activa", True)
    ]


def catalogo_para_uso(
    uso: str,
    ruta_perfil: Optional[str | Path] = None,
) -> list[ReglaNormativa]:
    """
    Devuelve reglas filtradas por uso.
    Si ruta_perfil es None, usa el catálogo interno (CATALOGO_BASE).
    """
    catalogo = (catalogo_desde_json(ruta_perfil)
                if ruta_perfil else CATALOGO_BASE)
    return [r for r in catalogo if r.activa and r.aplica_a(uso)]


# ── Catálogo interno (fallback sin JSON externo) ──────────────────────────────
CATALOGO_BASE: list[ReglaNormativa] = [
    ReglaNormativa(
        id="NTC-HAB-001", capa="normativa",
        fuente="NTC-CDMX Habitabilidad", apartado="Art. 10 Fracc. II",
        descripcion="Área mínima sala-comedor",
        parametros={"area_minima_m2": 13.00},
        palabras_clave=["sala", "comedor"],
        uso_aplica=["vivienda_unifamiliar", "vivienda_plurifamiliar"],
    ),
    ReglaNormativa(
        id="NTC-HAB-002", capa="normativa",
        fuente="NTC-CDMX Habitabilidad", apartado="Art. 10 Fracc. II",
        descripcion="Área mínima recámaras",
        parametros={"area_minima_principal_m2": 7.30,
                    "area_minima_secundaria_m2": 6.00},
        palabras_clave=["recámara", "recamara"],
        uso_aplica=["vivienda_unifamiliar", "vivienda_plurifamiliar"],
    ),
    ReglaNormativa(
        id="NTC-HAB-003", capa="normativa",
        fuente="NTC-CDMX Habitabilidad", apartado="Art. 10 Fracc. II",
        descripcion="Área mínima cocina",
        parametros={"area_minima_m2": 3.00},
        palabras_clave=["cocina"],
        uso_aplica=["vivienda_unifamiliar", "vivienda_plurifamiliar"],
    ),
    ReglaNormativa(
        id="NTC-HAB-004", capa="normativa",
        fuente="NTC-CDMX Habitabilidad", apartado="Art. 10 Fracc. II",
        descripcion="Área mínima baño",
        parametros={"area_minima_m2": 2.50},
        palabras_clave=["baño", "bano"],
        uso_aplica=["vivienda_unifamiliar", "vivienda_plurifamiliar"],
    ),
    ReglaNormativa(
        id="NTC-HAB-005", capa="normativa",
        fuente="NTC-CDMX Habitabilidad", apartado="Art. 11",
        descripcion="Altura libre mínima en espacios habitables",
        parametros={"altura_minima_m": 2.30},
    ),
    ReglaNormativa(
        id="NTC-HAB-006", capa="normativa",
        fuente="NTC-CDMX Habitabilidad", apartado="Art. 13",
        descripcion="Iluminación y ventilación natural",
        palabras_clave=["sala", "comedor", "recámara", "recamara", "estudio"],
        uso_aplica=["vivienda_unifamiliar", "vivienda_plurifamiliar"],
    ),
    ReglaNormativa(
        id="CFT-001", capa="confort",
        fuente="ARQ-BIM Confort", apartado="CFT §1",
        descripcion="Orientación favorable de recámaras",
        parametros={"orientaciones_favorables": ["norte"]},
        palabras_clave=["recámara", "recamara"],
    ),
    ReglaNormativa(
        id="CFT-002", capa="confort",
        fuente="ARQ-BIM Confort", apartado="CFT §2",
        descripcion="Superficie vidriada máxima",
        parametros={"superficie_vidriada_max_pct": 30.0},
        palabras_clave=["sala", "comedor", "estudio"],
    ),
    ReglaNormativa(
        id="ENE-001", capa="energia",
        fuente="NOM-020-ENER-2011", apartado="§5.2",
        descripcion="Aislamiento térmico en espacios habitables",
        palabras_clave=["sala", "comedor", "recámara", "recamara"],
    ),
    ReglaNormativa(
        id="ENE-002", capa="energia",
        fuente="NOM-020-ENER-2011", apartado="§5.3",
        descripcion="Vidrio doble en fachadas sur y poniente",
        parametros={"orientaciones_exigentes": ["sur", "poniente"]},
        palabras_clave=["sala", "comedor", "estudio"],
    ),
    ReglaNormativa(
        id="FUN-001", capa="funcionalidad",
        fuente="ARQ-BIM Funcionalidad", apartado="FUN §1",
        descripcion="Relaciones espaciales prohibidas",
        parametros={"pares_prohibidos": [["cocina", "baño"],
                                         ["cocina", "bano"]]},
    ),
    ReglaNormativa(
        id="FUN-002", capa="funcionalidad",
        fuente="NTC-CDMX Accesibilidad", apartado="Art. 4",
        descripcion="Accesibilidad universal en espacios comunes",
        palabras_clave=["sala", "comedor", "cocina"],
    ),
    ReglaNormativa(
        id="ARQ-001", capa="diseno",
        fuente="ARQ-BIM Diseño", apartado="DIS §1",
        descripcion="Factor de forma eficiente (≤ 20)",
        parametros={"factor_forma_max": 20.0},
    ),
    ReglaNormativa(
        id="ARQ-002", capa="diseno",
        fuente="ARQ-BIM Diseño", apartado="DIS §2",
        descripcion="Índice de ocupación ≤ 70%",
        parametros={"indice_ocupacion_max": 0.70},
    ),
]
