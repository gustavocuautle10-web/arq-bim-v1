"""
ARQ-BIM V1 — motores/validador.py
Motor determinista de validación. Sin IA, sin aleatoriedad.
Consume modelos/normativa.py. Soporta perfil JSON externo.
"""
from __future__ import annotations
from pathlib import Path
from typing import Callable, Optional

from arq_bim.modelos.espacios import Espacio, RelacionEspacial, TipoAdyacencia
from arq_bim.modelos.proyecto import Proyecto
from arq_bim.modelos.terreno  import Terreno
from arq_bim.modelos.reglas   import (
    ResultadoEvaluacion,
    ResultadoNormativo, ResultadoConfort, ResultadoEnergia,
    ResultadoFuncionalidad, ResultadoDiseno,
)
from arq_bim.modelos.normativa import (
    ReglaNormativa, catalogo_para_uso, CAPAS_ORDEN,
)


# ─────────────────────────────────────────────────────────────────────────────
#  CONTEXTO
# ─────────────────────────────────────────────────────────────────────────────

class ContextoValidacion:
    def __init__(self, proyecto: Proyecto, terreno: Terreno,
                 espacios: list, relaciones: list):
        self.proyecto   = proyecto
        self.terreno    = terreno
        self.espacios   = espacios
        self.relaciones = relaciones
        self._idx: dict = {e.id: e for e in espacios}

    def espacio(self, id: str) -> Optional[Espacio]:
        return self._idx.get(id)

    def area_construida_total(self) -> float:
        return sum(e.area_m2 for e in self.espacios)


# ─────────────────────────────────────────────────────────────────────────────
#  REGISTRO DE HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

_H: dict[str, Callable] = {}

def handler(id_regla: str):
    def dec(fn):
        _H[id_regla] = fn
        return fn
    return dec


# ── Helpers internos ──────────────────────────────────────────────────────────

def _na(r, obs=""):
    return ResultadoEvaluacion(
        regla_id=r.id, capa=r.capa,
        resultado=ResultadoNormativo.NO_APLICA.value,
        observacion=obs)

def _eval_area(r, e, minimo):
    cumple = e.area_m2 >= minimo
    return ResultadoEvaluacion(
        regla_id=r.id, capa=r.capa, espacio_id=e.id,
        resultado=(ResultadoNormativo.CUMPLE if cumple
                   else ResultadoNormativo.NO_CUMPLE).value,
        valor_medido=e.area_m2, valor_requerido=minimo,
        observacion="" if cumple else f"Déficit {minimo - e.area_m2:.2f} m².")

def _filtrar(ctx, claves):
    return [e for e in ctx.espacios
            if any(c in e.nombre.lower() for c in claves)]


# ─────────────────────────────────────────────────────────────────────────────
#  HANDLERS — NORMATIVA
# ─────────────────────────────────────────────────────────────────────────────

@handler("NTC-HAB-001")
def _sala(ctx, r):
    items = _filtrar(ctx, r.palabras_clave)
    if not items: return _na(r, "No se definió sala ni comedor.")
    return [_eval_area(r, e, r.parametros["area_minima_m2"]) for e in items]

@handler("NTC-HAB-002")
def _recamara(ctx, r):
    items = _filtrar(ctx, r.palabras_clave)
    if not items: return _na(r, "No se definieron recámaras.")
    mp = r.parametros["area_minima_principal_m2"]
    ms = r.parametros["area_minima_secundaria_m2"]
    return [_eval_area(r, e, mp if i == 0 else ms)
            for i, e in enumerate(items)]

@handler("NTC-HAB-003")
def _cocina(ctx, r):
    items = _filtrar(ctx, r.palabras_clave)
    if not items: return _na(r, "No se definió cocina.")
    return [_eval_area(r, e, r.parametros["area_minima_m2"]) for e in items]

