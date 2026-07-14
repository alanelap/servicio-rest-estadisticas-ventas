"""Pruebas de normalización temporal del contrato."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.exceptions import ContractValidationError
from app.utils.dates import parse_iso_boundary


def test_date_only_is_midnight_in_fixed_utc_minus_four_converted_to_utc() -> None:
    boundary = parse_iso_boundary("2026-01-15", upper=False, filter_name="FECHA_DESDE")

    assert boundary.value == datetime(2026, 1, 15, 4, tzinfo=UTC)
    assert boundary.exclusive is False


def test_upper_date_includes_whole_local_day() -> None:
    boundary = parse_iso_boundary("2026-07-13", upper=True, filter_name="FECHA_HASTA")

    assert boundary.value == datetime(2026, 7, 14, 4, tzinfo=UTC)
    assert boundary.exclusive is True


def test_naive_datetime_uses_business_timezone() -> None:
    boundary = parse_iso_boundary("2026-01-15T09:30:00", upper=False, filter_name="FECHA_DESDE")

    assert boundary.value == datetime(2026, 1, 15, 13, 30, tzinfo=UTC)
    assert boundary.exclusive is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-01-15T09:30:00Z", datetime(2026, 1, 15, 9, 30, tzinfo=UTC)),
        ("2026-01-15T09:30:00-05:00", datetime(2026, 1, 15, 14, 30, tzinfo=UTC)),
        ("2026-01-15T09:30:00+03:00", datetime(2026, 1, 15, 6, 30, tzinfo=UTC)),
    ],
)
def test_datetime_with_offset_represents_same_instant(raw: str, expected: datetime) -> None:
    boundary = parse_iso_boundary(raw, upper=True, filter_name="FECHA_HASTA")

    assert boundary.value == expected
    assert boundary.exclusive is False


@pytest.mark.parametrize("raw", [None, 20260115, "", "no-es-fecha", "2026-02-30"])
def test_invalid_iso_boundary_is_rejected(raw: object) -> None:
    with pytest.raises(ContractValidationError, match="fecha ISO 8601 válida"):
        parse_iso_boundary(raw, upper=False, filter_name="FECHA_DESDE")
