# ARQ-BIM V1 — Motor Validador Arquitectónico

**Ing. Gustavo Ángel Cuautle Zimarrón** — DRO / CSE / Perito Estructural

Motor modular de validación arquitectónica conforme NTC-CDMX 2023.
Flujo: **GitHub → Google Colab → Drafted IA**

---

## Estructura del repositorio

```
arq-bim-v1/
├── ARQ_BIM_Colab.py           ← cuaderno principal (7 celdas)
├── requirements.txt
├── .gitignore
│
├── arq_bim/                   ← paquete Python principal
│   ├── __init__.py
│   ├── modelos/
│   │   ├── proyecto.py        ← Proyecto, Nivel
│   │   ├── terreno.py         ← Terreno, Colindancia
│   │   ├── espacios.py        ← Espacio, programa_desde_dict()
│   │   ├── reglas.py          ← Enums de resultado (5 capas)
│   │   └── normativa.py       ← Catálogo de reglas + carga JSON
│   ├── motores/
│   │   └── validador.py       ← Motor determinista, 5 capas
│   ├── integracion/
│   │   ├── drafted.py         ← DraftedExporter, exportar_a_drafted()
│   │   └── importador_espacial.py  ← DXF / IFC / GLB (opcional)
│   └── reportes/
│       ├── reportes.py        ← CLI minimalista con emojis
│       └── reporte_cumplimiento.py ← Reporte Word
│
├── agentes/
│   └── crew_agente.py         ← CrewAI opcional (texto → JSON)
│
├── perfiles/
│   ├── vivienda_unifamiliar.json  ← perfil normativo intercambiable
│   └── uso_mixto.json
│
└── tests/
    ├── test_caso_vivienda_8x20.py
    └── test_ifc_parser.py
```

---

## Inicio rápido en Colab

```python
# Celda 1 — una sola vez por sesión
!git clone https://github.com/TU_USUARIO/arq-bim-v1.git
import sys; sys.path.insert(0, "/content/arq-bim-v1")
!pip install -q python-docx
```

---

## Comandos Git — actualizar desde tu PC

```bash
# Primera vez
git init
git remote add origin https://github.com/TU_USUARIO/arq-bim-v1.git
git branch -M main

# Cada cambio
git add .
git commit -m "descripción del cambio"
git push origin main
```

---

## Salida CLI

```
========================================================================
  REPORTE ARQ-BIM — Vivienda Cliente
========================================================================

  ── 1. NORMATIVA  (NTC-CDMX) ────────────
  [✔️ CUMPLE]   NTC-HAB-001   Sala-Comedor        med=15.00  req=13.00
  [✔️ CUMPLE]   NTC-HAB-002   Recámara Principal  med=8.50   req=7.30
  [❌ NO CUMPLE] NTC-HAB-004  Baño                med=2.30   req=2.50
                               ↳ Déficit 0.20 m².

  ── 2. CONFORT ────────────────────────────
  [✔️ CUMPLE]   CFT-001       Recámara Principal

  ── 3. EFICIENCIA ENERGÉTICA  (NOM-020) ──
  [⚠️ VERIFICAR] ENE-001      Sala-Comedor

  ── 4. FUNCIONALIDAD ──────────────────────
  [✔️ CUMPLE]   FUN-001       —Global—

  ── 5. CRITERIOS ARQ-BIM ──────────────────
  [⚠️ VERIFICAR] ARQ-001      Sala-Comedor

------------------------------------------------------------------------
  RESUMEN  ✔️ 7  ❌ 1  ⚠️ 3  🚫 0  │ Total: 11
========================================================================
```
