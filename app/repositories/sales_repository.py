"""Repositorio de consultas analíticas sobre snapshots Parquet validados.

Esta capa encapsula el acceso a disco, la validación de consistencia entre
artefactos y la traducción de filtros de dominio a expresiones Polars.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import polars as pl

from app.domain.exceptions import DataNotReadyError
from app.domain.models import SalesFilters, StatisticsResult
from app.utils.locks import data_read_lock
from app.utils.snapshot import SnapshotState, validate_snapshot

_LOGGER = logging.getLogger(__name__)
_TARGET_MAPPING = {
    "MONTO APLICADO": "monto_aplicado",
    "monto_aplicado": "monto_aplicado",
}


class SalesRepository:
    """Consulta una generación coherente publicada por el proceso de ingesta.

    Las lecturas se protegen con un lock compartido para impedir que una
    publicación concurrente mezcle artefactos de generaciones distintas.
    """

    def __init__(
        self,
        processed_path: Path,
        summary_path: Path,
        metadata_path: Path,
        quality_report_path: Path,
        stat_target_column: str,
    ) -> None:
        """Inicializa las rutas y valida la columna estadística contractual.

        Args:
            processed_path: Ruta del dataset analítico en formato Parquet.
            summary_path: Ruta del resumen estadístico precomputado.
            metadata_path: Ruta del manifiesto de la generación.
            quality_report_path: Ruta del reporte agregado de calidad.
            stat_target_column: Nombre público o interno de la columna objetivo.

        Raises:
            RuntimeError: Si la columna objetivo no corresponde a
                ``MONTO APLICADO``.
        """
        try:
            self.target_column = _TARGET_MAPPING[stat_target_column]
        except KeyError as exc:
            raise RuntimeError(
                "STAT_TARGET_COLUMN solo admite 'MONTO APLICADO' en este contrato"
            ) from exc
        self.processed_path = processed_path
        self.summary_path = summary_path
        self.metadata_path = metadata_path
        self.quality_report_path = quality_report_path
        self.stat_target_column = stat_target_column

    def calculate(self, filters: SalesFilters) -> StatisticsResult:
        """Calcula estadísticas dinámicas aplicando filtros con *pushdown*.

        Args:
            filters: Filtros de dominio previamente validados.

        Returns:
            Resultado de las siete estadísticas contractuales para las filas
            coincidentes.

        Raises:
            DataNotReadyError: Si el snapshot falta, es incoherente, no puede
                leerse o no se obtiene el lock dentro del plazo.
            StatisticsCalculationError: Si Polars no puede obtener o convertir
                las agregaciones estadísticas del snapshot válido.
        """
        started = time.perf_counter()
        try:
            with data_read_lock(self.processed_path):
                self._validated_snapshot()
                lazy = pl.scan_parquet(self.processed_path)
                predicates = self._predicates(filters)
                if predicates:
                    lazy = lazy.filter(*predicates)

                # La importación local evita el ciclo entre el servicio estadístico
                # y el repositorio, una decisión de ensamblaje entre ambas capas.
                from app.services.statistics_service import statistics_from_lazyframe

                result = statistics_from_lazyframe(lazy, self.target_column)
        except (OSError, ValueError, TimeoutError, pl.exceptions.PolarsError) as exc:
            raise DataNotReadyError("Los datos estadísticos aún no están preparados") from exc
        _LOGGER.info(
            "Consulta estadística completada",
            extra={
                "event": "statistics_query",
                "filter_names": filters.names,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "result_count": result.conteo,
            },
        )
        return result

    def load_cached_statistics(self) -> StatisticsResult:
        """Obtiene las estadísticas globales de una caché coherente y validada.

        Returns:
            Estadísticas precomputadas para todo el dataset válido.

        Raises:
            DataNotReadyError: Si algún artefacto falta, es incoherente, no es
                legible o el lock de lectura expira.
        """
        try:
            with data_read_lock(self.processed_path):
                return self._validated_snapshot().statistics
        except (OSError, ValueError, TimeoutError, pl.exceptions.PolarsError) as exc:
            raise DataNotReadyError("Los datos estadísticos aún no están preparados") from exc

    def readiness(self) -> tuple[bool, str]:
        """Comprueba presencia, coherencia y legibilidad de todos los artefactos.

        Returns:
            Par ``(disponible, estado)``. El estado es ``"ready"`` cuando la
            generación es válida y ``"unreadable"`` ante cualquier fallo de
            lectura, consistencia o adquisición del lock.
        """
        try:
            with data_read_lock(self.processed_path):
                self._validated_snapshot()
        except (
            OSError,
            ValueError,
            TimeoutError,
            pl.exceptions.PolarsError,
        ):
            return False, "unreadable"
        return True, "ready"

    def _validated_snapshot(self) -> SnapshotState:
        """Valida y materializa el estado de la generación configurada.

        Returns:
            Snapshot con manifiesto, calidad y estadísticas ya validados.

        Raises:
            OSError: Si un artefacto no puede abrirse.
            ValueError: Si los artefactos no satisfacen el contrato común.
            polars.exceptions.PolarsError: Si Polars no puede leer el Parquet.
        """
        return validate_snapshot(
            processed_path=self.processed_path,
            summary_path=self.summary_path,
            metadata_path=self.metadata_path,
            quality_report_path=self.quality_report_path,
            schema_version=1,
            stat_target_column=self.stat_target_column,
        )

    @staticmethod
    def _predicates(filters: SalesFilters) -> list[pl.Expr]:
        """Traduce filtros de dominio a predicados Polars combinables con AND.

        Args:
            filters: Filtros opcionales ya normalizados.

        Returns:
            Expresiones en el mismo orden estable del contrato público. Una
            lista vacía representa una consulta sin filtros.
        """
        expressions: list[pl.Expr] = []
        if filters.genero is not None:
            expressions.append(pl.col("genero_texto") == filters.genero)
        if filters.edad is not None:
            expressions.append(pl.col("edad_en_transaccion") == filters.edad)
        if filters.canal is not None:
            expressions.append(pl.col("canal") == filters.canal)
        if filters.codigo_producto is not None:
            expressions.append(pl.col("sku") == filters.codigo_producto)
        if filters.id_persona is not None:
            expressions.append(pl.col("codigo_cliente") == filters.id_persona)
        if filters.local is not None:
            expressions.append(pl.col("local") == filters.local)
        if filters.fecha_desde is not None:
            expressions.append(pl.col("fecha") >= pl.lit(filters.fecha_desde))
        if filters.fecha_hasta is not None:
            operator = pl.col("fecha") < pl.lit(filters.fecha_hasta)
            if not filters.fecha_hasta_exclusiva:
                operator = pl.col("fecha") <= pl.lit(filters.fecha_hasta)
            expressions.append(operator)
        return expressions
