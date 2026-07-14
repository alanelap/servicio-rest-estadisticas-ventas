#!/bin/sh
# Prepara exactamente una generación analítica antes de entregar el proceso a
# Gunicorn. El modo estricto evita continuar con variables o comandos fallidos.
set -eu

DATASET_PATH="${DATASET_PATH:-data/ventas.csv}"
PROCESSED_DATA_PATH="${PROCESSED_DATA_PATH:-data/processed/ventas.parquet}"
SUMMARY_CACHE_PATH="${SUMMARY_CACHE_PATH:-data/processed/statistics.json}"
METADATA_PATH="${METADATA_PATH:-data/processed/metadata.json}"
QUALITY_REPORT_PATH="${QUALITY_REPORT_PATH:-data/processed/quality_report.json}"
AUTO_INGEST="${AUTO_INGEST:-true}"

# AUTO_INGEST acepta las mismas variantes booleanas que la configuración Python.
# Si está desactivado, se exige un snapshot completo para evitar servir un estado
# parcialmente inicializado.
case "$(printf '%s' "$AUTO_INGEST" | tr '[:upper:]' '[:lower:]')" in
  1|true|yes|on|si|sí)
    if [ ! -r "$DATASET_PATH" ]; then
      echo "Error: no existe o no se puede leer el dataset configurado: $DATASET_PATH" >&2
      exit 1
    fi
    python -m flask --app 'app:create_app()' ingest-data --csv "$DATASET_PATH"
    ;;
  *)
    if [ ! -r "$PROCESSED_DATA_PATH" ] || [ ! -r "$SUMMARY_CACHE_PATH" ] || [ ! -r "$METADATA_PATH" ] || [ ! -r "$QUALITY_REPORT_PATH" ]; then
      echo "Error: AUTO_INGEST está desactivado y faltan artefactos procesados" >&2
      exit 1
    fi
    ;;
esac

# exec convierte a Gunicorn en el proceso principal para preservar señales de
# terminación y permitir un apagado ordenado del contenedor.
exec gunicorn --config gunicorn.conf.py wsgi:app
