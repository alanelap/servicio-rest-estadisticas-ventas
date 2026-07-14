# syntax=docker/dockerfile:1
# La etapa de construcción genera un wheel reproducible sin trasladar herramientas
# de desarrollo a la imagen final.
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build

COPY pyproject.toml README.md ./
COPY app ./app
RUN python -m pip wheel --wheel-dir /wheels .

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    FLASK_DEBUG=0

# UID/GID estable permite asignar permisos al volumen sin ejecutar como root.
RUN apt-get update \
    && apt-get install --no-install-recommends --yes tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app app

WORKDIR /app
COPY --from=builder /wheels /wheels
RUN python -m pip install /wheels/* && rm -rf /wheels

COPY --chown=app:app app ./app
COPY --chown=app:app scripts ./scripts
COPY --chown=app:app wsgi.py gunicorn.conf.py ./
RUN mkdir -p data/processed && chown -R app:app /app

USER app
EXPOSE 8000

# El healthcheck comprueba liveness; /ready queda reservado para validar el snapshot.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD ["python", "-c", "import os, urllib.request; port=os.getenv('PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=3).read()"]

ENTRYPOINT ["./scripts/entrypoint.sh"]
