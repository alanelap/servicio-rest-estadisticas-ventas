# Matriz de trazabilidad de requisitos

Esta matriz se creó **antes de la implementación** a partir de `Trabajo ReST(1).md` (fuente principal) y `PROMPT_CODEX.md` (decisiones complementarias). La columna “Evidencia prevista” define desde el inicio dónde se implementará o comprobará cada requisito; al finalizar se actualizará su estado con evidencia real.

## Enunciado oficial

| ID | Requisito obligatorio | Evidencia prevista (archivo, endpoint o prueba) | Estado final |
|---|---|---|---|
| OF-01 | Procesar un CSV de gran volumen eficientemente. | `app/services/ingestion_service.py`; `app/repositories/sales_repository.py`; pruebas de ingesta | Cumplido |
| OF-02 | Aplicar procesamiento paralelo, chunking, streaming o biblioteca equivalente. | Polars `scan_csv`/`scan_parquet`, motor multihilo y sink Parquet en `ingestion_service.py`; README | Cumplido |
| OF-03 | Documentar técnicamente en Swagger o ReadTheDocs. | `/docs`, `/openapi.json`, esquemas bajo `app/schemas/` | Cumplido |
| OF-04 | Cargar datos desatendidamente al iniciar mediante CLI o script. | Comando `ingest-data`; `scripts/entrypoint.sh`; `AUTO_INGEST` | Cumplido |
| OF-05 | Implementar GET para consultar totales y métricas precomputadas. | `GET /v1/estadisticas/ventas`; pruebas `test_get_statistics.py` | Cumplido |
| OF-06 | Implementar POST para consultas dinámicas con parámetros. | `POST /v1/estadisticas/ventas`; pruebas `test_post_statistics.py` | Cumplido |
| OF-07 | Dejar los datos disponibles a GET y POST sin intervención manual. | Parquet, caché JSON, metadatos, `entrypoint.sh`, `/ready` | Cumplido |
| OF-08 | Usar estructuras eficientes para almacenamiento y acceso rápido. | Parquet columnar, LazyFrame, caché del resumen global | Cumplido |
| OF-09 | Servir ambas operaciones en la ruta base exacta `/v1/estadisticas/ventas`. | Blueprint `app/api/ventas.py`; pruebas de rutas | Cumplido |
| OF-10 | GET admite filtros opcionales predeterminados mediante query params. | Validador de filtros GET y servicio de filtros; pruebas por filtro | Cumplido |
| OF-11 | POST admite filtros personalizados opcionales según el contrato. | Esquemas Marshmallow y validador de POST | Cumplido |
| OF-12 | La respuesta exitosa contiene exactamente suma, conteo, promedio, mínimo, máximo, mediana y desviación estándar. | `StatisticsResult`; `StatisticsSchema`; pruebas unitarias e integración | Cumplido |
| OF-13 | Admitir filtros `GENERO`, `EDAD`, `CANAL`, `CODIGO_PRODUCTO`, `ID_PERSONA`, `LOCAL`, `FECHA_DESDE`, `FECHA_HASTA`. | `FilterName`; `FilterService`; OpenAPI; pruebas por cada filtro | Cumplido |
| OF-14 | `GENERO` admite No especificado, Masculino, Femenino y Otro. | Normalización de ingesta y validación; fixture con los cuatro casos | Cumplido |
| OF-15 | `EDAD` es un entero. | Conversión estricta/rango en `filter_service.py`; pruebas de error | Cumplido |
| OF-16 | `CANAL` admite POS, WEB, APP, CCT, APR y WPR. | Enum/validador, fixture con los seis canales y pruebas | Cumplido |
| OF-17 | `CODIGO_PRODUCTO` identifica el producto y se consulta sobre `SKU`. | Mapeo en repositorio; pruebas GET/POST | Cumplido |
| OF-18 | `ID_PERSONA` es el UUID que identifica al cliente. | Validación UUID y filtro sobre `codigo_cliente`; pruebas | Cumplido |
| OF-19 | `LOCAL` es el número de local. | Conversión a entero positivo y filtro; pruebas | Cumplido |
| OF-20 | Fechas desde/hasta se reciben en ISO 8601. | Utilidad de fechas; UTC−4 fijo para valores sin offset; respeto de offsets explícitos; pruebas de rango | Cumplido |
| OF-21 | Las consultas pueden combinar una cantidad arbitraria de filtros. | Composición AND en `SalesRepository`; pruebas de varios filtros | Cumplido |
| OF-22 | Todos los errores respetan exactamente la estructura JSON indicada. | Fábrica `problem_details.py`; handlers; pruebas campo por campo | Cumplido |
| OF-23 | Responder 400 si `consultas` está vacío/nulo, el filtro no existe o el valor no convierte. | Validación estricta POST y manejadores; `test_validation_errors.py` | Cumplido |
| OF-24 | Responder 500 con el mismo contrato ante errores internos. | Handler 500 centralizado y prueba controlada | Cumplido |
| OF-25 | Promedio = suma/conteo. | Agregaciones Polars y pruebas numéricas | Cumplido |
| OF-26 | Mediana = central o promedio de los dos centrales. | Agregación `median`; casos par e impar | Cumplido |
| OF-27 | Desviación estándar = raíz de la varianza. | `std(ddof=0)` poblacional; prueba numérica | Cumplido |
| OF-28 | Entregar código fuente de la API. | Árbol `app/`, `wsgi.py`, configuración del proyecto | Cumplido |
| OF-29 | Entregar README con instrucciones y ejemplos. | `README.md` en español | Cumplido |
| OF-30 | Entregar `datos.json` con datos de prueba. | `datos.json` | Cumplido |
| OF-31 | Entregar pruebas unitarias. | `tests/unit/` y `tests/integration/`; CI | Cumplido |
| OF-32 | Usar tecnología open source instalable nativamente en GNU/Linux. | Python/Flask/Polars; `pyproject.toml`, Dockerfile y README | Cumplido |
| OF-33 | Respetar las 15 columnas y tipos del CSV oficial. | Constantes y normalización en `ingestion_service.py`; fixture CSV | Cumplido |
| OF-34 | Proveer mecanismo para cargar el CSV compartido. | `DATASET_PATH`, CLI `--csv`, script de descarga opcional documentado | Cumplido |
| OF-35 | Maximizar criterios de rúbrica: endpoints 30 %, errores 20 %, estadísticas 20 %, filtros 15 %, calidad 15 %. | Suite integral, lint, tipos, cobertura y documentación | Cumplido |
| OF-36 | Entregar el repositorio GitHub agregando manualmente al académico `sebasalazar` antes del 17/07/2026 23:59:59.999999, hora continental de Chile. | Repositorio público y sincronizado; instrucción y fecha exacta en `README.md` | Parcial: repositorio publicado; invitación manual pendiente |

