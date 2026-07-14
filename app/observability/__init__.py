"""API pública de observabilidad estructurada y segura del servicio."""

from app.observability.logging import configure_logging, register_request_hooks

__all__ = ["configure_logging", "register_request_hooks"]
