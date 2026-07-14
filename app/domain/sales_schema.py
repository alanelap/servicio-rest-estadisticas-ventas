"""Define el esquema físico canónico de los artefactos analíticos Parquet.

``ANALYTIC_COLUMNS`` fija la proyección y el orden que publica la ingesta;
``ANALYTIC_SCHEMA`` valida el esquema físico del Parquet antes de aceptar un
snapshot para consultas.
"""

from typing import Final

import polars as pl
from polars.datatypes import DataType, DataTypeClass

_ANALYTIC_DTYPES: Final[dict[str, DataType | DataTypeClass]] = {
    # Todas las fechas se comparan en UTC y con precisión de microsegundos.
    "fecha": pl.Datetime(time_unit="us", time_zone="UTC"),
    "canal": pl.String,
    "sku": pl.Int64,
    "monto_aplicado": pl.Float64,
    "local": pl.Int64,
    "codigo_cliente": pl.String,
    "genero_texto": pl.String,
    "edad_en_transaccion": pl.Int16,
}
# El orden también es parte del contrato interno: permite seleccionar y validar
# artefactos sin depender del orden observado en el CSV de origen.
ANALYTIC_SCHEMA: Final = pl.Schema(_ANALYTIC_DTYPES)
ANALYTIC_COLUMNS: Final = tuple(ANALYTIC_SCHEMA.names())
