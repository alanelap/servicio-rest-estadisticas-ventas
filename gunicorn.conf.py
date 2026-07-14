"""Configuración de producción para Gunicorn."""

import os

bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("WORKERS", "2"))
worker_class = "sync"
threads = 1
timeout = 30
graceful_timeout = 30
keepalive = 5
preload_app = False
max_requests = 1000
max_requests_jitter = 100
# El formato predeterminado registra la query completa (incluido ID_PERSONA).
# Los eventos HTTP seguros y estructurados los emite la aplicación.
accesslog = None
errorlog = "-"
capture_output = True
loglevel = os.getenv("LOG_LEVEL", "INFO").lower()
