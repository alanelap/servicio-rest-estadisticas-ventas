"""Esquemas de documentación y validación estructural de filtros."""

from __future__ import annotations

from marshmallow import RAISE, Schema, fields, validate

from app.domain.enums import Channel, FilterName, Gender


class QueryItemSchema(Schema):
    """Elemento individual de ``consultas``."""

    class Meta:
        unknown = RAISE

    consulta = fields.String(
        required=True,
        validate=validate.OneOf([item.value for item in FilterName]),
        metadata={"description": "Nombre exacto del filtro, en mayúsculas."},
    )
    valor = fields.Raw(
        required=True,
        allow_none=False,
        metadata={"description": "Valor que será convertido al tipo del filtro."},
    )


class PostFiltersSchema(Schema):
    """Cuerpo obligatorio de POST."""

    class Meta:
        unknown = RAISE

    consultas = fields.List(
        fields.Nested(QueryItemSchema),
        required=True,
        allow_none=False,
        validate=validate.Length(min=1, max=len(FilterName)),
    )


class GetFiltersSchema(Schema):
    """Parámetros opcionales de GET usados para producir OpenAPI."""

    class Meta:
        unknown = RAISE

    genero = fields.String(
        data_key="GENERO",
        validate=validate.OneOf([item.value for item in Gender]),
        metadata={"description": "Género; el valor no distingue mayúsculas."},
    )
    edad = fields.Integer(
        data_key="EDAD",
        validate=validate.Range(min=0, max=120),
        metadata={"description": "Edad de la persona en la fecha de la venta."},
    )
    canal = fields.String(
        data_key="CANAL",
        validate=validate.OneOf([item.value for item in Channel]),
    )
    codigo_producto = fields.Integer(
        data_key="CODIGO_PRODUCTO",
        validate=validate.Range(min=1),
        metadata={"description": "Identificador SKU del producto."},
    )
    id_persona = fields.UUID(
        data_key="ID_PERSONA",
        metadata={"description": "UUID sintácticamente válido del cliente."},
    )
    local = fields.Integer(data_key="LOCAL", validate=validate.Range(min=1))
    fecha_desde = fields.String(
        data_key="FECHA_DESDE",
        metadata={"description": "Fecha o fecha-hora ISO 8601 inclusiva."},
    )
    fecha_hasta = fields.String(
        data_key="FECHA_HASTA",
        metadata={
            "description": ("Fecha o fecha-hora ISO 8601 inclusiva; una fecha abarca todo el día.")
        },
    )
