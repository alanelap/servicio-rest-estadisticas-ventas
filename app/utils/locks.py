"""Lock de lectores/escritor entre procesos para snapshots analíticos."""

from __future__ import annotations

import fcntl
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def ingestion_lock(processed_path: Path, timeout: float = 300.0) -> Iterator[None]:
    """Bloqueo exclusivo durante toda comprobación/publicación de la ingesta."""

    with _file_lock(processed_path, shared=False, timeout=timeout):
        yield


@contextmanager
def data_read_lock(processed_path: Path, timeout: float = 30.0) -> Iterator[None]:
    """Bloqueo compartido: permite consultas paralelas y excluye publicaciones."""

    with _file_lock(processed_path, shared=True, timeout=timeout):
        yield


@contextmanager
def _file_lock(processed_path: Path, *, shared: bool, timeout: float) -> Iterator[None]:
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
