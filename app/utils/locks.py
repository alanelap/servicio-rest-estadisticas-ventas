"""Exclusión lectores-escritor entre procesos para snapshots analíticos.

Los locks se implementan con ``flock`` sobre un archivo estable asociado al
Parquet. Son locks consultivos: todos los lectores y escritores del servicio
deben usar estos context managers para respetar la sección crítica.
"""

from __future__ import annotations

import fcntl
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def ingestion_lock(processed_path: Path, timeout: float = 300.0) -> Iterator[None]:
    """Adquiere exclusión mutua durante la comprobación y publicación de ingesta.

    Args:
        processed_path: Ruta del Parquet que identifica el recurso compartido.
        timeout: Presupuesto aproximado de segundos para adquirir el lock
            exclusivo, sujeto al intervalo de sondeo interno.

    Yields:
        Control al llamador mientras mantiene el lock de escritura.

    Raises:
        TimeoutError: Si un reintento fallido detecta que se agotó el plazo.
        OSError: Si el archivo de lock no puede crearse o manipularse.
    """
    with _file_lock(processed_path, shared=False, timeout=timeout):
        yield


@contextmanager
def data_read_lock(processed_path: Path, timeout: float = 30.0) -> Iterator[None]:
    """Adquiere un lock compartido para leer una generación estable.

    Args:
        processed_path: Ruta del Parquet que identifica el recurso compartido.
        timeout: Presupuesto aproximado de segundos para adquirir el lock
            compartido, sujeto al intervalo de sondeo interno.

    Yields:
        Control al llamador mientras mantiene el lock de lectura. Otros lectores
        pueden avanzar en paralelo, pero ninguna publicación puede comenzar.

    Raises:
        TimeoutError: Si un reintento fallido detecta que se agotó el plazo.
        OSError: Si el archivo de lock no puede crearse o manipularse.
    """
    with _file_lock(processed_path, shared=True, timeout=timeout):
        yield


@contextmanager
def _file_lock(processed_path: Path, *, shared: bool, timeout: float) -> Iterator[None]:
    """Gestiona la adquisición no bloqueante y liberación de un ``flock``.

    Args:
        processed_path: Ruta usada para derivar el nombre ``.lock`` estable.
        shared: Selecciona un lock compartido si es ``True`` o exclusivo si es
            ``False``.
        timeout: Presupuesto aproximado de espera antes de cancelar la
            adquisición. El sondeo de 50 ms puede sobrepasarlo ligeramente.

    Yields:
        Control al llamador una vez adquirido el lock solicitado.

    Raises:
        TimeoutError: Si un intento bloqueado comprueba un reloj monotónico que
            ya alcanzó el límite calculado.
        OSError: Si falla una operación sobre el archivo o ``flock``.
    """
    lock_path = processed_path.with_suffix(processed_path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    operation = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
    deadline = time.monotonic() + timeout
    with lock_path.open("a+b") as stream:
        while True:
            try:
                fcntl.flock(stream.fileno(), operation | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Se agotó el tiempo de espera del lock analítico") from exc
                time.sleep(0.05)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