@handler("NTC-HAB-004")
def _bano(ctx, r):
    items = _filtrar(ctx, r.palabras_clave)
    if not items: return _na(r, "No se definió baño.")
    return [_eval_area(r, e, r.parametros["area_minima_m2"]) for e in items]

@handler("NTC-HAB-005")
def _altura(ctx, r):
    minimo = r.parametros["altura_minima_m"]
    out = []
    for e in ctx.espacios:
        if e.altura_m is None:
            out.append(ResultadoEvaluacion(
                regla_id=r.id, capa=r.capa, espacio_id=e.id,
                resultado=ResultadoNormativo.REQUIERE_VERIFICACION.value,
                observacion="Altura no capturada."))
        else:
            cumple = e.altura_m >= minimo
            out.append(ResultadoEvaluacion(
                regla_id=r.id, capa=r.capa, espacio_id=e.id,
                resultado=(ResultadoNormativo.CUMPLE if cumple
                           else ResultadoNormativo.NO_CUMPLE).value,
                valor_medido=e.altura_m, valor_requerido=minimo))
    return out

@handler("NTC-HAB-006")
def _ilum_vent(ctx, r):
    out = []
    for e in ctx.espacios:
        if not any(k in e.nombre.lower() for k in r.palabras_clave):
            continue
        if e.iluminacion_natural and e.ventilacion_natural:
            res, obs = ResultadoNormativo.CUMPLE.value, ""
        elif not e.iluminacion_natural and not e.ventilacion_natural:
            res = ResultadoNormativo.NO_CUMPLE.value
            obs = "Falta iluminación y ventilación natural."
        else:
            res = ResultadoNormativo.NO_CUMPLE.value
            obs = ("Falta ventilación." if e.iluminacion_natural
                   else "Falta iluminación.")
        out.append(ResultadoEvaluacion(
            regla_id=r.id, capa=r.capa, espacio_id=e.id,
            resultado=res, observacion=obs))
    return out or _na(r, "Sin espacios habitables.")


# ─────────────────────────────────────────────────────────────────────────────
#  HANDLERS — CONFORT
# ─────────────────────────────────────────────────────────────────────────────

@handler("CFT-001")
def _orient(ctx, r):
    favorables = r.parametros.get("orientaciones_favorables", ["norte"])
    out = []
    for e in _filtrar(ctx, r.palabras_clave):
        ori = (e.orientacion.value
               if hasattr(e.orientacion, "value") else str(e.orientacion))
        cumple = ori in favorables
        out.append(ResultadoEvaluacion(
            regla_id=r.id, capa=r.capa, espacio_id=e.id,
            resultado=(ResultadoConfort.FAVORABLE if cumple
                       else ResultadoConfort.ACEPTABLE).value,
            observacion=("Orientación óptima." if cumple
                         else f"Orientación '{ori}': revisar asoleamiento.")))
    return out or _na(r, "Sin recámaras definidas.")

@handler("CFT-002")
def _vidriado(ctx, r):
    limite = r.parametros.get("superficie_vidriada_max_pct", 30.0)
    out = []
    for e in _filtrar(ctx, r.palabras_clave):
        pct = getattr(e, "superficie_vidriada_pct", None)
        if pct is None:
            out.append(ResultadoEvaluacion(
                regla_id=r.id, capa=r.capa, espacio_id=e.id,
                resultado=ResultadoConfort.ACEPTABLE.value,
                observacion="% vidriado no capturado."))
        else:
            cumple = pct <= limite
            out.append(ResultadoEvaluacion(
                regla_id=r.id, capa=r.capa, espacio_id=e.id,
                resultado=(ResultadoConfort.FAVORABLE if cumple
                           else ResultadoConfort.REVISAR).value,
                valor_medido=pct, valor_requerido=limite,
                observacion="" if cumple
                    else f"Vidriado {pct:.0f}% > límite {limite:.0f}%."))
    return out or _na(r, "Sin espacios aplicables.")


# ─────────────────────────────────────────────────────────────────────────────
#  HANDLERS — ENERGÍA
# ─────────────────────────────────────────────────────────────────────────────

