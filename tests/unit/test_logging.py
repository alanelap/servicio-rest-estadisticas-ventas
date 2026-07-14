"""Pruebas de redacción defensiva del logging estructurado."""

from __future__ import annotations

import json
import logging
import sys

from app.observability.logging import JsonFormatter

_UUID = "11111111-1111-4111-8111-111111111111"
_RUN = "12.345.678-K"


def test_formatter_redacts_personal_values_from_messages() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=f"valores {_UUID} y {_RUN}",
        args=(),
        exc_info=None,
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "valores [UUID_REDACTADO] y [RUN_REDACTADO]"


def test_formatter_redacts_personal_values_from_exception_trace() -> None:
    try:
        raise RuntimeError(f"falló el cliente {_UUID}")
    except RuntimeError:
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="error controlado",
            args=(),
            exc_info=sys.exc_info(),
        )

    serialized = JsonFormatter().format(record)

    assert _UUID not in serialized
    assert "[UUID_REDACTADO]" in serialized
