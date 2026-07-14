"""Excepciones de dominio que pueden exponerse de forma controlada."""

from __future__ import annotations


class ApplicationError(Exception):
    """Error esperado con metadatos HTTP seguros."""

    status_code = 500
    error_code = "IE"
    error_label = "Error Interno"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ContractValidationError(ApplicationError):
    """Entrada que incumple el contrato de la API."""

    status_code = 400
    error_code = "VF"
    error_label = "Validación Fallida"


class DataNotReadyError(ApplicationError):
    """Los artefactos analíticos aún no están disponibles."""

    status_code = 503
    error_code = "ND"
    error_label = "Servicio No Disponible"


class StatisticsCalculationError(ApplicationError):
    """Una agregación no puede representarse con números JSON finitos."""

    status_code = 500
    error_code = "IE"
    error_label = "Error Interno"

    def __init__(self, detail: str = "No fue posible calcular estadísticas finitas") -> None:
        super().__init__(detail)


class IngestionError(Exception):
    """Fallo controlado durante la preparación del dataset."""
