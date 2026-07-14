"""Pruebas de integración del pipeline CSV, sus artefactos y el comando CLI."""

from __future__ import annotations

import csv
import json
import os
import shutil
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
import pytest

from app import create_app
from app.domain.exceptions import DataNotReadyError, IngestionError
from app.repositories.sales_repository import SalesRepository
from app.services.ingestion_service import IngestionService

FIXTURE_CSV = Path(__file__).parents[1] / "fixtures" / "ventas.csv"
EXPECTED_ANALYTIC_COLUMNS = [
    "fecha",
    "canal",
    "sku",
    "monto_aplicado",
    "local",
    "codigo_cliente",
    "genero_texto",
    "edad_en_transaccion",
]
SOURCE_AMOUNTS = [
    1000.5,
    2000.0,
    3000.5,
    4000.0,
    5000.5,
    6000.0,
    7000.5,
    8000.0,
    9000.5,
    10000.0,
    11000.5,
    12000.0,
]


@dataclass(frozen=True, slots=True)
class IngestionCase:
    """Servicio de ingesta y rutas confinadas a un directorio temporal."""

    root: Path
    source: Path
    parquet: Path
    summary: Path
    metadata: Path
    quality: Path
    service: IngestionService

    @property
    def artifacts(self) -> tuple[Path, ...]:
        return (self.parquet, self.summary, self.metadata, self.quality)


def _build_case(tmp_path: Path) -> IngestionCase:
    root = tmp_path / "workspace"
    root.mkdir()
    source = root / "ventas.csv"
    shutil.copyfile(FIXTURE_CSV, source)
    processed = root / "processed"
    parquet = processed / "ventas.parquet"
    summary = processed / "statistics.json"
    metadata = processed / "metadata.json"
    quality = processed / "quality_report.json"
    service = IngestionService(
        default_dataset_path=source,
        processed_path=parquet,
        summary_path=summary,
        metadata_path=metadata,
        quality_report_path=quality,
        allowed_root=root,
        stat_target_column="MONTO APLICADO",
    )
    return IngestionCase(root, source, parquet, summary, metadata, quality, service)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames is not None
        rows = [
            {str(name): "" if value is None else str(value) for name, value in row.items()}
            for row in reader
        ]
        return list(reader.fieldnames), rows


def _write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
    *,
    delimiter: str = ",",
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
            delimiter=delimiter,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _app_config(case: IngestionCase) -> dict[str, Any]:
    return {
        "TESTING": True,
        "APP_ENV": "testing",
        "AUTO_INGEST": False,
        "DATASET_PATH": str(case.source),
        "PROCESSED_DATA_PATH": str(case.parquet),
        "SUMMARY_CACHE_PATH": str(case.summary),
        "METADATA_PATH": str(case.metadata),
        "QUALITY_REPORT_PATH": str(case.quality),
        "INGEST_ALLOWED_ROOT": str(case.root),
        "STAT_TARGET_COLUMN": "MONTO APLICADO",
    }


