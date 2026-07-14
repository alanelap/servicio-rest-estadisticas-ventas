"""Adaptadores de tipos para decoradores sin anotaciones de Flask-Smorest."""

from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar, cast

_P = ParamSpec("_P")
_R = TypeVar("_R")


def typed_decorator(value: Any) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    """Conserva la firma estática que los decoradores de terceros no declaran."""

    return cast(Callable[[Callable[_P, _R]], Callable[_P, _R]], value)
