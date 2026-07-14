"""Cálculo vectorizado de las siete estadísticas exigidas por el contrato.

El módulo mantiene la agregación independiente de HTTP y ofrece una única ruta
de cálculo para la ingesta inicial y las consultas filtradas del repositorio.
"""

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
    """Calcula las estadísticas contractuales sobre una columna numérica.

    Los valores nulos o no finitos se excluyen antes de agregar. La desviación
    estándar es poblacional (``ddof=0``) y la ejecución solicita el motor streaming
    de Polars para reducir la presión de memoria.

    Args:
        frame: Plan perezoso que contiene las ventas que se deben resumir.
        target_column: Nombre de la columna numérica que se agregará.

    Returns:
        Las siete estadísticas del contrato, o un resultado vacío si no quedan
        valores válidos.

    Raises:
        StatisticsCalculationError: Si Polars produce un agregado que no puede
            representarse como número finito.
        polars.exceptions.PolarsError: Si el plan no puede resolverse, por ejemplo,
            porque la columna objetivo no existe.
    """
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
    """Convierte un agregado y exige que su representación sea finita.

    Args:
        value: Resultado escalar devuelto por Polars.

    Returns:
        Valor convertido a ``float``.

    Raises:
        StatisticsCalculationError: Si el valor no es numérico, desborda o es
            infinito/NaN.
    """
    try:
        converted = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise StatisticsCalculationError() from exc
    if not math.isfinite(converted):
        raise StatisticsCalculationError()
    return converted


class StatisticsService:
    """Orquesta estadísticas globales o filtradas sin depender de HTTP."""

    def __init__(self, repository: SalesRepository) -> None:
        """Inicializa el caso de uso con su repositorio de ventas.

        Args:
            repository: Fuente de estadísticas precalculadas y consultas dinámicas.
        """
        self._repository = repository

    def calculate(self, filters: SalesFilters) -> StatisticsResult:
        """Obtiene estadísticas globales precalculadas o calcula las filtradas.

        Args:
            filters: Criterios de selección ya validados por la capa de servicio.

        Returns:
            Resultado estadístico correspondiente al conjunto seleccionado.

        Raises:
            DataNotReadyError: Si el repositorio no dispone de un snapshot válido.
            StatisticsCalculationError: Si algún agregado no es representable como
                número finito.
        """
        if filters.is_empty:
            # El caso global reutiliza el resumen publicado durante la ingesta;
            # cualquier filtro requiere evaluar el Parquet para respetar su alcance.
            return self._repository.load_cached_statistics()
        return self._repository.calculate(filters)
