Actúa como un ingeniero de software senior especializado en Python, Flask, diseño de APIs REST, procesamiento eficiente de grandes volúmenes de datos, arquitectura limpia, testing automatizado y documentación técnica.

Tu tarea es IMPLEMENTAR COMPLETAMENTE DESDE CERO un proyecto académico llamado:

“Servicio REST de Resumen Estadístico de Ventas — Cruz Morada”

No te limites a planificar ni a explicar qué harías. Debes crear todos los archivos, escribir el código funcional, configurar el proyecto, ejecutar las pruebas, corregir los errores encontrados y dejar la aplicación lista para ejecutarse y entregarse.

======================================================================
1. OBJETIVO GENERAL
======================================================================

Construir una API REST en Python con Flask que procese un archivo CSV de gran volumen con información de ventas de una cadena de farmacias chilena.

La API debe:

- Procesar eficientemente archivos CSV grandes.
- Evitar cargar innecesariamente todo el CSV con pandas.
- Utilizar procesamiento multihilo, paralelo, por bloques o streaming.
- Preprocesar automáticamente los datos antes de atender solicitudes.
- Calcular estadísticas de ventas.
- Permitir consultas sin filtros y con filtros dinámicos.
- Generar documentación OpenAPI/Swagger.
- Entregar errores con un formato JSON obligatorio.
- Incluir pruebas unitarias y de integración.
- Poder ejecutarse nativamente en GNU/Linux.
- Mantener una arquitectura modular, limpia, testeable y documentada.

Implementa la solución utilizando preferentemente:

- Python 3.12 o una versión estable compatible.
- Flask.
- Flask-Smorest o una alternativa estable para OpenAPI/Swagger.
- Marshmallow para validación y serialización.
- Polars LazyFrame para lectura paralela, streaming, filtros y agregaciones.
- PyArrow/Parquet para persistir datos normalizados.
- Pytest para pruebas.
- Ruff para linting y formateo.
- Mypy para comprobación estática de tipos.

No uses pandas como motor principal de procesamiento.

======================================================================
2. ENDPOINT PRINCIPAL OBLIGATORIO
======================================================================

La ruta base obligatoria es:

/v1/estadisticas/ventas

Debe aceptar:

1. GET /v1/estadisticas/ventas

Comportamiento:

- Sin query parameters: devolver las estadísticas globales precomputadas.
- Con query parameters: aplicar los filtros recibidos y calcular las estadísticas correspondientes.
- Todos los filtros deben combinarse mediante AND.
- No se debe modificar el estado del sistema.
- Debe devolver Content-Type application/json.

Ejemplo:

GET /v1/estadisticas/ventas?GENERO=Femenino&CANAL=POS&LOCAL=1999

2. POST /v1/estadisticas/ventas

Debe recibir un body JSON como:

{
  "consultas": [
    {
      "consulta": "GENERO",
      "valor": "Femenino"
    },
    {
      "consulta": "EDAD",
      "valor": "31"
    },
    {
      "consulta": "CANAL",
      "valor": "POS"
    }
  ]
}

Reglas del POST:

- El body debe existir.
- “consultas” debe existir.
- “consultas” no puede ser null.
- “consultas” debe ser un arreglo.
- “consultas” no puede estar vacío.
- Cada elemento debe incluir exactamente los campos requeridos:
  - consulta
  - valor
- Se pueden enviar uno o varios filtros.
- Los filtros se combinan mediante AND.
- Se deben rechazar filtros desconocidos.
- Se deben rechazar filtros duplicados para evitar ambigüedad.
- El valor debe validarse y convertirse al tipo correspondiente.
- No aceptar propiedades desconocidas silenciosamente.

Debido a una aparente contradicción del enunciado, adopta y documenta esta decisión:

- GET puede ejecutarse sin filtros.
- POST requiere al menos una consulta, porque el apartado de validaciones indica que “consultas vacío o nulo” debe producir un error 400.

