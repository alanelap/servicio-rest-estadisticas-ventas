"""Pruebas unitarias de conversión y validación de filtros."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from werkzeug.datastructures import MultiDict

from app.domain.exceptions import ContractValidationError
from app.domain.models import SalesFilters
from app.services.filter_service import FilterService

_UUID = "3D8594A2-3D1E-3FFC-85ED-6A94F3BAAAA9"


def _from_post(name: str, value: object) -> SalesFilters:
    return FilterService().from_post({"consultas": [{"consulta": name, "valor": value}]})


def test_empty_get_builds_empty_filters() -> None:
    filters = FilterService().from_get(MultiDict())

    assert filters.is_empty
    assert filters.names == []


def test_get_normalizes_all_supported_scalar_filters() -> None:
    filters = FilterService().from_get(
        MultiDict(
            [
                ("GENERO", "  femenino "),
                ("EDAD", " 30 "),
                ("CANAL", " web "),
                ("CODIGO_PRODUCTO", "+1001"),
                ("ID_PERSONA", f" {_UUID} "),
                ("LOCAL", "101"),
            ]
        )
    )

    assert filters.genero == "Femenino"
    assert filters.edad == 30
    assert filters.canal == "WEB"
    assert filters.codigo_producto == 1001
    assert filters.id_persona == str(UUID(_UUID))
    assert filters.local == 101


def test_integer_filter_accepts_convertible_leading_zeroes_without_size_bypass() -> None:
    value = "+" + ("0" * 100) + "101"

    assert _from_post("LOCAL", value).local == 101


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("EDAD", True),
        ("EDAD", 30.0),
        ("EDAD", "30.0"),
        ("EDAD", "3e1"),
        ("EDAD", ""),
        ("CODIGO_PRODUCTO", False),
        ("CODIGO_PRODUCTO", 1001.5),
        ("CODIGO_PRODUCTO", "1001.5"),
        ("LOCAL", True),
        ("LOCAL", 101.0),
        ("LOCAL", "uno"),
    ],
)
def test_integer_filters_reject_booleans_decimals_and_non_integers(
    name: str, value: object
) -> None:
    with pytest.raises(ContractValidationError, match="entero válido"):
        _from_post(name, value)


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("EDAD", -1, "entre 0 y 120"),
        ("EDAD", 121, "entre 0 y 120"),
        ("CODIGO_PRODUCTO", 0, "mayor o igual a 1"),
        ("LOCAL", -5, "mayor o igual a 1"),
    ],
)
def test_integer_filters_enforce_ranges(name: str, value: object, message: str) -> None:
    with pytest.raises(ContractValidationError, match=message):
        _from_post(name, value)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("no especificado", "No especificado"),
        (" MASCULINO ", "Masculino"),
        ("fEmEnInO", "Femenino"),
        ("OTRO", "Otro"),
    ],
)
def test_gender_is_case_insensitive_and_trimmed(raw: str, expected: str) -> None:
    assert _from_post("GENERO", raw).genero == expected


@pytest.mark.parametrize("raw", [1, "desconocido"])
def test_invalid_gender_is_rejected(raw: object) -> None:
    with pytest.raises(ContractValidationError, match="GENERO"):
        _from_post("GENERO", raw)


@pytest.mark.parametrize("raw", ["pos", " WEB ", "App", "cct", "APR", "wpr"])
def test_all_channels_are_normalized(raw: str) -> None:
    assert _from_post("CANAL", raw).canal == raw.strip().upper()


@pytest.mark.parametrize("raw", [1, "TIENDA", "ONLINE"])
def test_invalid_channel_is_rejected(raw: object) -> None:
    with pytest.raises(ContractValidationError, match="CANAL"):
        _from_post("CANAL", raw)


def test_uuid_is_validated_and_canonicalized() -> None:
    filters = _from_post("ID_PERSONA", f" {_UUID} ")

    assert filters.id_persona == "3d8594a2-3d1e-3ffc-85ed-6a94f3baaaa9"


@pytest.mark.parametrize("raw", [123, "no-es-uuid", "3d8594a2-3d1e-3ffc"])
def test_invalid_uuid_is_rejected(raw: object) -> None:
    with pytest.raises(ContractValidationError, match="UUID"):
        _from_post("ID_PERSONA", raw)


@pytest.mark.parametrize("name", ["GENERO", "CANAL", "ID_PERSONA"])
def test_null_filter_value_is_rejected_structurally(name: str) -> None:
    with pytest.raises(ContractValidationError, match="no es válida"):
        _from_post(name, None)


def test_date_range_is_converted_to_utc_and_upper_day_is_inclusive() -> None:
    filters = FilterService().from_post(
        {
            "consultas": [
                {"consulta": "FECHA_DESDE", "valor": "2026-01-15"},
                {"consulta": "FECHA_HASTA", "valor": "2026-01-15"},
            ]
        }
    )

    assert filters.fecha_desde == datetime(2026, 1, 15, 4, tzinfo=UTC)
    assert filters.fecha_hasta == datetime(2026, 1, 16, 4, tzinfo=UTC)
    assert filters.fecha_hasta_exclusiva is True


def test_timestamp_range_accepts_equal_inclusive_boundaries() -> None:
    filters = FilterService().from_get(
        MultiDict(
            [
                ("FECHA_DESDE", "2026-01-15T09:00:00-03:00"),
                ("FECHA_HASTA", "2026-01-15T12:00:00Z"),
            ]
        )
    )

    expected = datetime(2026, 1, 15, 12, tzinfo=UTC)
    assert filters.fecha_desde == expected
    assert filters.fecha_hasta == expected
    assert filters.fecha_hasta_exclusiva is False


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("2026-03-02", "2026-03-01"),
        ("2026-03-02T01:00:00-03:00", "2026-03-01"),
        ("2026-03-02T00:00:01Z", "2026-03-02T00:00:00Z"),
    ],
)
def test_reversed_date_range_is_rejected(start: str, end: str) -> None:
    with pytest.raises(ContractValidationError, match="FECHA_DESDE"):
        FilterService().from_post(
            {
                "consultas": [
                    {"consulta": "FECHA_DESDE", "valor": start},
                    {"consulta": "FECHA_HASTA", "valor": end},
                ]
            }
        )


def test_unknown_and_repeated_get_filters_are_rejected() -> None:
    service = FilterService()

    with pytest.raises(ContractValidationError, match="no está permitido"):
        service.from_get(MultiDict([("genero", "Femenino")]))
    with pytest.raises(ContractValidationError, match="no puede repetirse"):
        service.from_get(MultiDict([("CANAL", "POS"), ("CANAL", "WEB")]))


def test_repeated_post_filter_is_rejected() -> None:
    with pytest.raises(ContractValidationError, match="duplicado"):
        FilterService().from_post(
            {
                "consultas": [
                    {"consulta": "LOCAL", "valor": 101},
                    {"consulta": "LOCAL", "valor": 102},
                ]
            }
        )
