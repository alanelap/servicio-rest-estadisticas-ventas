"""Objetos de valor inmutables compartidos por las capas de la aplicación."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class SalesFilters:
    """Agrupa filtros validados y convertidos a tipos de dominio.

    La inmutabilidad permite compartir una consulta entre servicios sin que una
    capa altere accidentalmente sus condiciones. ``fecha_hasta_exclusiva`` solo
    describe cómo interpretar ``fecha_hasta`` y no constituye un filtro público.

    Attributes:
        genero: Género normalizado o ausencia de filtro.
        edad: Edad exacta en la fecha de la transacción.
        canal: Código normalizado del canal de venta.
        codigo_producto: Identificador SKU exacto.
        id_persona: UUID canónico de la persona.
        local: Identificador exacto del establecimiento.
        fecha_desde: Límite temporal inferior inclusivo.
        fecha_hasta: Límite temporal superior.
        fecha_hasta_exclusiva: Si el límite superior se compara de forma exclusiva.
    """

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
        """Indica si no se recibió ningún filtro público.

        Returns:
            ``True`` cuando todos los filtros del contrato están ausentes.
        """
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
        """Obtiene solo los nombres públicos de los filtros activos.

        Los valores se excluyen deliberadamente para evitar que UUID u otros datos
        del cliente terminen en logs y métricas.

        Returns:
            Nombres canónicos de los filtros presentes, en orden estable.
        """
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
    """Representa la respuesta estadística exacta del contrato público.

    Para un conjunto vacío, solo suma y conteo tienen identidad numérica; las
    estadísticas restantes se expresan como ``None`` y se serializan como JSON
    ``null``.

    Attributes:
        suma: Suma de los montos coincidentes.
        conteo: Cantidad de ventas coincidentes.
        promedio: Media aritmética, si existe al menos un monto.
        minimo: Menor monto, si existe al menos un monto.
        maximo: Mayor monto, si existe al menos un monto.
        mediana: Mediana de los montos, si existe al menos un monto.
        desviacion_estandar: Desviación estándar poblacional de los montos.
    """

    suma: float
    conteo: int
    promedio: float | None
    minimo: float | None
    maximo: float | None
    mediana: float | None
    desviacion_estandar: float | None

    @classmethod
    def empty(cls) -> StatisticsResult:
        """Crea la respuesta definida para un conjunto sin coincidencias.

        Returns:
            Un resultado con suma y conteo en cero y agregados indefinidos en
            ``None``.
        """
        return cls(0.0, 0, None, None, None, None, None)

    def to_dict(self) -> dict[str, Any]:
        """Convierte el resultado al objeto exacto expuesto como JSON.

        Returns:
            Diccionario con los siete campos públicos y sus valores nativos.
        """
        return asdict(self)