======================================================================
3. FILTROS SOPORTADOS
======================================================================

Los nombres deben reconocerse exactamente en mayúsculas:

- GENERO
- EDAD
- CANAL
- CODIGO_PRODUCTO
- ID_PERSONA
- LOCAL
- FECHA_DESDE
- FECHA_HASTA

No agregar otros filtros al contrato público obligatorio.

3.1. GENERO

Valores permitidos:

- No especificado
- Masculino
- Femenino
- Otro

La columna CSV “GÉNERO” utiliza valores numéricos. Normalizar de la siguiente manera:

- 1: Masculino
- 2: Femenino
- 3 u otros valores conocidos distintos de 0: Otro
- 0, null, vacío o dato no informado: No especificado

La validación textual debe ser sensible al contrato indicado, pero puede normalizar espacios externos. Documentar el comportamiento respecto de mayúsculas y minúsculas. Preferentemente aceptar los valores sin distinguir mayúsculas/minúsculas y devolver mensajes claros.

3.2. EDAD

- Debe ser un entero.
- No aceptar booleanos como enteros.
- No aceptar decimales.
- Rango permitido: 0 a 120.
- Calcular la edad usando “FECHA NACIMIENTO”.
- Para que el resultado sea determinista en ventas históricas, calcular la edad que tenía la persona en la fecha de la transacción, usando la columna “FECHA”.
- Documentar expresamente esta decisión.

3.3. CANAL

Valores permitidos:

- POS
- WEB
- APP
- CCT
- APR
- WPR

Normalizar espacios y mayúsculas antes de validar.

3.4. CODIGO_PRODUCTO

Corresponde a la columna CSV:

SKU

- Debe ser un entero positivo.
- No aceptar booleanos, decimales ni strings no convertibles.

3.5. ID_PERSONA

Corresponde a la columna CSV:

CODIGO CLIENTE

- Debe ser un UUID válido.
- Conservar su representación canónica.
- El enunciado menciona UUID v3, pero el ejemplo presentado tiene formato UUID general. Valida que sea un UUID sintácticamente correcto sin rechazar innecesariamente otras versiones.
- Documentar esta decisión.

3.6. LOCAL

Corresponde a la columna CSV:

LOCAL

- Debe ser un entero positivo.
- Producir un error de validación claro cuando el dato no sea convertible.

3.7. FECHA_DESDE y FECHA_HASTA

- Deben aceptar fechas y fechas-hora ISO 8601.
- Comparar contra la columna FECHA.
- FECHA_DESDE es inclusiva.
- FECHA_HASTA es inclusiva.
- Si ambas están presentes, FECHA_DESDE no puede ser posterior a FECHA_HASTA.
- Las fechas del negocio deben tratarse en la zona horaria America/Santiago.
- Normalizar internamente de forma consistente.
- Documentar claramente el tratamiento de zona horaria.

======================================================================
4. ESTRUCTURA DEL CSV
======================================================================

El CSV contiene estas columnas:

- FECHA: String ISO 8601, ejemplo 2026-05-08T00:02:53
- CANAL: String
- SKU: Integer
- PRODUCTO: String
- UNIDADES: Integer
- PORCENTAJE DESCUENTO: Float entre 0 y 1
- MONTO APLICADO: Float en CLP
- BOLETA: Integer
- LOCAL: Integer
- CODIGO CLIENTE: UUID
- RUN CLIENTE: String
- NOMBRES: String
- APELLIDOS: String
- FECHA NACIMIENTO: String AAAA-MM-DD
- GÉNERO: Integer

El archivo original puede obtenerse desde:

https://drive.google.com/file/d/15jLBlJ9eMQSoHsoCMnFWBGopr98FIHlK/view?usp=sharing

No hagas que las pruebas dependan de Internet.

Implementa la aplicación para recibir la ubicación del CSV mediante:

