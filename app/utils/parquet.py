"""Lectura defensiva del footer de los snapshots Parquet."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, cast

import pyarrow.parquet as pq

_GENERATION_KEY = b"generation_id"


class _ParquetMetadata(Protocol):
    """Vista mínima del objeto de metadatos que necesita la aplicación.

    Attributes:
        metadata: Pares de metadatos binarios almacenados en el footer.
        num_rows: Cantidad total de filas declarada por los grupos del archivo.
    """

    metadata: Mapping[bytes, bytes] | None
    num_rows: int


def parquet_generation(path: Path) -> str:
    """Obtiene el identificador de generación almacenado en el footer Parquet.

    Args:
        path: Ruta del snapshot Parquet.

    Returns:
        Identificador de generación UTF-8 no vacío.

    Raises:
        ValueError: Si el archivo es ilegible, falta la clave, su valor no es
            UTF-8 válido o está vacío.
    """
    metadata = _read_metadata(path)
    key_values = metadata.metadata or {}
    raw = key_values.get(_GENERATION_KEY)
    if raw is None:
        raise ValueError("El Parquet no declara generation_id")
    generation_id = raw.decode("utf-8")
    if not generation_id:
        raise ValueError("El generation_id del Parquet está vacío")
    return generation_id


def parquet_row_count(path: Path) -> int:
    """Obtiene el conteo de filas del footer sin materializar columnas.

    Args:
        path: Ruta del snapshot Parquet.

    Returns:
        Cantidad de filas declarada en sus metadatos.

    Raises:
        ValueError: Si PyArrow no puede leer los metadatos del archivo.
    """
    return int(_read_metadata(path).num_rows)


def _read_metadata(path: Path) -> _ParquetMetadata:
    """Adapta los errores variables de PyArrow a una excepción de contrato.

    Args:
        path: Ruta del archivo cuyos metadatos se leerán.

    Returns:
        Vista tipada de los metadatos Parquet requeridos.

    Raises:
        ValueError: Si el footer no existe, está dañado o no puede leerse.
    """
    try:
        return cast(_ParquetMetadata, pq.read_metadata(path))
    except Exception as exc:  # PyArrow expone varias excepciones según el daño del footer.
        raise ValueError("El Parquet no se puede leer") from exc
