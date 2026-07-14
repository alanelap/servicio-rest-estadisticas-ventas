"""Validaciones HTTP y contrato uniforme de errores."""

from __future__ import annotations

from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.exceptions import UnprocessableEntity
from werkzeug.test import TestResponse

from app import create_app

ENDPOINT = "/v1/estadisticas/ventas"
PROBLEM_FIELDS = {
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
ERROR_METADATA = {
    400: ("VF", "Validación Fallida"),
    404: ("RN", "Recurso No Encontrado"),
    405: ("MN", "Método No Permitido"),
    413: ("TC", "Contenido Demasiado Grande"),
    415: ("TM", "Tipo de Medio No Soportado"),
    500: ("IE", "Error Interno"),
}


def _assert_problem(
    response: TestResponse,
    *,
    status: int,
    method: str,
    instance: str = ENDPOINT,
    detail_contains: str | None = None,
) -> dict[str, Any]:
    """Valida todos los campos del error contractual y devuelve su cuerpo."""
    assert response.status_code == status
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert set(payload) == PROBLEM_FIELDS
    assert isinstance(payload["detail"], str)
    assert payload["detail"].strip()
    if detail_contains is not None:
        assert detail_contains.casefold() in payload["detail"].casefold()
    assert payload["instance"] == instance
    assert payload["status"] == status
    assert payload["title"] == HTTPStatus(status).phrase
    assert payload["type"] == (
        f"https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/{status}"
    )
    timestamp = payload["timestamp"]
    assert isinstance(timestamp, str)
    assert timestamp.endswith("Z")
    parsed_timestamp = datetime.fromisoformat(timestamp.removesuffix("Z") + "+00:00")
    assert parsed_timestamp.utcoffset() == timedelta(0)
    assert (payload["errorCode"], payload["errorLabel"]) == ERROR_METADATA[status]
    assert payload["method"] == method
    if status == 400:
        assert response.status_code != 422
    return payload


@pytest.mark.parametrize(
    ("query_string", "detail_fragment"),
    [
        ({"DESCONOCIDO": "x"}, "no está permitido"),
        ([("LOCAL", "101"), ("LOCAL", "102")], "no puede repetirse"),
        ({"EDAD": "31.5"}, "no es un número entero válido"),
        ({"EDAD": "-1"}, "entre 0 y 120"),
        ({"EDAD": "121"}, "entre 0 y 120"),
        ({"CODIGO_PRODUCTO": "0"}, "mayor o igual a 1"),
        ({"LOCAL": "qwerqwer"}, "no es un número entero válido"),
        ({"CANAL": "TIENDA"}, "no es válido para CANAL"),
        ({"GENERO": "Desconocido"}, "no es válido para GENERO"),
        ({"ID_PERSONA": "uuid-invalido"}, "no es un UUID válido"),
        ({"FECHA_DESDE": "13/07/2026"}, "no es una fecha ISO 8601 válida"),
        (
            {"FECHA_DESDE": "2026-07-02", "FECHA_HASTA": "2026-07-01"},
            "no puede ser posterior",
        ),
    ],
    ids=[
        "filtro-desconocido",
        "filtro-repetido",
        "edad-decimal",
        "edad-negativa",
        "edad-sobre-rango",
        "producto-no-positivo",
        "local-no-entero",
        "canal-invalido",
        "genero-invalido",
        "uuid-invalido",
        "fecha-invalida",
        "rango-invertido",
    ],
)
def test_get_validation_failures_are_400_problem_details(
    client: FlaskClient,
    query_string: dict[str, str] | list[tuple[str, str]],
    detail_fragment: str,
) -> None:
    response = client.get(ENDPOINT, query_string=query_string)

    _assert_problem(
        response,
        status=400,
        method="GET",
        detail_contains=detail_fragment,
    )


def test_post_rejects_absent_body_as_400(client: FlaskClient) -> None:
    response = client.post(ENDPOINT)

    _assert_problem(
        response,
        status=400,
        method="POST",
        detail_contains="cuerpo JSON es obligatorio",
    )


def test_post_rejects_unsupported_content_type_as_415(client: FlaskClient) -> None:
    response = client.post(
        ENDPOINT,
        data='{"consultas": [{"consulta": "LOCAL", "valor": 101}]}',
        content_type="text/plain",
    )

    _assert_problem(
        response,
        status=415,
        method="POST",
        detail_contains="Content-Type application/json",
    )


def test_post_rejects_malformed_json_as_400(client: FlaskClient) -> None:
    response = client.post(
        ENDPOINT,
        data='{"consultas": [',
        content_type="application/json",
    )

    _assert_problem(response, status=400, method="POST", detail_contains="no es válida")


def test_post_rejects_json_null_as_non_object(client: FlaskClient) -> None:
    response = client.post(ENDPOINT, data="null", content_type="application/json")

    _assert_problem(
        response,
        status=400,
        method="POST",
        detail_contains="debe ser un objeto",
    )


@pytest.mark.parametrize(
    ("payload", "detail_fragment"),
    [
        ([], "debe ser un objeto"),
        ({}, "'consultas' es obligatorio"),
        ({"consultas": None}, "no puede ser null"),
        ({"consultas": "LOCAL"}, "debe ser un arreglo"),
        ({"consultas": []}, "no puede estar vacío"),
        ({"consultas": [{}]}, "estructura del cuerpo JSON no es válida"),
        (
            {"consultas": [{"valor": 101}]},
            "estructura del cuerpo JSON no es válida",
        ),
        (
            {"consultas": [{"consulta": "LOCAL"}]},
            "estructura del cuerpo JSON no es válida",
        ),
        (
            {"consultas": [{"consulta": "LOCAL", "valor": None}]},
            "estructura del cuerpo JSON no es válida",
        ),
        (
            {"consultas": [{"consulta": "NO_EXISTE", "valor": "x"}]},
            "estructura del cuerpo JSON no es válida",
        ),
        (
            {
                "consultas": [{"consulta": "LOCAL", "valor": 101, "extra": True}],
            },
            "estructura del cuerpo JSON no es válida",
        ),
        (
            {
                "consultas": [{"consulta": "LOCAL", "valor": 101}],
                "extra": True,
            },
            "estructura del cuerpo JSON no es válida",
        ),
        (
            {
                "consultas": [
                    {"consulta": "LOCAL", "valor": 101},
                    {"consulta": "LOCAL", "valor": 102},
                ]
            },
            "está duplicado",
        ),
        (
            {"consultas": [{"consulta": "EDAD", "valor": True}]},
            "no es un número entero válido",
        ),
        (
            {"consultas": [{"consulta": "EDAD", "valor": 31.5}]},
            "no es un número entero válido",
        ),
        (
            {"consultas": [{"consulta": "EDAD", "valor": 121}]},
            "entre 0 y 120",
        ),
        (
            {"consultas": [{"consulta": "CODIGO_PRODUCTO", "valor": 0}]},
            "mayor o igual a 1",
        ),
        (
            {"consultas": [{"consulta": "LOCAL", "valor": "qwerqwer"}]},
            "no es un número entero válido",
        ),
        (
            {"consultas": [{"consulta": "GENERO", "valor": "Desconocido"}]},
            "no es válido para GENERO",
        ),
        (
            {"consultas": [{"consulta": "CANAL", "valor": "TIENDA"}]},
            "no es válido para CANAL",
        ),
        (
            {"consultas": [{"consulta": "ID_PERSONA", "valor": "no-uuid"}]},
            "no es un UUID válido",
        ),
        (
            {"consultas": [{"consulta": "FECHA_DESDE", "valor": "ayer"}]},
            "no es una fecha ISO 8601 válida",
        ),
        (
            {
                "consultas": [
                    {"consulta": "FECHA_DESDE", "valor": "2026-12-02"},
                    {"consulta": "FECHA_HASTA", "valor": "2026-12-01"},
                ]
            },
            "no puede ser posterior",
        ),
    ],
    ids=[
        "body-no-objeto",
        "consultas-ausente",
        "consultas-null",
        "consultas-no-arreglo",
        "consultas-vacio",
        "elemento-vacio",
        "elemento-sin-consulta",
        "elemento-sin-valor",
        "valor-null",
        "consulta-desconocida",
        "propiedad-elemento-desconocida",
        "propiedad-raiz-desconocida",
        "filtro-duplicado",
        "booleano-no-entero",
        "decimal-no-entero",
        "edad-sobre-rango",
        "producto-no-positivo",
        "local-no-entero",
        "genero-invalido",
        "canal-invalido",
        "uuid-invalido",
        "fecha-invalida",
        "rango-invertido",
    ],
)
def test_post_contract_validation_failures_are_400_not_422(
    client: FlaskClient,
    payload: object,
    detail_fragment: str,
) -> None:
    response = client.post(ENDPOINT, json=payload)

    _assert_problem(
        response,
        status=400,
        method="POST",
        detail_contains=detail_fragment,
    )


def test_unknown_route_uses_404_problem_contract(client: FlaskClient) -> None:
    response = client.get("/v1/recurso-inexistente")

    _assert_problem(
        response,
        status=404,
        method="GET",
        instance="/v1/recurso-inexistente",
        detail_contains="no existe",
    )


def test_unsupported_method_uses_405_problem_contract(client: FlaskClient) -> None:
    response = client.put(ENDPOINT, json={"consultas": []})

    _assert_problem(
        response,
        status=405,
        method="PUT",
        detail_contains="no está permitido",
    )


def test_oversized_body_uses_413_problem_contract(app: Flask, client: FlaskClient) -> None:
    limit = int(app.config["MAX_REQUEST_BODY_BYTES"])
    response = client.post(
        ENDPOINT,
        data=b"x" * (limit + 1),
        content_type="application/json",
    )

    _assert_problem(
        response,
        status=413,
        method="POST",
        detail_contains="tamaño máximo",
    )


def test_body_limit_is_enforced_even_when_endpoint_does_not_read_body(
    app: Flask, client: FlaskClient, caplog: pytest.LogCaptureFixture
) -> None:
    limit = int(app.config["MAX_REQUEST_BODY_BYTES"])
    response = client.get("/health", data=b"x" * (limit + 1))

    _assert_problem(
        response,
        status=413,
        method="GET",
        instance="/health",
        detail_contains="tamaño máximo",
    )
    request_logs = [
        record
        for record in caplog.records
        if record.name == "app.requests" and getattr(record, "status", None) == 413
    ]
    assert request_logs[-1].request_id == response.headers["X-Request-ID"]


def test_transfer_encoded_body_is_rejected_when_length_cannot_be_prevalidated(
    client: FlaskClient,
) -> None:
    response = client.get(
        "/health",
        data=b"contenido",
        headers={"Transfer-Encoding": "chunked"},
    )

    _assert_problem(
        response,
        status=413,
        method="GET",
        instance="/health",
        detail_contains="tamaño máximo",
    )


@pytest.mark.parametrize("filter_name", ["LOCAL", "CODIGO_PRODUCTO"])
def test_very_large_integers_are_rejected_as_400_not_500(
    client: FlaskClient, filter_name: str
) -> None:
    response = client.get(ENDPOINT, query_string={filter_name: "9" * 4301})

    _assert_problem(response, status=400, method="GET", detail_contains="entero válido")


def test_structural_post_errors_do_not_expose_english_library_messages(
    client: FlaskClient,
) -> None:
    response = client.post(
        ENDPOINT,
        json={"consultas": [{"consulta": "LOCAL", "extra": True}]},
    )

    payload = _assert_problem(
        response,
        status=400,
        method="POST",
        detail_contains="estructura del cuerpo JSON no es válida",
    )
    detail = payload["detail"]
    assert "Unknown field" not in detail
    assert "Missing data" not in detail
    assert "Field may not be null" not in detail


def test_filter_values_never_appear_in_application_logs(
    client: FlaskClient, capsys: pytest.CaptureFixture[str]
) -> None:
    sensitive_uuid = "11111111-1111-4111-8111-111111111111"
    capsys.readouterr()

    response = client.get(
        ENDPOINT,
        query_string={"ID_PERSONA": sensitive_uuid},
        headers={"X-Request-ID": sensitive_uuid},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"].startswith("req_")
    captured = capsys.readouterr()
    assert sensitive_uuid not in captured.out
    assert sensitive_uuid not in captured.err


def test_production_forces_debug_off_even_if_flask_debug_is_set(
    test_paths: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FLASK_DEBUG", "1")
    production_app = create_app(
        {
            "TESTING": False,
            "APP_ENV": "production",
            "DATASET_PATH": str(test_paths["dataset"]),
            "PROCESSED_DATA_PATH": str(test_paths["processed"]),
            "SUMMARY_CACHE_PATH": str(test_paths["summary"]),
            "METADATA_PATH": str(test_paths["metadata"]),
            "QUALITY_REPORT_PATH": str(test_paths["quality"]),
            "INGEST_ALLOWED_ROOT": str(test_paths["root"]),
        }
    )

    assert production_app.debug is False
    assert production_app.config["DEBUG"] is False


def test_unexpected_exception_uses_safe_500_problem_contract(
    app: Flask,
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statistics_service = app.extensions["statistics_service"]

    def fail_safely(_filters: object) -> None:
        raise RuntimeError("dato-interno-que-no-debe-filtrarse")

    monkeypatch.setattr(statistics_service, "calculate", fail_safely)
    response = client.get(ENDPOINT)

    payload = _assert_problem(
        response,
        status=500,
        method="GET",
        detail_contains="error interno",
    )
    assert "dato-interno-que-no-debe-filtrarse" not in str(payload)


def test_framework_422_is_normalized_to_400_problem_contract(app: Flask) -> None:
    with app.test_request_context(ENDPOINT, method="POST"):
        response = app.make_response(app.handle_user_exception(UnprocessableEntity()))

    _assert_problem(
        response,
        status=400,
        method="POST",
        detail_contains="no es válida",
    )
