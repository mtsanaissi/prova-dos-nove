"""Build do site estático da Prova dos Nove (fase 1 de `docs/FASE-1.md`).

Entrada: `data/public/` (`escolas.parquet`, `indicadores.parquet`,
         `infraestrutura.parquet` e `procedencia.json`), gerado por
         `06_analysis.py --public data/public`.
Saída:   `site/index.html`, `site/indice.json`, `site/estilo.css`,
         `site/creditos.html`, `site/como-ler.html`, uma página por escola
         (`site/<CO_ENTIDADE>.html`) e a procedência de cada número
         (`site/dados/<CO_ENTIDADE>.json`).
Idempotente: sim — o build não chama `datetime.now()`, itera em ordem fixa e
usa `--data-build` como único carimbo de tempo.

Regras de leitura: `estado` vem do parquet e nunca é deduzido de `NaN` quando a
fonte o registra; `0` é zero; `—` é não aplicável. O build lê apenas
`data/public/` e confere o sha256 registrado em `procedencia.json`.

Uso:
    python scripts/12_build_site.py --public data/public --out site \
        --data-build 2026-11-06 --limiar-n 30
    python scripts/12_build_site.py --public data/public --out site --check
    python scripts/12_build_site.py --public data/public --out site --check-casos
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import tempfile
from pathlib import Path

import pandas as pd

from sitegen.errors import BuildError
from sitegen.contract import DEFAULT_DATA_BUILD, DEFAULT_N_THRESHOLD, MAX_SITE_BYTES, STAGES, STAGE_LABEL, ENROLLMENT_LABEL, OFFERINGS, INFRA_ITEMS, IDEB_YEARS_BY_STAGE, STATES, PHRASE_STAGE_NOT_OFFERED, PHRASE_IDEB_PRIVATE, PHRASE_IDEB_PUBLIC, PHRASE_CENSUS_2024_NO_ROW, PHRASE_ENROLLMENT_2024, PHRASE_ENROLLMENT_2025, PHRASE_NO_INDICATOR, PHRASE_INFRA_NOT_APPLICABLE, PHRASE_SMALL_N, STUDENT_COUNT_FAMILIES, SLUG_BY_STAGE_LABEL
from sitegen.fmt import fmt_int, fmt_dec, fmt_years, stage_slug, stage_title, student_word
from sitegen.loader import sha256, load_data, get_indicator, has_published_ideb, has_rate_row
from sitegen.assets import CSS
from sitegen.layout import document
from sitegen.index_page import render_index_page
from sitegen.info_pages import render_how_to_read_page, render_credits_page


class SchoolPage:
    """Uma página de escola e o coletor de procedência dos números dela."""

    def __init__(self, data: dict, school: dict, data_build: str, threshold: int):
        self.d = data
        self.e = school
        self.data_build = data_build
        self.threshold = threshold
        self.numbers: list[dict] = []
        self.by_id: dict[str, dict] = {}
        self.enrollment_cache: dict[tuple[str, str], str] = {}

    def _add(
        self,
        *,
        id: str,
        family: str,
        block: str,
        stage: str,
        year: str,
        value,
        state: str,
        n: int | None,
        text: str,
        limits: list[str] | None = None,
        n_reference: str | None = None,
    ) -> str:
        record = self.d["registros"][family]
        if id in self.by_id:
            current = self.by_id[id]
            if current["valor"] != value or current["estado"] != state:
                raise BuildError(f"número {id} reaparece com valor/estado diferente")
            return f'<span class="num" data-numero="{html.escape(id)}" data-estado="{state}">{text}</span>'
        number_record = {
            "id": id,
            "bloco": block,
            "etapa": stage,
            "ano": str(year),
            "valor": value,
            "estado": state,
            "fonte": record["fonte"],
            "arquivo": record["arquivo"],
            "calculo": record["calculo"],
            "n": int(n) if n is not None else None,
            "limites": list(limits if limits is not None else record["limites"]),
        }
        if n_reference is not None:
            number_record["n_referencia"] = str(n_reference)
        self.by_id[id] = number_record
        self.numbers.append(number_record)
        return f'<span class="num" data-numero="{html.escape(id)}" data-estado="{state}">{text}</span>'

    def enrollment_span(self, stage: str, year: str, family: str = "matricula") -> str:
        """Renderiza a matrícula da etapa/ano e registra o estado no JSON.

        A frase da ausência não sai daqui: o bloco a renderiza uma vez, com
        `enrollment_absences`, porque o motivo depende da presença da escola no Censo
        de 2024 e do ano.
        """
        key = (family, stage, str(year))
        if key in self.enrollment_cache:
            return self.enrollment_cache[key]
        value = self.e.get(f"mat_{stage}_{year}")
        if family == "creche":
            number_id = f"creche-{year}"
            block = "creche"
            stage_label = "creche"
        else:
            number_id = f"matricula-{stage_slug(stage)}-{year}"
            block = "matricula"
            stage_label = ENROLLMENT_LABEL[stage]
        if value is None:
            number_html = self._add(
                id=number_id, family=family, block=block, stage=stage_label,
                year=year, value=None, state="ausente", n=1, text="-",
            )
        elif int(value) == 0:
            number_html = self._add(
                id=number_id, family=family, block=block, stage=stage_label,
                year=year, value=0, state="zero", n=1, text="0",
            )
        else:
            number_html = self._add(
                id=number_id, family=family, block=block, stage=stage_label,
                year=year, value=int(value), state="valor", n=1, text=fmt_int(value),
            )
        self.enrollment_cache[key] = number_html
        return number_html

    def enrollment_absences(self, family: str, years: tuple[str, ...], stages: list[str]) -> str:
        """Frases de ausência de matrícula, uma por motivo e por bloco."""
        parts = []
        for year in years:
            missing = [
                stage for stage in stages if self.e.get(f"mat_{stage}_{year}") is None
            ]
            if not missing:
                continue
            if str(year) == "2024":
                if not self.e["censo_2024_presente"]:
                    parts.append(
                        self.absence(PHRASE_CENSUS_2024_NO_ROW, "L-63", "censo")
                    )
                else:
                    parts.append(self.absence(PHRASE_ENROLLMENT_2024, "L-28", "censo"))
            else:
                parts.append(self.absence(PHRASE_ENROLLMENT_2025, "L-28", "censo"))
        return "".join(parts)

    def rate_span(self, family: str, name: str, stage: str, n: int | None, entry: dict) -> str:
        value = entry.get("valor")
        state = str(entry.get("estado", "ausente"))
        if state == "nao_aplicavel":
            value, text = None, "—"
        elif state == "ausente" or value is None:
            state, value, text = "ausente", None, "-"
        elif float(value) == 0:
            state, value, text = "zero", 0.0, "0,0%"
        else:
            state, value, text = "valor", float(value), fmt_dec(value) + "%"
        return self._add(
            id=f"{family}-{stage_slug(stage)}-{name}-2025",
            family=family, block=family, stage=STAGE_LABEL[stage],
            year="2025", value=value, state=state, n=n, text=text,
        )

    def ideb_cell(self, stage: str, year: str, n: int | None) -> str:
        entry = get_indicator(self.d, self.e["co"], stage, "ideb_observado", year)
        n_reference = "2025" if str(year) != "2025" and n is not None else None
        if entry["estado"] == "valor" and entry["valor"] is not None:
            value = float(entry["valor"])
            state = "zero" if value == 0 else "valor"
            text = fmt_dec(value)
            return self._add(
                id=f"ideb-{stage_slug(stage)}-{year}", family="ideb", block="ideb",
                stage=STAGE_LABEL[stage], year=year, value=value, state=state, n=n,
                text=text, n_reference=n_reference,
            )
        if str(year) == "2025":
            return self._add(
                id=f"ideb-{stage_slug(stage)}-2025", family="ideb", block="ideb",
                stage=STAGE_LABEL[stage], year="2025", value=None, state="ausente", n=n,
                text="-",
            )
        return '<span class="simbolo" data-estado="ausente">-</span>'

    def source_note(self, family: str) -> str:
        r = self.d["registros"][family]
        return (
            f'<p class="fonte">Fonte: {html.escape(r["fonte"])} · '
            f'{html.escape(fmt_years(r["anos"]))} · {html.escape(r["calculo"])} · '
            f'limites: {html.escape(", ".join(r["limites"]))} · '
            f'<a href="dados/{self.e["co"]}.json">procedência</a></p>'
        )

    def absence(self, text: str, ids: str, anchor: str, state: str = "ausente") -> str:
        symbol = "—" if state == "nao_aplicavel" else "-"
        prefix = ""
        if not (text.startswith("—") or text.startswith("- ")):
            prefix = f'<span class="simbolo">{symbol}</span> '
        return (
            f'<p class="ausencia" data-estado="{state}">'
            f'{prefix}'
            f'<span class="texto">{html.escape(text)}</span> '
            f'<a class="id-limite" href="como-ler.html#{anchor}">{html.escape(ids)}</a>'
            "</p>"
        )

    def small_n(self, stage: str, n: int) -> str:
        word = student_word(n)
        return (
            '<p class="suprimido" data-estado="suprimido">'
            f'{self.enrollment_span(stage, "2025")} '
            f'<span class="texto">{word} {PHRASE_SMALL_N}</span> '
            '<a class="id-limite" href="como-ler.html#n">D4, L-40</a>'
            "</p>"
        )

    def _section_heading(self, title: str) -> str:
        return f"<h2>{html.escape(title)}</h2>"

    def _stage_article(self, block: str, stage: str, n: int | None, status: str, body: str) -> str:
        n_attr = "" if n is None else f' data-n="{int(n)}"'
        return (
            f'<article class="etapa" data-bloco="{block}" data-etapa="{stage}"'
            f'{n_attr} data-situacao="{status}">{body}</article>'
        )

    def render(self) -> str:
        e = self.e
        code = e["co"]
        has_ideb = has_published_ideb(self.d, e)
        has_rate = has_rate_row(self.d, e)

        parts = []
        parts.append(
            '<main>'
            f'<p class="trilha"><a href="index.html">Todas as escolas</a></p>'
            f'<h1>{html.escape(e["nome"])}</h1>'
            f'<p class="subtitulo">{html.escape(e["ra"])} · rede {html.escape(e["rede"])}</p>'
        )

        offers_assessed_stage = any(e[offering] for _, _, offering in STAGES)
        if offers_assessed_stage and not has_ideb and not has_rate:
            parts.append(self.absence(PHRASE_NO_INDICATOR, "L-09", "ideb"))

        # 1. identificação
        parts.append('<section class="bloco" id="identificacao">')
        parts.append(self._section_heading("Identificação"))
        parts.append(
            "<dl class=\"ficha\">"
            f"<dt>Escola</dt><dd>{html.escape(e['nome'])}</dd>"
            f"<dt>Região Administrativa</dt><dd>{html.escape(e['ra'])}</dd>"
            f"<dt>Rede</dt><dd>{html.escape(e['rede'])}</dd>"
            f"<dt>Código INEP</dt><dd>{html.escape(code)}</dd>"
            "</dl>"
            f'<p class="fonte">Rede no cadastro: {html.escape(e["rede_cadastro"])}.</p>'
            f'{self.source_note("identificacao")}'
            "</section>"
        )

        # 2. oferta
        parts.append('<section class="bloco" id="oferta">')
        parts.append(self._section_heading("Oferta por etapa"))
        parts.append('<table class="tabela"><thead><tr><th>Etapa</th><th>Oferta em 2025</th></tr></thead><tbody>')
        for column, item_label in OFFERINGS:
            value = "oferta" if e[column] == 1 else "não oferta"
            parts.append(f"<tr><td>{html.escape(item_label)}</td><td>{value}</td></tr>")
        parts.append("</tbody></table>")
        parts.append(self.source_note("oferta"))
        parts.append("</section>")

        # 3. matrícula
        parts.append('<section class="bloco" id="matricula">')
        parts.append(self._section_heading("Matrícula por etapa"))
        parts.append(
            '<table class="tabela"><thead><tr><th>Etapa</th><th>2024</th><th>2025</th></tr></thead><tbody>'
        )
        for stage, item_label in (("CRE", "Creche"), ("AI", "Anos iniciais"), ("AF", "Anos finais"), ("EM", "Ensino médio")):
            parts.append(
                f"<tr><td>{item_label}</td><td>{self.enrollment_span(stage, '2024')}</td>"
                f"<td>{self.enrollment_span(stage, '2025')}</td></tr>"
            )
        parts.append("</tbody></table>")
        parts.append(self.enrollment_absences("matricula", ("2024", "2025"), ["CRE", "AI", "AF", "EM"]))
        parts.append(self.source_note("matricula"))
        parts.append("</section>")

        # 4. Ideb
        parts.append('<section class="bloco" id="ideb">')
        parts.append(self._section_heading("Ideb por etapa"))
        for stage, item_label, offering in STAGES:
            if not e[offering]:
                body = (
                    f"<h3>{stage_title(item_label)}</h3>"
                    + self.absence(PHRASE_STAGE_NOT_OFFERED, "L-59", "estados", state="nao_aplicavel")
                )
                parts.append(self._stage_article("ideb", stage, None, "nao_ofertada", body))
                continue
            n = e.get(f"mat_{stage}_2025")
            year_2025 = get_indicator(self.d, code, stage, "ideb_observado")
            status = "publicado" if year_2025["estado"] == "valor" else "ausente"
            body = [f"<h3>{stage_title(item_label)}</h3>"]
            if n is None:
                body.append(
                    f'<p class="n">n = {self.enrollment_span(stage, "2025")} '
                    "em 2025 (matrícula da etapa)</p>"
                )
            else:
                body.append(
                    f'<p class="n">n = {self.enrollment_span(stage, "2025")} '
                    f'{student_word(n)} em 2025 (matrícula da etapa)</p>'
                )
            body.append('<table class="tabela tabela-estreita"><thead><tr><th>Ano</th><th>Ideb</th></tr></thead><tbody>')
            for year in IDEB_YEARS_BY_STAGE[stage]:
                body.append(f"<tr><td>{year}</td><td>{self.ideb_cell(stage, year, n)}</td></tr>")
            body.append("</tbody></table>")
            if year_2025["estado"] != "valor":
                if e["rede"].startswith("privada"):
                    body.append(self.absence(PHRASE_IDEB_PRIVATE, "L-08", "ideb-privada"))
                else:
                    body.append(self.absence(PHRASE_IDEB_PUBLIC, "L-09, L-30", "ideb"))
            parts.append(self._stage_article("ideb", stage, n, status, "".join(body)))
        parts.append(self.source_note("ideb"))
        parts.append("</section>")

        # 5. fluxo
        parts.append('<section class="bloco" id="fluxo">')
        parts.append(self._section_heading("Fluxo escolar"))
        for stage, item_label, offering in STAGES:
            if not e[offering]:
                body = f"<h3>{stage_title(item_label)}</h3>" + self.absence(
                    PHRASE_STAGE_NOT_OFFERED, "L-59", "estados", state="nao_aplicavel"
                )
                parts.append(self._stage_article("fluxo", stage, None, "nao_ofertada", body))
                continue
            n = e.get(f"mat_{stage}_2025")
            if n is None:
                body = (
                    f"<h3>{stage_title(item_label)}</h3>"
                    f'<p class="n">n = {self.enrollment_span(stage, "2025")} em 2025</p>'
                    + self.absence(PHRASE_ENROLLMENT_2025, "L-28", "censo")
                )
                parts.append(self._stage_article("fluxo", stage, None, "ausente", body))
                continue
            if n < self.threshold:
                body = f"<h3>{stage_title(item_label)}</h3>" + self.small_n(stage, n)
                parts.append(self._stage_article("fluxo", stage, n, "suprimido", body))
                continue
            rows = []
            has_value = False
            for name, label in (("aprovacao", "Aprovação"), ("reprovacao", "Reprovação"), ("abandono", "Abandono")):
                entry = get_indicator(self.d, code, stage, name)
                if entry["estado"] in ("valor", "zero"):
                    has_value = True
                rows.append(
                    f"<tr><td>{label}</td><td>{self.rate_span('fluxo', name, stage, n, entry)}</td></tr>"
                )
            body = f"<h3>{stage_title(item_label)}</h3>"
            body += f'<p class="n">n = {self.enrollment_span(stage, "2025")} {student_word(n)} em 2025</p>'
            body += '<table class="tabela"><thead><tr><th>Indicador</th><th>2025</th></tr></thead><tbody>'
            body += "".join(rows) + "</tbody></table>"
            parts.append(self._stage_article("fluxo", stage, n, "publicado" if has_value else "ausente", body))
        parts.append(self.source_note("fluxo"))
        parts.append("</section>")

        # 6. distorção idade-série
        parts.append('<section class="bloco" id="tdi">')
        parts.append(self._section_heading("Distorção idade-série"))
        for stage, item_label, offering in STAGES:
            if not e[offering]:
                body = f"<h3>{stage_title(item_label)}</h3>" + self.absence(
                    PHRASE_STAGE_NOT_OFFERED, "L-59", "estados", state="nao_aplicavel"
                )
                parts.append(self._stage_article("tdi", stage, None, "nao_ofertada", body))
                continue
            n = e.get(f"mat_{stage}_2025")
            if n is None:
                body = (
                    f"<h3>{stage_title(item_label)}</h3>"
                    f'<p class="n">n = {self.enrollment_span(stage, "2025")} em 2025</p>'
                    + self.absence(PHRASE_ENROLLMENT_2025, "L-28", "censo")
                )
                parts.append(self._stage_article("tdi", stage, None, "ausente", body))
                continue
            if n < self.threshold:
                body = f"<h3>{stage_title(item_label)}</h3>" + self.small_n(stage, n)
                parts.append(self._stage_article("tdi", stage, n, "suprimido", body))
                continue
            entry = get_indicator(self.d, code, stage, "tdi")
            body = (
                f"<h3>{stage_title(item_label)}</h3>"
                f'<p class="n">n = {self.enrollment_span(stage, "2025")} {student_word(n)} em 2025</p>'
                '<table class="tabela"><thead><tr><th>Indicador</th><th>2025</th></tr></thead><tbody>'
                f"<tr><td>Distorção idade-série</td><td>{self.rate_span('tdi', 'tdi', stage, n, entry)}</td></tr>"
                "</tbody></table>"
            )
            parts.append(self._stage_article("tdi", stage, n, "publicado" if entry["estado"] in ("valor", "zero") else "ausente", body))
        parts.append(self.source_note("tdi"))
        parts.append("</section>")

        # 7. não-resposta
        parts.append('<section class="bloco" id="tnr">')
        parts.append(self._section_heading("Taxa de não-resposta"))
        for stage, item_label, offering in STAGES:
            if not e[offering]:
                body = f"<h3>{stage_title(item_label)}</h3>" + self.absence(
                    PHRASE_STAGE_NOT_OFFERED, "L-59", "estados", state="nao_aplicavel"
                )
                parts.append(self._stage_article("tnr", stage, None, "nao_ofertada", body))
                continue
            n = e.get(f"mat_{stage}_2025")
            if n is None:
                body = (
                    f"<h3>{stage_title(item_label)}</h3>"
                    f'<p class="n">n = {self.enrollment_span(stage, "2025")} em 2025</p>'
                    + self.absence(PHRASE_ENROLLMENT_2025, "L-28", "censo")
                )
                parts.append(self._stage_article("tnr", stage, None, "ausente", body))
                continue
            if n < self.threshold:
                body = f"<h3>{stage_title(item_label)}</h3>" + self.small_n(stage, n)
                parts.append(self._stage_article("tnr", stage, n, "suprimido", body))
                continue
            entry = get_indicator(self.d, code, stage, "tnr")
            body = (
                f"<h3>{stage_title(item_label)}</h3>"
                f'<p class="n">n = {self.enrollment_span(stage, "2025")} {student_word(n)} em 2025</p>'
                '<table class="tabela"><thead><tr><th>Indicador</th><th>2025</th></tr></thead><tbody>'
                f"<tr><td>Taxa de não-resposta</td><td>{self.rate_span('tnr', 'tnr', stage, n, entry)}</td></tr>"
                "</tbody></table>"
            )
            parts.append(self._stage_article("tnr", stage, n, "publicado" if entry["estado"] in ("valor", "zero") else "ausente", body))
        parts.append(
            '<p class="nota">A taxa de não-resposta mede falta de informação de rendimento '
            'e movimento, não participação no Saeb. <a href="como-ler.html#tnr">Como ler</a>.</p>'
        )
        parts.append(self.source_note("tnr"))
        parts.append("</section>")

        # 8. infraestrutura
        parts.append('<section class="bloco" id="infraestrutura">')
        parts.append(self._section_heading("Infraestrutura"))
        infra_universe = e["oferta_fund_ai"] == 1 or e["oferta_fund_af"] == 1 or e["oferta_med"] == 1
        if not infra_universe:
            parts.append(
                self.absence(
                    PHRASE_INFRA_NOT_APPLICABLE, "L-25", "infraestrutura", state="nao_aplicavel"
                )
            )
        else:
            parts.append('<table class="tabela"><thead><tr><th>Item</th><th>Declarado em 2025</th></tr></thead><tbody>')
            for item, item_label in INFRA_ITEMS:
                entry = self.d["infra"].get((code, item), {"valor": None, "estado": "ausente"})
                if entry["estado"] == "valor" and entry["valor"] is not None:
                    text = "tem" if entry["valor"] == 1 else "não tem"
                    cell = self._add(
                        id=f"infra-{item.lower()}", family="infraestrutura", block="infraestrutura",
                        stage="", year="2025", value=int(entry["valor"]), state="valor", n=1, text=text,
                    )
                else:
                    cell = self._add(
                        id=f"infra-{item.lower()}", family="infraestrutura", block="infraestrutura",
                        stage="", year="2025", value=None, state="ausente", n=1, text="-",
                    )
                parts.append(f"<tr><td>{html.escape(item_label)}</td><td>{cell}</td></tr>")
            parts.append("</tbody></table>")
            parts.append('<p class="nota">O item é o que a escola declarou ao Censo Escolar de 2025.</p>')
        parts.append(self.source_note("infraestrutura"))
        parts.append("</section>")

        # 9. creche (só quando a escola oferta creche)
        if e["oferta_inf_cre"] == 1:
            parts.append('<section class="bloco" id="creche">')
            parts.append(self._section_heading("Creche da escola"))
            parts.append('<table class="tabela tabela-estreita"><thead><tr><th>Ano</th><th>Matrícula em creche</th></tr></thead><tbody>')
            for year in ("2024", "2025"):
                parts.append(
                    f"<tr><td>{year}</td><td>{self.enrollment_span('CRE', year, 'creche')}</td></tr>"
                )
            parts.append("</tbody></table>")
            parts.append(self.enrollment_absences("creche", ("2024", "2025"), ["CRE"]))
            parts.append(self.source_note("creche"))
            parts.append("</section>")

        parts.append(
            f'<p class="rodape-pagina">Procedência de cada número: '
            f'<a href="dados/{code}.json">dados/{code}.json</a>. '
            '<a href="como-ler.html">Como ler os números</a> · '
            '<a href="creditos.html">Créditos e licenças</a>.</p>'
        )
        parts.append("</main>")
        return "".join(parts)


def _clean_output(site: Path) -> None:
    for name in ("index.html", "creditos.html", "como-ler.html", "estilo.css", "indice.json"):
        target = site / name
        if target.is_file():
            target.unlink()
    for target in site.glob("[0-9]" * 8 + ".html"):
        target.unlink()
    data_dir = site / "dados"
    if data_dir.is_dir():
        for target in data_dir.glob("*.json"):
            target.unlink()


def _total_size(site: Path) -> int:
    return sum(p.stat().st_size for p in site.rglob("*") if p.is_file())


def build_site(public: Path, out: Path, data_build: str, threshold: int, quiet: bool = False) -> dict:
    """Gera o site inteiro; devolve contagens e tamanho."""
    data = load_data(public)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "dados").mkdir(parents=True, exist_ok=True)
    _clean_output(out)

    (out / "estilo.css").write_text(CSS, encoding="utf-8")

    index_entries = [
        {"co_entidade": e["co"], "nome": e["nome"], "ra": e["ra"], "rede": e["rede"]}
        for e in data["escolas"]
    ]
    index_entries.sort(key=lambda x: (x["nome"], x["co_entidade"]))
    (out / "indice.json").write_text(
        json.dumps(index_entries, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    (out / "index.html").write_text(render_index_page(data, data_build, threshold), encoding="utf-8")
    (out / "como-ler.html").write_text(render_how_to_read_page(data_build, threshold), encoding="utf-8")
    (out / "creditos.html").write_text(render_credits_page(data, data_build, threshold), encoding="utf-8")

    for school in data["escolas"]:
        page = SchoolPage(data, school, data_build, threshold)
        body = page.render()
        (out / f'{school["co"]}.html').write_text(
            document(f'{school["nome"]} — Prova dos Nove', body, data_build, threshold),
            encoding="utf-8",
        )
        (out / "dados" / f'{school["co"]}.json').write_text(
            json.dumps(
                {"escola": school["co"], "gerado_em": data_build, "numeros": page.numbers},
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    total = _total_size(out)
    if total > MAX_SITE_BYTES:
        raise BuildError(
            f"site com {total / (1024 * 1024):.1f} MB passa do limite de "
            f"{MAX_SITE_BYTES / (1024 * 1024):.0f} MB"
        )
    if not quiet:
        print(
            f"site: {len(data['escolas']):,} páginas de escola, "
            f"{total / (1024 * 1024):.1f} MB em {out}"
        )
    return {"escolas": len(data["escolas"]), "bytes": total, "dados": data}


def read_page(site: Path, code: str) -> str:
    return (site / f"{code}.html").read_text(encoding="utf-8")


def read_school_json(site: Path, code: str) -> dict:
    path = site / "dados" / f"{code}.json"
    if not path.is_file():
        raise BuildError(f"falta {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def number_ids(markup: str) -> list[str]:
    return re.findall(r'data-numero="([^"]+)"', markup)


def check_provenance(site: Path, data: dict, data_build: str) -> str:
    for school in data["escolas"]:
        markup = read_page(site, school["co"])
        record = read_school_json(site, school["co"])
        if record.get("escola") != school["co"]:
            raise BuildError(f"{school['co']}: JSON de procedência com escola diferente")
        if record.get("gerado_em") != data_build:
            raise BuildError(f"{school['co']}: JSON de procedência com gerado_em diferente")
        numbers = record.get("numeros")
        if not isinstance(numbers, list) or not numbers:
            raise BuildError(f"{school['co']}: JSON de procedência sem números")
        by_id = {}
        for number in numbers:
            identifier = number.get("id")
            if not identifier or identifier in by_id:
                raise BuildError(f"{school['co']}: número sem id ou id duplicado")
            by_id[identifier] = number
        for identifier in number_ids(markup):
            if identifier not in by_id:
                raise BuildError(f"{school['co']}: número {identifier} sem procedência")
            number = by_id[identifier]
            for field in ("fonte", "arquivo", "ano", "calculo", "estado"):
                if not number.get(field):
                    raise BuildError(f"{school['co']}: {identifier} sem {field}")
            n = number.get("n")
            if not (n is None or isinstance(n, int)):
                raise BuildError(f"{school['co']}: {identifier} sem n inteiro ou null")
            if n is None:
                if number.get("bloco") not in STUDENT_COUNT_FAMILIES:
                    raise BuildError(
                        f"{school['co']}: {identifier} com n null fora de família de alunos"
                    )
                # Ideb com valor e denominador ausente continua sendo valor; as
                # taxas (fluxo, TDI, TNR) são suprimidas e ficam ausentes.
                if number["bloco"] == "ideb":
                    states_when_n_null = ("valor", "zero", "ausente")
                else:
                    states_when_n_null = ("ausente", "nao_aplicavel")
                if number["estado"] not in states_when_n_null:
                    raise BuildError(
                        f"{school['co']}: {identifier} com n null e estado {number['estado']}"
                    )
                slug = SLUG_BY_STAGE_LABEL.get(number.get("etapa"))
                if slug is None or (
                    f'data-numero="matricula-{slug}-2025" data-estado="ausente"' not in markup
                ):
                    raise BuildError(
                        f"{school['co']}: {identifier} com n null sem matrícula ausente na página"
                    )
            if not number.get("limites"):
                raise BuildError(f"{school['co']}: {identifier} sem limites")
            if number["estado"] not in STATES:
                raise BuildError(f"{school['co']}: {identifier} com estado fora do contrato")
            if number["estado"] in ("valor", "zero") and number.get("valor") is None:
                raise BuildError(f"{school['co']}: {identifier} com estado {number['estado']} e valor nulo")
            if number["estado"] in ("ausente", "nao_aplicavel") and number.get("valor") is not None:
                raise BuildError(f"{school['co']}: {identifier} com estado {number['estado']} e valor")
            if not str(number["arquivo"]).startswith("data/public/"):
                raise BuildError(f"{school['co']}: {identifier} aponta para fora de data/public")
            requires_reference = (
                number.get("bloco") in STUDENT_COUNT_FAMILIES
                and str(number.get("ano")) != "2025"
                and n is not None
            )
            if requires_reference and number.get("n_referencia") != "2025":
                raise BuildError(
                    f"{school['co']}: {identifier} sem n_referencia = '2025' para ano != 2025"
                )
            if not requires_reference and "n_referencia" in number:
                raise BuildError(
                    f"{school['co']}: {identifier} com n_referencia onde não há outro ano de n"
                )
    return f"{len(data['escolas']):,} páginas com procedência completa"


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


def check_threshold(site: Path, data: dict, threshold: int) -> str:
    units = 0
    with_tdi = 0
    without_enrollment = 0
    for school in data["escolas"]:
        markup = read_page(site, school["co"])
        for stage, _, offering in STAGES:
            if not school[offering]:
                continue
            n = school.get(f"mat_{stage}_2025")
            if n is not None and n >= threshold:
                continue
            if n is None:
                without_enrollment += 1
            else:
                units += 1
                if get_indicator(data, school["co"], stage, "tdi")["estado"] in ("valor", "zero"):
                    with_tdi += 1
            word = student_word(n)
            note = f"{n} {word} {PHRASE_SMALL_N}"
            for block in ("fluxo", "tdi", "tnr"):
                found_block = re.search(
                    rf'<article class="etapa" data-bloco="{block}" data-etapa="{stage}"[^>]*>(.*?)</article>',
                    markup,
                    re.S,
                )
                if not found_block:
                    raise BuildError(f"{school['co']}/{stage}/{block}: falta o cartão da etapa")
                snippet = found_block.group(1)
                if n is None:
                    if 'data-situacao="suprimido"' not in found_block.group(0) and 'data-situacao="ausente"' not in found_block.group(0):
                        raise BuildError(f"{school['co']}/{stage}/{block}: n ausente não foi suprimido")
                    if PHRASE_ENROLLMENT_2025 not in re.sub(r"<[^>]+>", "", snippet):
                        raise BuildError(f"{school['co']}/{stage}/{block}: falta a frase de 2025")
                else:
                    if 'data-situacao="suprimido"' not in found_block.group(0):
                        raise BuildError(f"{school['co']}/{stage}/{block}: n < {threshold} não foi suprimido")
                    if note not in re.sub(r"<[^>]+>", "", snippet):
                        raise BuildError(f"{school['co']}/{stage}/{block}: falta a nota de amostra pequena")
                if re.search(rf'data-numero="{block}-[^"]+"', snippet):
                    raise BuildError(f"{school['co']}/{stage}/{block}: publica taxa sem denominador")

    target = "53001419"
    markup = read_page(site, target)
    if 15 < threshold:
        if "15 alunos nesta etapa — o indicador não é publicado quando a turma é pequena" not in re.sub(
            r"<[^>]+>", "", markup
        ):
            raise BuildError(f"{target}: falta a nota de 15 alunos")
        if "0,0%" in markup:
            raise BuildError(f"{target}: TDI 0,0% aparece como taxa mesmo com 15 alunos")
    return (
        f"{units:,} unidades escola × etapa com n < {threshold} suprimidas "
        f"({with_tdi:,} delas com TDI valor/zero, a matriz do q16); "
        f"{without_enrollment:,} sem matrícula de 2025 também suprimidas"
    )


def check_states(site: Path, data: dict, threshold: int) -> str:
    phrases = {
        "53000862": [PHRASE_IDEB_PUBLIC],
        "53000781": [PHRASE_IDEB_PRIVATE],
        "53000226": [PHRASE_STAGE_NOT_OFFERED],
        "53020529": [PHRASE_CENSUS_2024_NO_ROW, PHRASE_NO_INDICATOR],
        "53013662": [PHRASE_ENROLLMENT_2024],
        "53000331": [PHRASE_NO_INDICATOR],
    }
    if 15 < threshold:
        phrases["53001419"] = [
            "15 alunos nesta etapa — o indicador não é publicado quando a turma é pequena"
        ]
    for code, entries in phrases.items():
        markup = read_page(site, code)
        visible_text = re.sub(r"<[^>]+>", "", markup)
        for phrase in entries:
            if phrase not in visible_text:
                raise BuildError(f"{code}: frase ausente ou com redação diferente: {phrase!r}")

    for school in data["escolas"]:
        markup = read_page(site, school["co"])
        if "NaN" in markup:
            raise BuildError(f"{school['co']}: NaN na página")
        visible_text = re.sub(r"<[^>]+>", "", markup)
        if not school["censo_2024_presente"]:
            if PHRASE_CENSUS_2024_NO_ROW not in visible_text:
                raise BuildError(f"{school['co']}: sem linha em 2024 e sem a frase de L-63")
            if PHRASE_ENROLLMENT_2024 in visible_text:
                raise BuildError(f"{school['co']}: sem linha em 2024 com a frase de célula vazia")
        elif any(school.get(f"mat_{stage}_2024") is None for stage in ("CRE", "AI", "AF", "EM")):
            if PHRASE_ENROLLMENT_2024 not in visible_text:
                raise BuildError(f"{school['co']}: célula vazia em 2024 sem a frase de L-28")
            if PHRASE_CENSUS_2024_NO_ROW in visible_text:
                raise BuildError(f"{school['co']}: linha em 2024 com a frase de escola ausente")
        elif (
            PHRASE_ENROLLMENT_2024 in visible_text
            or PHRASE_CENSUS_2024_NO_ROW in visible_text
        ):
            raise BuildError(f"{school['co']}: frase de 2024 sem ausência de 2024")
        for state, snippet in re.findall(
            r'data-estado="(ausente|nao_aplicavel|zero|valor)"[^>]*>([^<]*)<', markup
        ):
            text = html.unescape(snippet).strip()
            if state == "ausente" and text and not text.startswith("-"):
                raise BuildError(f"{school['co']}: estado ausente sem hífen: {text!r}")
            if state == "nao_aplicavel" and text and not text.startswith("—"):
                raise BuildError(f"{school['co']}: estado nao_aplicavel sem travessão: {text!r}")
            if state == "zero" and text and not text.startswith("0"):
                raise BuildError(f"{school['co']}: estado zero sem 0: {text!r}")
    return "símbolos, frases de 2024 e presença no Censo conferidos"


def site_hashes(site: Path) -> dict[str, str]:
    return {
        str(p.relative_to(site)): sha256(p)
        for p in sorted(site.rglob("*"))
        if p.is_file()
    }


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


def check_edge_cases(public: Path, data_build: str) -> str:
    """Reproduz os casos de borda em uma cópia do insumo, sem build completo.

    Copia `data/public/` para um diretório temporário, altera as escolas dos
    casos, recalcula o sha256 e passa pelo `load_data` (portanto pela coluna
    nova e pelo guard de sha256). Renderiza só as escolas afetadas.
    """
    public = Path(public)
    temp_base = Path("/tmp/opencode") if Path("/tmp/opencode").is_dir() else None
    columns_2024 = ["mat_inf_cre_2024", "mat_fund_ai_2024", "mat_fund_af_2024", "mat_med_2024"]
    with tempfile.TemporaryDirectory(prefix="prova-dos-nove-casos-", dir=temp_base) as tmp:
        tmp = Path(tmp)
        for name in ("escolas.parquet", "indicadores.parquet", "infraestrutura.parquet", "procedencia.json"):
            shutil.copy2(public / name, tmp / name)

        schools = pd.read_parquet(tmp / "escolas.parquet")

        def alter(code: str, column: str, value) -> None:
            mask = schools["co_entidade"].astype(str) == code
            if not mask.any():
                raise BuildError(f"caso de limite: escola {code} não está no insumo")
            schools.loc[mask, column] = value

        # 2025 sem matrícula em anos iniciais; creche 2025 sem matrícula.
        alter("53000854", "mat_fund_ai_2025", pd.NA)
        alter("53000781", "mat_inf_cre_2025", pd.NA)
        # Os dois casos de 2024: sem linha e com linha e células vazias.
        alter("53020529", "censo_2024_presente", False)
        for column in columns_2024:
            alter("53020529", column, pd.NA)
        alter("53013662", "censo_2024_presente", True)
        for column in columns_2024:
            alter("53013662", column, pd.NA)
        # Oferta de 2025 não descreve a matrícula de 2024.
        alter("53014618", "oferta_fund_ai", 0)
        alter("53014618", "mat_fund_ai_2024", 493)
        # n = 0 precisa ser gravado como 0 quando o limiar é 0.
        alter("53000986", "mat_med_2025", 0)
        # Creche com célula vazia em 2024 (o 53000781 tem 2024 com valor).
        alter("53001419", "mat_inf_cre_2024", pd.NA)

        for column in (
            "mat_inf_cre_2024", "mat_fund_ai_2024", "mat_fund_af_2024", "mat_med_2024",
            "mat_inf_cre_2025", "mat_fund_ai_2025", "mat_fund_af_2025", "mat_med_2025",
        ):
            schools[column] = schools[column].astype("Int64")
        schools["censo_2024_presente"] = schools["censo_2024_presente"].astype(bool)
        schools.to_parquet(tmp / "escolas.parquet", index=False)

        provenance = json.loads((tmp / "procedencia.json").read_text(encoding="utf-8"))
        provenance["sha256"]["escolas.parquet"] = sha256(tmp / "escolas.parquet")
        (tmp / "procedencia.json").write_text(
            json.dumps(provenance, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

        data = load_data(tmp)

        def page(code: str, threshold: int) -> tuple[SchoolPage, str, str]:
            school = data["por_co"][code]
            p = SchoolPage(data, school, data_build, threshold)
            markup = p.render()
            return p, markup, re.sub(r"<[^>]+>", "", markup)

        def number(p: SchoolPage, identifier: str) -> dict:
            for item in p.numbers:
                if item["id"] == identifier:
                    return item
            raise BuildError(f"caso de limite: falta o número {identifier}")

        # 1. 2024 sem linha: frase de L-63, nunca a de célula vazia.
        p, markup, text = page("53020529", 30)
        if PHRASE_CENSUS_2024_NO_ROW not in text:
            raise BuildError("53020529: falta 'a escola não consta do Censo de 2024'")
        if PHRASE_ENROLLMENT_2024 in text:
            raise BuildError("53020529: usa a frase de célula vazia sem ter linha em 2024")
        if number(p, "matricula-ai-2024")["estado"] != "ausente":
            raise BuildError("53020529: matrícula de 2024 não está ausente")

        # 2. 2024 com linha e célula vazia: frase de L-28.
        p, markup, text = page("53013662", 30)
        if PHRASE_ENROLLMENT_2024 not in text:
            raise BuildError("53013662: falta 'matrícula não declarada no Censo de 2024'")
        if PHRASE_CENSUS_2024_NO_ROW in text:
            raise BuildError("53013662: usa a frase de escola ausente tendo linha em 2024")
        if number(p, "matricula-ai-2024")["estado"] != "ausente":
            raise BuildError("53013662: matrícula de 2024 não está ausente")

        # 3. 2025 sem matrícula: sem taxa, n = -, Ideb com n null. n_referencia
        #    só aparece nas linhas históricas com n presente (teste 3b).
        p, markup, text = page("53000854", 30)
        if PHRASE_ENROLLMENT_2025 not in text:
            raise BuildError("53000854: falta 'matrícula não declarada no Censo de 2025'")
        if "n = -" not in text:
            raise BuildError("53000854: a linha do n não mostra '-'")
        if number(p, "matricula-ai-2025")["estado"] != "ausente":
            raise BuildError("53000854: matrícula de AI em 2025 não está ausente")
        for item in p.numbers:
            if item["bloco"] in ("fluxo", "tdi", "tnr") and item["etapa"] == "anos iniciais":
                raise BuildError(f"53000854: publica taxa de AI sem denominador ({item['id']})")
            if item["bloco"] in STUDENT_COUNT_FAMILIES and item["n"] == 1:
                raise BuildError(f"53000854: n virou 1 em {item['id']}")
            if item["bloco"] == "ideb" and item["etapa"] == "anos iniciais":
                if item["ano"] == "2025":
                    if item["n"] is not None:
                        raise BuildError("53000854: Ideb de 2025 deveria ter n null")
                    if "n_referencia" in item:
                        raise BuildError("53000854: Ideb de 2025 não leva n_referencia")
                else:
                    if item["n"] is not None:
                        raise BuildError("53000854: Ideb histórico deveria ter n null")
                    if "n_referencia" in item:
                        raise BuildError(
                            "53000854: Ideb histórico com n null não leva n_referencia"
                        )

        # 3b. Ideb histórico com n presente continua carimbando o ano do n.
        for item in p.numbers:
            if (
                item["bloco"] == "ideb"
                and item["etapa"] == "anos finais"
                and item["ano"] != "2025"
            ):
                if item["n"] != 138:
                    raise BuildError("53000854: Ideb histórico de AF deveria ter n = 138")
                if item.get("n_referencia") != "2025":
                    raise BuildError(
                        "53000854: Ideb histórico de AF sem n_referencia 2025"
                    )

        # 4. Creche 2025 ausente usa a frase de 2025; 2024 presente não a usa.
        p, markup, text = page("53000781", 30)
        if PHRASE_ENROLLMENT_2025 not in text:
            raise BuildError("53000781: falta a frase de 2025 no bloco da creche")
        if PHRASE_ENROLLMENT_2024 in text or PHRASE_CENSUS_2024_NO_ROW in text:
            raise BuildError("53000781: bloco da creche com frase de 2024 sem célula vazia")
        if number(p, "creche-2025")["estado"] != "ausente":
            raise BuildError("53000781: creche 2025 não está ausente")
        if number(p, "creche-2024")["estado"] != "valor":
            raise BuildError("53000781: creche 2024 deveria continuar com valor")

        # 4b. Creche com célula vazia em 2024 usa a frase de L-28.
        p, markup, text = page("53001419", 30)
        if PHRASE_ENROLLMENT_2024 not in text:
            raise BuildError("53001419: falta a frase de célula vazia de 2024 na creche")
        if number(p, "creche-2024")["estado"] != "ausente":
            raise BuildError("53001419: creche 2024 não está ausente")

        # 5. 36 school-years: oferta de 2025 não apaga matrícula positiva de 2024.
        p, markup, text = page("53014618", 30)
        item = number(p, "matricula-ai-2024")
        if item["estado"] != "valor" or item["valor"] != 493:
            raise BuildError("53014618: 493 alunos em AI/2024 não aparecem como valor")

        # 6. Limiar 0: n = 0 é gravado como 0, não como 1.
        p, markup, text = page("53000986", 0)
        rates = [
            item for item in p.numbers
            if item["bloco"] in ("fluxo", "tdi", "tnr") and item["etapa"] == "ensino médio"
        ]
        if not rates:
            raise BuildError("53000986: nenhuma taxa do médio renderizada a limiar 0")
        if any(item["n"] != 0 for item in rates):
            raise BuildError("53000986: n=0 não foi gravado como 0 a limiar 0")

    return (
        "53 sem linha/3 com célula vazia em 2024, 2025 e creche ausentes, "
        "493 em 2024 preservado e n=0 a limiar 0 conferidos"
    )


def check_licenses(site: Path, data: dict) -> str:
    records = data["registros"]
    license_by_source: dict[str, tuple[str, str | None]] = {}
    for family, record in records.items():
        license_name = record.get("licenca")
        if not license_name:
            raise BuildError(f"registro {family!r} sem licença em procedencia.json")
        lowercase = str(license_name).lower()
        if any(term in lowercase for term in ("odbl", "odc", "open data commons")):
            raise BuildError(f"registro {family!r} publicado sob licença ODbL: {license_name!r}")
        license_by_source[record["fonte"]] = (license_name, record.get("licenca_url"))

    sources = set()
    for path in sorted((site / "dados").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        for number in record["numeros"]:
            source = number["fonte"]
            sources.add(source)
            lowercase = source.lower()
            for term in ("odbl", "odc", "open data commons", "matriculas__relatorio_matriculas"):
                if term in lowercase:
                    raise BuildError(f"{path.name}: fonte ODbL/matrículas proibida: {source}")
            if source not in license_by_source:
                raise BuildError(f"{path.name}: fonte {source!r} sem licença no insumo")

    credits_html = (site / "creditos.html").read_text(encoding="utf-8")
    for source in sources:
        if source not in credits_html:
            raise BuildError(f"creditos.html não lista a fonte {source!r}")
        license_name, url = license_by_source[source]
        if html.escape(license_name) not in credits_html:
            raise BuildError(f"creditos.html não mostra a licença de {source!r}")
        if url and html.escape(url, quote=True) not in credits_html:
            raise BuildError(f"creditos.html não mostra a licenca_url de {source!r}")
    for required in ("MIT", "CC BY 4.0", "Marcelo Anaissi"):
        if required not in credits_html:
            raise BuildError(f"creditos.html sem {required!r}")
    return f"{len(sources)} fontes com licença declarada nos créditos"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build estático da página por escola (FASE-1).")
    ap.add_argument("--public", type=Path, default=Path("data/public"), help="diretório do insumo público")
    ap.add_argument("--out", type=Path, default=Path("site"), help="diretório de saída")
    ap.add_argument("--data-build", default=DEFAULT_DATA_BUILD, help="único carimbo de tempo do build")
    ap.add_argument("--limiar-n", type=int, default=DEFAULT_N_THRESHOLD, help="limiar de n pequeno (D4)")
    ap.add_argument("--check", action="store_true", help="roda os critérios do §8 e os casos de limite")
    ap.add_argument("--check-procedencia", action="store_true", help="critério 1: procedência de todo número")
    ap.add_argument("--check-limiar", action="store_true", help="critério 3: n < limiar não publica taxa")
    ap.add_argument("--check-estados", action="store_true", help="critério 4: valor, zero, ausente e não aplicável")
    ap.add_argument("--check-licencas", action="store_true", help="critério 6: licenças e fontes")
    ap.add_argument("--check-casos", action="store_true", help="casos de limite: 2024, 2025, creche, 493 e limiar 0")
    args = ap.parse_args(argv)
    if args.limiar_n < 0:
        ap.error("--limiar-n não pode ser negativo")

    try:
        result = build_site(args.public, args.out, args.data_build, args.limiar_n)
    except (BuildError, FileNotFoundError, ValueError) as exc:
        print(f"ERRO: {exc}")
        return 1

    selected = []
    if args.check:
        selected = [
            "procedencia", "ranking", "limiar", "estados",
            "reprodutibilidade", "licencas", "casos_limite",
        ]
    else:
        if args.check_procedencia:
            selected.append("procedencia")
        if args.check_limiar:
            selected.append("limiar")
        if args.check_estados:
            selected.append("estados")
        if args.check_licencas:
            selected.append("licencas")
        if args.check_casos:
            selected.append("casos_limite")

    checks_by_key = {
        "procedencia": lambda: check_provenance(args.out, result["dados"], args.data_build),
        "ranking": lambda: check_no_ranking(args.out),
        "limiar": lambda: check_threshold(args.out, result["dados"], args.limiar_n),
        "estados": lambda: check_states(args.out, result["dados"], args.limiar_n),
        "reprodutibilidade": lambda: check_reproducibility(
            args.public, args.out, args.data_build, args.limiar_n
        ),
        "licencas": lambda: check_licenses(args.out, result["dados"]),
        "casos_limite": lambda: check_edge_cases(args.public, args.data_build),
    }
    for name in selected:
        try:
            detail = checks_by_key[name]()
        except BuildError as exc:
            print(f"[falhou] {name}: {exc}")
            return 1
        print(f"[ok] {name}: {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
