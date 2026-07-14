"""Endpoints mínimos de liveness y readiness."""

from __future__ import annotations

from typing import cast

from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint

from app.api.typing import typed_decorator
from app.domain.exceptions import DataNotReadyError
from app.repositories.sales_repository import SalesRepository
from app.schemas.errors import ErrorSchema
from app.schemas.statistics import StatusSchema

blp = Blueprint("health", __name__, description="Estado del proceso y sus datos.")


@blp.route("/health")
class HealthView(MethodView):
    @typed_decorator(blp.doc(tags=["estado"], summary="Verificar que el proceso está activo"))
    @typed_decorator(blp.response(200, StatusSchema))
    @typed_decorator(
        blp.alt_response(
            413, schema=ErrorSchema, description="Cuerpo de solicitud demasiado grande"
        )
    )
    def get(self) -> dict[str, str]:
        return {"status": "ok"}


@blp.route("/ready")
class ReadinessView(MethodView):
    @typed_decorator(blp.doc(tags=["estado"], summary="Verificar los artefactos analíticos"))
    @typed_decorator(blp.response(200, StatusSchema))
    @typed_decorator(
        blp.alt_response(
            413, schema=ErrorSchema, description="Cuerpo de solicitud demasiado grande"
        )
    )
    @typed_decorator(blp.alt_response(503, schema=ErrorSchema, description="Datos no preparados"))
    def get(self) -> dict[str, str]:
        repository = cast(SalesRepository, current_app.extensions["sales_repository"])
        ready, _reason = repository.readiness()
        if not ready:
            raise DataNotReadyError("Los datos estadísticos aún no están preparados")
        return {"status": "ready"}