DATASET_PATH

Valor de desarrollo sugerido:

data/ventas.csv

También admite una variable:

PROCESSED_DATA_PATH

Valor sugerido:

data/processed/ventas.parquet

======================================================================
5. COLUMNA SOBRE LA QUE SE CALCULAN LAS ESTADÍSTICAS
======================================================================

El enunciado no declara de manera totalmente explícita cuál columna numérica debe resumirse.

Adopta la siguiente decisión técnica:

- Calcular las estadísticas sobre “MONTO APLICADO”.
- Definir esta columna mediante una configuración centralizada:
  STAT_TARGET_COLUMN
- Usar “MONTO APLICADO” como valor predeterminado.
- Documentar esta decisión en el README y en Swagger.
- No permitir que el cliente elija arbitrariamente otra columna desde la API, para evitar alterar el contrato y reducir riesgos.

======================================================================
6. RESPUESTA EXITOSA
======================================================================

Toda consulta exitosa debe responder exactamente con esta estructura:

{
  "suma": 1500.5,
  "conteo": 42,
  "promedio": 35.73,
  "minimo": 10.0,
  "maximo": 100.0,
  "mediana": 30.0,
  "desviacion_estandar": 25.4
}

Reglas:

- suma: suma de MONTO APLICADO.
- conteo: cantidad de filas que cumplen los filtros.
- promedio: suma / conteo.
- minimo: valor mínimo.
- maximo: valor máximo.
- mediana:
  - Si el conteo es impar, valor central.
  - Si es par, promedio de los dos valores centrales.
- desviacion_estandar:
  - Usar desviación estándar poblacional.
  - Usar ddof=0.
  - Documentar esta decisión.

Tipos:

- conteo debe ser integer.
- El resto debe serializarse como number o null.
- No devolver NaN ni Infinity porque no son JSON válido.

Cuando ningún registro cumple los filtros, responder HTTP 200 con:

{
  "suma": 0.0,
  "conteo": 0,
  "promedio": null,
  "minimo": null,
  "maximo": null,
  "mediana": null,
  "desviacion_estandar": null
}

Documentar esta decisión.

======================================================================
7. FORMATO OBLIGATORIO DE ERRORES
======================================================================

Todas las respuestas de error controladas deben utilizar esta estructura:

{
  "detail": "Descripción detallada del error",
  "instance": "/v1/estadisticas/ventas",
  "status": 400,
  "title": "Bad Request",
  "type": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/400",
  "timestamp": "2026-06-30T20:44:49.201437Z",
  "errorCode": "VF",
  "errorLabel": "Validación Fallida",
  "method": "POST"
}

Requisitos:

- detail: mensaje específico y útil en español.
- instance: ruta real solicitada.
- status: código HTTP.
- title: nombre estándar del estado HTTP.
- type: enlace MDN correspondiente.
- timestamp: fecha y hora UTC en formato ISO 8601/RFC 3339 terminada en Z.
- errorCode: código interno.
- errorLabel: etiqueta interna.
- method: método HTTP real.

Para HTTP 400 usar:

- errorCode: VF
- errorLabel: Validación Fallida

Para HTTP 500 usar:

- errorCode: IE
- errorLabel: Error Interno

Ejemplo de validación:

{
  "detail": "El valor 'qwerqwer' no es un número entero válido para el ID de tienda",
  "instance": "/v1/estadisticas/ventas",
  "status": 400,
  "title": "Bad Request",
  "type": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/400",
  "timestamp": "2026-06-30T20:44:49.201437Z",
  "errorCode": "VF",
  "errorLabel": "Validación Fallida",
  "method": "POST"
}

Ejemplo de error interno:

{
  "detail": "Error al calcular la desviación estándar",
  "instance": "/v1/estadisticas/ventas",
  "status": 500,
  "title": "Internal Server Error",
  "type": "https://developer.mozilla.org/es/docs/Web/HTTP/Reference/Status/500",
  "timestamp": "2026-06-30T20:44:49.201437Z",
  "errorCode": "IE",
  "errorLabel": "Error Interno",
  "method": "GET"
}

