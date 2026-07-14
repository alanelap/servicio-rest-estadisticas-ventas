"""Expone la aplicación WSGI que importa Gunicorn en producción.

La instancia se construye mediante la misma factoría utilizada por Flask CLI y
las pruebas, de modo que el cableado de extensiones y servicios sea único.
"""

from app import create_app

app = create_app()
