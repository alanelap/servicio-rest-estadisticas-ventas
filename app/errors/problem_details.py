"""Construye el formato estable de errores que expone la API."""

from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

_ERROR_METADATA: dict[int, tuple[str, str]] = {
    400: ("VF", "Validación Fallida"),
    404: ("RN", "Recurso No Encontrado"),
    405: ("MN", "Método No Permitido"),
    413: ("TC", "Contenido Demasiado Grande"),
    415: ("TM", "Tipo de Medio No Soportado"),
    500: ("IE", "Error Interno"),
    503: ("ND", "Servicio No Disponible"),
}


def build_problem(
    *,
    detail: str,
    status: int,
    instance: str,
    method: str,
    error_code: str | None = None,
    error_label: str | None = None,
) -> dict[str, Any]:
    """Construye exactamente los nueve campos exigidos por el contrato.

    Args:
        detail: Descripción pública y segura del problema.
        status: Código HTTP reconocido que identifica la categoría del error.
        instance: Ruta de la solicitud que produjo el problema.
        method: Método HTTP de la solicitud.
        error_code: Código de negocio opcional; si se omite se deriva de ``status``.
        error_label: Etiqueta opcional; si se omite se deriva de ``status``.

    Returns:
        Un diccionario serializable como JSON con metadatos de tipo, tiempo e
        instancia, además del código y la etiqueta de negocio.

    Raises:
        ValueError: Si ``status`` no corresponde a un estado definido por HTTP.
    """
    default_code, default_label = _ERROR_METADATA.get(status, ("IE", "Error Interno"))
    return {
        "detail": detail,
        "instance": instance,
        "status": status,
        "title": HTTPStatus(status).phrase,
        "type": f"https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/{status}",
        "timestamp": datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "errorCode": error_code or default_code,
        "errorLabel": error_label or default_label,
        "method": method,
    }
