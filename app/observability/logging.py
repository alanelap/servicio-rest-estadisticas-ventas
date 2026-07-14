"""Logging JSON, correlación HTTP y reducción de exposición accidental.

Solo se serializa una lista explícita de atributos adicionales. Como defensa en
profundidad, se redactan UUID canónicos con guiones y RUN escritos con puntos;
este filtrado de patrones no sustituye evitar datos personales desde el origen.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from flask import Flask, Response, g, request
from werkzeug.exceptions import RequestEntityTooLarge

_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_UUID_VALUE = re.compile(r"(?i)\b[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\b")
_RUN_VALUE = re.compile(r"\b\d{1,3}(?:\.\d{3}){2}-[\dkK]\b")
_EXTRA_FIELDS = {
    "event",
    "request_id",
    "method",
    "path",
    "status",
    "duration_ms",
    "filter_names",
    "result_count",
    "valid_rows",
    "discarded_rows",
}


class JsonFormatter(logging.Formatter):
    """Produce eventos JSON con un conjunto explícitamente permitido de atributos."""

    def format(self, record: logging.LogRecord) -> str:
        """Convierte un registro de logging en una línea JSON redactada.

        Args:
            record: Registro estándar que contiene el mensaje y atributos extra.

        Returns:
            Documento JSON compacto con timestamp UTC, nivel, logger, mensaje y
            los campos adicionales permitidos presentes en ``record``.
        """
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact_personal_values(record.getMessage()),
        }
        for key in _EXTRA_FIELDS:
            if hasattr(record, key):
                extra_value = getattr(record, key)
                payload[key] = (
                    _redact_personal_values(extra_value)
                    if isinstance(extra_value, str)
                    else extra_value
                )
        if record.exc_info:
            payload["exception"] = _redact_personal_values(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


def _redact_personal_values(value: str) -> str:
    """Sustituye UUID canónicos y RUN con puntos por marcadores fijos.

    Args:
        value: Texto que podría contener identificadores personales.

    Returns:
        Texto con las coincidencias cubiertas por ``_UUID_VALUE`` y
        ``_RUN_VALUE`` redactadas. Otros formatos permanecen sin cambios.
    """
    redacted = _UUID_VALUE.sub("[UUID_REDACTADO]", value)
    return _RUN_VALUE.sub("[RUN_REDACTADO]", redacted)


def _new_request_id() -> str:
    """Genera un identificador interno de correlación no aportado por el cliente.

    Returns:
        Identificador con prefijo ``req_`` y 32 dígitos hexadecimales aleatorios.
    """
    return f"req_{uuid4().hex}"


def configure_logging(app: Flask) -> None:
    """Configura logging estructurado y desactiva el logger HTTP de Werkzeug.

    Args:
        app: Aplicación cuya clave ``LOG_LEVEL`` determina el nivel raíz.

    Note:
        La función reemplaza los handlers del logger raíz del proceso. Debe
        invocarse durante la inicialización, antes de atender solicitudes.

    Raises:
        ValueError: Si ``LOG_LEVEL`` no corresponde a un nivel reconocido por
            el módulo estándar :mod:`logging`.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(str(app.config["LOG_LEVEL"]).upper())
    # Werkzeug incluye la query string completa en su access log. La aplicación
    # emite su propio evento seguro usando solo request.path y nombres de filtros.
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.handlers.clear()
    werkzeug_logger.disabled = True


def register_request_hooks(app: Flask) -> None:
    """Registra correlación, límite temprano, métricas y cabeceras defensivas.

    Args:
        app: Aplicación Flask sobre la que se instalan los hooks de solicitud.

    Los identificadores entregados por clientes se reutilizan si satisfacen la
    lista de caracteres y no coinciden con los formatos de UUID o RUN cubiertos
    por los patrones de redacción; en cualquier otro caso se genera uno interno.
    """

    @app.before_request
    def start_request() -> None:
        """Inicializa el contexto y rechaza cuerpos evidentemente grandes.

        Raises:
            RequestEntityTooLarge: Si existe transferencia codificada o el
                tamaño declarado excede ``MAX_CONTENT_LENGTH``.
        """
        supplied = request.headers.get("X-Request-ID", "")
        supplied_is_safe = bool(_SAFE_REQUEST_ID.fullmatch(supplied)) and not (
            _UUID_VALUE.search(supplied) or _RUN_VALUE.search(supplied)
        )
        g.request_id = supplied if supplied_is_safe else _new_request_id()
        g.request_started = time.perf_counter()
        content_length = request.content_length
        maximum = int(app.config["MAX_CONTENT_LENGTH"])
        transfer_encoded = bool(request.headers.get("Transfer-Encoding"))
        if transfer_encoded or (content_length is not None and content_length > maximum):
            raise RequestEntityTooLarge()

    @app.after_request
    def finish_request(response: Response) -> Response:
        """Agrega cabeceras seguras y registra la finalización de la solicitud.

        Args:
            response: Respuesta construida por la vista o el manejador de error.

        Returns:
            La misma respuesta enriquecida con correlación, políticas del
            navegador y, para endpoints de negocio, prohibición de caché.
        """
        response.headers["X-Request-ID"] = getattr(g, "request_id", _new_request_id())
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        if request.path.startswith("/v1/"):
            response.headers["Cache-Control"] = "no-store"
        logging.getLogger("app.requests").info(
            "Solicitud completada",
            extra={
                "event": "request_completed",
                "request_id": getattr(g, "request_id", "unknown"),
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": round(
                    (time.perf_counter() - getattr(g, "request_started", time.perf_counter()))
                    * 1000,
                    3,
                ),
            },
        )
        return response