## Requisitos complementarios del prompt

| ID | Decisión o requisito complementario | Evidencia prevista | Estado final |
|---|---|---|---|
| PR-01 | Python + Flask, Flask-Smorest, Marshmallow, Polars/Parquet; no pandas como motor. | `pyproject.toml`; todo `app/` | Cumplido |
| PR-02 | GET sin filtros usa resumen precomputado; GET filtrado y POST usan filtros AND. | API, servicio estadístico, repositorio; pruebas | Cumplido |
| PR-03 | POST exige body JSON y una lista no vacía, sin campos extra ni filtros duplicados. | Esquemas estrictos y pruebas exhaustivas | Cumplido |
| PR-04 | Los nombres públicos de filtros son exactamente mayúsculos; no se agregan otros. | Enum y validación de query/body | Cumplido |
| PR-05 | Edad entre 0 y 120 calculada en la fecha de venta. | Expresión vectorizada de ingesta; pruebas de cumpleaños | Cumplido |
| PR-06 | Fechas inclusivas y normalizadas a `America/Santiago`. | Sustituido por CT-07 debido a la prioridad del enunciado oficial: UTC−4 fijo sin DST para timestamps sin offset | Sustituido por requisito oficial |
| PR-07 | Estadísticas calculadas sobre `MONTO APLICADO`, configurable centralmente pero no por el cliente. | `STAT_TARGET_COLUMN`; caché/metadatos; Swagger/README | Cumplido |
| PR-08 | Desviación estándar poblacional (`ddof=0`) y respuesta sin NaN/Infinity. | Servicio y pruebas | Cumplido |
| PR-09 | Sin coincidencias: HTTP 200, suma 0.0, conteo 0 y restantes métricas null. | Servicio, schemas y pruebas | Cumplido |
| PR-10 | Handlers uniformes 400/404/405/413/415/422/500 y `/ready` 503. | `app/errors/`; límite global de body; OpenAPI; pruebas | Cumplido |
| PR-11 | Ingesta valida archivo/columnas, descarta filas inválidas de modo explícito y reporta calidad. | Servicio de ingesta, metadatos y `quality_report.json` | Cumplido |
| PR-12 | Ingesta publica un snapshot coherente de Parquet y JSON, con SHA-256, `generation_id` común y lock interproceso de lectores/escritor. | Servicios y utilidades; validación de generación; pruebas de idempotencia, reproceso y corrupción | Cumplido |
| PR-13 | Proyección excluye RUN, nombres y apellidos; API y logs no exponen datos personales ni valores de filtros. | Esquema Parquet; access log de Gunicorn desactivado; logging estructurado sin query string; pruebas | Cumplido |
| PR-14 | Arquitectura modular, factory pattern, blueprints, capas, tipos y docstrings. | Árbol `app/`; Ruff/Mypy | Cumplido |
| PR-15 | `/health` solo informa proceso activo y `/ready` verifica artefactos legibles de una misma generación. | `app/api/health.py`; lock compartido; `generation_id` en Parquet/JSON; pruebas | Cumplido |
| PR-16 | Swagger interactivo en `/docs` y OpenAPI válido en `/openapi.json`, incluido el error 413. | Flask-Smorest; validación del documento y prueba manual | Cumplido |
| PR-17 | Cobertura mínima 85 % con fixture local, sin Internet. | Configuración pytest/coverage y suite | Cumplido |
| PR-18 | Seguridad: límite global de body, JSON estricto, headers, request ID, sin CORS/debug/secretos; producción fuerza debug apagado. | Config, middleware, handlers, OpenAPI y pruebas | Cumplido |
| PR-19 | Docker no root, publicación predeterminada en `127.0.0.1`, CSV de solo lectura, volumen nombrado para procesados, Gunicorn sin access log, healthcheck y autoingesta única. | Dockerfile, Compose, entrypoint, config Gunicorn y README de despliegue público con TLS/auth/rate limit | Cumplido |
| PR-20 | Ruff, format, Mypy y Pytest pasan; Makefile ofrece todos los comandos pedidos. | `pyproject.toml`, `Makefile`, CI y reporte final | Cumplido |
| PR-21 | README contiene los 34 apartados pedidos, diagramas y paso manual para colaborador `sebasalazar`. | `README.md` | Cumplido |
| PR-22 | GitHub Actions corre instalación, Ruff, formato, Mypy y cobertura en push/PR sin red de datos. | `.github/workflows/ci.yml` | Cumplido |
| PR-23 | Verificación manual de arranque, GET, POST, 400, `/docs` y `/openapi.json`. | Registro real de comandos en reporte final | Cumplido |

