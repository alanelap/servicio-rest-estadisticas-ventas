"""Enumeraciones del contrato público."""

from enum import StrEnum


class FilterName(StrEnum):
    """Filtros admitidos exactamente por la API."""

    GENERO = "GENERO"
    EDAD = "EDAD"
    CANAL = "CANAL"
    CODIGO_PRODUCTO = "CODIGO_PRODUCTO"
    ID_PERSONA = "ID_PERSONA"
    LOCAL = "LOCAL"
    FECHA_DESDE = "FECHA_DESDE"
    FECHA_HASTA = "FECHA_HASTA"


class Gender(StrEnum):
    """Valores públicos normalizados de género."""

    UNSPECIFIED = "No especificado"
    MALE = "Masculino"
    FEMALE = "Femenino"
    OTHER = "Otro"


class Channel(StrEnum):
    """Canales de venta válidos."""

    POS = "POS"
    WEB = "WEB"
    APP = "APP"
    CCT = "CCT"
    APR = "APR"
    WPR = "WPR"
