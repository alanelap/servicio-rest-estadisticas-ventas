"""Pruebas de liveness, readiness y documentación interactiva."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any

import polars as pl
import pytest
from flask import Flask
from flask.testing import FlaskClient
from openapi_spec_validator import validate
from werkzeug.test import TestResponse

STATISTIC_FIELDS = {
    "suma",
    "conteo",
    "promedio",
    "minimo",
    "maximo",
    "mediana",
    "desviacion_estandar",
}
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
FILTER_NAMES = {
    "GENERO",
    "EDAD",
    "CANAL",
    "CODIGO_PRODUCTO",
    "ID_PERSONA",
    "LOCAL",
    "FECHA_DESDE",
    "FECHA_HASTA",
}


def _assert_unavailable_problem(response: TestResponse) -> dict[str, Any]:
    """Comprueba el Problem Details contractual usado cuando el snapshot no está listo."""
    assert response.status_code == 503
    assert response.mimetype == "application/json"
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert set(payload) == PROBLEM_FIELDS
    assert payload["detail"] == "Los datos estadísticos aún no están preparados"
    assert payload["instance"] == "/ready"
    assert payload["status"] == 503
    assert payload["title"] == HTTPStatus(503).phrase
    assert payload["type"] == (
        "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/503"
    )
    timestamp = payload["timestamp"]
    assert isinstance(timestamp, str)
    assert timestamp.endswith("Z")
    parsed_timestamp = datetime.fromisoformat(timestamp.removesuffix("Z") + "+00:00")
    assert parsed_timestamp.utcoffset() == timedelta(0)
    assert payload["errorCode"] == "ND"
    assert payload["errorLabel"] == "Servicio No Disponible"
    assert payload["method"] == "GET"
    return payload


def test_health_only_reports_process_liveness(client: FlaskClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert response.get_json() == {"status": "ok"}


def test_ready_reports_prepared_artifacts(client: FlaskClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert response.get_json() == {"status": "ready"}


def test_ready_uses_standard_503_when_artifacts_are_unavailable(
    app: Flask,
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = app.extensions["sales_repository"]
    monkeypatch.setattr(repository, "readiness", lambda: (False, "summary_missing"))

    response = client.get("/ready")

    _assert_unavailable_problem(response)


def test_wrong_parquet_schema_makes_ready_and_global_query_unavailable(
    app: Flask, client: FlaskClient, test_paths: dict[str, Any]
) -> None:
    metadata = json.loads(test_paths["metadata"].read_text(encoding="utf-8"))
    pl.DataFrame({"foo": [1]}).write_parquet(
        test_paths["processed"], metadata={"generation_id": metadata["generation_id"]}
    )

    assert client.get("/ready").status_code == 503
    assert client.get("/v1/estadisticas/ventas").status_code == 503
    assert client.get("/v1/estadisticas/ventas?LOCAL=101").status_code == 503


def test_missing_generation_id_is_rejected_by_global_query(
    client: FlaskClient, test_paths: dict[str, Any]
) -> None:
    for key in ("summary", "metadata", "quality"):
        path = test_paths[key]
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload.pop("generation_id")
        path.write_text(json.dumps(payload), encoding="utf-8")

    assert client.get("/ready").status_code == 503
    assert client.get("/v1/estadisticas/ventas").status_code == 503


def test_huge_json_number_marks_snapshot_unavailable_and_reingestable(
    app: Flask, client: FlaskClient, test_paths: dict[str, Any]
) -> None:
    path = test_paths["summary"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["statistics"]["suma"] = 10**400
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert client.get("/ready").status_code == 503
    assert client.get("/v1/estadisticas/ventas").status_code == 503
    assert client.get("/v1/estadisticas/ventas?LOCAL=101").status_code == 503
    assert app.extensions["ingestion_service"].needs_ingestion() is True


def test_swagger_ui_opens_and_targets_the_openapi_document(client: FlaskClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    html = response.get_data(as_text=True)
    assert "swagger-ui-container" in html
    assert 'url: "/openapi.json"' in html


def test_openapi_documents_the_complete_public_contract(client: FlaskClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    document = response.get_json()
    assert isinstance(document, dict)
    validate(document)
    assert document["openapi"] == "3.0.3"
    assert document["info"]["title"]
    assert document["info"]["version"]
    assert {"/v1/estadisticas/ventas", "/health", "/ready"} <= set(document["paths"])

    sales_path = document["paths"]["/v1/estadisticas/ventas"]
    assert {"get", "post"} <= set(sales_path)
    get_operation = sales_path["get"]
    post_operation = sales_path["post"]
    assert {parameter["name"] for parameter in get_operation["parameters"]} == FILTER_NAMES
    assert all(parameter["in"] == "query" for parameter in get_operation["parameters"])
    assert {"200", "400", "413", "500", "503"} <= set(get_operation["responses"])
    assert {"200", "400", "413", "415", "500", "503"} <= set(post_operation["responses"])

    request_body = post_operation["requestBody"]
    assert request_body["required"] is True
    media = request_body["content"]["application/json"]
    assert {"valido", "invalido"} <= set(media["examples"])
    body_schema = media["schema"]
    assert body_schema["additionalProperties"] is False
    assert body_schema["required"] == ["consultas"]
    queries_schema = body_schema["properties"]["consultas"]
    assert queries_schema["type"] == "array"
    assert queries_schema["minItems"] == 1
    item_schema = queries_schema["items"]
    assert item_schema["additionalProperties"] is False
    assert set(item_schema["required"]) == {"consulta", "valor"}
    assert set(item_schema["properties"]["consulta"]["enum"]) == FILTER_NAMES

    schemas = document["components"]["schemas"]
    statistics_schema = schemas["Statistics"]
    assert statistics_schema["additionalProperties"] is False
    assert set(statistics_schema["properties"]) == STATISTIC_FIELDS
    assert set(statistics_schema["required"]) == STATISTIC_FIELDS
    error_schema = schemas["Error"]
    assert error_schema["additionalProperties"] is False
    assert set(error_schema["properties"]) == PROBLEM_FIELDS
    assert set(error_schema["required"]) == PROBLEM_FIELDS

    documented_text = " ".join(
        [
            document["info"]["description"],
            get_operation["description"],
            post_operation["description"],
        ]
    )
    assert "MONTO APLICADO" in documented_text
    assert "poblacional" in documented_text
    assert "null" in documented_text
