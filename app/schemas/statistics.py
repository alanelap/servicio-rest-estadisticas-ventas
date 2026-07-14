"""Esquemas de respuestas exitosas."""

from marshmallow import Schema, fields


class StatisticsSchema(Schema):
    """Siete estadísticas públicas sobre MONTO APLICADO."""

    suma = fields.Float(required=True)
    conteo = fields.Integer(required=True)
    promedio = fields.Float(required=True, allow_none=True)
    minimo = fields.Float(required=True, allow_none=True)
    maximo = fields.Float(required=True, allow_none=True)
    mediana = fields.Float(required=True, allow_none=True)
    desviacion_estandar = fields.Float(required=True, allow_none=True)


class StatusSchema(Schema):
    """Respuesta mínima de salud/preparación."""

    status = fields.String(required=True)
