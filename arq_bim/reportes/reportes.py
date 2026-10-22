"""
ARQ-BIM V1 — reportes/reportes.py
Salida CLI minimalista. Sin ruido. Sin trazas.

Formato estricto:
  [✔️ CUMPLE]    [❌ NO CUMPLE]    [⚠️ VERIFICAR]    [🚫 NO APLICA]

Capas en orden obligatorio:
  1.Normativa  2.Confort  3.Energía  4.Funcionalidad  5.Criterios ARQ-BIM
"""
from __future__ import annotations
from typing import Optional
from arq_bim.modelos.normativa import CAPAS_ORDEN, ENCABEZADO_CAPA

_EMOJI: dict[str, str] = {
    "CUMPLE":                  "✔️ CUMPLE",
    "NO_CUMPLE":               "❌ NO CUMPLE",
    "REQUIERE_VERIFICACIÓN":   "⚠️ VERIFICAR",
    "NO_APLICA":               "🚫 NO APLICA",
    "FAVORABLE":               "✔️ CUMPLE",
    "ACEPTABLE":               "⚠️ VERIFICAR",
    "REVISAR":                 "❌ NO CUMPLE",
    "EFICIENTE":               "✔️ CUMPLE",
    "MEJORABLE":               "⚠️ VERIFICAR",
    "DEFICIENTE":              "❌ NO CUMPLE",
    "PREFERENTE":              "✔️ CUMPLE",
    "EVITAR":                  "❌ NO CUMPLE",
}

_POS = {"CUMPLE","FAVORABLE","EFICIENTE","PREFERENTE"}
_NEG = {"NO_CUMPLE","REVISAR","DEFICIENTE","EVITAR"}
_VER = {"MEJORABLE"}


def imprimir_reporte(
    resultados: list,
    titulo: str = "REPORTE ARQ-BIM V1",
    espacios_idx: Optional[dict] = None,
    mostrar_observaciones: bool = True,
) -> None:
    W = 72
    print(); print("=" * W)
    print(f"  {titulo}"); print("=" * W)

    por_capa: dict[str, list] = {c: [] for c in CAPAS_ORDEN}
    for r in resultados:
        capa = r.capa if r.capa in por_capa else "diseno"
        por_capa[capa].append(r)

    for capa in CAPAS_ORDEN:
        items = por_capa[capa]
        if not items:
            continue
        print(f"\n  ── {ENCABEZADO_CAPA.get(capa, capa.upper())} {'─'*8}")
        for r in items:
            tag   = _EMOJI.get(r.resultado, f"❓ {r.resultado}")
            esp   = _nombre_esp(r.espacio_id, espacios_idx)
            med   = _med(r)
            linea = f"  [{tag}]  {r.regla_id:<14} {esp}"
            if med:
                linea += f"  {med}"
            print(linea)
            if mostrar_observaciones and r.observacion:
                print(f"{'':>36}↳ {r.observacion}")

    print(); print("─" * W)
    _resumen(resultados)
    print("=" * W); print()


def imprimir_resumen(resultados: list) -> None:
    print(); _resumen(resultados); print()


def _resumen(resultados: list) -> None:
    pos  = sum(1 for r in resultados if r.resultado in _POS)
    neg  = sum(1 for r in resultados if r.resultado in _NEG)
    ver  = sum(1 for r in resultados
               if "VERIFICAC" in r.resultado or r.resultado in _VER)
    na   = sum(1 for r in resultados if r.resultado == "NO_APLICA")
    print(f"  RESUMEN  ✔️ {pos}  ❌ {neg}  "
          f"⚠️ {ver}  🚫 {na}  │ Total: {len(resultados)}")


def resultados_a_dict(resultados: list) -> dict:
    por_capa: dict = {c: [] for c in CAPAS_ORDEN}
    for r in resultados:
        capa = r.capa if r.capa in por_capa else "diseno"
        por_capa[capa].append(r.to_dict())
    pos = sum(1 for r in resultados if r.resultado in _POS)
    neg = sum(1 for r in resultados if r.resultado in _NEG)
    ver = sum(1 for r in resultados
              if "VERIFICAC" in r.resultado or r.resultado in _VER)
    return {
        "capas": por_capa,
        "resumen": {
            "cumple":    pos,
            "no_cumple": neg,
            "verificar": ver,
            "no_aplica": sum(1 for r in resultados
                             if r.resultado == "NO_APLICA"),
            "total":     len(resultados),
        },
    }


def _nombre_esp(espacio_id, idx) -> str:
    if not espacio_id:
        return f"{'—Global—':<22}"
    if idx and espacio_id in idx:
        return f"{idx[espacio_id].nombre:<22}"
    return f"{espacio_id:<22}"


def _med(r) -> str:
    partes = []
    if r.valor_medido    is not None: partes.append(f"med={r.valor_medido:.2f}")
    if r.valor_requerido is not None: partes.append(f"req={r.valor_requerido:.2f}")
    return "  ".join(partes)