@handler("ENE-001")
def _aislamiento(ctx, r):
    out = []
    for e in _filtrar(ctx, r.palabras_clave):
        aislado = getattr(e, "tiene_aislamiento", None)
        if aislado is None:
            out.append(ResultadoEvaluacion(
                regla_id=r.id, capa=r.capa, espacio_id=e.id,
                resultado=ResultadoEnergia.VERIFICAR.value,
                observacion="Dato de aislamiento no capturado."))
        else:
            out.append(ResultadoEvaluacion(
                regla_id=r.id, capa=r.capa, espacio_id=e.id,
                resultado=(ResultadoEnergia.EFICIENTE if aislado
                           else ResultadoEnergia.MEJORABLE).value,
                observacion=("Aislamiento presente." if aislado
                             else "Sin aislamiento; revisar ganancia solar.")))
    return out or _na(r, "Sin espacios habitables.")

@handler("ENE-002")
def _vidrio_doble(ctx, r):
    exigentes = r.parametros.get("orientaciones_exigentes", ["sur", "poniente"])
    out = []
    for e in _filtrar(ctx, r.palabras_clave):
        ori = (e.orientacion.value
               if hasattr(e.orientacion, "value") else str(e.orientacion))
        if ori not in exigentes:
            out.append(ResultadoEvaluacion(
                regla_id=r.id, capa=r.capa, espacio_id=e.id,
                resultado=ResultadoEnergia.EFICIENTE.value,
                observacion=f"Orientación '{ori}' no exige vidrio doble."))
            continue
        tiene = getattr(e, "vidrio_doble", None)
        if tiene is None:
            out.append(ResultadoEvaluacion(
                regla_id=r.id, capa=r.capa, espacio_id=e.id,
                resultado=ResultadoEnergia.VERIFICAR.value,
                observacion="Dato de vidrio no capturado."))
        else:
            out.append(ResultadoEvaluacion(
                regla_id=r.id, capa=r.capa, espacio_id=e.id,
                resultado=(ResultadoEnergia.EFICIENTE if tiene
                           else ResultadoEnergia.MEJORABLE).value,
                observacion=("Vidrio doble presente." if tiene
                             else f"Fachada {ori}: considerar vidrio doble.")))
    return out or _na(r, "Sin espacios con fachadas exigentes.")


# ─────────────────────────────────────────────────────────────────────────────
#  HANDLERS — FUNCIONALIDAD
# ─────────────────────────────────────────────────────────────────────────────

@handler("FUN-001")
def _rel_prohibida(ctx, r):
    pares = {frozenset(p) for p in
             r.parametros.get("pares_prohibidos", [])}
    out = []
    for rel in ctx.relaciones:
        if rel.tipo != TipoAdyacencia.PROHIBIDA:
            continue
        ea = ctx.espacio(rel.espacio_a)
        eb = ctx.espacio(rel.espacio_b)
        ns = frozenset([
            ea.nombre.lower() if ea else rel.espacio_a,
            eb.nombre.lower() if eb else rel.espacio_b,
        ])
        out.append(ResultadoEvaluacion(
            regla_id=r.id, capa=r.capa,
            resultado=ResultadoFuncionalidad.REVISAR.value,
            observacion=(
                f"Relación prohibida: {rel.espacio_a} ↔ {rel.espacio_b}."
                + (" (CDMX: acceso indirecto obligatorio.)"
                   if ns in pares else ""))))
    return out or ResultadoEvaluacion(
        regla_id=r.id, capa=r.capa,
        resultado=ResultadoFuncionalidad.FAVORABLE.value,
        observacion="Sin relaciones prohibidas.")

