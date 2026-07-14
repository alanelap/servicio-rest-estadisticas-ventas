# Interfaz estable para que desarrollo local y CI ejecuten los mismos comandos.
PYTHON ?= python3
CSV ?= data/ventas.csv
FLASK_APP ?= app:create_app()

.PHONY: help install format lint typecheck test check ingest run docker-build docker-up docker-down

help:
	@echo "Targets disponibles:"
	@echo "  install       Instala el proyecto y sus dependencias de desarrollo"
	@echo "  format        Corrige lint autofixable y formatea el código"
	@echo "  lint          Comprueba lint y formato sin modificar archivos"
	@echo "  typecheck     Ejecuta la comprobación estática de tipos"
	@echo "  test          Ejecuta las pruebas con cobertura mínima de 85%"
	@echo "  check         Ejecuta lint, typecheck y test"
	@echo "  ingest        Procesa el CSV indicado por CSV (por defecto: $(CSV))"
	@echo "  run           Inicia el servidor de desarrollo de Flask"
	@echo "  docker-build  Construye las imágenes de Docker Compose"
	@echo "  docker-up     Construye e inicia los servicios de Docker Compose"
	@echo "  docker-down   Detiene los servicios de Docker Compose"

install:
	$(PYTHON) -m pip install -e ".[dev]"

format:
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

typecheck:
	$(PYTHON) -m mypy app

test:
	$(PYTHON) -m pytest --cov=app --cov-report=term-missing

check: lint typecheck test

ingest:
	$(PYTHON) -m flask --app '$(FLASK_APP)' ingest-data --csv "$(CSV)"

run:
	$(PYTHON) -m flask --app '$(FLASK_APP)' run --host "$${HOST:-0.0.0.0}" --port "$${PORT:-8000}"

docker-build:
	docker compose build

docker-up:
	docker compose up --build

docker-down:
	docker compose down
