"""Excepciones esperadas que atraviesan las capas de la aplicación."""

from __future__ import annotations


class ApplicationError(Exception):
    """Error esperado con metadatos seguros para construir una respuesta HTTP.

    La jerarquía separa mensajes aptos para clientes de excepciones internas, que
    nunca deben exponer trazas ni detalles de infraestructura.

    Attributes:
        detail: Explicación pública del error.
        status_code: Estado HTTP asociado.
        error_code: Código breve y estable del contrato.
        error_label: Etiqueta legible asociada al código.
    """

    status_code = 500
    error_code = "IE"
    error_label = "Error Interno"

    def __init__(self, detail: str) -> None:
        """Inicializa un error controlado.

        Args:
            detail: Mensaje seguro que puede devolverse al cliente.
        """
        super().__init__(detail)
        self.detail = detail


class ContractValidationError(ApplicationError):
    """Indica que una entrada del cliente incumple el contrato de la API."""

    status_code = 400
    error_code = "VF"
    error_label = "Validación Fallida"


class DataNotReadyError(ApplicationError):
    """Indica que los artefactos analíticos todavía no están disponibles."""

    status_code = 503
    error_code = "ND"
    error_label = "Servicio No Disponible"


class StatisticsCalculationError(ApplicationError):
    """Indica que una agregación no puede expresarse con números JSON finitos."""

    status_code = 500
    error_code = "IE"
    error_label = "Error Interno"

    def __init__(self, detail: str = "No fue posible calcular estadísticas finitas") -> None:
        """Inicializa un fallo de cálculo con un mensaje público seguro.

        Args:
            detail: Explicación pública del fallo estadístico.
        """
        super().__init__(detail)


class IngestionError(Exception):
    """Indica un fallo controlado durante la preparación del dataset."""
