"""ARQ-BIM V1 — paquete principal."""
from arq_bim.modelos.proyecto   import Proyecto, Nivel
from arq_bim.modelos.terreno    import Terreno, Colindancia
from arq_bim.modelos.espacios   import Espacio, RelacionEspacial, programa_desde_dict
from arq_bim.modelos.reglas     import ResultadoEvaluacion
from arq_bim.motores.validador  import ContextoValidacion, ejecutar_validacion
from arq_bim.reportes.reportes  import imprimir_reporte, resultados_a_dict
from arq_bim.integracion.drafted import DraftedExporter, exportar_a_drafted

__version__ = "1.0.0"
__all__ = [
    "Proyecto","Nivel","Terreno","Colindancia",
    "Espacio","RelacionEspacial","programa_desde_dict",
    "ResultadoEvaluacion",
    "ContextoValidacion","ejecutar_validacion",
    "imprimir_reporte","resultados_a_dict",
    "DraftedExporter","exportar_a_drafted",
]
