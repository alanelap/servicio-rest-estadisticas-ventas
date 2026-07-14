"""Conversión determinista de límites temporales del contrato a UTC.

Las fechas sin zona horaria se interpretan con el offset comercial fijo UTC-4
definido por el enunciado, sin depender de la zona ni del horario de verano del
sistema operativo.
"""

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
    """Límite temporal normalizado para construir filtros de dominio.

    Attributes:
        value: Instante consciente de zona horaria expresado en UTC.
        exclusive: Indica que ``value`` no forma parte del intervalo. Se usa
            para representar una fecha superior inclusiva como la medianoche
            siguiente exclusiva.
    """

    value: datetime
    exclusive: bool = False


def parse_iso_boundary(raw: object, *, upper: bool, filter_name: str) -> ParsedDateBoundary:
    """Interpreta una fecha o fecha-hora ISO 8601 como límite en UTC.

    Una fecha usada como límite superior representa el día completo y se convierte
    a la medianoche siguiente exclusiva, equivalente a un límite inclusivo del día.

    Args:
        raw: Valor recibido desde el contrato HTTP; debe ser texto no vacío.
        upper: Indica si el valor corresponde al límite superior del intervalo.
        filter_name: Nombre público del filtro, utilizado en mensajes de error.

    Returns:
        Límite normalizado a UTC junto con su semántica inclusiva o exclusiva.

    Raises:
        ContractValidationError: Si el valor no es texto ISO 8601 válido o la
            operación de fecha excede el rango admitido.
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
