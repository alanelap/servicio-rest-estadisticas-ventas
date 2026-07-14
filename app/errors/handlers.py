"""Manejadores uniformes para excepciones de dominio y HTTP."""

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
    """Registra todos los códigos controlados y una barrera para fallos inesperados."""

    @app.errorhandler(ApplicationError)
    def handle_application_error(error: ApplicationError) -> tuple[Response, int]:
        return _response(
            detail=error.detail,
            status=error.status_code,
            error_code=error.error_code,
            error_label=error.error_label,
        )

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException) -> tuple[Response, int]:
        original_status = error.code or 500
        status = 400 if original_status == 422 else original_status
        detail = _HTTP_DETAILS.get(status, "La solicitud no pudo ser procesada")
        return _response(detail=detail, status=status)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> tuple[Response, int]:
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
    payload: dict[str, Any] = build_problem(
        detail=detail,
        status=status,
        instance=request.path,
        method=request.method,
        error_code=error_code,
        error_label=error_label,
    )
    return jsonify(payload), status
