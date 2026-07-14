"""Validación integral de una generación de artefactos analíticos.

El snapshot se acepta solo cuando Parquet, metadatos, resumen y reporte de
calidad pertenecen a la misma generación y satisfacen el esquema y los conteos
esperados. Centralizar estas invariantes evita criterios distintos entre el
endpoint de preparación y las consultas estadísticas.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import polars as pl

from app.domain.models import StatisticsResult
from app.domain.sales_schema import ANALYTIC_COLUMNS, ANALYTIC_SCHEMA
from app.utils.hashing import read_json_object
from app.utils.parquet import parquet_generation, parquet_row_count

_QUALITY_REASONS = {
    "fecha_invalida",
    "canal_invalido",
    "sku_invalido",
    "producto_invalido",
    "unidades_invalidas",
    "descuento_invalido",
    "monto_invalido",
    "boleta_invalida",
    "local_invalido",
    "uuid_invalido",
    "fecha_nacimiento_invalida",
    "genero_invalido",
    "edad_invalida",
}


@dataclass(frozen=True, slots=True)
class SnapshotState:
    """Estado validado cuyos campos no pueden reasignarse.

    La dataclass es ``frozen``, pero los diccionarios contenidos siguen siendo
    mutables; el contrato no ofrece inmutabilidad profunda.

    Attributes:
        generation_id: UUID canónico compartido por los cuatro artefactos.
        metadata: Manifiesto de origen, esquema y publicación.
        summary: Documento que contiene las estadísticas precomputadas.
        quality: Reporte agregado de filas válidas, descartadas y sus motivos.
        statistics: Estadísticas convertidas al modelo de dominio.
    """

    generation_id: str
    metadata: dict[str, Any]
    summary: dict[str, Any]
    quality: dict[str, Any]
    statistics: StatisticsResult


def validate_snapshot(
    *,
    processed_path: Path,
    summary_path: Path,
    metadata_path: Path,
    quality_report_path: Path,
    schema_version: int,
    stat_target_column: str,
) -> SnapshotState:
    """Valida que todos los artefactos formen un snapshot coherente.

    La validación cubre presencia, UUID de generación, versión de esquema,
    columnas y tipos físicos, conteos cruzados, motivos de descarte, timestamps
    y el contrato numérico del resumen.

    Args:
        processed_path: Ruta del snapshot Parquet.
        summary_path: Ruta de las estadísticas precomputadas en JSON.
        metadata_path: Ruta del manifiesto de la generación en JSON.
        quality_report_path: Ruta del reporte de calidad en JSON.
        schema_version: Versión exacta de esquema esperada.
        stat_target_column: Nombre contractual de la columna estadística.

    Returns:
        Estado con referencias no reasignables a los documentos y estadísticas
        ya validados; los diccionarios contenidos conservan su mutabilidad.

    Raises:
        ValueError: Si falta un artefacto o cualquier invariante de generación,
            esquema, conteo, calidad o estadística no se cumple.
        OSError: Si un documento JSON no puede abrirse o leerse.
        polars.exceptions.PolarsError: Si Polars no puede inspeccionar el
            esquema Parquet.
    """
    for path in (processed_path, summary_path, metadata_path, quality_report_path):
        if not path.is_file():
            raise ValueError(f"Falta el artefacto {path.name}")

    metadata = read_json_object(metadata_path)
    summary = read_json_object(summary_path)
    quality = read_json_object(quality_report_path)
    generation_id = _generation_id(metadata.get("generation_id"))
    if _generation_id(summary.get("generation_id")) != generation_id:
        raise ValueError("El resumen pertenece a otra generación")
    if _generation_id(quality.get("generation_id")) != generation_id:
        raise ValueError("El reporte de calidad pertenece a otra generación")
    if parquet_generation(processed_path) != generation_id:
        raise ValueError("El Parquet pertenece a otra generación")

    if metadata.get("schema_version") != schema_version:
        raise ValueError("La versión de esquema no coincide")
    if metadata.get("stat_target_column") != stat_target_column:
        raise ValueError("La columna estadística no coincide")
    if metadata.get("analytic_columns") != list(ANALYTIC_COLUMNS):
        raise ValueError("Las columnas analíticas declaradas no coinciden")

    parquet_schema = pl.scan_parquet(processed_path).collect_schema()
    if parquet_schema != ANALYTIC_SCHEMA:
        raise ValueError("El esquema físico del Parquet no coincide")

    valid_rows = _nonnegative_integer(metadata.get("valid_rows"), "filas válidas")
    discarded_rows = _nonnegative_integer(metadata.get("discarded_rows"), "filas descartadas")
    if parquet_row_count(processed_path) != valid_rows:
        raise ValueError("El conteo del Parquet no coincide")
    if _nonnegative_integer(quality.get("valid_rows"), "calidad válidas") != valid_rows:
        raise ValueError("El conteo de calidad no coincide")
    if _nonnegative_integer(quality.get("discarded_rows"), "calidad descartadas") != discarded_rows:
        raise ValueError("El conteo descartado de calidad no coincide")
    total_rows = _nonnegative_integer(quality.get("total_rows"), "calidad total")
    if total_rows != valid_rows + discarded_rows:
        raise ValueError("El total del reporte de calidad no coincide")
    reasons = quality.get("invalid_reason_counts")
    if not isinstance(reasons, dict) or set(reasons) != _QUALITY_REASONS:
        raise ValueError("Los motivos del reporte de calidad no coinciden")
    for name, value in reasons.items():
        if _nonnegative_integer(value, name) > total_rows:
            raise ValueError("Un motivo de calidad excede el total de filas")
    if not isinstance(quality.get("policy"), str) or not quality["policy"]:
        raise ValueError("La política del reporte de calidad es inválida")

    processed_at = metadata.get("processed_at")
    if not isinstance(processed_at, str) or not processed_at:
        raise ValueError("El timestamp de metadatos es inválido")
    if summary.get("processed_at") != processed_at or quality.get("processed_at") != processed_at:
        raise ValueError("Los timestamps de publicación no coinciden")

    statistics = validate_statistics_payload(summary.get("statistics"))
    if statistics.conteo != valid_rows:
        raise ValueError("El conteo estadístico no coincide con el Parquet")
    return SnapshotState(generation_id, metadata, summary, quality, statistics)


def validate_statistics_payload(payload: object) -> StatisticsResult:
    """Convierte un resumen JSON que respete exactamente el contrato numérico.

    Args:
        payload: Valor deserializado del campo ``statistics``.

    Returns:
        Modelo de dominio con números finitos. Para un conjunto vacío devuelve
        suma y conteo cero, y las demás métricas en ``None``.

    Raises:
        ValueError: Si faltan o sobran campos, los tipos son inválidos, algún
            número no es finito o la semántica del conjunto vacío no coincide.
    """
    if not isinstance(payload, dict):
        raise ValueError("El resumen estadístico no es un objeto")
    expected = {
        "suma",
        "conteo",
        "promedio",
        "minimo",
        "maximo",
        "mediana",
        "desviacion_estandar",
    }
    if set(payload) != expected:
        raise ValueError("El resumen estadístico no tiene los campos exactos")
    count = _nonnegative_integer(payload["conteo"], "conteo estadístico")
    total = _finite_float(payload["suma"], "suma")
    optional_names = (
        "promedio",
        "minimo",
        "maximo",
        "mediana",
        "desviacion_estandar",
    )
    if count == 0:
        if total != 0.0 or any(payload[name] is not None for name in optional_names):
            raise ValueError("El resumen vacío no respeta el contrato")
        return StatisticsResult.empty()
    if any(payload[name] is None for name in optional_names):
        raise ValueError("Una estadística no vacía contiene null")
    return StatisticsResult(
        suma=total,
        conteo=count,
        promedio=_finite_float(payload["promedio"], "promedio"),
        minimo=_finite_float(payload["minimo"], "mínimo"),
        maximo=_finite_float(payload["maximo"], "máximo"),
        mediana=_finite_float(payload["mediana"], "mediana"),
        desviacion_estandar=_finite_float(payload["desviacion_estandar"], "desviación estándar"),
    )


def _generation_id(value: object) -> str:
    """Exige un UUID textual no vacío y en su representación canónica.

    Args:
        value: Identificador deserializado desde un artefacto JSON.

    Returns:
        El mismo identificador validado.

    Raises:
        ValueError: Si no es texto, está vacío, no es un UUID o no está
            canonizado.
    """
    if not isinstance(value, str) or not value:
        raise ValueError("Falta generation_id")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ValueError("generation_id no es un UUID") from exc
    if str(parsed) != value:
        raise ValueError("generation_id no está canonizado")
    return value


def _nonnegative_integer(value: object, label: str) -> int:
    """Valida un entero no negativo rechazando booleanos implícitos.

    Args:
        value: Valor que debe ser un ``int`` mayor o igual que cero.
        label: Nombre usado para contextualizar el error.

    Returns:
        Entero validado sin conversión coercitiva.

    Raises:
        ValueError: Si el valor es booleano, no es entero o es negativo.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} no es un entero no negativo")
    return value


def _finite_float(value: object, label: str) -> float:
    """Convierte un número real a ``float`` y exige que sea finito.

    Args:
        value: Entero o flotante que representa una métrica estadística.
        label: Nombre usado para contextualizar el error.

    Returns:
        Número convertido a ``float`` finito.

    Raises:
        ValueError: Si el valor es booleano, no es numérico, no puede
            representarse como ``float`` o es infinito/NaN.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} no es numérica")
    try:
        converted = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} no se puede representar") from exc
    if not math.isfinite(converted):
        raise ValueError(f"{label} no es finita")
    return converted