Crea una única fábrica centralizada de errores.

Implementa manejadores para:

- 400
- 404
- 405
- 415
- 422, si alguna biblioteca intenta producirlo
- 500

Las validaciones del contrato deben responder 400 y no 422.

No expongas:

- Stack traces.
- Rutas internas.
- Contenido completo de excepciones inesperadas.
- Información sensible del servidor.

Registra internamente la excepción completa con un identificador de correlación.

Para errores adicionales puedes utilizar códigos coherentes, por ejemplo:

- RN: Recurso No Encontrado
- MN: Método No Permitido
- TM: Tipo de Medio No Soportado

Mantén siempre la misma estructura JSON.

======================================================================
8. CARGA AUTOMÁTICA Y PROCESAMIENTO DE DATOS
======================================================================

La aplicación debe garantizar que los datos estén disponibles sin intervención manual durante las consultas.

Implementa:

1. Un comando CLI de Flask:

flask --app "app:create_app()" ingest-data --csv data/ventas.csv

Debe:

- Validar que el archivo exista.
- Validar que sea legible.
- Validar las columnas obligatorias.
- Leer mediante Polars con escaneo perezoso.
- Usar procesamiento multihilo y streaming cuando la versión instalada lo permita.
- Normalizar los nombres y tipos.
- Detectar filas inválidas.
- Aplicar una política explícita para valores inválidos.
- Guardar los datos normalizados como Parquet.
- Precalcular las estadísticas globales.
- Guardar las estadísticas en un archivo JSON de caché.
- Guardar metadatos:
  - tamaño del archivo
  - fecha de modificación
  - cantidad de filas válidas
  - cantidad de filas descartadas
  - huella SHA-256 del archivo de origen
  - fecha del procesamiento
  - columna estadística utilizada

2. Un script de inicio:

scripts/entrypoint.sh

Debe:

- Comprobar si existe el Parquet procesado.
- Comprobar si existe el resumen precomputado.
- Comprobar si el CSV cambió mediante metadatos o SHA-256.
- Ejecutar la ingesta cuando sea necesario.
- Iniciar Gunicorn.
- Detenerse con un mensaje claro si no existe el dataset requerido.

3. Variables de entorno:

- APP_ENV
- FLASK_DEBUG
- HOST
- PORT
- WORKERS
- LOG_LEVEL
- DATASET_PATH
- PROCESSED_DATA_PATH
- SUMMARY_CACHE_PATH
- STAT_TARGET_COLUMN
- AUTO_INGEST
- MAX_REQUEST_BODY_BYTES
- POLARS_MAX_THREADS, cuando corresponda

4. Comportamiento de desarrollo:

- Debe existir una forma sencilla de ejecutar la ingesta manualmente.
- Debe existir una opción AUTO_INGEST=true.
- No realizar una ingesta costosa en cada worker de Gunicorn.
- Evitar condiciones de carrera usando un lock de archivo durante la ingesta.
- Aplicar escritura atómica para Parquet, metadatos y caché.

======================================================================
9. PROCESAMIENTO PARALELO Y EFICIENCIA
======================================================================

Usa Polars como motor analítico.

Requisitos:

- Usar scan_csv o un mecanismo lazy equivalente.
- Aplicar filtros antes de materializar resultados.
- Ejecutar agregaciones desde expresiones Polars.
- Evitar convertir la tabla completa en listas de Python.
- Evitar bucles fila por fila.
- Usar Parquet como representación normalizada para consultas posteriores.
- Utilizar scan_parquet para consultas filtradas.
- Aprovechar predicate pushdown y projection pushdown.
- Seleccionar únicamente las columnas necesarias.
- No cargar nombres, apellidos o RUN cuando no son necesarios para las estadísticas.
- Documentar cómo la solución utiliza paralelismo, ejecución vectorizada, streaming y almacenamiento columnar.
- Medir y registrar el tiempo de ingesta.
- Medir el tiempo de cada consulta sin registrar datos personales.
- Mantener la capa de datos desacoplada para permitir reemplazar Polars por Dask o Spark en el futuro.

