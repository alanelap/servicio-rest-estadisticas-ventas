"""Conversión determinista de fechas del contrato a UTC."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone

from app.domain.exceptions import ContractValidationError

# El enunciado oficial define explícitamente UTC-4. Se usa un offset fijo para
# que el resultado no dependa de las reglas de horario de verano del sistema.
BUSINESS_TIMEZONE = timezone(timedelta(hours=-4), name="UTC-04:00")
_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True, slots=True)
class ParsedDateBoundary:
    """Instante UTC y semántica del límite superior."""

    value: datetime
    exclusive: bool = False


def parse_iso_boundary(raw: object, *, upper: bool, filter_name: str) -> ParsedDateBoundary:
    """Interpreta fecha/fecha-hora ISO; los valores sin offset usan UTC-4 fijo.

    Una fecha usada como límite superior representa el día completo y se convierte
    a la medianoche siguiente exclusiva, equivalente a un límite inclusivo del día.
    """

    if not isinstance(raw, str) or not raw.strip():
        raise ContractValidationError(
            f"El valor de {filter_name} debe ser una fecha ISO 8601 válida"
        )
    value = raw.strip()
    try:
        if _DATE_ONLY.fullmatch(value):
            parsed_date = date.fromisoformat(value)
            if upper:
                parsed_date += timedelta(days=1)
            local = datetime.combine(parsed_date, time.min, BUSINESS_TIMEZONE)
            return ParsedDateBoundary(local.astimezone(UTC), exclusive=upper)

        normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=BUSINESS_TIMEZONE)
        return ParsedDateBoundary(parsed.astimezone(UTC), exclusive=False)
    except (ValueError, OverflowError) as exc:
        raise ContractValidationError(
            f"El valor '{value}' no es una fecha ISO 8601 válida para {filter_name}"
        ) from exc
