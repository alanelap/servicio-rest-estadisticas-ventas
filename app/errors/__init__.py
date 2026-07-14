"""Expone la construcción y el registro del contrato uniforme de errores HTTP."""

from app.errors.handlers import register_error_handlers
from app.errors.problem_details import build_problem

__all__ = ["build_problem", "register_error_handlers"]
