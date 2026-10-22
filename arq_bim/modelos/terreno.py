"""ARQ-BIM V1 — modelos/terreno.py"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Colindancia:
    orientacion: str
    descripcion: str
    restriccion_m: float = 0.0


@dataclass
class Terreno:
    frente_m: float
    fondo_m: float
    colindancias: list = field(default_factory=list)
    restriccion_frontal_m: float = 0.0
    restriccion_lateral_m: float = 0.0
    restriccion_fondo_m: float = 0.0
    area_total_m2: float = field(init=False)

    def __post_init__(self):
        self.area_total_m2 = self.frente_m * self.fondo_m

    @property
    def area_util_m2(self) -> float:
        frente_util = self.frente_m - 2 * self.restriccion_lateral_m
        fondo_util = self.fondo_m - self.restriccion_frontal_m - self.restriccion_fondo_m
        return max(frente_util * fondo_util, 0.0)

    def to_dict(self) -> dict:
        return {
            "frente_m": self.frente_m,
            "fondo_m": self.fondo_m,
            "area_total_m2": self.area_total_m2,
            "area_util_m2": self.area_util_m2,
            "restricciones": {
                "frontal_m": self.restriccion_frontal_m,
                "lateral_m": self.restriccion_lateral_m,
                "fondo_m": self.restriccion_fondo_m,
            },
            "colindancias": [vars(c) for c in self.colindancias],
        }
