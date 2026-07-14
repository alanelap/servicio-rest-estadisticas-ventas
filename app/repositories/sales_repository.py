"""Acceso analítico desacoplado basado en Parquet y Polars."""

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
    """Consulta artefactos publicados atómicamente por la ingesta."""

    def __init__(
        self,
        processed_path: Path,
        summary_path: Path,
        metadata_path: Path,
        quality_report_path: Path,
        stat_target_column: str,
    ) -> None:
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
        """Aplica predicados conocidos y ejecuta agregaciones con pushdown."""

        started = time.perf_counter()
        try:
            with data_read_lock(self.processed_path):
                self._validated_snapshot()
                lazy = pl.scan_parquet(self.processed_path)
                predicates = self._predicates(filters)
                if predicates:
                    lazy = lazy.filter(*predicates)

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
        """Lee y valida la caché global, sin recalcular el dataset."""

        try:
            with data_read_lock(self.processed_path):
                return self._validated_snapshot().statistics
        except (OSError, ValueError, TimeoutError, pl.exceptions.PolarsError) as exc:
            raise DataNotReadyError("Los datos estadísticos aún no están preparados") from exc

    def readiness(self) -> tuple[bool, str]:
        """Comprueba presencia, coherencia y legibilidad de los cuatro artefactos."""

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