Las consultas deben ser seguras frente a solicitudes simultáneas.

======================================================================
10. NORMALIZACIÓN DE DATOS
======================================================================

Implementa una capa de normalización clara.

Columnas internas sugeridas:

- fecha
- canal
- sku
- producto
- unidades
- porcentaje_descuento
- monto_aplicado
- boleta
- local
- codigo_cliente
- fecha_nacimiento
- genero_codigo
- genero_texto
- edad_en_transaccion

No almacenar en el Parquet analítico columnas personales innecesarias como:

- RUN CLIENTE
- NOMBRES
- APELLIDOS

Salvo que exista una justificación técnica. La API no debe exponerlas.

Reglas mínimas:

- FECHA debe convertirse a datetime.
- FECHA NACIMIENTO debe convertirse a date.
- SKU, UNIDADES, BOLETA y LOCAL deben ser enteros.
- MONTO APLICADO y PORCENTAJE DESCUENTO deben ser números.
- CODIGO CLIENTE debe normalizarse como string UUID.
- CANAL debe normalizarse en mayúsculas.
- GÉNERO debe normalizarse al texto público.
- edad_en_transaccion debe calcularse correctamente considerando si la persona ya cumplió años ese año.
- Rechazar o descartar de forma controlada filas que no puedan utilizarse.
- Nunca ocultar silenciosamente la cantidad de filas descartadas.
- Guardar un reporte de calidad de datos.

No registres valores de:

- RUN.
- Nombres.
- Apellidos.
- UUID completos.
- Boletas completas.

======================================================================
11. ARQUITECTURA DEL PROYECTO
======================================================================

Utiliza una estructura similar a esta, adaptándola cuando sea necesario:

.
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── ventas.py
│   │   └── health.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── filters.py
│   │   ├── statistics.py
│   │   └── errors.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── statistics_service.py
│   │   ├── filter_service.py
│   │   └── ingestion_service.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── sales_repository.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── enums.py
│   │   └── exceptions.py
│   ├── errors/
│   │   ├── __init__.py
│   │   ├── handlers.py
│   │   └── problem_details.py
│   ├── cli/
│   │   ├── __init__.py
│   │   └── ingest.py
│   ├── observability/
│   │   ├── __init__.py
│   │   └── logging.py
│   └── utils/
│       ├── __init__.py
│       ├── dates.py
│       ├── hashing.py
│       └── locks.py
├── data/
│   ├── .gitkeep
│   └── processed/
│       └── .gitkeep
├── scripts/
│   ├── entrypoint.sh
│   ├── download_data.py
│   └── generate_sample_data.py
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   │   └── ventas.csv
│   ├── unit/
│   │   ├── test_filter_service.py
│   │   ├── test_statistics_service.py
│   │   ├── test_dates.py
│   │   └── test_problem_details.py
│   └── integration/
│       ├── test_get_statistics.py
│       ├── test_post_statistics.py
│       ├── test_validation_errors.py
│       └── test_ingestion_cli.py
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── gunicorn.conf.py
├── datos.json
├── README.md
└── wsgi.py

No crees un único archivo main.py con toda la lógica.

Aplica:

- Application Factory Pattern.
- Blueprints.
- Separación entre API, validación, dominio, servicios y acceso a datos.
- Inyección explícita de dependencias cuando sea útil.
- Configuración por entorno.
- Excepciones de dominio.
- Type hints completos.
- Docstrings útiles.
- Funciones pequeñas.
- Nombres claros.
- Código en inglés o español de forma consistente.
- Respuestas públicas en español.

