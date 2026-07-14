"""Traduce excepciones de aplicación y HTTP al contrato JSON uniforme."""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask, Response, g, jsonify, request
from werkzeug.exceptions import HTTPException

from app.domain.exceptions import ApplicationError
from app.errors.problem_details import build_problem

_LOGGER = logging.getLogger(__name__)
_HTTP_DETAILS = {
    400: "La solicitud no es válida",
    404: "El recurso solicitado no existe",
    405: "El método HTTP no está permitido para este recurso",
    413: "El cuerpo de la solicitud supera el tamaño máximo permitido",
    415: "El cuerpo debe enviarse con Content-Type application/json",
    500: "Ocurrió un error interno al procesar la solicitud",
    503: "El servicio aún no está preparado",
}


def register_error_handlers(app: Flask) -> None:
    """Registra los manejadores de errores esperados y la barrera de seguridad.

    Args:
        app: Instancia Flask en la que se instalarán los manejadores.

    Los errores inesperados se registran con su traza para diagnóstico, pero la
    respuesta pública utiliza un mensaje genérico para no revelar información de
    implementación.
    """

    @app.errorhandler(ApplicationError)
    def handle_application_error(error: ApplicationError) -> tuple[Response, int]:
        """Convierte un error controlado sin perder sus metadatos públicos."""
        return _response(
            detail=error.detail,
            status=error.status_code,
            error_code=error.error_code,
            error_label=error.error_label,
        )

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException) -> tuple[Response, int]:
        """Normaliza una excepción HTTP producida por Flask o Werkzeug."""
        original_status = error.code or 500
        # Flask-Smorest usa 422 para validación; el contrato oficial exige 400.
        status = 400 if original_status == 422 else original_status
        detail = _HTTP_DETAILS.get(status, "La solicitud no pudo ser procesada")
        return _response(detail=detail, status=status)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> tuple[Response, int]:
        """Registra un fallo imprevisto y devuelve una respuesta sin datos sensibles."""
        _LOGGER.exception(
            "Error no controlado",
            extra={
                "event": "unhandled_exception",
                "request_id": getattr(g, "request_id", "unknown"),
            },
        )
        return _response(detail=_HTTP_DETAILS[500], status=500)


def _response(
    *,
    detail: str,
    status: int,
    error_code: str | None = None,
    error_label: str | None = None,
) -> tuple[Response, int]:
    """Crea una respuesta Flask a partir de un problema normalizado.

    Args:
        detail: Explicación segura para el consumidor de la API.
        status: Código de estado HTTP de la respuesta.
        error_code: Código de negocio opcional que reemplaza el valor por defecto.
        error_label: Etiqueta opcional que reemplaza el valor por defecto.

    Returns:
        La respuesta JSON y el código HTTP que Flask debe enviar.
    """
    payload: dict[str, Any] = build_problem(
        detail=detail,
        status=status,
        instance=request.path,
        method=request.method,
        error_code=error_code,
        error_label=error_label,
    )
    return jsonify(payload), status
