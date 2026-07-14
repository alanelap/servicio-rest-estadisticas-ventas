"""Punto de entrada WSGI para Gunicorn."""

from app import create_app

app = create_app()