======================================================================
12. ENDPOINTS AUXILIARES
======================================================================

Además del endpoint obligatorio, crea:

GET /health

Debe indicar solamente si el proceso está activo.

Ejemplo:

{
  "status": "ok"
}

GET /ready

Debe validar que:

- El Parquet procesado exista.
- La caché de estadísticas exista.
- Los metadatos existan.
- El servicio pueda leerlos.

Cuando esté preparado:

{
  "status": "ready"
}

Si no está preparado, devolver 503 usando el formato estándar de error.

No expongas información sensible ni rutas absolutas.

======================================================================
13. DOCUMENTACIÓN SWAGGER / OPENAPI
======================================================================

Configura documentación interactiva.

Rutas sugeridas:

- /docs
- /openapi.json

La documentación debe incluir:

- Descripción general.
- Endpoint GET.
- Endpoint POST.
- Query parameters.
- Esquema completo del body POST.
- Esquema de respuesta exitosa.
- Esquema de error.
- Ejemplos válidos.
- Ejemplos inválidos.
- Enumeraciones de filtros y canales.
- Explicación de que las estadísticas se calculan sobre MONTO APLICADO.
- Explicación de la desviación estándar poblacional.
- Comportamiento cuando no hay resultados.
- Códigos HTTP posibles.
- Forma de ejecutar la carga de datos.

Verifica que Swagger realmente abra y que el documento OpenAPI sea válido.

======================================================================
14. PRUEBAS AUTOMATIZADAS
======================================================================

Las pruebas son parte obligatoria de la entrega.

Usa pytest.

Cubre como mínimo:

14.1. Estadísticas

- Suma.
- Conteo.
- Promedio.
- Mínimo.
- Máximo.
- Mediana con cantidad impar.
- Mediana con cantidad par.
- Desviación estándar poblacional.
- Dataset con un solo elemento.
- Dataset sin resultados.
- Valores decimales.
- Ausencia de NaN e Infinity.

14.2. GET

- GET sin filtros.
- GET con un filtro.
- GET con varios filtros.
- GET con GENERO.
- GET con EDAD.
- GET con CANAL.
- GET con CODIGO_PRODUCTO.
- GET con ID_PERSONA.
- GET con LOCAL.
- GET con rango de fechas.
- Filtro desconocido.
- Tipo inválido.
- Canal inválido.
- Género inválido.
- UUID inválido.
- FECHA_DESDE posterior a FECHA_HASTA.

14.3. POST

- Body válido.
- Una consulta.
- Varias consultas.
- Body ausente.
- Content-Type incorrecto.
- JSON mal formado.
- consultas ausente.
- consultas null.
- consultas no es arreglo.
- consultas vacío.
- elemento sin consulta.
- elemento sin valor.
- consulta desconocida.
- filtro duplicado.
- valor entero inválido.
- valor de fecha inválido.
- propiedades desconocidas.

14.4. Errores

Para cada error relevante comprobar:

- status HTTP.
- detail.
- instance.
- status.
- title.
- type.
- timestamp terminado en Z.
- errorCode.
- errorLabel.
- method.
- Content-Type application/json.

14.5. Ingesta

- CSV válido.
- CSV inexistente.
- Falta una columna obligatoria.
- Tipos inválidos.
- Generación del Parquet.
- Generación del resumen.
- Generación de metadatos.
- Detección de archivo sin cambios.
- Reprocesamiento cuando cambia el CSV.
- Exclusión de datos personales innecesarios.

Configura cobertura y establece un objetivo mínimo razonable de 85%.

Las pruebas deben usar un CSV pequeño y determinista incluido en tests/fixtures.

No deben descargar el dataset real.

======================================================================
15. DATOS DE PRUEBA
======================================================================

Crea en la raíz:

datos.json

Debe contener datos de prueba representativos, con al menos:

