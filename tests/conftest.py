"""Fixtures compartidos con datos aislados y deterministas."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.services.ingestion_service import IngestionService

_FIXTURE_CSV = Path(__file__).parent / "fixtures" / "ventas.csv"


@pytest.fixture
def test_paths(tmp_path: Path) -> dict[str, Path]:
    """Copia el CSV y define todos los artefactos dentro del directorio temporal."""
    dataset = tmp_path / "ventas.csv"
    shutil.copy2(_FIXTURE_CSV, dataset)
    processed = tmp_path / "processed"
    return {
        "root": tmp_path,
        "dataset": dataset,
        "processed": processed / "ventas.parquet",
        "summary": processed / "statistics.json",
        "metadata": processed / "metadata.json",
        "quality": processed / "quality_report.json",
    }


@pytest.fixture
def app(test_paths: dict[str, Path]) -> Iterator[Flask]:
    """Crea una aplicación sin estado compartido y con rutas temporales."""
    application = create_app(
        {
            "TESTING": True,
            "APP_ENV": "test",
            "AUTO_INGEST": False,
            "DATASET_PATH": str(test_paths["dataset"]),
            "PROCESSED_DATA_PATH": str(test_paths["processed"]),
            "SUMMARY_CACHE_PATH": str(test_paths["summary"]),
            "METADATA_PATH": str(test_paths["metadata"]),
            "QUALITY_REPORT_PATH": str(test_paths["quality"]),
            "INGEST_ALLOWED_ROOT": str(test_paths["root"]),
        }
    )
    yield application


@pytest.fixture
def ingestion_service(app: Flask) -> IngestionService:
    """Expone la instancia cableada por la factory para pruebas de ingesta."""
    service = app.extensions["ingestion_service"]
    assert isinstance(service, IngestionService)
    return service


@pytest.fixture
def client(app: Flask, ingestion_service: IngestionService) -> Iterator[FlaskClient]:
    """Entrega un cliente cuya copia temporal del fixture ya fue procesada."""
    ingestion_service.ingest()
    with app.test_client() as test_client:
        yield test_client
