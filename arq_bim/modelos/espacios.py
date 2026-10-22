"""ARQ-BIM V1 — modelos/espacios.py"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TipoAdyacencia(Enum):
    OBLIGATORIA = "obligatoria"
    PREFERENTE  = "preferente"
    NEUTRA      = "neutra"
    EVITAR      = "evitar"
    PROHIBIDA   = "prohibida"


class OrientacionFachada(Enum):
    NORTE    = "norte"
    SUR      = "sur"
    ORIENTE  = "oriente"
    PONIENTE = "poniente"
    NO_DEF   = "no_definida"


@dataclass
class Espacio:
    id: str
    nombre: str
    area_m2: float
    nivel_id: str
    iluminacion_natural: bool = False
    ventilacion_natural: bool = False
    ancho_minimo_m: Optional[float] = None
    altura_m: Optional[float] = None
    orientacion: OrientacionFachada = OrientacionFachada.NO_DEF
    superficie_vidriada_pct: float = 0.0
    tiene_aislamiento: bool = False
    vidrio_doble: bool = False
    accesibilidad_universal: bool = False

    def to_dict(self) -> dict:
        d = {k: v for k, v in vars(self).items()}
        d["orientacion"] = self.orientacion.value
        return d


@dataclass
class RelacionEspacial:
    espacio_a: str
    espacio_b: str
    tipo: TipoAdyacencia

    def to_dict(self) -> dict:
        return {
            "espacio_a": self.espacio_a,
            "espacio_b": self.espacio_b,
            "tipo": self.tipo.value,
        }


def programa_desde_dict(lista: list[dict]) -> list[Espacio]:
    """Construye list[Espacio] desde lista de dicts. Uso rápido en Colab."""
    espacios = []
    for d in lista:
        d = dict(d)
        ori_raw = d.pop("orientacion", "no_definida")
        try:
            ori = OrientacionFachada(ori_raw)
        except ValueError:
            ori = OrientacionFachada.NO_DEF
        campos = {k: v for k, v in d.items()
                  if k in Espacio.__dataclass_fields__}
        e = Espacio(**campos)
        e.orientacion = ori
        espacios.append(e)
    return espacios
