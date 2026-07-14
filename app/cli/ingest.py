"""Comando Flask para preparar los artefactos analíticos."""

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
    """Valida, normaliza y publica el dataset."""

    service = cast(IngestionService, current_app.extensions["ingestion_service"])
    try:
        result = service.ingest(csv_path, force=force)
    except IngestionError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result.to_dict(), ensure_ascii=False))


def register_cli(app: Flask) -> None:
    """Registra comandos sin efectos laterales al importar módulos."""

    app.cli.add_command(ingest_data_command)
