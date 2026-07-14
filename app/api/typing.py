"""Adaptadores que preservan tipos al aplicar decoradores de Flask-Smorest."""

from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar, cast

_P = ParamSpec("_P")
_R = TypeVar("_R")


def typed_decorator(value: Any) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    """Conserva la firma estática que los decoradores de terceros no declaran.

    El adaptador solo informa al analizador estático: en tiempo de ejecución
    devuelve exactamente el decorador recibido.

    Args:
        value: Decorador proporcionado por una biblioteca sin tipos completos.

    Returns:
        El mismo decorador, tipado como una transformación que conserva parámetros
        y retorno de la función decorada.
    """
    return cast(Callable[[Callable[_P, _R]], Callable[_P, _R]], value)
