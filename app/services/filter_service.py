"""Validación estricta y conversión de filtros públicos."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from marshmallow import ValidationError as MarshmallowValidationError
from werkzeug.datastructures import MultiDict

from app.domain.enums import Channel, FilterName, Gender
from app.domain.exceptions import ContractValidationError
from app.domain.models import SalesFilters
from app.schemas.filters import PostFiltersSchema
from app.utils.dates import ParsedDateBoundary, parse_iso_boundary

_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")
_INT64_MAX = 2**63 - 1
_GENDERS_BY_CASEFOLD = {item.value.casefold(): item.value for item in Gender}


class FilterService:
    """Transforma entradas HTTP en ``SalesFilters`` seguros."""

    def __init__(self) -> None:
        self._post_schema = PostFiltersSchema()

    def from_get(self, query: MultiDict[str, str]) -> SalesFilters:
        """Valida query params, incluidos desconocidos y repetidos."""

        pairs: list[tuple[object, object]] = []
        for name, values in query.lists():
            if name not in FilterName:
                raise ContractValidationError(f"El filtro '{name}' no está permitido")
            if len(values) != 1:
                raise ContractValidationError(f"El filtro '{name}' no puede repetirse")
            pairs.append((name, values[0]))
        return self._from_pairs(pairs)

    def from_post(self, payload: object) -> SalesFilters:
        """Valida la estructura exacta de POST y convierte sus consultas."""

        if not isinstance(payload, Mapping):
            raise ContractValidationError("El cuerpo JSON debe ser un objeto")
        if "consultas" not in payload:
            raise ContractValidationError("El campo 'consultas' es obligatorio")
        consultas = payload["consultas"]
        if consultas is None:
            raise ContractValidationError("El campo 'consultas' no puede ser null")
        if not isinstance(consultas, list):
            raise ContractValidationError("El campo 'consultas' debe ser un arreglo")
        if not consultas:
            raise ContractValidationError("El campo 'consultas' no puede estar vacío")

        try:
            loaded = self._post_schema.load(dict(payload))
        except MarshmallowValidationError as exc:
            raise ContractValidationError(
                "La estructura del cuerpo JSON no es válida: "
                + _spanish_schema_errors(exc.messages)
            ) from exc

        loaded_queries = loaded["consultas"]
        pairs = [(item["consulta"], item["valor"]) for item in loaded_queries]
        return self._from_pairs(pairs)

    def _from_pairs(self, pairs: list[tuple[object, object]]) -> SalesFilters:
        values: dict[str, Any] = {}
        seen: set[FilterName] = set()
        upper_boundary: ParsedDateBoundary | None = None

        for raw_name, raw_value in pairs:
            if not isinstance(raw_name, str) or raw_name not in FilterName:
                raise ContractValidationError(
                    f"La consulta '{raw_name}' no es uno de los filtros permitidos"
                )
            name = FilterName(raw_name)
            if name in seen:
                raise ContractValidationError(f"El filtro '{name.value}' está duplicado")
            seen.add(name)

            if name is FilterName.GENERO:
                values["genero"] = self._parse_gender(raw_value)
            elif name is FilterName.EDAD:
                values["edad"] = self._parse_integer(
                    raw_value, label="la edad", minimum=0, maximum=120
                )
            elif name is FilterName.CANAL:
                values["canal"] = self._parse_channel(raw_value)
            elif name is FilterName.CODIGO_PRODUCTO:
                values["codigo_producto"] = self._parse_integer(
                    raw_value, label="el código de producto", minimum=1
                )
            elif name is FilterName.ID_PERSONA:
                values["id_persona"] = self._parse_uuid(raw_value)
            elif name is FilterName.LOCAL:
                values["local"] = self._parse_integer(raw_value, label="el ID de tienda", minimum=1)
            elif name is FilterName.FECHA_DESDE:
                values["fecha_desde"] = parse_iso_boundary(
                    raw_value, upper=False, filter_name=name.value
                ).value
            elif name is FilterName.FECHA_HASTA:
                upper_boundary = parse_iso_boundary(raw_value, upper=True, filter_name=name.value)
                values["fecha_hasta"] = upper_boundary.value
                values["fecha_hasta_exclusiva"] = upper_boundary.exclusive

        self._validate_date_range(values, upper_boundary)
        return SalesFilters(**values)

    @staticmethod
    def _parse_integer(raw: object, *, label: str, minimum: int, maximum: int | None = None) -> int:
        if isinstance(raw, bool) or not isinstance(raw, (str, int)):
            raise ContractValidationError(
                f"El valor '{raw}' no es un número entero válido para {label}"
            )
        text = str(raw).strip()
        if not _INTEGER_PATTERN.fullmatch(text):
            raise ContractValidationError(
                f"El valor '{raw}' no es un número entero válido para {label}"
            )
        significant_digits = text.lstrip("+-").lstrip("0") or "0"
        if len(significant_digits) > 19:
            raise ContractValidationError(
                f"El valor '{raw}' no es un número entero válido para {label}"
            )
        try:
            value = int(text)
        except ValueError as exc:
            raise ContractValidationError(
                f"El valor '{raw}' no es un número entero válido para {label}"
            ) from exc
        if value > _INT64_MAX:
            raise ContractValidationError(f"El valor de {label} excede el rango permitido")
        if value < minimum or (maximum is not None and value > maximum):
            range_text = f"entre {minimum} y {maximum}" if maximum else f"mayor o igual a {minimum}"
            raise ContractValidationError(f"El valor de {label} debe ser {range_text}")
        return value

    @staticmethod
    def _parse_gender(raw: object) -> str:
        if not isinstance(raw, str):
            raise ContractValidationError("El valor de GENERO debe ser texto")
        normalized = _GENDERS_BY_CASEFOLD.get(raw.strip().casefold())
        if normalized is None:
            allowed = ", ".join(item.value for item in Gender)
            raise ContractValidationError(
                f"El valor '{raw}' no es válido para GENERO; use: {allowed}"
            )
        return normalized

    @staticmethod
    def _parse_channel(raw: object) -> str:
        if not isinstance(raw, str):
            raise ContractValidationError("El valor de CANAL debe ser texto")
        normalized = raw.strip().upper()
        if normalized not in Channel:
            allowed = ", ".join(item.value for item in Channel)
            raise ContractValidationError(
                f"El valor '{raw}' no es válido para CANAL; use: {allowed}"
            )
        return normalized

    @staticmethod
    def _parse_uuid(raw: object) -> str:
        if not isinstance(raw, str):
            raise ContractValidationError("El valor de ID_PERSONA debe ser un UUID")
        try:
            return str(UUID(raw.strip()))
        except (ValueError, AttributeError) as exc:
            raise ContractValidationError(
                f"El valor '{raw}' no es un UUID válido para ID_PERSONA"
            ) from exc

    @staticmethod
    def _validate_date_range(
        values: dict[str, Any], upper_boundary: ParsedDateBoundary | None
    ) -> None:
        start = values.get("fecha_desde")
        end = values.get("fecha_hasta")
        if start is None or end is None:
            return
        invalid = start >= end if upper_boundary and upper_boundary.exclusive else start > end
        if invalid:
            raise ContractValidationError("FECHA_DESDE no puede ser posterior a FECHA_HASTA")


def _spanish_schema_errors(messages: object, path: str = "cuerpo") -> str:
    """Aplana errores de Marshmallow sin exponer sus mensajes internos en inglés."""

    if isinstance(messages, Mapping):
        parts = [_spanish_schema_errors(value, f"{path}.{key}") for key, value in messages.items()]
        return "; ".join(parts)
    if isinstance(messages, list):
        if messages and all(isinstance(item, str) for item in messages):
            return f"{path}: valor o propiedad no permitida"
        parts = [
            _spanish_schema_errors(value, f"{path}[{index}]")
            for index, value in enumerate(messages)
        ]
        return "; ".join(parts)
    return f"{path}: valor o propiedad no permitida"