@handler("FUN-002")
def _accesibilidad(ctx, r):
    out = []
    for e in _filtrar(ctx, r.palabras_clave):
        acc = getattr(e, "accesibilidad_universal", None)
        if acc is None:
            out.append(ResultadoEvaluacion(
                regla_id=r.id, capa=r.capa, espacio_id=e.id,
                resultado=ResultadoNormativo.REQUIERE_VERIFICACION.value,
                observacion="Dato de accesibilidad no capturado."))
        else:
            out.append(ResultadoEvaluacion(
                regla_id=r.id, capa=r.capa, espacio_id=e.id,
                resultado=(ResultadoFuncionalidad.FAVORABLE.value if acc
                           else ResultadoFuncionalidad.REVISAR.value),
                observacion=("Accesibilidad declarada." if acc
                             else "Revisar dimensiones para acc. universal.")))
    return out or _na(r, "Sin espacios comunes definidos.")


# ─────────────────────────────────────────────────────────────────────────────
#  HANDLERS — CRITERIOS ARQ-BIM
# ─────────────────────────────────────────────────────────────────────────────

@handler("ARQ-001")
def _factor_forma(ctx, r):
    limite = r.parametros.get("factor_forma_max", 20.0)
    out = []
    for e in ctx.espacios:
        ff = getattr(e, "factor_forma", None)
        if ff is None:
            out.append(ResultadoEvaluacion(
                regla_id=r.id, capa=r.capa, espacio_id=e.id,
                resultado=ResultadoNormativo.REQUIERE_VERIFICACION.value,
                observacion="Factor de forma no calculado."))
        else:
            cumple = ff <= limite
            out.append(ResultadoEvaluacion(
                regla_id=r.id, capa=r.capa, espacio_id=e.id,
                resultado=(ResultadoDiseno.CUMPLE if cumple
                           else ResultadoDiseno.EVITAR).value,
                valor_medido=ff, valor_requerido=limite))
    return out or _na(r, "Sin espacios definidos.")

@handler("ARQ-002")
def _indice_ocupacion(ctx, r):
    limite = r.parametros.get("indice_ocupacion_max", 0.70)
    area_util = ctx.terreno.area_util_m2
    if area_util <= 0:
        return _na(r, "Área útil no calculable.")
    construida = ctx.area_construida_total()
    indice = construida / area_util
    cumple = indice <= limite
    return ResultadoEvaluacion(
        regla_id=r.id, capa=r.capa,
        resultado=(ResultadoDiseno.CUMPLE if cumple
                   else ResultadoDiseno.NO_CUMPLE).value,
        valor_medido=round(indice, 3), valor_requerido=limite,
        observacion=(f"Índice {indice:.1%} OK." if cumple
                     else f"Índice {indice:.1%} > límite {limite:.0%}."))


# ─────────────────────────────────────────────────────────────────────────────
#  MOTOR PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def ejecutar_validacion(
    ctx: ContextoValidacion,
    catalogo: Optional[list] = None,
    ruta_perfil: Optional[str | Path] = None,
) -> list:
    """
    Corre todas las reglas activas en orden CAPAS_ORDEN.
    catalogo  : inyectar catálogo custom (tests, clientes especiales).
    ruta_perfil: path a JSON de perfil externo (vivienda_unifamiliar.json, etc.).
    """
    if catalogo:
        reglas = catalogo
    else:
        reglas = catalogo_para_uso(
            ctx.proyecto.uso_predominante,
            ruta_perfil=ruta_perfil)

    reglas_ord = sorted(
        reglas,
        key=lambda r: (CAPAS_ORDEN.index(r.capa)
                       if r.capa in CAPAS_ORDEN else 99))

    resultados = []
    for reg in reglas_ord:
        fn = _H.get(reg.id)
        if fn is None:
            resultados.append(ResultadoEvaluacion(
                regla_id=reg.id, capa=reg.capa,
                resultado=ResultadoNormativo.REQUIERE_VERIFICACION.value,
                observacion="Handler Python no registrado."))
            continue
        salida = fn(ctx, reg)
        if isinstance(salida, list):
            resultados.extend(salida)
        else:
            resultados.append(salida)
    return resultados
