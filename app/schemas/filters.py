"""Define la estructura pública de filtros para documentación y validación."""

from __future__ import annotations

from marshmallow import RAISE, Schema, fields, validate

from app.domain.enums import Channel, FilterName, Gender


class QueryItemSchema(Schema):
    """Representa un par nombre-valor dentro de la colección ``consultas``.

    El esquema valida la forma y el nombre del filtro; la conversión semántica de
    ``valor`` corresponde al servicio de filtros porque depende de ``consulta``.
    """

    class Meta:
        """Rechaza propiedades ajenas al contrato en cada elemento."""

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
    """Representa el cuerpo obligatorio para consultar filtros mediante POST.

    Se admite como máximo un elemento por filtro definido. La detección explícita
    de duplicados se realiza en el servicio, donde puede producirse un mensaje de
    validación contextual.
    """

    class Meta:
        """Rechaza propiedades desconocidas en el objeto raíz."""

        unknown = RAISE

    consultas = fields.List(
        fields.Nested(QueryItemSchema),
        required=True,
        allow_none=False,
        validate=validate.Length(min=1, max=len(FilterName)),
    )


class GetFiltersSchema(Schema):
    """Describe los parámetros opcionales aceptados por una consulta GET.

    Los ``data_key`` conservan los nombres en mayúsculas del contrato externo,
    mientras los atributos Python permanecen en ``snake_case``. La normalización
    completa de mayúsculas, UUID y límites temporales se delega al servicio.
    """

    class Meta:
        """Impide aceptar silenciosamente parámetros fuera del contrato."""

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
