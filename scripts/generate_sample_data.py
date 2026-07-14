"""Genera ``data/ventas.csv`` a partir de los casos válidos de ``datos.json``."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COLUMNS = [
    "FECHA",
    "CANAL",
    "SKU",
    "PRODUCTO",
    "UNIDADES",
    "PORCENTAJE DESCUENTO",
    "MONTO APLICADO",
    "BOLETA",
    "LOCAL",
    "CODIGO CLIENTE",
    "RUN CLIENTE",
    "NOMBRES",
    "APELLIDOS",
    "FECHA NACIMIENTO",
    "GÉNERO",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/ventas.csv"))
    args = parser.parse_args()
    destination = _safe_destination(args.output)

    with (PROJECT_ROOT / "datos.json").open(encoding="utf-8") as stream:
        payload: Any = json.load(stream)
    if not isinstance(payload, dict) or not isinstance(payload.get("casos_validos"), list):
        raise SystemExit("datos.json no contiene una lista casos_validos")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS, extrasaction="raise")
        writer.writeheader()
        writer.writerows(payload["casos_validos"])
    print(f"CSV sintético generado con {len(payload['casos_validos'])} filas")


def _safe_destination(raw: Path) -> Path:
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
