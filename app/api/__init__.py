"""Blueprints HTTP."""

from app.api.health import blp as health_blueprint
from app.api.ventas import blp as sales_blueprint

__all__ = ["health_blueprint", "sales_blueprint"]
