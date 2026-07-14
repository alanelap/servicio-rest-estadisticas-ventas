"""Esquema del formato uniforme de errores."""

from marshmallow import Schema, fields


class ErrorSchema(Schema):
    """Problem details extendido exigido por el enunciado."""

    detail = fields.String(required=True)
    instance = fields.String(required=True)
    status = fields.Integer(required=True)
    title = fields.String(required=True)
    type = fields.Url(required=True)
    timestamp = fields.String(required=True)
    errorCode = fields.String(required=True)
    errorLabel = fields.String(required=True)
    method = fields.String(required=True)
