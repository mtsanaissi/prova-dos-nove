"""Índice de escolas com busca por nome.

Entrada: modelo de `loader.load_data`, carimbo do build e limiar.
Saída: HTML do índice (lista por RA e script de busca).
Idempotente: sim — render puro."""

from __future__ import annotations

import html

from .assets import JS_INDEX
from .layout import document


def render_index_page(data: dict, data_build: str, threshold: int) -> str:
    schools = data["escolas"]
    by_region: dict[str, list[dict]] = {}
    for school in schools:
        by_region.setdefault(school["ra"], []).append(school)
    for entries in by_region.values():
        entries.sort(key=lambda e: (e["nome"], e["co"]))

    parts = [
        "<main>",
        "<h1>Escolha uma escola</h1>",
        '<p class="subtitulo">Distrito Federal · uma página por escola, em português comum.</p>',
        '<div class="busca">',
        '<label for="busca">Buscar escola pelo nome</label>',
        '<input id="busca" type="search" autocomplete="off" placeholder="Digite parte do nome">',
        '<p class="status" id="busca-status" role="status"></p>',
        "</div>",
        '<noscript><p class="aviso">A busca por nome precisa de JavaScript. '
        "A lista por Região Administrativa abaixo continua completa.</p></noscript>",
        '<div id="lista">',
    ]
    for region in sorted(by_region):
        parts.append(f'<section class="ra" data-ra="{html.escape(region)}">')
        parts.append(f"<h2>{html.escape(region)}</h2><ul>")
        for school in by_region[region]:
            parts.append(
                f'<li data-codigo="{school["co"]}" data-nome="{html.escape(school["nome"])}">'
                f'<a href="{school["co"]}.html">{html.escape(school["nome"])}</a>'
                f'<span class="rede">{html.escape(school["rede"])}</span></li>'
            )
        parts.append("</ul></section>")
    parts.append("</div></main>")
    body = "".join(parts)

    js = "\n<script>\n" + JS_INDEX + "</script>\n"
    return document("Prova dos Nove — escolas do Distrito Federal", body + js, data_build, threshold)
