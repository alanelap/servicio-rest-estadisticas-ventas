"""API pública de comandos administrativos para Flask CLI."""

from app.cli.ingest import register_cli

__all__ = ["register_cli"]
