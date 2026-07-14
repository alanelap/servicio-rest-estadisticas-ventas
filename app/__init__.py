"""Construcción y cableado de la aplicación Flask del servicio Cruz Morada.

El módulo expone una *application factory* para reutilizar la misma composición
en producción, comandos CLI y pruebas. Cada aplicación conserva su configuración
y extensiones, aunque el logging raíz y ciertas variables de entorno son efectos
compartidos por todo el proceso.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from flask import Flask

from app.api import health_blueprint, sales_blueprint
from app.cli import register_cli
from app.config import Config, path_from_config
from app.errors import register_error_handlers
from app.extensions import create_api
from app.observability import configure_logging, register_request_hooks
from app.repositories.sales_repository import SalesRepository
from app.services.filter_service import FilterService
from app.services.ingestion_service import IngestionService
from app.services.statistics_service import StatisticsService


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Crea y configura una instancia del servicio REST.

    La factoría parte de los valores de :class:`app.config.Config`, evaluados al
    importar su módulo, instala observabilidad y manejo de errores, construye
    los servicios de dominio y registra la API y los comandos administrativos.
    ``test_config`` se aplica inicialmente sobre esos valores; después se fuerzan
    ``DEBUG=False`` en producción y ``MAX_CONTENT_LENGTH`` a partir de
    ``MAX_REQUEST_BODY_BYTES``.

    Args:
        test_config: Sobrescrituras opcionales de la configuración de Flask.

    Returns:
        Aplicación Flask completamente configurada y lista para atender
        solicitudes o ejecutar comandos CLI.

    Raises:
        RuntimeError: Si el límite de cuerpo HTTP no es positivo o alguna
            configuración requerida por los componentes es inválida.
        ValueError: Si el nivel de logging no es válido o un valor esperado como
            entero no puede convertirse.
        TypeError: Si una sobrescritura usa un tipo incompatible con la
            conversión requerida por la factoría.
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if str(app.config["APP_ENV"]).lower() == "production":
        # Flask CLI vuelve a aplicar FLASK_DEBUG después de cargar la factory.
        # Neutralizar también la variable evita que sobreescriba este control.
        os.environ["FLASK_DEBUG"] = "0"
        app.config["DEBUG"] = False
        app.debug = False
    if int(app.config["MAX_REQUEST_BODY_BYTES"]) <= 0:
        raise RuntimeError("MAX_REQUEST_BODY_BYTES debe ser mayor que cero")
    app.config["MAX_CONTENT_LENGTH"] = int(app.config["MAX_REQUEST_BODY_BYTES"])

    configure_logging(app)
    register_request_hooks(app)
    repository = SalesRepository(
        processed_path=path_from_config(app.config["PROCESSED_DATA_PATH"]),
        summary_path=path_from_config(app.config["SUMMARY_CACHE_PATH"]),
        metadata_path=path_from_config(app.config["METADATA_PATH"]),
        quality_report_path=path_from_config(app.config["QUALITY_REPORT_PATH"]),
        stat_target_column=str(app.config["STAT_TARGET_COLUMN"]),
    )
    ingestion_service = IngestionService(
        default_dataset_path=path_from_config(app.config["DATASET_PATH"]),
        processed_path=repository.processed_path,
        summary_path=repository.summary_path,
        metadata_path=repository.metadata_path,
        quality_report_path=path_from_config(app.config["QUALITY_REPORT_PATH"]),
        allowed_root=Path(str(app.config["INGEST_ALLOWED_ROOT"])),
        stat_target_column=str(app.config["STAT_TARGET_COLUMN"]),
    )
    app.extensions["sales_repository"] = repository
    app.extensions["filter_service"] = FilterService()
    app.extensions["statistics_service"] = StatisticsService(repository)
    app.extensions["ingestion_service"] = ingestion_service

    api = create_api(app)
    api.register_blueprint(sales_blueprint)
    api.register_blueprint(health_blueprint)
    # Smorest instala su manejador HTTP al inicializarse; registrar el contrato
    # después garantiza el mismo formato también para 404/405/415/422.
    register_error_handlers(app)
    register_cli(app)

    return app
