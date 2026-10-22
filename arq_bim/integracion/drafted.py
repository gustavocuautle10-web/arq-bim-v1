"""
ARQ-BIM V1 — integracion/drafted.py
Exportador JSON normalizado para Drafted IA.
"""
from __future__ import annotations
import json, math
from datetime import datetime
from pathlib  import Path
from typing   import Optional

from arq_bim.modelos.proyecto  import Proyecto
from arq_bim.modelos.terreno   import Terreno
from arq_bim.modelos.espacios  import Espacio, RelacionEspacial

SCHEMA_VERSION = "1.0"


class DraftedExporter:
    def __init__(self, proyecto: Proyecto, terreno: Terreno,
                 espacios: list, relaciones: list,
                 metadata: Optional[dict] = None):
        self.proyecto   = proyecto
        self.terreno    = terreno
        self.espacios   = espacios
        self.relaciones = relaciones
        self.metadata   = metadata or {}

    def exportar(self, indent: int = 2) -> str:
        return json.dumps(self._payload(),
                          ensure_ascii=False, indent=indent)

    def guardar(self, ruta: str | Path) -> Path:
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(self.exportar(), encoding="utf-8")
        print(f"[DRAFTED] Payload → {ruta}")
        return ruta

    def geometria_simplificada(self) -> list[dict]:
        out, x = [], 0.0
        for e in self.espacios:
            ancho = e.ancho_minimo_m or round(math.sqrt(e.area_m2 / 1.6), 2)
            fondo = round(e.area_m2 / ancho, 2) if ancho else 0.0
            out.append({
                "id": e.id, "nombre": e.nombre, "nivel": e.nivel_id,
                "bbox": {"x": round(x, 2), "y": 0.0,
                         "ancho": round(ancho, 2), "fondo": fondo,
                         "area": e.area_m2},
            })
            x += ancho + 0.10
        return out

    def _payload(self) -> dict:
        return {
            "_schema":    SCHEMA_VERSION,
            "_generado":  datetime.now().isoformat(timespec="seconds"),
            "_motor":     "ARQ-BIM V1",
            "metadata":   self.metadata,
            "proyecto":   self.proyecto.to_dict(),
            "terreno":    self.terreno.to_dict(),
            "programa":   [self._esp(e) for e in self.espacios],
            "relaciones": [{"de": r.espacio_a, "a": r.espacio_b,
                            "tipo": r.tipo.value if hasattr(r.tipo, "value")
                            else str(r.tipo)}
                           for r in self.relaciones],
            "geometria_simplificada": self.geometria_simplificada(),
            "restricciones_drafted": {
                "prohibir_calculo_estructural": True,
                "prohibir_sismico": True,
                "modo": "validacion_arquitectonica",
            },
        }

    def _esp(self, e: Espacio) -> dict:
        return {
            "id":                    e.id,
            "nombre":                e.nombre,
            "area_m2":               e.area_m2,
            "nivel":                 e.nivel_id,
            "altura_m":              e.altura_m,
            "ancho_minimo_m":        e.ancho_minimo_m,
            "iluminacion_natural":   e.iluminacion_natural,
            "ventilacion_natural":   e.ventilacion_natural,
            "orientacion":           e.orientacion.value
                                     if hasattr(e.orientacion, "value")
                                     else str(e.orientacion),
            "superficie_vidriada_pct": getattr(e, "superficie_vidriada_pct", 0.0),
            "tiene_aislamiento":     getattr(e, "tiene_aislamiento", False),
            "vidrio_doble":          getattr(e, "vidrio_doble", False),
            "accesibilidad_universal": getattr(e, "accesibilidad_universal", False),
        }


def exportar_a_drafted(
    proyecto, terreno, espacios, relaciones,
    ruta_salida: str = "/content/drafted_payload.json",
    metadata: Optional[dict] = None,
) -> str:
    exp = DraftedExporter(proyecto, terreno, espacios, relaciones, metadata)
    exp.guardar(ruta_salida)
    return exp.exportar()
