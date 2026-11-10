"""Critério 2: nenhum ranking, percentil ou contagem no índice.

Entrada: HTML e JSON do índice no diretório do site.
Saída: o texto do `[ok]` ou `BuildError`.
Idempotente: sim — só lê."""

from __future__ import annotations

import json
import re

from ..errors import BuildError


def check_no_ranking(site: Path) -> str:
    forbidden = ("p10", "p90", "mediana da rede")
    for path in sorted(site.glob("*.html")):
        text = path.read_text(encoding="utf-8").lower()
        for term in forbidden:
            if term in text:
                raise BuildError(f"{path.name} publica {term!r}")
    index_entries = json.loads((site / "indice.json").read_text(encoding="utf-8"))
    names = [x["nome"] for x in index_entries]
    if names != sorted(names):
        raise BuildError("indice.json não está em ordem alfabética por nome")
    index = (site / "index.html").read_text(encoding="utf-8")
    if 'class="num"' in index or "data-numero=" in index:
        raise BuildError("index.html publica número de escola")
    if re.search(r"\b\d[\d.]*\s+escolas?\b", index, re.IGNORECASE):
        raise BuildError("index.html publica contagem de escolas")
    return f"{len(index_entries):,} entradas alfabéticas, sem número no índice"
