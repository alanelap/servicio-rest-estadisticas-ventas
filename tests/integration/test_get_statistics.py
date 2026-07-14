"""Pruebas de integración del contrato GET de estadísticas."""

from __future__ import annotations

import math
from statistics import fmean, median, pstdev
from typing import Any

import pytest
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

ENDPOINT = "/v1/estadisticas/ventas"
STATISTIC_FIELDS = {
    "suma",
    "conteo",
    "promedio",
    "minimo",
    "maximo",
    "mediana",
    "desviacion_estandar",
}


def _expected(*amounts: float) -> dict[str, float | int | None]:
    """Calcula con Python el resultado esperado para los montos del escenario."""
    values = list(amounts)
    if not values:
        return {
            "suma": 0.0,
            "conteo": 0,
            "promedio": None,
            "minimo": None,
            "maximo": None,
            "mediana": None,
            "desviacion_estandar": None,
        }
    return {
        "suma": sum(values),
        "conteo": len(values),
        "promedio": fmean(values),
        "minimo": min(values),
        "maximo": max(values),
        "mediana": median(values),
        "desviacion_estandar": pstdev(values),
    }


def _assert_statistics(
    response: TestResponse, expected: dict[str, float | int | None]
) -> dict[str, Any]:
    """Valida el contrato JSON y compara cada estadística con el valor esperado."""
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert set(payload) == STATISTIC_FIELDS
    assert isinstance(payload["conteo"], int)
    assert not isinstance(payload["conteo"], bool)

    for field, expected_value in expected.items():
        actual = payload[field]
        if expected_value is None:
            assert actual is None
        elif field == "conteo":
            assert actual == expected_value
        else:
            assert isinstance(actual, (int, float))
            assert not isinstance(actual, bool)
            assert math.isfinite(actual)
            assert actual == pytest.approx(expected_value)
    return payload


def test_get_without_filters_returns_exact_global_statistics(client: FlaskClient) -> None:
    response = client.get(ENDPOINT)

    _assert_statistics(
        response,
        _expected(
            1000.5,
            2000.0,
            3000.5,
            4000.0,
            5000.5,
            6000.0,
            7000.5,
            8000.0,
            9000.5,
            10000.0,
            11000.5,
            12000.0,
        ),
    )


@pytest.mark.parametrize(
    ("query", "amounts"),
    [
        ({"GENERO": " femenino "}, (2000.0, 6000.0, 10000.0)),
        ({"EDAD": "30"}, (1000.5,)),
        ({"CANAL": " app "}, (3000.5, 9000.5)),
        ({"CODIGO_PRODUCTO": "1001"}, (1000.5, 2000.0, 3000.5)),
        (
            {"ID_PERSONA": "AFA7E3AE-A514-37E8-9E8E-05C79692F9F2"},
            (6000.0,),
        ),
        ({"LOCAL": "101"}, (1000.5, 5000.5, 9000.5)),
    ],
    ids=["genero", "edad", "canal", "codigo-producto", "id-persona", "local"],
)
def test_get_applies_each_supported_scalar_filter(
    client: FlaskClient,
    query: dict[str, str],
    amounts: tuple[float, ...],
) -> None:
    response = client.get(ENDPOINT, query_string=query)

    _assert_statistics(response, _expected(*amounts))


def test_get_applies_inclusive_date_range_in_santiago_timezone(client: FlaskClient) -> None:
    response = client.get(
        ENDPOINT,
        query_string={"FECHA_DESDE": "2026-03-01", "FECHA_HASTA": "2026-04-10"},
    )

    _assert_statistics(response, _expected(3000.5, 4000.0, 5000.5))


def test_get_combines_multiple_filters_with_and(client: FlaskClient) -> None:
    response = client.get(
        ENDPOINT,
        query_string={"GENERO": "Masculino", "CANAL": "POS", "LOCAL": "101"},
    )

    _assert_statistics(response, _expected(1000.5))


def test_get_without_matches_returns_null_metrics_and_valid_json(client: FlaskClient) -> None:
    response = client.get(
        ENDPOINT,
        query_string={"GENERO": "Femenino", "CANAL": "POS"},
    )

    _assert_statistics(response, _expected())
    encoded = response.get_data(as_text=True)
    assert "NaN" not in encoded
    assert "Infinity" not in encoded
