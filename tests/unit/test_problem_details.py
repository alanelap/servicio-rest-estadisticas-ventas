"""Pruebas de la fábrica única y del contrato HTTP de errores."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from flask.testing import FlaskClient

from app.errors.problem_details import build_problem

_PROBLEM_KEYS = {
    "detail",
    "instance",
    "status",
    "title",
    "type",
    "timestamp",
    "errorCode",
    "errorLabel",
    "method",
}


def _assert_utc_timestamp(raw: str) -> None:
    assert raw.endswith("Z")
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    assert parsed.tzinfo == UTC


@pytest.mark.parametrize(
    ("status", "title", "code", "label"),
    [
        (400, "Bad Request", "VF", "Validación Fallida"),
        (404, "Not Found", "RN", "Recurso No Encontrado"),
        (405, "Method Not Allowed", "MN", "Método No Permitido"),
        (415, "Unsupported Media Type", "TM", "Tipo de Medio No Soportado"),
        (500, "Internal Server Error", "IE", "Error Interno"),
        (503, "Service Unavailable", "ND", "Servicio No Disponible"),
    ],
)
def test_problem_factory_uses_status_metadata(
    status: int, title: str, code: str, label: str
) -> None:
    problem = build_problem(
        detail="Detalle seguro", status=status, instance="/recurso", method="GET"
    )

    assert set(problem) == _PROBLEM_KEYS
    assert problem["detail"] == "Detalle seguro"
    assert problem["instance"] == "/recurso"
    assert problem["status"] == status
    assert problem["title"] == title
    assert problem["type"].endswith(f"/Status/{status}")
    assert problem["errorCode"] == code
    assert problem["errorLabel"] == label
    assert problem["method"] == "GET"
    _assert_utc_timestamp(problem["timestamp"])


def test_problem_factory_accepts_explicit_internal_metadata() -> None:
    problem = build_problem(
        detail="Fallo controlado",
        status=500,
        instance="/v1/estadisticas/ventas",
        method="POST",
        error_code="XX",
        error_label="Error de prueba",
    )

    assert problem["errorCode"] == "XX"
    assert problem["errorLabel"] == "Error de prueba"


def test_validation_error_response_has_exact_problem_contract(client: FlaskClient) -> None:
    response = client.get("/v1/estadisticas/ventas?LOCAL=no-es-entero")

    assert response.status_code == 400
    assert response.content_type == "application/json"
    problem = response.get_json()
    assert set(problem) == _PROBLEM_KEYS
    assert "número entero válido" in problem["detail"]
    assert problem["instance"] == "/v1/estadisticas/ventas"
    assert problem["status"] == 400
    assert problem["title"] == "Bad Request"
    assert problem["type"].endswith("/Status/400")
    assert problem["errorCode"] == "VF"
    assert problem["errorLabel"] == "Validación Fallida"
    assert problem["method"] == "GET"
    _assert_utc_timestamp(problem["timestamp"])


def test_framework_404_uses_same_problem_contract(client: FlaskClient) -> None:
    response = client.get("/ruta-inexistente")

    assert response.status_code == 404
    assert response.content_type == "application/json"
    problem = response.get_json()
    assert set(problem) == _PROBLEM_KEYS
    assert problem["instance"] == "/ruta-inexistente"
    assert problem["status"] == 404
    assert problem["errorCode"] == "RN"
    assert problem["errorLabel"] == "Recurso No Encontrado"
    assert problem["method"] == "GET"
    _assert_utc_timestamp(problem["timestamp"])
