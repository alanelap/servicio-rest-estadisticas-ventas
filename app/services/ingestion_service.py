"""Ingesta perezosa, vectorizada, auditable y publicada de forma atómica."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final
from uuid import uuid4

import polars as pl

from app.domain.enums import Channel, Gender
from app.domain.exceptions import IngestionError, StatisticsCalculationError
from app.domain.sales_schema import ANALYTIC_COLUMNS
from app.services.statistics_service import statistics_from_lazyframe
from app.utils.hashing import atomic_write_json, read_json_object, sha256_file
from app.utils.locks import ingestion_lock
from app.utils.snapshot import validate_snapshot

_LOGGER = logging.getLogger(__name__)
SCHEMA_VERSION: Final = 1
REQUIRED_COLUMNS: Final = {
    "FECHA",
    "CANAL",
    "SKU",
    "PRODUCTO",
    "UNIDADES",
    "PORCENTAJE DESCUENTO",
    "MONTO APLICADO",
    "BOLETA",
    "LOCAL",
    "CODIGO CLIENTE",
    "RUN CLIENTE",
    "NOMBRES",
    "APELLIDOS",
    "FECHA NACIMIENTO",
    "GÉNERO",
}
_UUID_PATTERN: Final = (
    r"(?i)^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}$"
)


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """Resultado no sensible del comando de ingesta."""

    status: str
    valid_rows: int
    discarded_rows: int
    source_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IngestionService:
    """Normaliza el CSV con Polars y construye artefactos consistentes."""

    def __init__(
        self,
        *,
        default_dataset_path: Path,
        processed_path: Path,
        summary_path: Path,
        metadata_path: Path,
        quality_report_path: Path,
        allowed_root: Path,
        stat_target_column: str,
    ) -> None:
        if stat_target_column not in {"MONTO APLICADO", "monto_aplicado"}:
            raise RuntimeError("STAT_TARGET_COLUMN solo admite 'MONTO APLICADO' en este contrato")
        self.default_dataset_path = default_dataset_path
        self.processed_path = processed_path
        self.summary_path = summary_path
        self.metadata_path = metadata_path
        self.quality_report_path = quality_report_path
        self.allowed_root = allowed_root.resolve()
        self.stat_target_column = stat_target_column

    def ingest(self, csv_path: Path | None = None, *, force: bool = False) -> IngestionResult:
        """Procesa el CSV solo si cambió y publica metadatos como último commit."""

        source_path = self._validated_source(csv_path or self.default_dataset_path)
        self.processed_path.parent.mkdir(parents=True, exist_ok=True)

        with ingestion_lock(self.processed_path):
            source_stat = source_path.stat()
            source_hash = sha256_file(source_path)
            if not force and self._is_current(source_stat, source_hash):
                metadata = read_json_object(self.metadata_path)
                return IngestionResult(
                    status="sin_cambios",
                    valid_rows=int(metadata["valid_rows"]),
                    discarded_rows=int(metadata["discarded_rows"]),
                    source_sha256=source_hash,
                )
            try:
                return self._process(source_path, source_stat, source_hash)
            except IngestionError:
                raise
            except (OSError, TypeError, ValueError, pl.exceptions.PolarsError) as exc:
                raise IngestionError("No fue posible procesar y publicar el CSV") from exc

    def needs_ingestion(self, csv_path: Path | None = None) -> bool:
        """Indica si faltan artefactos o cambió el contenido/configuración."""

        source_path = self._validated_source(csv_path or self.default_dataset_path)
        with ingestion_lock(self.processed_path):
            source_stat = source_path.stat()
            return not self._is_current(source_stat, sha256_file(source_path))

    def _process(
        self, source_path: Path, source_stat: os.stat_result, source_hash: str
    ) -> IngestionResult:
        started = time.perf_counter()
        raw = self._scan_source(source_path)
        normalized = self._normalized_frame(raw)
        invalid_reasons = self._invalid_reasons()
        invalid_any = pl.any_horizontal(list(invalid_reasons.values()))

        quality_row = (
            normalized.select(
                pl.len().alias("total_rows"),
                (~invalid_any).sum().alias("valid_rows"),
                invalid_any.sum().alias("discarded_rows"),
                *[expression.sum().alias(name) for name, expression in invalid_reasons.items()],
            )
            .collect(engine="streaming")
            .row(0, named=True)
        )

        valid_rows = int(quality_row["valid_rows"])
        discarded_rows = int(quality_row["discarded_rows"])
        generation_id = str(uuid4())
        temporary_parquet = self.processed_path.with_name(
            f".{self.processed_path.name}.{generation_id}.tmp.parquet"
        )
        try:
            normalized.filter(~invalid_any).select(ANALYTIC_COLUMNS).sink_parquet(
                temporary_parquet,
                compression="zstd",
                statistics=True,
                maintain_order=False,
                mkdir=True,
                engine="streaming",
                metadata={"generation_id": generation_id},
            )
            summary = statistics_from_lazyframe(
                pl.scan_parquet(temporary_parquet), "monto_aplicado"
            )
            with temporary_parquet.open("rb") as stream:
                os.fsync(stream.fileno())

            # Los LazyFrame recorren el CSV de forma perezosa. Antes de publicar,
            # se verifica que la fuente siga siendo exactamente la inicialmente
            # identificada; una modificación concurrente aborta toda la generación.
            final_source_stat = source_path.stat()
            if (
                final_source_stat.st_size != source_stat.st_size
                or final_source_stat.st_mtime_ns != source_stat.st_mtime_ns
                or sha256_file(source_path) != source_hash
            ):
                raise IngestionError("El CSV cambió durante la ingesta; vuelva a intentarlo")
            os.replace(temporary_parquet, self.processed_path)

            processed_at = _utc_now()
            duration_seconds = round(time.perf_counter() - started, 6)
            quality_payload: dict[str, Any] = {
                "generation_id": generation_id,
                "processed_at": processed_at,
                "total_rows": int(quality_row["total_rows"]),
                "valid_rows": valid_rows,
                "discarded_rows": discarded_rows,
                "invalid_reason_counts": {name: int(quality_row[name]) for name in invalid_reasons},
                "policy": (
                    "Se descarta una fila si falla al menos una regla; una fila puede "
                    "figurar en más de un motivo. No se guardan valores personales."
                ),
            }
            cache_payload = {
                "generation_id": generation_id,
                "processed_at": processed_at,
                "statistics": summary.to_dict(),
            }
            metadata_payload: dict[str, Any] = {
                "generation_id": generation_id,
                "schema_version": SCHEMA_VERSION,
                "source_file": source_path.name,
                "source_size_bytes": source_stat.st_size,
                "source_mtime_ns": source_stat.st_mtime_ns,
                "source_sha256": source_hash,
                "valid_rows": valid_rows,
                "discarded_rows": discarded_rows,
                "processed_at": processed_at,
                "duration_seconds": duration_seconds,
                "stat_target_column": self.stat_target_column,
                "analytic_columns": list(ANALYTIC_COLUMNS),
            }
            atomic_write_json(self.summary_path, cache_payload)
            atomic_write_json(self.quality_report_path, quality_payload)
            atomic_write_json(self.metadata_path, metadata_payload)
        except (OSError, pl.exceptions.PolarsError, StatisticsCalculationError, ValueError) as exc:
            temporary_parquet.unlink(missing_ok=True)
            raise IngestionError("No fue posible procesar y publicar el CSV") from exc
        except IngestionError:
            temporary_parquet.unlink(missing_ok=True)
            raise

        _LOGGER.info(
            "Ingesta completada",
            extra={
                "event": "ingestion_completed",
                "valid_rows": valid_rows,
                "discarded_rows": discarded_rows,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            },
        )
        return IngestionResult(
            status="procesado",
            valid_rows=valid_rows,
            discarded_rows=discarded_rows,
            source_sha256=source_hash,
        )

    def _scan_source(self, source_path: Path) -> pl.LazyFrame:
        try:
            separator = self._detect_separator(source_path)
            raw = pl.scan_csv(
                source_path,
                separator=separator,
                infer_schema=False,
                null_values=["", "NULL", "null"],
                try_parse_dates=False,
                encoding="utf8",
                raise_if_empty=True,
            )
            columns = set(raw.collect_schema().names())
            if "GENERO" in columns and "GÉNERO" in columns:
                raise IngestionError("El CSV contiene simultáneamente las columnas GENERO y GÉNERO")
            if "GENERO" in columns:
                raw = raw.rename({"GENERO": "GÉNERO"})
                columns.remove("GENERO")
                columns.add("GÉNERO")
        except (OSError, pl.exceptions.PolarsError) as exc:
            raise IngestionError("El CSV no se pudo leer o no es válido") from exc
        missing = sorted(REQUIRED_COLUMNS - columns)
        if missing:
            raise IngestionError("Faltan columnas obligatorias en el CSV: " + ", ".join(missing))
        return raw.select(sorted(REQUIRED_COLUMNS))

    @staticmethod
    def _detect_separator(source_path: Path) -> str:
        """Detecta los formatos oficiales/sintéticos sin leer filas personales."""

        with source_path.open("rb") as stream:
            header = stream.readline(64 * 1024)
        semicolons = header.count(b";")
        commas = header.count(b",")
        if semicolons == commas == 0:
            raise IngestionError("No se pudo detectar el delimitador del CSV")
        return ";" if semicolons > commas else ","

    @staticmethod
    def _normalized_frame(raw: pl.LazyFrame) -> pl.LazyFrame:
        raw_sale_date = pl.col("FECHA").str.strip_chars()
        has_time = raw_sale_date.str.contains(r"[T ]\d{2}:\d{2}").fill_null(False)
        has_offset_suffix = raw_sale_date.str.contains(
            r"(?:[zZ]|[+-]\d{2}(?::?\d{2})?)$"
        ).fill_null(False)
        has_explicit_offset = has_time & has_offset_suffix
        aware_utc = (
            pl.when(has_explicit_offset)
            .then(raw_sale_date)
            .otherwise(None)
            .str.to_datetime(
                time_zone="UTC",
                strict=False,
            )
        )
        naive_utc = (
            pl.when(~has_explicit_offset)
            .then(raw_sale_date)
            .otherwise(None)
            .str.to_datetime(strict=False)
            .dt.replace_time_zone("Etc/GMT+4", ambiguous="null", non_existent="null")
            .dt.convert_time_zone("UTC")
        )
        sale_utc = pl.coalesce(aware_utc, naive_utc)
        sale_local = sale_utc.dt.convert_time_zone("Etc/GMT+4")
        birth = pl.col("FECHA NACIMIENTO").str.strip_chars().str.to_date("%Y-%m-%d", strict=False)
        frame = raw.select(
            sale_local.alias("_fecha_local"),
            sale_utc.alias("fecha"),
            pl.col("CANAL").str.strip_chars().str.to_uppercase().alias("canal"),
            pl.col("SKU").str.strip_chars().cast(pl.Int64, strict=False).alias("sku"),
            pl.col("PRODUCTO").str.strip_chars().alias("producto"),
            pl.col("UNIDADES").str.strip_chars().cast(pl.Int64, strict=False).alias("unidades"),
            pl.col("PORCENTAJE DESCUENTO")
            .str.strip_chars()
            .cast(pl.Float64, strict=False)
            .alias("porcentaje_descuento"),
            pl.col("MONTO APLICADO")
            .str.strip_chars()
            .cast(pl.Float64, strict=False)
            .alias("monto_aplicado"),
            pl.col("BOLETA").str.strip_chars().cast(pl.Int64, strict=False).alias("boleta"),
            pl.col("LOCAL").str.strip_chars().cast(pl.Int64, strict=False).alias("local"),
            pl.col("CODIGO CLIENTE").str.strip_chars().str.to_lowercase().alias("codigo_cliente"),
            birth.alias("fecha_nacimiento"),
            pl.col("GÉNERO").str.strip_chars().cast(pl.Int64, strict=False).alias("genero_codigo"),
            (
                pl.col("GÉNERO").str.strip_chars().is_not_null()
                & (pl.col("GÉNERO").str.strip_chars().str.len_chars() > 0)
            ).alias("_genero_informado"),
        )
        birthday_pending = (
            pl.col("_fecha_local").dt.month() < pl.col("fecha_nacimiento").dt.month()
        ) | (
            (pl.col("_fecha_local").dt.month() == pl.col("fecha_nacimiento").dt.month())
            & (pl.col("_fecha_local").dt.day() < pl.col("fecha_nacimiento").dt.day())
        )
        return frame.with_columns(
            (
                pl.col("_fecha_local").dt.year()
                - pl.col("fecha_nacimiento").dt.year()
                - birthday_pending.cast(pl.Int16)
            )
            .cast(pl.Int16)
            .alias("edad_en_transaccion"),
            pl.when(pl.col("genero_codigo") == 1)
            .then(pl.lit(Gender.MALE.value))
            .when(pl.col("genero_codigo") == 2)
            .then(pl.lit(Gender.FEMALE.value))
            .when(pl.col("genero_codigo").is_null() | (pl.col("genero_codigo") == 0))
            .then(pl.lit(Gender.UNSPECIFIED.value))
            .otherwise(pl.lit(Gender.OTHER.value))
            .alias("genero_texto"),
        )

    @staticmethod
    def _invalid_reasons() -> dict[str, pl.Expr]:
        return {
            "fecha_invalida": pl.col("fecha").is_null(),
            "canal_invalido": pl.col("canal").is_null()
            | ~pl.col("canal").is_in([item.value for item in Channel]),
            "sku_invalido": pl.col("sku").is_null() | (pl.col("sku") <= 0),
            "producto_invalido": pl.col("producto").is_null()
            | (pl.col("producto").str.len_chars() == 0),
            "unidades_invalidas": pl.col("unidades").is_null() | (pl.col("unidades") <= 0),
            "descuento_invalido": pl.col("porcentaje_descuento").is_null()
            | ~pl.col("porcentaje_descuento").is_finite()
            | (pl.col("porcentaje_descuento") < 0)
            | (pl.col("porcentaje_descuento") > 1),
            "monto_invalido": pl.col("monto_aplicado").is_null()
            | ~pl.col("monto_aplicado").is_finite(),
            "boleta_invalida": pl.col("boleta").is_null() | (pl.col("boleta") <= 0),
            "local_invalido": pl.col("local").is_null() | (pl.col("local") <= 0),
            "uuid_invalido": pl.col("codigo_cliente").is_null()
            | ~pl.col("codigo_cliente").str.contains(_UUID_PATTERN),
            "fecha_nacimiento_invalida": pl.col("fecha_nacimiento").is_null(),
            "genero_invalido": pl.col("_genero_informado") & pl.col("genero_codigo").is_null(),
            "edad_invalida": pl.col("edad_en_transaccion").is_null()
            | (pl.col("edad_en_transaccion") < 0)
            | (pl.col("edad_en_transaccion") > 120),
        }

    def _validated_source(self, raw_path: Path) -> Path:
        path = raw_path.expanduser()
        if not path.is_absolute():
            path = (self.allowed_root / path).resolve()
        else:
            path = path.resolve()
        try:
            path.relative_to(self.allowed_root)
        except ValueError as exc:
            raise IngestionError(
                "La ruta del CSV debe permanecer dentro de la raíz autorizada"
            ) from exc
        if not path.is_file():
            raise IngestionError("El archivo CSV no existe")
        if path.suffix.lower() != ".csv":
            raise IngestionError("El archivo de entrada debe tener extensión .csv")
        if not os.access(path, os.R_OK):
            raise IngestionError("El archivo CSV no tiene permisos de lectura")
        return path

    def _is_current(self, source_stat: os.stat_result, source_hash: str) -> bool:
        required_artifacts = (
            self.processed_path,
            self.summary_path,
            self.metadata_path,
            self.quality_report_path,
        )
        if not all(path.is_file() for path in required_artifacts):
            return False
        try:
            state = validate_snapshot(
                processed_path=self.processed_path,
                summary_path=self.summary_path,
                metadata_path=self.metadata_path,
                quality_report_path=self.quality_report_path,
                schema_version=SCHEMA_VERSION,
                stat_target_column=self.stat_target_column,
            )
            metadata = state.metadata
        except (OSError, ValueError, pl.exceptions.PolarsError):
            return False
        return all(
            (
                metadata.get("source_size_bytes") == source_stat.st_size,
                metadata.get("source_mtime_ns") == source_stat.st_mtime_ns,
                metadata.get("source_sha256") == source_hash,
            )
        )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
