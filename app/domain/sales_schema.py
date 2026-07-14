"""Esquema físico único del Parquet analítico."""

from typing import Final

import polars as pl
from polars.datatypes import DataType, DataTypeClass

_ANALYTIC_DTYPES: Final[dict[str, DataType | DataTypeClass]] = {
    "fecha": pl.Datetime(time_unit="us", time_zone="UTC"),
    "canal": pl.String,
    "sku": pl.Int64,
    "monto_aplicado": pl.Float64,
    "local": pl.Int64,
    "codigo_cliente": pl.String,
    "genero_texto": pl.String,
    "edad_en_transaccion": pl.Int16,
}
ANALYTIC_SCHEMA: Final = pl.Schema(_ANALYTIC_DTYPES)
ANALYTIC_COLUMNS: Final = tuple(ANALYTIC_SCHEMA.names())
