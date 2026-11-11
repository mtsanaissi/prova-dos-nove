"""Critério 2: nenhum ranking, percentil ou contagem na lista de escolas.

O escopo é `escolas.html` e as 1.291 páginas de escola — os dois lugares onde D3
vale. A home compara redes por decisão do mantenedor e por isso nomeia `p10` e
`p90` na legenda e na tabela do gráfico; `metodologia.html` e `como-ler.html`
explicam o mesmo. Os três ficam fora da varredura de termos por construção:
`escolas.html` e as páginas numeradas é que são varridas.

Entrada: HTML da lista e das páginas de escola, e o `indice.json`.
Saída: o texto do `[ok]` ou `BuildError`.
Idempotente: sim — só lê."""

from __future__ import annotations

from pathlib import Path

import json
import re

from ..errors import BuildError


def check_no_ranking(site: Path) -> str:
    forbidden = ("p10", "p90", "mediana da rede")
    scope = [site / "escolas.html", *sorted(site.glob("[0-9]*.html"))]
    for path in scope:
        text = path.read_text(encoding="utf-8").lower()
        for term in forbidden:
            if term in text:
                raise BuildError(f"{path.name} publica {term!r}")
    index_entries = json.loads((site / "indice.json").read_text(encoding="utf-8"))
    names = [x["nome"] for x in index_entries]
    if names != sorted(names):
        raise BuildError("indice.json não está em ordem alfabética por nome")
    lista = (site / "escolas.html").read_text(encoding="utf-8")
    if 'class="num"' in lista or "data-numero=" in lista:
        raise BuildError("escolas.html publica número de escola")
    if re.search(r"\b\d[\d.]*\s+escolas?\b", lista, re.IGNORECASE):
        raise BuildError("escolas.html publica contagem de escolas")
    return f"{len(index_entries):,} entradas alfabéticas, sem número na lista"
