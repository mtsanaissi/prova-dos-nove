"""Critério 5: o segundo build produz os mesmos bytes.

Entrada: insumo público, site gerado, carimbo e limiar.
Saída: o texto do `[ok]` ou `BuildError`.
Idempotente: sim — gera em diretório temporário."""

from __future__ import annotations

import tempfile
from pathlib import Path

from ..build import build_site
from ..errors import BuildError
from .common import site_hashes


def check_reproducibility(public: Path, site: Path, data_build: str, threshold: int) -> str:
    temp_base = Path("/tmp/opencode") if Path("/tmp/opencode").is_dir() else None
    with tempfile.TemporaryDirectory(prefix="prova-dos-nove-site-", dir=temp_base) as tmp:
        build_site(public, Path(tmp), data_build, threshold, quiet=True)
        a = site_hashes(site)
        b = site_hashes(Path(tmp))
        if a != b:
            differing = sorted(set(a) ^ set(b)) or sorted(k for k in a if a.get(k) != b.get(k))
            raise BuildError(f"build não é idempotente; arquivos diferentes: {differing[:5]}")
    return "segundo build produz os mesmos bytes"
