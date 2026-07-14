"""Pruebas de integración del contrato POST de estadísticas."""

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


def _expected(*amounts: float) -> dict[str, float | int]:
    """Calcula con Python el resultado esperado para una consulta POST con datos."""
    values = list(amounts)
    return {
        "suma": sum(values),
        "conteo": len(values),
        "promedio": fmean(values),
        "minimo": min(values),
        "maximo": max(values),
        "mediana": median(values),
        "desviacion_estandar": pstdev(values),
    }


def _assert_statistics(response: TestResponse, expected: dict[str, float | int]) -> dict[str, Any]:
    """Valida el contrato de éxito y compara sus métricas con el resultado esperado."""
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert set(payload) == STATISTIC_FIELDS
    assert isinstance(payload["conteo"], int)
    assert not isinstance(payload["conteo"], bool)

    for field, expected_value in expected.items():
        actual = payload[field]
        if field == "conteo":
            assert actual == expected_value
        else:
            assert isinstance(actual, (int, float))
            assert not isinstance(actual, bool)
            assert math.isfinite(actual)
            assert actual == pytest.approx(expected_value)
    return payload


@pytest.mark.parametrize(
    ("query", "amounts"),
    [
        ({"consulta": "GENERO", "valor": " otro "}, (3000.5, 7000.5, 11000.5)),
        ({"consulta": "EDAD", "valor": 39}, (2000.0,)),
        ({"consulta": "CANAL", "valor": " wpr "}, (6000.0, 12000.0)),
        (
            {"consulta": "CODIGO_PRODUCTO", "valor": 1004},
            (10000.0, 11000.5, 12000.0),
        ),
        (
            {
                "consulta": "ID_PERSONA",
                "valor": "FCE50ED1-9E82-3DC7-B695-3934CDBCCA33",
            },
            (8000.0,),
        ),
        ({"consulta": "LOCAL", "valor": 104}, (4000.0, 8000.0, 12000.0)),
        ({"consulta": "FECHA_DESDE", "valor": "2026-12-01"}, (12000.0,)),
        ({"consulta": "FECHA_HASTA", "valor": "2026-01-15"}, (1000.5,)),
    ],
    ids=[
        "genero",
        "edad",
        "canal",
        "codigo-producto",
        "id-persona",
        "local",
        "fecha-desde",
        "fecha-hasta",
    ],
)
def test_post_accepts_one_query_for_every_supported_filter(
    client: FlaskClient,
    query: dict[str, object],
    amounts: tuple[float, ...],
) -> None:
    response = client.post(ENDPOINT, json={"consultas": [query]})

    _assert_statistics(response, _expected(*amounts))


def test_post_combines_multiple_queries_with_and(client: FlaskClient) -> None:
    response = client.post(
        ENDPOINT,
        json={
            "consultas": [
                {"consulta": "GENERO", "valor": "Otro"},
                {"consulta": "CANAL", "valor": "APR"},
                {"consulta": "CODIGO_PRODUCTO", "valor": "1004"},
                {"consulta": "LOCAL", "valor": "103"},
                {"consulta": "FECHA_DESDE", "valor": "2026-11-29T00:00:00"},
                {"consulta": "FECHA_HASTA", "valor": "2026-11-29T23:59:59"},
            ]
        },
    )

    _assert_statistics(response, _expected(11000.5))
