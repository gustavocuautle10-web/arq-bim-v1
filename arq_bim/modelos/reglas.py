"""ARQ-BIM V1 — modelos/reglas.py — Enums de resultado para 5 capas."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ResultadoNormativo(Enum):
    CUMPLE                = "CUMPLE"
    NO_CUMPLE             = "NO_CUMPLE"
    NO_APLICA             = "NO_APLICA"
    REQUIERE_VERIFICACION = "REQUIERE_VERIFICACIÓN"


class ResultadoConfort(Enum):
    FAVORABLE = "FAVORABLE"
    ACEPTABLE = "ACEPTABLE"
    REVISAR   = "REVISAR"


class ResultadoEnergia(Enum):
    EFICIENTE  = "EFICIENTE"
    MEJORABLE  = "MEJORABLE"
    DEFICIENTE = "DEFICIENTE"
    VERIFICAR  = "REQUIERE_VERIFICACIÓN"


class ResultadoFuncionalidad(Enum):
    FAVORABLE = "FAVORABLE"
    ACEPTABLE = "ACEPTABLE"
    REVISAR   = "REVISAR"


class ResultadoDiseno(Enum):
    CUMPLE     = "CUMPLE"
    NO_CUMPLE  = "NO_CUMPLE"
    PREFERENTE = "PREFERENTE"
    EVITAR     = "EVITAR"


@dataclass
class ResultadoEvaluacion:
    regla_id: str
    capa: str
    resultado: str
    espacio_id: Optional[str]    = None
    valor_medido: Optional[float]    = None
    valor_requerido: Optional[float] = None
    observacion: str = ""

    def to_dict(self) -> dict:
        return {
            "regla_id":        self.regla_id,
            "capa":            self.capa,
            "espacio_id":      self.espacio_id,
            "resultado":       self.resultado,
            "valor_medido":    self.valor_medido,
            "valor_requerido": self.valor_requerido,
            "observacion":     self.observacion,
        }
