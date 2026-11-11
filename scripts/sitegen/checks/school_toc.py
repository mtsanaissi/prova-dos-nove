"""Critério 8: sumário da página da escola.

Entrada: HTML das páginas de escola em `site/` e o modelo do insumo.
Saída: o texto do `[ok]` ou `BuildError`.
Idempotente: sim — só lê."""

from __future__ import annotations

from pathlib import Path

import html
import re

from ..errors import BuildError
from .common import read_page, require_equal_lists


# Cópia congelada de `docs/FASE-1.md` §2.2: (âncora, rótulo, só com creche).
# É deliberadamente independente de `school_page.SCHOOL_SECTIONS`: renomear um id
# ou um rótulo só no gerador quebraria o `--check`, e os ids são âncoras públicas.
CONTRACT_SECTIONS = (
    ("identificacao", "Identificação", False),
    ("oferta", "Oferta por etapa", False),
    ("matricula", "Matrícula por etapa", False),
    ("ideb", "Ideb por etapa", False),
    ("fluxo", "Fluxo escolar", False),
    ("tdi", "Distorção idade-série", False),
    ("tnr", "Taxa de não-resposta", False),
    ("infraestrutura", "Infraestrutura", False),
    ("creche", "Creche da escola", True),
)

NAV_OPEN = '<nav class="sumario-escola"'
NAV_LABEL = "Seções desta página"
DAYCARE_ITEM = '<li><a href="#creche">Creche da escola</a></li>'


def _verify_school_toc(code: str, markup: str, daycare_offered: bool) -> None:
    """Confere o sumário de uma página contra as seções e contra o contrato."""
    nav_count = markup.count(NAV_OPEN)
    if nav_count != 1:
        raise BuildError(f"{code}: {nav_count} <nav class=\"sumario-escola\"> (esperado 1)")
    nav_match = re.search(rf"{re.escape(NAV_OPEN)}[^>]*>(.*?)</nav>", markup, re.DOTALL)
    if nav_match is None:
        raise BuildError(f"{code}: <nav class=\"sumario-escola\"> sem fechamento")
    nav = nav_match.group(1)
    nav_open = markup[nav_match.start() : markup.index(">", nav_match.start()) + 1]
    if f'aria-label="{NAV_LABEL}"' not in nav_open:
        raise BuildError(
            f"{code}: <nav> do sumário sem aria-label=\"{NAV_LABEL}\""
        )

    h1 = markup.find("<h1>")
    subtitle = markup.find('<p class="subtitulo">')
    first_section = markup.find('<section class="bloco"')
    if (
        h1 < 0
        or subtitle < 0
        or first_section < 0
        or not (h1 < subtitle < nav_match.start() < first_section)
    ):
        raise BuildError(
            f"{code}: o sumário não está entre o subtítulo e a primeira seção"
        )

    if not re.search(r"<details\b[^>]*>", nav):
        raise BuildError(f"{code}: sumário sem <details>")
    if re.search(r"<details\b[^>]*\bopen\b", nav):
        raise BuildError(f"{code}: <details> do sumário aberto por padrão")
    if "<summary>" not in nav or "</summary>" not in nav:
        raise BuildError(f"{code}: sumário sem <summary>")

    ul_match = re.search(r"<ul\b([^>]*)>", nav)
    if ul_match is None or "</ul>" not in nav:
        raise BuildError(f"{code}: sumário sem <ul>…</ul>")
    if 'role="list"' not in ul_match.group(1):
        raise BuildError(f'{code}: <ul> do sumário sem role="list"')

    item_count = len(re.findall(r"<li\b", nav))
    link_count = len(re.findall(r'<a href="#[^"]*"', nav))
    items = re.findall(r'<li><a href="#([^"]+)">([^<]+)</a></li>', nav)
    if not item_count == link_count == len(items):
        raise BuildError(
            f"{code}: {item_count} <li>, {link_count} links e {len(items)} itens completos"
            " no sumário"
        )

    sections = re.findall(
        r'<section class="bloco" id="([^"]+)"><h2>([^<]+)</h2>', markup
    )
    toc_ids = [anchor for anchor, _ in items]
    toc_labels = [html.unescape(label) for _, label in items]
    section_ids = [anchor for anchor, _ in sections]
    section_labels = [html.unescape(label) for _, label in sections]

    if daycare_offered:
        if "creche" not in toc_ids:
            raise BuildError(f"{code}: oferta_inf_cre = 1 sem o link #creche no sumário")
        if "creche" not in section_ids:
            raise BuildError(f"{code}: oferta_inf_cre = 1 sem a seção id=\"creche\"")
    else:
        if "creche" in toc_ids:
            raise BuildError(f"{code}: oferta_inf_cre != 1 com o link #creche no sumário")
        if "creche" in section_ids:
            raise BuildError(f"{code}: oferta_inf_cre != 1 com a seção id=\"creche\"")

    expected_ids = [
        anchor for anchor, _, only_with_daycare in CONTRACT_SECTIONS
        if not only_with_daycare or daycare_offered
    ]
    expected_labels = [
        label for _, label, only_with_daycare in CONTRACT_SECTIONS
        if not only_with_daycare or daycare_offered
    ]
    require_equal_lists(
        code, "âncoras no sumário", toc_ids, "âncoras nas seções", section_ids
    )
    require_equal_lists(
        code, "âncoras no sumário", toc_ids, "âncoras do contrato", expected_ids
    )
    require_equal_lists(
        code, "rótulos no sumário", toc_labels, "rótulos nas seções", section_labels
    )
    require_equal_lists(
        code, "rótulos no sumário", toc_labels, "rótulos do contrato", expected_labels
    )

    for anchor in toc_ids:
        occurrences = len(re.findall(rf'id="{re.escape(anchor)}"', markup))
        if occurrences != 1:
            raise BuildError(
                f"{code}: href=\"#{anchor}\" casa com {occurrences} id=\"{anchor}\""
            )

    visible = html.unescape(re.sub(r"<[^>]+>", " ", nav))
    visible = re.sub(r"\s+", " ", visible).strip()
    expected_text = "Nesta página " + " ".join(expected_labels)
    if visible != expected_text:
        raise BuildError(
            f"{code}: o texto do sumário é {visible!r}, esperado {expected_text!r}"
        )
    if any(character.isdigit() for character in visible):
        raise BuildError(f"{code}: o sumário publica número: {visible!r}")
    if "data-numero" in nav or 'class="num"' in nav:
        raise BuildError(f"{code}: o sumário tem marcação de número")


