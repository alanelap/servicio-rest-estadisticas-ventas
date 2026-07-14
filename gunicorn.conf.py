"""Parámetros de ejecución segura y predecible para Gunicorn.

El servidor usa procesos síncronos sin precarga para que cada worker construya
su propia aplicación. El access log predeterminado se desactiva porque puede
incluir consultas con identificadores personales; Flask emite eventos HTTP JSON
con campos controlados y redacción por patrones desde sus hooks de observabilidad.
"""

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
accesslog = None
errorlog = "-"
capture_output = True
loglevel = os.getenv("LOG_LEVEL", "INFO").lower()
