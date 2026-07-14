"""Cálculo de huellas y persistencia segura de artefactos JSON.

La publicación JSON se realiza en un archivo temporal del mismo sistema de
archivos para que :func:`os.replace` efectúe el cambio de nombre atómicamente.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Calcula SHA-256 por bloques sin materializar todo el archivo.

    Args:
        path: Archivo cuya huella se calculará.
        chunk_size: Bytes solicitados en cada lectura. El llamador debe usar un
            entero positivo; esta función no valida esa precondición.

    Returns:
        Resumen SHA-256 hexadecimal de 64 caracteres.

    Raises:
        OSError: Si el archivo no puede abrirse o leerse por completo.
    """
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Serializa y publica un objeto JSON mediante reemplazo atómico.

    El temporal se sincroniza con ``fsync`` antes de reemplazar el destino y se
    elimina en todos los caminos de salida. No se permiten valores ``NaN`` ni
    infinitos porque no pertenecen al estándar JSON.

    Args:
        path: Ruta final del artefacto JSON.
        payload: Objeto serializable que se escribirá como raíz del documento.

    Raises:
        OSError: Si no se puede crear, escribir, sincronizar o publicar el archivo.
        TypeError: Si ``payload`` contiene un valor no serializable.
        ValueError: Si ``payload`` contiene un número no finito.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def read_json_object(path: Path) -> dict[str, Any]:
    """Lee un documento JSON cuya raíz debe ser un objeto.

    Args:
        path: Ruta del documento codificado en UTF-8.

    Returns:
        Objeto JSON deserializado como diccionario.

    Raises:
        OSError: Si el archivo no puede abrirse o leerse.
        json.JSONDecodeError: Si el contenido no es JSON válido.
        ValueError: Si la raíz JSON no es un objeto.
    """
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError("El archivo JSON no contiene un objeto")
    return value
