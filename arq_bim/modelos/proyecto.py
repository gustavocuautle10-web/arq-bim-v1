"""ARQ-BIM V1 — modelos/proyecto.py"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Nivel:
    id: str
    altura_piso_techo: float
    uso: str = "habitacional"


@dataclass
class Proyecto:
    nombre: str
    clave: str
    uso_predominante: str
    niveles: list = field(default_factory=list)
    orientacion_norte: float = 0.0
    version: str = "1.0"

    def to_dict(self) -> dict:
        return {
            "nombre": self.nombre,
            "clave": self.clave,
            "uso_predominante": self.uso_predominante,
            "niveles": [vars(n) for n in self.niveles],
            "orientacion_norte": self.orientacion_norte,
            "version": self.version,
        }