def test_valid_csv_generates_parquet_summary_metadata_and_quality_report(
    tmp_path: Path,
) -> None:
    case = _build_case(tmp_path)

    result = case.service.ingest()

    assert result.status == "procesado"
    assert result.valid_rows == len(SOURCE_AMOUNTS)
    assert result.discarded_rows == 0
    assert len(result.source_sha256) == 64
    assert all(path.is_file() for path in case.artifacts)

    frame = pl.read_parquet(case.parquet)
    assert frame.columns == EXPECTED_ANALYTIC_COLUMNS
    assert frame.height == len(SOURCE_AMOUNTS)
    assert frame.schema["sku"] == pl.Int64
    assert frame.schema["monto_aplicado"] == pl.Float64
    assert frame.schema["local"] == pl.Int64
    assert frame.schema["codigo_cliente"] == pl.String
    assert frame.schema["edad_en_transaccion"] == pl.Int16
    assert frame.schema["fecha"].is_temporal()
    assert frame["canal"].unique().sort().to_list() == ["APP", "APR", "CCT", "POS", "WEB", "WPR"]
    assert set(frame["genero_texto"].unique()) == {
        "Femenino",
        "Masculino",
        "No especificado",
        "Otro",
    }

    forbidden_columns = {
        "RUN CLIENTE",
        "run_cliente",
        "NOMBRES",
        "nombres",
        "APELLIDOS",
        "apellidos",
        "BOLETA",
        "boleta",
    }
    assert forbidden_columns.isdisjoint(frame.columns)

    summary = _read_json(case.summary)
    metadata = _read_json(case.metadata)
    quality = _read_json(case.quality)
    assert summary["generation_id"] == metadata["generation_id"] == quality["generation_id"]
    assert summary["processed_at"] == metadata["processed_at"] == quality["processed_at"]

    cached_statistics = summary["statistics"]
    assert cached_statistics["conteo"] == len(SOURCE_AMOUNTS)
    expected_statistics = {
        "suma": sum(SOURCE_AMOUNTS),
        "promedio": statistics.mean(SOURCE_AMOUNTS),
        "minimo": min(SOURCE_AMOUNTS),
        "maximo": max(SOURCE_AMOUNTS),
        "mediana": statistics.median(SOURCE_AMOUNTS),
        "desviacion_estandar": statistics.pstdev(SOURCE_AMOUNTS),
    }
    for name, expected in expected_statistics.items():
        assert cached_statistics[name] == pytest.approx(expected)

    source_stat = case.source.stat()
    assert metadata["source_file"] == case.source.name
    assert metadata["source_size_bytes"] == source_stat.st_size
    assert metadata["source_mtime_ns"] == source_stat.st_mtime_ns
    assert metadata["source_sha256"] == result.source_sha256
    assert metadata["valid_rows"] == len(SOURCE_AMOUNTS)
    assert metadata["discarded_rows"] == 0
    assert metadata["stat_target_column"] == "MONTO APLICADO"
    assert metadata["analytic_columns"] == EXPECTED_ANALYTIC_COLUMNS
    assert metadata["duration_seconds"] >= 0
    assert quality["total_rows"] == len(SOURCE_AMOUNTS)
    assert quality["valid_rows"] == len(SOURCE_AMOUNTS)
    assert quality["discarded_rows"] == 0
    assert all(count == 0 for count in quality["invalid_reason_counts"].values())


def test_official_semicolon_format_and_unaccented_gender_header_are_supported(
    tmp_path: Path,
) -> None:
    case = _build_case(tmp_path)
    fieldnames, rows = _read_csv(case.source)
    fieldnames[fieldnames.index("GÉNERO")] = "GENERO"
    for row in rows:
        row["GENERO"] = row.pop("GÉNERO")
    _write_csv(case.source, fieldnames, rows, delimiter=";")

    result = case.service.ingest()

    assert result.valid_rows == len(SOURCE_AMOUNTS)
    assert result.discarded_rows == 0
    assert pl.read_parquet(case.parquet).height == len(SOURCE_AMOUNTS)


def test_nonexistent_csv_is_rejected(tmp_path: Path) -> None:
    case = _build_case(tmp_path)

    with pytest.raises(IngestionError, match="El archivo CSV no existe"):
        case.service.ingest(Path("inexistente.csv"))

    assert not any(path.exists() for path in case.artifacts)


def test_csv_outside_allowed_root_is_rejected_even_with_path_traversal(tmp_path: Path) -> None:
    case = _build_case(tmp_path)
    outside = tmp_path / "fuera.csv"
    shutil.copyfile(FIXTURE_CSV, outside)

    with pytest.raises(IngestionError, match="debe permanecer dentro de la raíz autorizada"):
        case.service.ingest(Path("..") / outside.name)

    assert not any(path.exists() for path in case.artifacts)


def test_csv_with_missing_required_column_is_rejected(tmp_path: Path) -> None:
    case = _build_case(tmp_path)
    fieldnames, rows = _read_csv(case.source)
    fieldnames.remove("MONTO APLICADO")
    for row in rows:
        row.pop("MONTO APLICADO")
    _write_csv(case.source, fieldnames, rows)

    with pytest.raises(
        IngestionError,
        match="Faltan columnas obligatorias en el CSV: MONTO APLICADO",
    ):
        case.service.ingest()

    assert not any(path.exists() for path in case.artifacts)


