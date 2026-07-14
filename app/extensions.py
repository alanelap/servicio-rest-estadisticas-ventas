"""Construcción de extensiones sin estado global entre factories."""

from typing import Any, Protocol, cast

from flask import Flask
from flask_smorest import Api

from app.schemas.errors import ErrorSchema


class ApiProtocol(Protocol):
    """Superficie tipada que usa la factory de una extensión sin stubs."""

    def register_blueprint(self, blueprint: object, **options: Any) -> None: ...


def create_api(app: Flask) -> ApiProtocol:
    """Inicializa Flask-Smorest para una instancia concreta de Flask."""

    api = Api()
    api.ERROR_SCHEMA = ErrorSchema
    api.init_app(app)
    return cast(ApiProtocol, api)