- Masculino.
- Femenino.
- Otro.
- No especificado.
- Todos los canales válidos.
- Distintos locales.
- Distintos SKU.
- Distintas fechas.
- Distintas edades.
- UUID válidos.
- Montos que permitan comprobar mediana par e impar.
- Descuentos válidos.
- Uno o más casos de datos inválidos identificados claramente.

Además crea:

tests/fixtures/ventas.csv

Debe derivarse de datos de prueba coherentes y ser utilizado por las pruebas.

Incluye ejemplos de request y response en un apartado separado de datos.json o en archivos adicionales cuando resulte más limpio.

======================================================================
16. SEGURIDAD Y ROBUSTEZ
======================================================================

Implementa como mínimo:

- Límite configurable para el tamaño del body.
- Validación estricta de JSON.
- Rechazo de propiedades desconocidas.
- Sin ejecución de expresiones entregadas por el usuario.
- Sin SQL construido mediante concatenación.
- Sin exposición de datos personales.
- Sin CORS abierto innecesariamente.
- Sin modo debug en producción.
- Cabeceras de seguridad básicas.
- Logging estructurado.
- Request ID o correlation ID.
- Manejo de señales de terminación en Gunicorn.
- Timeouts razonables.
- Usuario no root en Docker.
- Imagen Docker pequeña.
- Healthcheck.
- Dependencias con versiones compatibles y acotadas.
- No incluir secretos en el repositorio.
- .env incluido en .gitignore.
- .env.example sin credenciales.
- Protegerse frente a path traversal al aceptar rutas desde CLI.
- El endpoint no debe permitir seleccionar archivos arbitrarios.

======================================================================
17. CALIDAD DE CÓDIGO
======================================================================

Configura en pyproject.toml:

- Dependencias normales.
- Dependencias de desarrollo.
- Ruff lint.
- Ruff format.
- Mypy.
- Pytest.
- Coverage.

El proyecto debe pasar:

ruff check .
ruff format --check .
mypy app
pytest --cov=app --cov-report=term-missing

Incluye comandos equivalentes en Makefile:

make install
make format
make lint
make typecheck
make test
make ingest
make run
make docker-build
make docker-up

No silencies errores de lint o tipos sin justificación.

No uses `# type: ignore` de forma generalizada.

======================================================================
18. DOCKER Y EJECUCIÓN
======================================================================

Crea:

- Dockerfile.
- docker-compose.yml.
- gunicorn.conf.py.
- scripts/entrypoint.sh.

El contenedor debe:

- Ejecutarse como usuario sin privilegios.
- Montar o copiar el dataset mediante configuración.
- Ingerir automáticamente cuando AUTO_INGEST=true.
- Ejecutar Gunicorn.
- Exponer el puerto configurado.
- Incluir healthcheck.
- Evitar múltiples ingestas paralelas.
- Persistir el Parquet y la caché mediante volumen.

Ejemplo de ejecución local esperado:

cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
flask --app "app:create_app()" ingest-data --csv data/ventas.csv
flask --app "app:create_app()" run

Ejemplo con Docker:

docker compose up --build

======================================================================
19. README EN ESPAÑOL
======================================================================

Crea un README.md profesional y completo con:

1. Nombre del proyecto.
2. Descripción.
3. Objetivos.
4. Arquitectura.
5. Diagrama Mermaid de componentes.
6. Diagrama Mermaid del flujo de ingesta.
7. Tecnologías utilizadas.
8. Requisitos previos.
9. Instalación local.
10. Configuración.
11. Variables de entorno.
12. Cómo descargar o ubicar el CSV.
13. Cómo ejecutar la ingesta.
14. Cómo iniciar la API.
15. Cómo ejecutar con Docker.
16. Cómo ejecutar las pruebas.
17. Cómo usar Swagger.
18. Ejemplos curl de GET.
19. Ejemplos curl de POST.
20. Ejemplos de errores.
21. Tabla de filtros.
22. Decisiones y supuestos.
23. Tratamiento de la edad.
24. Mapeo de género.
25. Estadísticas sobre MONTO APLICADO.
26. Desviación estándar poblacional.
27. Comportamiento sin coincidencias.
28. Estrategia de procesamiento paralelo.
29. Protección de datos personales.
30. Estructura del proyecto.
31. Solución de problemas.
32. Lista de entregables.
33. Instrucción manual para agregar al profesor “sebasalazar” como colaborador del repositorio GitHub.
34. Fecha de entrega: 17 de julio de 2026, 23:59:59 hora continental de Chile.

