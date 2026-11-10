"""Índice de escolas com busca por nome e salto por Região Administrativa.

Entrada: modelo de `loader.load_data`, carimbo do build e limiar.
Saída: HTML do índice (salto, lista por RA e script de busca).
Idempotente: sim — render puro."""

from __future__ import annotations

import html

from .assets import JS_INDEX
from .errors import BuildError
from .layout import document
from .region import region_anchor_id, region_label, region_sort_key


def render_index_page(data: dict, data_build: str, threshold: int) -> str:
    schools = data["escolas"]
    by_region: dict[str, list[dict]] = {}
    for school in schools:
        by_region.setdefault(school["ra"], []).append(school)
    for entries in by_region.values():
        entries.sort(key=lambda e: (e["nome"], e["co"]))

    order = sorted(by_region, key=region_sort_key)
    region_ids: dict[str, str] = {}
    seen: dict[str, str] = {}
    for region in order:
        anchor = region_anchor_id(region)
        if anchor in seen:
            raise BuildError(
                f"duas RAs com a mesma âncora {anchor!r}: {seen[anchor]!r} e {region!r}"
            )
        seen[anchor] = region
        region_ids[region] = anchor

    parts = [
        "<main>",
        "<h1>Escolha uma escola</h1>",
        '<p class="subtitulo">Distrito Federal · uma página por escola, em português comum.</p>',
        '<div class="busca">',
        '<label for="busca">Buscar escola pelo nome</label>',
        '<input id="busca" type="search" autocomplete="off" placeholder="Digite parte do nome">',
        '<p class="status" id="busca-status" role="status"></p>',
        "</div>",
        '<noscript><p class="aviso">A busca por nome e o salto por Região Administrativa '
        "precisam de JavaScript. A lista por Região Administrativa abaixo continua completa.</p></noscript>",
        '<div class="sumario" id="sumario">',
        '<label for="ir-ra">Ir para uma Região Administrativa</label>',
        '<select id="ir-ra" autocomplete="off">',
        '<option value="">Selecione…</option>',
    ]
    for region in order:
        parts.append(
            f'<option value="#{region_ids[region]}">{html.escape(region_label(region))}</option>'
        )
    parts.append("</select>")
    parts.append("</div>")
    parts.append('<div id="lista">')
    for region in order:
        parts.append(
            f'<section class="ra" id="{region_ids[region]}" data-ra="{html.escape(region)}">'
        )
        parts.append(f"<h2>{html.escape(region_label(region))}</h2><ul>")
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
    head_extra = "<noscript><style>.sumario { display: none; }</style></noscript>"
    return document(
        "Prova dos Nove — escolas do Distrito Federal",
        body + js,
        data_build,
        threshold,
        head_extra=head_extra,
    )