def test_invalid_types_are_discarded_and_reported_without_personal_data(tmp_path: Path) -> None:
    case = _build_case(tmp_path)
    fieldnames, source_rows = _read_csv(case.source)
    rows = source_rows[:2]
    rows[1].update(
        {
            "FECHA": "fecha-invalida",
            "CANAL": "FAX",
            "SKU": "sku-invalido",
            "PRODUCTO": "",
            "UNIDADES": "0",
            "PORCENTAJE DESCUENTO": "1.5",
            "MONTO APLICADO": "monto-invalido",
            "BOLETA": "-1",
            "LOCAL": "local-invalido",
            "CODIGO CLIENTE": "uuid-invalido",
            "RUN CLIENTE": "11.111.111-1",
            "NOMBRES": "NOMBRE_SECRETO",
            "APELLIDOS": "APELLIDO_SECRETO",
            "FECHA NACIMIENTO": "nacimiento-invalido",
            "GÉNERO": "genero-invalido",
        }
    )
    _write_csv(case.source, fieldnames, rows)

    result = case.service.ingest()

    assert result.status == "procesado"
    assert result.valid_rows == 1
    assert result.discarded_rows == 1
    assert pl.read_parquet(case.parquet).height == 1

    quality = _read_json(case.quality)
    assert quality["total_rows"] == 2
    assert quality["valid_rows"] == 1
    assert quality["discarded_rows"] == 1
    assert quality["invalid_reason_counts"] == {
        "fecha_invalida": 1,
        "canal_invalido": 1,
        "sku_invalido": 1,
        "producto_invalido": 1,
        "unidades_invalidas": 1,
        "descuento_invalido": 1,
        "monto_invalido": 1,
        "boleta_invalida": 1,
        "local_invalido": 1,
        "uuid_invalido": 1,
        "fecha_nacimiento_invalida": 1,
        "genero_invalido": 1,
        "edad_invalida": 1,
    }
    serialized_report = json.dumps(quality, ensure_ascii=False)
    for sensitive_value in (
        "11.111.111-1",
        "NOMBRE_SECRETO",
        "APELLIDO_SECRETO",
        "uuid-invalido",
    ):
        assert sensitive_value not in serialized_report


def test_null_channel_and_malformed_gender_are_discarded_independently(tmp_path: Path) -> None:
    case = _build_case(tmp_path)
    fieldnames, source_rows = _read_csv(case.source)
    rows = source_rows[:3]
    rows[1]["CANAL"] = ""
    rows[2]["GÉNERO"] = "no-es-codigo"
    _write_csv(case.source, fieldnames, rows)

    result = case.service.ingest()
    reasons = _read_json(case.quality)["invalid_reason_counts"]

    assert result.valid_rows == 1
    assert result.discarded_rows == 2
    assert reasons["canal_invalido"] == 1
    assert reasons["genero_invalido"] == 1


def test_sale_dates_accept_common_iso_offsets_and_normalize_to_utc(tmp_path: Path) -> None:
    case = _build_case(tmp_path)
    fieldnames, source_rows = _read_csv(case.source)
    rows = source_rows[:3]
    rows[0]["FECHA"] = "2026-05-08T00:02:53Z"
    rows[1]["FECHA"] = "2026-05-08 00:02:53+03:00"
    rows[2]["FECHA"] = "2026-05-08T00:02:53+03"
    _write_csv(case.source, fieldnames, rows)

    result = case.service.ingest()
    instants = pl.read_parquet(case.parquet)["fecha"].sort().to_list()

    assert result.discarded_rows == 0
    assert instants == [
        datetime(2026, 5, 7, 21, 2, 53, tzinfo=UTC),
        datetime(2026, 5, 7, 21, 2, 53, tzinfo=UTC),
        datetime(2026, 5, 8, 0, 2, 53, tzinfo=UTC),
    ]


def test_date_only_sale_uses_fixed_utc_minus_four_not_day_suffix_as_offset(
    tmp_path: Path,
) -> None:
    case = _build_case(tmp_path)
    fieldnames, source_rows = _read_csv(case.source)
    rows = source_rows[:1]
    rows[0]["FECHA"] = "2026-05-08"
    _write_csv(case.source, fieldnames, rows)

    result = case.service.ingest()
    instant = pl.read_parquet(case.parquet)["fecha"].item()

    assert result.discarded_rows == 0
    assert instant == datetime(2026, 5, 8, 4, tzinfo=UTC)


def test_failed_multi_artifact_publication_is_never_served_and_is_repaired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _build_case(tmp_path)
    case.service.ingest()
    repository = SalesRepository(
        processed_path=case.parquet,
        summary_path=case.summary,
        metadata_path=case.metadata,
        quality_report_path=case.quality,
        stat_target_column="MONTO APLICADO",
    )
    import app.services.ingestion_service as ingestion_module

    real_atomic_write = ingestion_module.atomic_write_json
    calls = 0

    def fail_during_publication(path: Path, payload: dict[str, Any]) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("fallo simulado entre artefactos")
        real_atomic_write(path, payload)

    monkeypatch.setattr(ingestion_module, "atomic_write_json", fail_during_publication)
    with pytest.raises(IngestionError, match="publicar"):
        case.service.ingest(force=True)

    assert repository.readiness() == (False, "unreadable")
    with pytest.raises(DataNotReadyError):
        repository.load_cached_statistics()

    monkeypatch.setattr(ingestion_module, "atomic_write_json", real_atomic_write)
    repaired = case.service.ingest()

    assert repaired.status == "procesado"
    assert repository.readiness() == (True, "ready")


