"""Entidades y reglas de dominio."""

from app.domain.enums import Channel, FilterName, Gender
from app.domain.exceptions import (
    ApplicationError,
    ContractValidationError,
    DataNotReadyError,
    IngestionError,
    StatisticsCalculationError,
)
from app.domain.models import SalesFilters, StatisticsResult
from app.domain.sales_schema import ANALYTIC_COLUMNS, ANALYTIC_SCHEMA

__all__ = [
    "ApplicationError",
    "ANALYTIC_COLUMNS",
    "ANALYTIC_SCHEMA",
    "Channel",
    "ContractValidationError",
    "DataNotReadyError",
    "FilterName",
    "Gender",
    "IngestionError",
    "SalesFilters",
    "StatisticsResult",
    "StatisticsCalculationError",
]
