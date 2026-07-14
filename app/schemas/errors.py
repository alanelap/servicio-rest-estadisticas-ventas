"""Describe para OpenAPI el formato uniforme de las respuestas de error."""

from marshmallow import Schema, fields


class ErrorSchema(Schema):
    """Representa el problem details extendido exigido por el contrato.

    Todos los campos son obligatorios para que errores de dominio, de protocolo y
    fallos inesperados mantengan una forma predecible para los consumidores.
    """

    detail = fields.String(required=True)
    instance = fields.String(required=True)
    status = fields.Integer(required=True)
    title = fields.String(required=True)
    type = fields.Url(required=True)
    timestamp = fields.String(required=True)
    errorCode = fields.String(required=True)
    errorLabel = fields.String(required=True)
    method = fields.String(required=True)
