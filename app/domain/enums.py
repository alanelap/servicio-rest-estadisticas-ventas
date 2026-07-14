"""Valores enumerados que forman parte del contrato público de filtros."""

from enum import StrEnum


class FilterName(StrEnum):
    """Nombres canónicos de los filtros admitidos por la API.

    Sus valores preservan mayúsculas y guiones bajos porque se comparan con las
    claves recibidas en el contrato HTTP.
    """

    GENERO = "GENERO"
    EDAD = "EDAD"
    CANAL = "CANAL"
    CODIGO_PRODUCTO = "CODIGO_PRODUCTO"
    ID_PERSONA = "ID_PERSONA"
    LOCAL = "LOCAL"
    FECHA_DESDE = "FECHA_DESDE"
    FECHA_HASTA = "FECHA_HASTA"


class Gender(StrEnum):
    """Valores de género normalizados que la API expone al cliente."""

    UNSPECIFIED = "No especificado"
    MALE = "Masculino"
    FEMALE = "Femenino"
    OTHER = "Otro"


class Channel(StrEnum):
    """Códigos de canal de venta aceptados por los filtros públicos."""

    POS = "POS"
    WEB = "WEB"
    APP = "APP"
    CCT = "CCT"
    APR = "APR"
    WPR = "WPR"
