"""Configuración centralizada de la aplicación."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

PROJECT_ROOT: Final = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"La variable {name} debe ser un entero") from exc


class Config:
    """Valores predeterminados, reemplazables mediante variables de entorno."""

    APP_ENV = os.getenv("APP_ENV", "production").strip().lower()
    DEBUG = _env_bool("FLASK_DEBUG", False) if APP_ENV == "development" else False
    TESTING = False

    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = _env_int("PORT", 8000)
    WORKERS = _env_int("WORKERS", 2)
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    DATASET_PATH = os.getenv("DATASET_PATH", "data/ventas.csv")
    PROCESSED_DATA_PATH = os.getenv("PROCESSED_DATA_PATH", "data/processed/ventas.parquet")
    SUMMARY_CACHE_PATH = os.getenv("SUMMARY_CACHE_PATH", "data/processed/statistics.json")
    METADATA_PATH = os.getenv("METADATA_PATH", "data/processed/metadata.json")
    QUALITY_REPORT_PATH = os.getenv("QUALITY_REPORT_PATH", "data/processed/quality_report.json")
    INGEST_ALLOWED_ROOT = os.getenv("INGEST_ALLOWED_ROOT", str(PROJECT_ROOT))
    STAT_TARGET_COLUMN = os.getenv("STAT_TARGET_COLUMN", "MONTO APLICADO")
    AUTO_INGEST = _env_bool("AUTO_INGEST", False)

    MAX_REQUEST_BODY_BYTES = _env_int("MAX_REQUEST_BODY_BYTES", 16_384)
    MAX_CONTENT_LENGTH = MAX_REQUEST_BODY_BYTES

    API_TITLE = "Servicio REST de Resumen Estadístico de Ventas — Cruz Morada"
    API_VERSION = "1.0.0"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/"
    OPENAPI_JSON_PATH = "openapi.json"
    OPENAPI_SWAGGER_UI_PATH = "/docs"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.31.0/"
    API_SPEC_OPTIONS = {
        "info": {
            "description": (
                "API de estadísticas poblacionales calculadas sobre MONTO APLICADO. "
                "GET sin filtros usa un resumen precomputado; los filtros se combinan "
                "con AND. Si no hay coincidencias, suma es 0.0, conteo es 0 y las "
                "métricas no aplicables son null. La desviación estándar usa ddof=0. "
                'Antes de servir, ejecute: flask --app "app:create_app()" ingest-data '
                "--csv data/ventas.csv. Las validaciones responden 400 con el esquema "
                "Error documentado."
            )
        },
        "tags": [
            {"name": "ventas", "description": "Estadísticas de ventas"},
            {"name": "estado", "description": "Salud y preparación del servicio"},
        ],
    }


def path_from_config(value: object) -> Path:
    """Convierte un valor de configuración a una ruta absoluta estable."""

    path = Path(str(value)).expanduser()
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()
