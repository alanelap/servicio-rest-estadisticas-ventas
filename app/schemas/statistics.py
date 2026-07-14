"""Describe las respuestas exitosas publicadas en el contrato OpenAPI."""

from marshmallow import Schema, fields


class StatisticsSchema(Schema):
    """Representa las siete estadísticas públicas sobre ``MONTO APLICADO``.

    Cuando una consulta no contiene filas, promedio, extremos, mediana y
    desviación estándar aceptan ``null``; suma y conteo siempre son numéricos.
    """

    suma = fields.Float(required=True)
    conteo = fields.Integer(required=True)
    promedio = fields.Float(required=True, allow_none=True)
    minimo = fields.Float(required=True, allow_none=True)
    maximo = fields.Float(required=True, allow_none=True)
    mediana = fields.Float(required=True, allow_none=True)
    desviacion_estandar = fields.Float(required=True, allow_none=True)


class StatusSchema(Schema):
    """Representa la respuesta mínima de los endpoints de estado."""

    status = fields.String(required=True)
