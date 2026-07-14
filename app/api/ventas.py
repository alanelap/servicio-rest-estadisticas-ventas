"""Endpoint contractual de estadísticas de ventas."""

from __future__ import annotations

from typing import Any, cast

from flask import current_app, request
from flask.views import MethodView
from flask_smorest import Blueprint
from werkzeug.exceptions import UnsupportedMediaType

from app.api.typing import typed_decorator
from app.domain.exceptions import ContractValidationError
from app.schemas.errors import ErrorSchema
from app.schemas.statistics import StatisticsSchema
from app.services.filter_service import FilterService
from app.services.statistics_service import StatisticsService

blp = Blueprint(
    "sales_statistics",
    __name__,
    url_prefix="/v1/estadisticas",
    description="Resumen estadístico de ventas sobre MONTO APLICADO.",
)

_GET_PARAMETERS = [
    {
        "in": "query",
        "name": "GENERO",
        "schema": {
            "type": "string",
            "enum": ["No especificado", "Masculino", "Femenino", "Otro"],
        },
        "description": "No distingue mayúsculas/minúsculas.",
    },
    {
        "in": "query",
        "name": "EDAD",
        "schema": {"type": "integer", "minimum": 0, "maximum": 120},
        "description": "Edad en la fecha de la transacción.",
    },
    {
        "in": "query",
        "name": "CANAL",
        "schema": {"type": "string", "enum": ["POS", "WEB", "APP", "CCT", "APR", "WPR"]},
    },
    {
        "in": "query",
        "name": "CODIGO_PRODUCTO",
        "schema": {"type": "integer", "minimum": 1},
        "description": "SKU del producto.",
    },
    {
        "in": "query",
        "name": "ID_PERSONA",
        "schema": {"type": "string", "format": "uuid"},
    },
    {
        "in": "query",
        "name": "LOCAL",
        "schema": {"type": "integer", "minimum": 1},
    },
    {
        "in": "query",
        "name": "FECHA_DESDE",
        "schema": {
            "oneOf": [
                {"type": "string", "format": "date"},
                {"type": "string", "format": "date-time"},
            ]
        },
        "description": "Fecha o fecha-hora ISO 8601, inclusiva.",
    },
    {
        "in": "query",
        "name": "FECHA_HASTA",
        "schema": {
            "oneOf": [
                {"type": "string", "format": "date"},
                {"type": "string", "format": "date-time"},
            ]
        },
        "description": "Inclusiva; una fecha sin hora abarca todo el día.",
    },
]

_POST_REQUEST_BODY = {
    "required": True,
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["consultas"],
                "properties": {
                    "consultas": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 8,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["consulta", "valor"],
                            "properties": {
                                "consulta": {
                                    "type": "string",
                                    "enum": [
                                        "GENERO",
                                        "EDAD",
                                        "CANAL",
                                        "CODIGO_PRODUCTO",
                                        "ID_PERSONA",
                                        "LOCAL",
                                        "FECHA_DESDE",
                                        "FECHA_HASTA",
                                    ],
                                },
                                "valor": {"oneOf": [{"type": "string"}, {"type": "integer"}]},
                            },
                        },
                    }
                },
            },
            "examples": {
                "valido": {
                    "value": {
                        "consultas": [
                            {"consulta": "GENERO", "valor": "Femenino"},
                            {"consulta": "CANAL", "valor": "POS"},
                        ]
                    }
                },
                "invalido": {"value": {"consultas": []}},
            },
        }
    },
}

_SUCCESS_EXAMPLE = {
    "suma": 1500.5,
    "conteo": 42,
    "promedio": 35.73,
    "minimo": 10.0,
    "maximo": 100.0,
    "mediana": 30.0,
    "desviacion_estandar": 25.4,
}

_VALIDATION_ERROR_EXAMPLE = {
    "detail": "El valor 'TIENDA' no es válido para CANAL",
    "instance": "/v1/estadisticas/ventas",
    "status": 400,
    "title": "Bad Request",
    "type": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/400",
    "timestamp": "2026-06-30T20:44:49.201437Z",
    "errorCode": "VF",
    "errorLabel": "Validación Fallida",
    "method": "GET",
}


@blp.route("/ventas")
class SalesStatisticsView(MethodView):
    """GET precomputado/dinámico y POST de filtros dinámicos."""

    @typed_decorator(
        blp.doc(
            tags=["ventas"],
            summary="Consultar estadísticas de ventas",
            description=(
                "Sin filtros devuelve la caché global. Con filtros calcula suma, conteo, "
                "promedio, mínimo, máximo, mediana y desviación estándar poblacional "
                "(ddof=0) sobre MONTO APLICADO. Todos los filtros se combinan con AND."
            ),
            parameters=_GET_PARAMETERS,
        )
    )
    @typed_decorator(blp.response(200, StatisticsSchema, example=_SUCCESS_EXAMPLE))
    @typed_decorator(
        blp.alt_response(
            400,
            schema=ErrorSchema,
            description="Validación fallida",
            example=_VALIDATION_ERROR_EXAMPLE,
        )
    )
    @typed_decorator(
        blp.alt_response(
            413, schema=ErrorSchema, description="Cuerpo de solicitud demasiado grande"
        )
    )
    @typed_decorator(blp.alt_response(500, schema=ErrorSchema, description="Error interno"))
    @typed_decorator(blp.alt_response(503, schema=ErrorSchema, description="Datos no preparados"))
    def get(self) -> dict[str, Any]:
        filter_service, statistics_service = _services()
        filters = filter_service.from_get(request.args)
        return statistics_service.calculate(filters).to_dict()

    @typed_decorator(
        blp.doc(
            tags=["ventas"],
            summary="Consultar con filtros en JSON",
            description=(
                "Requiere al menos una consulta, no admite filtros duplicados ni propiedades "
                "desconocidas y combina todos los filtros con AND."
            ),
            requestBody=_POST_REQUEST_BODY,
        )
    )
    @typed_decorator(blp.response(200, StatisticsSchema, example=_SUCCESS_EXAMPLE))
    @typed_decorator(
        blp.alt_response(
            400,
            schema=ErrorSchema,
            description="Validación fallida",
            example={**_VALIDATION_ERROR_EXAMPLE, "method": "POST"},
        )
    )
    @typed_decorator(
        blp.alt_response(415, schema=ErrorSchema, description="Tipo de medio no soportado")
    )
    @typed_decorator(
        blp.alt_response(
            413, schema=ErrorSchema, description="Cuerpo de solicitud demasiado grande"
        )
    )
    @typed_decorator(blp.alt_response(500, schema=ErrorSchema, description="Error interno"))
    @typed_decorator(blp.alt_response(503, schema=ErrorSchema, description="Datos no preparados"))
    def post(self) -> dict[str, Any]:
        filter_service, statistics_service = _services()
        raw_body = request.get_data(cache=True)
        if not raw_body:
            raise ContractValidationError("El cuerpo JSON es obligatorio")
        if not request.is_json:
            raise UnsupportedMediaType()
        payload = request.get_json(silent=False)
        filters = filter_service.from_post(payload)
        return statistics_service.calculate(filters).to_dict()


def _services() -> tuple[FilterService, StatisticsService]:
    return (
        cast(FilterService, current_app.extensions["filter_service"]),
        cast(StatisticsService, current_app.extensions["statistics_service"]),
    )