No afirmes que el profesor fue agregado automáticamente. Indica que es un paso manual que debe realizar el estudiante desde GitHub.

======================================================================
20. CI DE GITHUB
======================================================================

Crea:

.github/workflows/ci.yml

Debe ejecutarse en push y pull request.

Debe realizar:

- Instalación.
- Ruff.
- Comprobación de formato.
- Mypy.
- Pytest con cobertura.

Las pruebas del CI no deben requerir el CSV real ni conexión a Internet.

======================================================================
21. CRITERIOS DE ACEPTACIÓN
======================================================================

El proyecto se considera completo solamente si:

- La aplicación inicia correctamente.
- La ingesta funciona.
- GET sin filtros devuelve estadísticas globales.
- GET con filtros devuelve estadísticas filtradas.
- POST aplica correctamente filtros dinámicos.
- Los cálculos son correctos.
- Los errores 400 y 500 respetan exactamente el contrato solicitado.
- Las validaciones devuelven 400, no 422.
- Swagger funciona.
- El CSV grande se procesa mediante Polars, streaming, ejecución vectorizada o paralela.
- Existe carga desatendida.
- Existe README.md.
- Existe datos.json.
- Existen pruebas.
- Existe Docker.
- Existe CI.
- No se exponen datos personales.
- Todos los comandos de calidad terminan correctamente.

======================================================================
22. METODOLOGÍA DE TRABAJO OBLIGATORIA
======================================================================

Sigue este orden:

1. Inspecciona la carpeta actual.
2. Si está vacía, crea el proyecto completo.
3. Si existe algún archivo, consérvalo salvo que sea claramente reemplazable.
4. Crea primero la estructura y configuración.
5. Implementa el dominio y validaciones.
6. Implementa ingesta y almacenamiento.
7. Implementa el repositorio y estadísticas.
8. Implementa GET y POST.
9. Implementa errores.
10. Implementa Swagger.
11. Implementa pruebas.
12. Implementa Docker y CI.
13. Ejecuta formateo, lint, mypy y pytest.
14. Corrige todos los problemas encontrados.
15. Realiza una prueba manual del servidor con el fixture.
16. Comprueba GET, POST y un error 400.
17. Comprueba que /openapi.json responda correctamente.
18. Revisa que el README coincida con el código real.

No finalices después de escribir un plan.

No dejes:

- TODO.
- FIXME.
- Métodos vacíos.
- Código simulado.
- Endpoints sin implementar.
- Pruebas omitidas.
- Pass sin justificación.
- Credenciales ficticias.
- Resultados de pruebas inventados.

======================================================================
23. REPORTE FINAL DE CODEX
======================================================================

Cuando hayas terminado, entrega un resumen que incluya:

- Archivos creados.
- Arquitectura implementada.
- Decisiones técnicas principales.
- Supuestos realizados.
- Comandos ejecutados.
- Resultado real de Ruff.
- Resultado real de Mypy.
- Resultado real de Pytest.
- Porcentaje de cobertura alcanzado.
- Ejemplos de curl.
- Cómo iniciar el proyecto.
- Problemas pendientes reales, si existieran.

No afirmes que una comprobación pasó si no fue ejecutada.

Comienza ahora y desarrolla el proyecto completo desde cero.
