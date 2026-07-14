"""Integración de la ingesta analítica con la interfaz Flask CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import click
from flask import Flask, current_app
from flask.cli import with_appcontext

from app.domain.exceptions import IngestionError
from app.services.ingestion_service import IngestionService


@click.command("ingest-data")
@click.option(
    "--csv",
    "csv_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="CSV dentro de la raíz autorizada; por defecto usa DATASET_PATH.",
)
@click.option("--force", is_flag=True, help="Reprocesa aunque el archivo no haya cambiado.")
@with_appcontext
def ingest_data_command(csv_path: Path | None, force: bool) -> None:
    """Valida, normaliza y publica los artefactos derivados del CSV.

    Args:
        csv_path: Fuente opcional dentro de la raíz autorizada; si se omite se
            usa la ruta configurada en ``DATASET_PATH``.
        force: Reprocesa la fuente aunque su huella y configuración no cambien.

    Raises:
        click.ClickException: Si el servicio de ingesta rechaza la fuente o no
            logra construir una generación completa.
        OSError: Si falla una operación inicial sobre el sistema de archivos.
        TimeoutError: Si expira la espera por el bloqueo exclusivo de ingesta.

    El resultado se emite como una línea JSON sin datos personales. La salida
    estándar también puede contener eventos JSON del sistema de logging cuando
    la configuración de la aplicación habilita mensajes informativos.
    """
    service = cast(IngestionService, current_app.extensions["ingestion_service"])
    try:
        result = service.ingest(csv_path, force=force)
    except IngestionError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result.to_dict(), ensure_ascii=False))


def register_cli(app: Flask) -> None:
    """Registra los comandos administrativos en una aplicación Flask.

    Args:
        app: Aplicación que expondrá ``ingest-data`` a través de Flask CLI.
    """
    app.cli.add_command(ingest_data_command)
