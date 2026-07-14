"""Publica los esquemas Marshmallow usados por validación y OpenAPI."""

from app.schemas.errors import ErrorSchema
from app.schemas.filters import GetFiltersSchema, PostFiltersSchema, QueryItemSchema
from app.schemas.statistics import StatisticsSchema, StatusSchema

__all__ = [
    "ErrorSchema",
    "GetFiltersSchema",
    "PostFiltersSchema",
    "QueryItemSchema",
    "StatisticsSchema",
    "StatusSchema",
]
