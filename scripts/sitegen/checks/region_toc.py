"""Critério 7: salto por RA e seções na mesma ordem.

Entrada: HTML da lista de escolas (`escolas.html`) no diretório do site.
Saída: o texto do `[ok]` ou `BuildError`.
Idempotente: sim — só lê."""

from __future__ import annotations

from pathlib import Path

import html
import re

from ..errors import BuildError
from ..region import REGION_LABELS, region_anchor_id, region_label
from .common import require_equal_lists


def check_region_toc(site: Path) -> str:
    index = (site / "escolas.html").read_text(encoding="utf-8")
    if 'id="ir-ra"' not in index:
        raise BuildError('escolas.html sem o seletor id="ir-ra"')
    if 'for="ir-ra"' not in index:
        raise BuildError('escolas.html sem o rótulo for="ir-ra"')
    if "<noscript><style>.sumario { display: none; }</style></noscript>" not in index:
        raise BuildError("escolas.html sem o <noscript> que esconde o salto sem JavaScript")
    options = re.findall(r'<option value="#(ra-[^"]+)">([^<]+)</option>', index)
    sections = re.findall(
        r'<section class="ra" id="(ra-[^"]+)" data-ra="([^"]*)"><h2>([^<]+)</h2>', index
    )
    if not options:
        raise BuildError("escolas.html sem opções de RA no salto")
    if not sections:
        raise BuildError("escolas.html sem seções de RA")

    option_slugs = [slug for slug, _ in options]
    section_slugs = [slug for slug, _, _ in sections]
    option_labels = [html.unescape(label) for _, label in options]
    section_labels = [html.unescape(label) for _, _, label in sections]
    section_regions = [html.unescape(region) for _, region, _ in sections]
    if len(set(option_slugs)) != len(option_slugs):
        raise BuildError("escolas.html repete uma âncora de RA no salto")
    if len(set(section_slugs)) != len(section_slugs):
        raise BuildError("escolas.html repete uma âncora de RA nas seções")
    require_equal_lists(
        "escolas.html", "âncoras no salto", option_slugs, "âncoras nas seções", section_slugs
    )
    require_equal_lists(
        "escolas.html", "rótulos no salto", option_labels, "rótulos nas seções", section_labels
    )
    for slug, region, label in zip(section_slugs, section_regions, section_labels):
        if slug != region_anchor_id(region):
            raise BuildError(
                f"escolas.html: a seção {slug!r} não deriva do valor bruto {region!r}"
            )
        if label != region_label(region):
            raise BuildError(
                f"escolas.html: a seção {slug!r} mostra {label!r} para {region!r}, fora do mapa"
            )
    known = set(REGION_LABELS.values())
    for label in option_labels:
        if label not in known:
            raise BuildError(f"escolas.html publica rótulo de RA fora do mapa: {label!r}")
    return f"{len(options)} RAs no salto, casando com as seções e com o rótulo"
