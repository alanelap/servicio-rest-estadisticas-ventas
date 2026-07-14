"""Modelos inmutables usados entre capas."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class SalesFilters:
    """Filtros ya validados y convertidos a tipos de dominio."""

    genero: str | None = None
    edad: int | None = None
    canal: str | None = None
    codigo_producto: int | None = None
    id_persona: str | None = None
    local: int | None = None
    fecha_desde: datetime | None = None
    fecha_hasta: datetime | None = None
    fecha_hasta_exclusiva: bool = False

    @property
    def is_empty(self) -> bool:
        """Indica si no se recibió ningún filtro público."""

        return all(
            value is None
            for value in (
                self.genero,
                self.edad,
                self.canal,
                self.codigo_producto,
                self.id_persona,
                self.local,
                self.fecha_desde,
                self.fecha_hasta,
            )
        )

    @property
    def names(self) -> list[str]:
        """Nombres no sensibles para observabilidad."""

        mapping = {
            "genero": "GENERO",
            "edad": "EDAD",
            "canal": "CANAL",
            "codigo_producto": "CODIGO_PRODUCTO",
            "id_persona": "ID_PERSONA",
            "local": "LOCAL",
            "fecha_desde": "FECHA_DESDE",
            "fecha_hasta": "FECHA_HASTA",
        }
        return [
            public for internal, public in mapping.items() if getattr(self, internal) is not None
        ]


@dataclass(frozen=True, slots=True)
class StatisticsResult:
    """Respuesta estadística exacta del contrato."""

    suma: float
    conteo: int
    promedio: float | None
    minimo: float | None
    maximo: float | None
    mediana: float | None
    desviacion_estandar: float | None

    @classmethod
    def empty(cls) -> StatisticsResult:
        """Crea la respuesta definida para un conjunto sin coincidencias."""

        return cls(0.0, 0, None, None, None, None, None)

    def to_dict(self) -> dict[str, Any]:
        """Serializa sin agregar campos internos."""

        return asdict(self)