## Resolución documentada de contradicciones y ambigüedades

| ID | Hallazgo | Prioridad y resolución |
|---|---|---|
| CT-01 | El enunciado dice que las consultas pueden hacerse sin filtros, pero también exige 400 para `consultas` vacío o nulo. | Se preservan ambas reglas: GET admite cero filtros; POST exige al menos una consulta. Esta decisión está documentada en README/OpenAPI. |
| CT-02 | El enunciado no explicita la columna numérica a resumir. | El prompt completa el vacío: se usa `MONTO APLICADO`, centralizado en `STAT_TARGET_COLUMN`. |
| CT-03 | `CODIGO_PRODUCTO` se describe por error como identificador único de la persona. | La tabla CSV y el nombre del filtro prevalecen: se mapea a `SKU`; `ID_PERSONA` se mapea a `CODIGO CLIENTE`. |
| CT-04 | La tabla declara UUID v3, pero entrega un ejemplo de UUID de otra versión/formato general. | Se valida sintaxis UUID general y se normaliza a representación canónica, sin restringir versión. |
| CT-05 | Una sección llama opcionales a las pruebas, pero la lista final de entregables las exige. | Se consideran obligatorias por la sección final “Entregables”. |
| CT-06 | El ejemplo de timestamp contiene 9 dígitos fraccionarios, mientras Python genera microsegundos. | Se cumple ISO 8601/RFC 3339 UTC terminado en `Z`; la precisión fraccionaria puede ser de microsegundos, tal como permite el prompt. |
| CT-07 | El enunciado define fecha de venta ISO 8601 UTC-4 y el prompt exige `America/Santiago`. | Prevalece el enunciado: los timestamps sin offset se interpretan en UTC−4 fijo, sin DST. Los timestamps con offset explícito respetan ese offset antes de normalizarse. La regla IANA del prompt queda sustituida y la contradicción se documenta en README. |
| CT-08 | La tabla oficial solo enumera género 1/2, pero el contrato también exige “Otro” y “No especificado”. | Se aplica el mapeo complementario: 1 Masculino, 2 Femenino, otros no cero Otro, 0/nulo/vacío No especificado. |
| CT-09 | El contexto menciona procesamiento paralelo y distribuido, mientras Polars ofrece paralelismo local. | Se implementa el requisito técnico explícito de procesamiento paralelo con Polars y se documenta el límite: no es un clúster distribuido; el repositorio desacoplado permite migrar a Dask/Spark. |
| CT-10 | El CSV oficial descargado usa delimitador `;` y la cabecera `GENERO`, aunque el enunciado muestra `GÉNERO`. | La ingesta detecta coma/punto y coma y normaliza `GENERO` a `GÉNERO`; existe una prueba específica sin alterar el archivo oficial. |

