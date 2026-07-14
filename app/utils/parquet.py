"""Lectura segura de metadatos del snapshot Parquet."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, cast

import pyarrow.parquet as pq

_GENERATION_KEY = b"generation_id"


class _ParquetMetadata(Protocol):
    metadata: Mapping[bytes, bytes] | None
    num_rows: int


def parquet_generation(path: Path) -> str:
    """Obtiene el identificador de generación grabado en el footer Parquet."""

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
    """Lee el conteo del footer sin materializar columnas."""

    return int(_read_metadata(path).num_rows)


def _read_metadata(path: Path) -> _ParquetMetadata:
    try:
        return cast(_ParquetMetadata, pq.read_metadata(path))
    except Exception as exc:  # PyArrow expone varias excepciones según el daño del footer.
        raise ValueError("El Parquet no se puede leer") from exc