def _mutated(markup: str, old: str, new: str, description: str) -> str:
    mutated = markup.replace(old, new, 1)
    if mutated == markup:
        raise BuildError(
            f"autoteste do sumário: a mutação {description} não alterou o HTML"
        )
    return mutated


def _must_fail(code: str, markup: str, daycare_offered: bool, description: str) -> None:
    try:
        _verify_school_toc(code, markup, daycare_offered)
    except BuildError:
        return
    raise BuildError(
        f"autoteste do sumário: {description} não fez o check falhar ({code})"
    )


def check_school_toc(site: Path, data: dict) -> str:
    """Varre todas as páginas de escola e compara sumário, seções e contrato."""
    site = Path(site)
    pages = sorted(site.glob("[0-9]" * 8 + ".html"))
    if len(pages) != len(data["escolas"]):
        raise BuildError(
            f"sumário: {len(pages)} páginas de escola contra "
            f"{len(data['escolas'])} escolas no insumo"
        )

    daycare_markup = read_page(site, "53000781")
    no_daycare_markup = read_page(site, "53000854")
    if data["por_co"]["53000781"]["oferta_inf_cre"] != 1:
        raise BuildError("autoteste do sumário: 53000781 perdeu a oferta de creche")
    if data["por_co"]["53000854"]["oferta_inf_cre"] == 1:
        raise BuildError("autoteste do sumário: 53000854 passou a ofertar creche")

    first_two = re.findall(r'<li><a href="#[^"]+">[^<]+</a></li>', daycare_markup)[:2]
    if len(first_two) != 2:
        raise BuildError("autoteste do sumário: 53000781 com menos de dois itens")
    _must_fail(
        "53000781",
        _mutated(daycare_markup, DAYCARE_ITEM, "", "remover o link da creche"),
        True,
        "remover o link da creche",
    )
    _must_fail(
        "53000854",
        _mutated(
            no_daycare_markup,
            "</ul></details></nav>",
            DAYCARE_ITEM + "</ul></details></nav>",
            "acrescentar o link da creche",
        ),
        False,
        "acrescentar o link da creche",
    )
    _must_fail(
        "53000781",
        _mutated(
            daycare_markup,
            "".join(first_two),
            "".join(reversed(first_two)),
            "trocar os dois primeiros itens",
        ),
        True,
        "trocar os dois primeiros itens",
    )
    _must_fail(
        "53000781",
        _mutated(
            daycare_markup,
            '<a href="#oferta">Oferta por etapa</a>',
            '<a href="#oferta">Oferta</a>',
            "encurtar o rótulo da oferta",
        ),
        True,
        "encurtar o rótulo da oferta",
    )
    _must_fail(
        "53000781",
        _mutated(daycare_markup, "<details>", "<details open>", "abrir o <details>"),
        True,
        "abrir o <details>",
    )
    _must_fail(
        "53000781",
        _mutated(
            daycare_markup,
            '<ul role="list">',
            "<ul>",
            "retirar o role de lista",
        ),
        True,
        "retirar o role de lista",
    )

    daycare_count = 0
    for path in pages:
        code = path.stem
        school = data["por_co"].get(code)
        if school is None:
            raise BuildError(f"{code}: página sem escola no insumo")
        daycare_offered = school["oferta_inf_cre"] == 1
        if daycare_offered:
            daycare_count += 1
        _verify_school_toc(
            code, path.read_text(encoding="utf-8"), daycare_offered
        )

    return (
        f"{len(pages):,} páginas: sumário = seções, na ordem e com o mesmo rótulo; "
        f"{daycare_count:,} com creche (oferta_inf_cre = 1), "
        f"{len(pages) - daycare_count:,} sem"
    )
