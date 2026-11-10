"""Leitores comuns às verificações do §8.

Entrada: diretório do site.
Saída: HTML, JSON de escola, ids de número e hashes.
Idempotente: sim — só lê."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..errors import BuildError
from ..loader import sha256


def read_page(site: Path, code: str) -> str:
    return (site / f"{code}.html").read_text(encoding="utf-8")


def read_school_json(site: Path, code: str) -> dict:
    path = site / "dados" / f"{code}.json"
    if not path.is_file():
        raise BuildError(f"falta {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def number_ids(markup: str) -> list[str]:
    return re.findall(r'data-numero="([^"]+)"', markup)


def require_equal_lists(
    where: str, name_a: str, a: list[str], name_b: str, b: list[str]
) -> None:
    """Compara duas listas e falha na primeira divergência, com a posição."""
    if len(a) != len(b):
        raise BuildError(f"{where}: {len(a)} {name_a} contra {len(b)} {name_b}")
    for position, (value_a, value_b) in enumerate(zip(a, b), start=1):
        if value_a != value_b:
            raise BuildError(
                f"{where}: posição {position}: {name_a} {value_a!r} != {name_b} {value_b!r}"
            )


def site_hashes(site: Path) -> dict[str, str]:
    return {
        str(p.relative_to(site)): sha256(p)
        for p in sorted(site.rglob("*"))
        if p.is_file()
    }
