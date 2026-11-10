"""Página de uma escola e o coletor de procedência dos números.

Entrada: modelo de `loader.load_data`, escola, carimbo e limiar de n.
Saída: HTML da página e a lista de números com procedência.
Idempotente: sim — render puro sobre o modelo."""

from __future__ import annotations

import html

from .errors import BuildError
from .contract import STAGES, STAGE_LABEL, ENROLLMENT_LABEL, OFFERINGS, INFRA_ITEMS, IDEB_YEARS_BY_STAGE, PHRASE_STAGE_NOT_OFFERED, PHRASE_IDEB_PRIVATE, PHRASE_IDEB_PUBLIC, PHRASE_CENSUS_2024_NO_ROW, PHRASE_ENROLLMENT_2024, PHRASE_ENROLLMENT_2025, PHRASE_NO_INDICATOR, PHRASE_INFRA_NOT_APPLICABLE, PHRASE_SMALL_N
from .fmt import fmt_int, fmt_dec, fmt_years, stage_slug, stage_title, student_word
from .loader import get_indicator, has_published_ideb, has_rate_row


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
