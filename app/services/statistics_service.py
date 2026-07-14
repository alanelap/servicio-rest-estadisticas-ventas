"""Cálculo vectorizado de las siete estadísticas del contrato."""

from __future__ import annotations

import math
from typing import Any

import polars as pl

from app.domain.exceptions import StatisticsCalculationError
from app.domain.models import SalesFilters, StatisticsResult
from app.repositories.sales_repository import SalesRepository


def statistics_from_lazyframe(
    frame: pl.LazyFrame, target_column: str = "monto_aplicado"
) -> StatisticsResult:
    """Agrega un LazyFrame con Polars y desviación estándar poblacional."""

    target = pl.col(target_column)
    valid = frame.filter(target.is_not_null() & target.is_finite())
    row = valid.select(
        pl.len().cast(pl.Int64).alias("conteo"),
        target.sum().alias("suma"),
        target.mean().alias("promedio"),
        target.min().alias("minimo"),
        target.max().alias("maximo"),
        target.median().alias("mediana"),
        target.std(ddof=0).alias("desviacion_estandar"),
    ).collect(engine="streaming")

    values = row.row(0, named=True)
    count = int(values["conteo"])
    if count == 0:
        return StatisticsResult.empty()
    return StatisticsResult(
        suma=_required_finite_float(values["suma"]),
        conteo=count,
        promedio=_required_finite_float(values["promedio"]),
        minimo=_required_finite_float(values["minimo"]),
        maximo=_required_finite_float(values["maximo"]),
        mediana=_required_finite_float(values["mediana"]),
        desviacion_estandar=_required_finite_float(values["desviacion_estandar"]),
    )


def _required_finite_float(value: Any) -> float:
    """Rechaza overflow en vez de inventar una estadística aparentemente válida."""

    try:
        converted = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise StatisticsCalculationError() from exc
    if not math.isfinite(converted):
        raise StatisticsCalculationError()
    return converted


class StatisticsService:
    """Selecciona caché global o consulta filtrada sin conocer HTTP."""

    def __init__(self, repository: SalesRepository) -> None:
        self._repository = repository

    def calculate(self, filters: SalesFilters) -> StatisticsResult:
        """Obtiene estadísticas globales precomputadas o dinámicas."""

        if filters.is_empty:
            return self._repository.load_cached_statistics()
        return self._repository.calculate(filters)
