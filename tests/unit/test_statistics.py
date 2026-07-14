"""Pruebas de las siete estadísticas contractuales."""

from __future__ import annotations

import json
import math
from statistics import pstdev

import polars as pl
import pytest

from app.domain.exceptions import StatisticsCalculationError
from app.services.statistics_service import statistics_from_lazyframe


def _calculate(values: list[float | None]):
    frame = pl.DataFrame({"monto_aplicado": values}, schema={"monto_aplicado": pl.Float64}).lazy()
    return statistics_from_lazyframe(frame)


def test_all_statistics_with_odd_count() -> None:
    values = [10.0, 20.0, 40.0]

    result = _calculate(values)

    assert result.suma == pytest.approx(70.0)
    assert result.conteo == 3
    assert isinstance(result.conteo, int)
    assert result.promedio == pytest.approx(70.0 / 3.0)
    assert result.minimo == pytest.approx(10.0)
    assert result.maximo == pytest.approx(40.0)
    assert result.mediana == pytest.approx(20.0)
    assert result.desviacion_estandar == pytest.approx(pstdev(values))


def test_median_with_even_count_averages_middle_values() -> None:
    result = _calculate([10.0, 20.0, 30.0, 80.0])

    assert result.mediana == pytest.approx(25.0)


def test_population_standard_deviation_uses_ddof_zero() -> None:
    values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]

    result = _calculate(values)

    assert result.desviacion_estandar == pytest.approx(2.0)
    assert result.desviacion_estandar == pytest.approx(pstdev(values))


def test_single_value_has_zero_population_deviation() -> None:
    result = _calculate([1250.75])

    assert result.to_dict() == {
        "suma": 1250.75,
        "conteo": 1,
        "promedio": 1250.75,
        "minimo": 1250.75,
        "maximo": 1250.75,
        "mediana": 1250.75,
        "desviacion_estandar": 0.0,
    }


def test_empty_dataset_uses_defined_null_contract() -> None:
    result = _calculate([])

    assert result.to_dict() == {
        "suma": 0.0,
        "conteo": 0,
        "promedio": None,
        "minimo": None,
        "maximo": None,
        "mediana": None,
        "desviacion_estandar": None,
    }


def test_decimal_values_are_not_truncated() -> None:
    result = _calculate([0.1, 0.2, 1.25, 2.75])

    assert result.suma == pytest.approx(4.3)
    assert result.promedio == pytest.approx(1.075)
    assert result.minimo == pytest.approx(0.1)
    assert result.maximo == pytest.approx(2.75)
    assert result.mediana == pytest.approx(0.725)


def test_non_finite_and_null_values_are_excluded_and_json_remains_valid() -> None:
    result = _calculate([1.5, None, math.nan, math.inf, -math.inf, 2.5])
    payload = result.to_dict()

    assert result.conteo == 2
    assert result.suma == pytest.approx(4.0)
    assert all(
        value is None or isinstance(value, int) or math.isfinite(value)
        for value in payload.values()
    )
    assert "NaN" not in json.dumps(payload, allow_nan=False)
    assert "Infinity" not in json.dumps(payload, allow_nan=False)


def test_only_non_finite_values_produce_empty_contract() -> None:
    result = _calculate([math.nan, math.inf, -math.inf, None])

    assert result.conteo == 0
    assert result.suma == 0.0
    assert result.promedio is None
    json.dumps(result.to_dict(), allow_nan=False)


def test_finite_inputs_whose_sum_overflows_raise_controlled_error() -> None:
    with pytest.raises(StatisticsCalculationError, match="estadísticas finitas"):
        _calculate([1e308, 1e308])
