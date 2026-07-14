"""Construye extensiones Flask aisladas para cada instancia de la aplicación."""

from typing import Any, Protocol, cast

from flask import Flask
from flask_smorest import Api

from app.schemas.errors import ErrorSchema


class ApiProtocol(Protocol):
    """Superficie mínima de Flask-Smorest requerida por la factoría.

    El protocolo evita propagar ``Any`` desde una dependencia sin stubs completos y
    desacopla el código llamador de métodos de la extensión que no utiliza.
    """

    def register_blueprint(self, blueprint: object, **options: Any) -> None:
        """Registra un blueprint en la API y en su especificación OpenAPI.

        Args:
            blueprint: Blueprint de Flask-Smorest que se incorporará a la aplicación.
            **options: Opciones de registro compatibles con Flask.
        """
        ...


def create_api(app: Flask) -> ApiProtocol:
    """Inicializa Flask-Smorest para una instancia concreta de Flask.

    Crear la extensión dentro de esta función evita compartir estado y documentos
    OpenAPI entre múltiples aplicaciones, como ocurre en pruebas o workers.

    Args:
        app: Aplicación Flask configurada que recibirá la extensión.

    Returns:
        Interfaz tipada para registrar los blueprints de la aplicación.
    """
    api = Api()
    api.ERROR_SCHEMA = ErrorSchema
    api.init_app(app)
    return cast(ApiProtocol, api)
