"""Descarga por streaming un recurso de datos y lo publica como CSV local.

El archivo remoto se escribe primero en un temporal del directorio de destino,
se sincroniza y solo entonces reemplaza atómicamente la ruta final. Esto evita
dejar un archivo parcial si la red o el proceso fallan. La URL predeterminada
apunta al dataset oficial, pero ``--url`` admite otro origen y el script no
valida el esquema CSV ni una huella criptográfica del contenido.
"""

from __future__ import annotations

import argparse
import os
import tempfile
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FILE_ID = "15jLBlJ9eMQSoHsoCMnFWBGopr98FIHlK"
DEFAULT_URL = (
    f"https://drive.usercontent.google.com/download?id={FILE_ID}&export=download&confirm=t"
)


def main() -> None:
    """Ejecuta la descarga con controles básicos de ruta, tipo y tamaño.

    Raises:
        SystemExit: Si los argumentos son inválidos o la salida escapa de la
            raíz del proyecto/no usa extensión ``.csv``.
        RuntimeError: Si el servidor devuelve HTML, se supera el límite de
            bytes o la descarga queda vacía.
        OSError: Si falla una operación de red o la creación, escritura,
            sincronización o publicación del archivo local.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/ventas.csv"))
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--max-bytes", type=int, default=20 * 1024**3)
    args = parser.parse_args()
    destination = _safe_destination(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(args.url, headers={"User-Agent": "CruzMoradaDataLoader/1.0"})
    descriptor, temp_name = tempfile.mkstemp(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".download"
    )
    total = 0
    temporary = Path(temp_name)
    try:
        with (
            os.fdopen(descriptor, "wb") as output,
            urllib.request.urlopen(request, timeout=60) as response,
        ):
            content_type = response.headers.get_content_type()
            if content_type == "text/html":
                raise RuntimeError(
                    "Google Drive devolvió HTML; descargue manualmente desde el enlace del README"
                )
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > args.max_bytes:
                    raise RuntimeError("La descarga excede el límite configurado")
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if total == 0:
            raise RuntimeError("La descarga produjo un archivo vacío")
        os.replace(temporary, destination)
        destination.chmod(0o644)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Dataset descargado correctamente ({total} bytes)")


def _safe_destination(raw: Path) -> Path:
    """Resuelve y valida una ruta de salida confinada a la raíz del proyecto.

    Args:
        raw: Ruta absoluta o relativa solicitada por el operador.

    Returns:
        Ruta absoluta resuelta con extensión ``.csv`` dentro del proyecto.

    Raises:
        SystemExit: Si la ruta resuelta escapa de :data:`PROJECT_ROOT` o no
            termina en ``.csv``.
    """
    destination = raw.expanduser()
    if not destination.is_absolute():
        destination = PROJECT_ROOT / destination
    destination = destination.resolve()
    try:
        destination.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise SystemExit("La salida debe permanecer dentro del proyecto") from exc
    if destination.suffix.lower() != ".csv":
        raise SystemExit("La salida debe usar extensión .csv")
    return destination


if __name__ == "__main__":
    main()