## Criterio de cierre

Los estados describen la cobertura implementada de cada requisito. Las comprobaciones siguientes se ejecutaron sobre la versión entregable. El repositorio ya está publicado y sincronizado; solo queda pendiente la acción externa de agregar manualmente al profesor como colaborador.

## Evidencia de cierre

| Comprobación ejecutada sobre la versión entregable | Resultado |
|---|---|
| `flask --app "app:create_app()" ingest-data --csv tests/fixtures/ventas.csv` | Aprobado: 12 válidas, 0 descartadas |
| `ruff check .` | Aprobado: sin hallazgos |
| `ruff format --check .` | Aprobado: 50 archivos formateados |
| `mypy app` | Aprobado: 35 archivos, sin hallazgos |
| `pytest --cov=app --cov-report=term-missing` | Aprobado: 172 pruebas, cobertura 91,74 % (mínimo 85 %) |
| Servidor real + curl de GET, POST, errores, OpenAPI y Swagger | Aprobado: GET/POST 200, error contractual 400, `/docs` 200 y `/openapi.json` 200 |
| `docker compose config --quiet` y `docker compose build` | Aprobado con imagen Python 3.12 |
| `docker compose up --detach`, healthcheck y consultas | Aprobado: contenedor healthy, `/health` y `/ready` 200, UID/GID 10001, publicación `127.0.0.1:8000` |