def test_source_change_during_lazy_ingestion_aborts_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _build_case(tmp_path)
    import app.services.ingestion_service as ingestion_module

    real_statistics = ingestion_module.statistics_from_lazyframe

    def calculate_then_mutate(frame: pl.LazyFrame, target: str):
        result = real_statistics(frame, target)
        case.source.write_text(case.source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        return result

    monkeypatch.setattr(ingestion_module, "statistics_from_lazyframe", calculate_then_mutate)

    with pytest.raises(IngestionError, match="cambió durante la ingesta"):
        case.service.ingest()
    assert not any(path.exists() for path in case.artifacts)


def test_unchanged_csv_does_not_rewrite_artifacts(tmp_path: Path) -> None:
    case = _build_case(tmp_path)
    first = case.service.ingest()
    original_metadata = _read_json(case.metadata)
    original_mtimes = {path: path.stat().st_mtime_ns for path in case.artifacts}

    assert case.service.needs_ingestion() is False
    second = case.service.ingest()

    assert second.status == "sin_cambios"
    assert second.valid_rows == first.valid_rows
    assert second.discarded_rows == first.discarded_rows
    assert second.source_sha256 == first.source_sha256
    assert _read_json(case.metadata) == original_metadata
    assert {path: path.stat().st_mtime_ns for path in case.artifacts} == original_mtimes


def test_changed_csv_is_reprocessed_when_size_and_mtime_are_unchanged(tmp_path: Path) -> None:
    case = _build_case(tmp_path)
    first = case.service.ingest()
    first_generation = _read_json(case.metadata)["generation_id"]
    original_stat = case.source.stat()
    fieldnames, rows = _read_csv(case.source)
    rows[0]["MONTO APLICADO"] = "1001.5"
    _write_csv(case.source, fieldnames, rows)
    assert case.source.stat().st_size == original_stat.st_size
    os.utime(case.source, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    assert case.source.stat().st_mtime_ns == original_stat.st_mtime_ns

    assert case.service.needs_ingestion() is True
    second = case.service.ingest()

    assert second.status == "procesado"
    assert second.source_sha256 != first.source_sha256
    assert _read_json(case.metadata)["generation_id"] != first_generation
    assert _read_json(case.summary)["statistics"]["suma"] == pytest.approx(
        sum(SOURCE_AMOUNTS) + 1.0
    )


def test_force_reprocesses_an_unchanged_csv(tmp_path: Path) -> None:
    case = _build_case(tmp_path)
    first = case.service.ingest()
    first_generation = _read_json(case.metadata)["generation_id"]

    second = case.service.ingest(force=True)

    metadata = _read_json(case.metadata)
    assert second.status == "procesado"
    assert second.source_sha256 == first.source_sha256
    assert metadata["generation_id"] != first_generation
    assert _read_json(case.summary)["generation_id"] == metadata["generation_id"]
    assert _read_json(case.quality)["generation_id"] == metadata["generation_id"]


def test_ingest_data_cli_succeeds_and_emits_machine_readable_result(tmp_path: Path) -> None:
    case = _build_case(tmp_path)
    app = create_app(_app_config(case))

    invocation = app.test_cli_runner().invoke(args=["ingest-data", "--csv", str(case.source)])

    assert invocation.exit_code == 0, invocation.output
    assert json.loads(invocation.output) == {
        "status": "procesado",
        "valid_rows": len(SOURCE_AMOUNTS),
        "discarded_rows": 0,
        "source_sha256": _read_json(case.metadata)["source_sha256"],
    }
    assert all(path.is_file() for path in case.artifacts)


def test_ingest_data_cli_returns_a_clear_error_for_invalid_input(tmp_path: Path) -> None:
    case = _build_case(tmp_path)
    app = create_app(_app_config(case))

    invocation = app.test_cli_runner().invoke(
        args=["ingest-data", "--csv", str(case.root / "inexistente.csv")]
    )

    assert invocation.exit_code != 0
    assert invocation.output == "Error: El archivo CSV no existe\n"
    assert not any(path.exists() for path in case.artifacts)
