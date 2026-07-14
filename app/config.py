"""Configuración centralizada y tipada desde variables de entorno.

Los valores de :class:`Config` se materializan al importar este módulo. Las
rutas que pasan por :func:`path_from_config` se interpretan respecto de la raíz
estable del proyecto; ``INGEST_ALLOWED_ROOT`` se conserva como configuración y
su resolución final corresponde al servicio de ingesta.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

PROJECT_ROOT: Final = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    """Lee una variable de entorno como indicador booleano tolerante a mayúsculas.

    Args:
        name: Nombre de la variable de entorno.
        default: Valor utilizado cuando la variable no está definida.

    Returns:
        ``True`` para ``1``, ``true``, ``yes``, ``on``, ``si`` o ``sí``;
        ``False`` para cualquier otro valor definido.
    """
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _env_int(name: str, default: int) -> int:
    """Lee una variable de entorno y exige que represente un entero.

    Args:
        name: Nombre de la variable de entorno.
        default: Valor utilizado cuando la variable no está definida.

    Returns:
        Entero configurado o el valor predeterminado.

    Raises:
        RuntimeError: Si la variable existe pero no contiene un entero válido.
    """
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"La variable {name} debe ser un entero") from exc


class Config:
    """Valores predeterminados de Flask reemplazables mediante el entorno.

    Attributes:
        APP_ENV: Entorno lógico de ejecución normalizado a minúsculas.
        DEBUG: Modo de depuración, habilitable solo en desarrollo.
        TESTING: Indicador de pruebas de Flask; desactivado por defecto.
        HOST: Interfaz de escucha del servidor.
        PORT: Puerto TCP de escucha.
        WORKERS: Cantidad sugerida de procesos Gunicorn.
        LOG_LEVEL: Nivel mínimo de logging normalizado a mayúsculas.
        DATASET_PATH: Ruta al CSV fuente.
        PROCESSED_DATA_PATH: Ruta al snapshot analítico Parquet.
        SUMMARY_CACHE_PATH: Ruta a la caché de estadísticas globales.
        METADATA_PATH: Ruta al manifiesto de la generación publicada.
        QUALITY_REPORT_PATH: Ruta al reporte agregado de calidad.
        INGEST_ALLOWED_ROOT: Raíz dentro de la que se autorizan fuentes de ingesta.
        STAT_TARGET_COLUMN: Columna contractual sobre la que se calculan estadísticas.
        AUTO_INGEST: Indicador para automatizaciones que decidan ejecutar la ingesta.
        MAX_REQUEST_BODY_BYTES: Tamaño máximo permitido para cuerpos HTTP.
        MAX_CONTENT_LENGTH: Alias de Flask para el límite máximo de cuerpo HTTP.
        API_TITLE: Título expuesto en OpenAPI.
        API_VERSION: Versión pública de la API.
        OPENAPI_VERSION: Versión de la especificación OpenAPI generada.
        OPENAPI_URL_PREFIX: Prefijo desde el que se publican los recursos OpenAPI.
        OPENAPI_JSON_PATH: Ruta relativa del documento OpenAPI JSON.
        OPENAPI_SWAGGER_UI_PATH: Endpoint de la interfaz interactiva Swagger UI.
        OPENAPI_SWAGGER_UI_URL: URL del paquete estático utilizado por Swagger UI.
        API_SPEC_OPTIONS: Metadatos, descripción y etiquetas adicionales de la API.
    """

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
    """Convierte un valor de configuración en una ruta absoluta estable.

    Args:
        value: Valor convertible a texto que representa una ruta absoluta o
            relativa a :data:`PROJECT_ROOT`.

    Returns:
        Ruta expandida y absoluta. Las rutas relativas se resuelven desde la
        raíz del proyecto.
    """
    path = Path(str(value)).expanduser()
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()
