"""Validación y normalización de los filtros expuestos por la API.

Este módulo concentra el contrato de entrada de los endpoints GET y POST. Su
responsabilidad es rechazar parámetros ambiguos o desconocidos y producir un
objeto de dominio :class:`SalesFilters` con valores ya tipados y normalizados.
"""

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
    """Transforma entradas HTTP no confiables en filtros de dominio seguros.

    La validación se mantiene fuera de las rutas para que ambos métodos HTTP
    compartan las mismas reglas de tipos, rangos y duplicidad.
    """

    def __init__(self) -> None:
        """Inicializa el esquema utilizado por el cuerpo del endpoint POST."""
        self._post_schema = PostFiltersSchema()

    def from_get(self, query: MultiDict[str, str]) -> SalesFilters:
        """Convierte los parámetros de consulta de una petición GET.

        Args:
            query: Colección de parámetros HTTP que conserva valores repetidos.

        Returns:
            Filtros normalizados y listos para consultar el repositorio.

        Raises:
            ContractValidationError: Si hay un filtro desconocido, repetido o
                con un valor que incumple el contrato.
        """
        pairs: list[tuple[object, object]] = []
        # La validación ocurre antes de colapsar el MultiDict para no ocultar
        # parámetros repetidos enviados por el cliente.
        for name, values in query.lists():
            if name not in FilterName:
                raise ContractValidationError(f"El filtro '{name}' no está permitido")
            if len(values) != 1:
                raise ContractValidationError(f"El filtro '{name}' no puede repetirse")
            pairs.append((name, values[0]))
        return self._from_pairs(pairs)

    def from_post(self, payload: object) -> SalesFilters:
        """Convierte el cuerpo JSON de una petición POST.

        Args:
            payload: Valor JSON decodificado recibido desde Flask.

        Returns:
            Filtros normalizados y listos para consultar el repositorio.

        Raises:
            ContractValidationError: Si el cuerpo no es un objeto, no contiene
                consultas o infringe la estructura o las reglas de un filtro.
        """
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
        """Valida pares nombre-valor y construye el modelo común de filtros.

        Args:
            pairs: Pares provenientes de GET o de las consultas validadas de POST.

        Returns:
            Instancia de :class:`SalesFilters` con los tipos del dominio.

        Raises:
            ContractValidationError: Si un nombre está duplicado o un valor no
                puede convertirse de acuerdo con su filtro.
        """
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
                # Una fecha sin hora representa el día completo y se convierte
                # internamente en el inicio exclusivo del día siguiente.
                values["fecha_hasta_exclusiva"] = upper_boundary.exclusive

        self._validate_date_range(values, upper_boundary)
        return SalesFilters(**values)

    @staticmethod
    def _parse_integer(raw: object, *, label: str, minimum: int, maximum: int | None = None) -> int:
        """Convierte un entero decimal aplicando límites del contrato y de Int64.

        Args:
            raw: Valor recibido desde JSON o desde la cadena de consulta.
            label: Nombre legible usado en los mensajes de error.
            minimum: Menor valor aceptado, inclusive.
            maximum: Mayor valor aceptado, inclusive; sin límite funcional si es
                ``None``.

        Returns:
            Entero validado.

        Raises:
            ContractValidationError: Si el valor no representa un entero o queda
                fuera de los límites permitidos.
        """
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
        """Normaliza un género sin distinguir mayúsculas ni espacios laterales.

        Args:
            raw: Valor que se validará contra :class:`Gender`.

        Returns:
            Valor canónico del género.

        Raises:
            ContractValidationError: Si el valor no es texto o no está permitido.
        """
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
        """Normaliza y valida un canal de venta.

        Args:
            raw: Valor que se validará contra :class:`Channel`.

        Returns:
            Canal canónico en mayúsculas.

        Raises:
            ContractValidationError: Si el valor no es texto o no está permitido.
        """
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
        """Valida y serializa un identificador de persona como UUID canónico.

        Args:
            raw: Identificador recibido del cliente.

        Returns:
            UUID en su representación textual canónica.

        Raises:
            ContractValidationError: Si el valor no es texto o no representa un UUID.
        """
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
        """Comprueba la coherencia cronológica cuando existen ambos extremos.

        Args:
            values: Filtros convertidos hasta el momento.
            upper_boundary: Metadatos del límite superior, incluida su inclusividad.

        Raises:
            ContractValidationError: Si el inicio queda después del final, o lo
                iguala cuando el límite superior es exclusivo.
        """
        start = values.get("fecha_desde")
        end = values.get("fecha_hasta")
        if start is None or end is None:
            return
        invalid = start >= end if upper_boundary and upper_boundary.exclusive else start > end
        if invalid:
            raise ContractValidationError("FECHA_DESDE no puede ser posterior a FECHA_HASTA")


def _spanish_schema_errors(messages: object, path: str = "cuerpo") -> str:
    """Aplana errores de Marshmallow sin exponer mensajes internos en inglés.

    Args:
        messages: Árbol de errores producido por Marshmallow.
        path: Ruta legible acumulada durante el recorrido recursivo.

    Returns:
        Descripción plana y estable de las propiedades inválidas.
    """
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
