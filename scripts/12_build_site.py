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
import hashlib
import html
import json
import re
import shutil
import tempfile
from pathlib import Path

import pandas as pd

DEFAULT_DATA_BUILD = "2026-11-06"
DEFAULT_N_THRESHOLD = 30
MAX_SITE_BYTES = 700 * 1024 * 1024

STAGES = [
    ("AI", "anos iniciais", "oferta_fund_ai"),
    ("AF", "anos finais", "oferta_fund_af"),
    ("EM", "ensino médio", "oferta_med"),
]
STAGE_LABEL = {stage_code: label for stage_code, label, _ in STAGES}
STAGE_SLUG = {"AI": "ai", "AF": "af", "EM": "em", "CRE": "creche"}
ENROLLMENT_COLUMNS = {
    ("CRE", "2024"): "mat_inf_cre_2024",
    ("CRE", "2025"): "mat_inf_cre_2025",
    ("AI", "2024"): "mat_fund_ai_2024",
    ("AI", "2025"): "mat_fund_ai_2025",
    ("AF", "2024"): "mat_fund_af_2024",
    ("AF", "2025"): "mat_fund_af_2025",
    ("EM", "2024"): "mat_med_2024",
    ("EM", "2025"): "mat_med_2025",
}
ENROLLMENT_LABEL = {"CRE": "creche", "AI": "anos iniciais", "AF": "anos finais", "EM": "ensino médio"}
OFFERINGS = [
    ("oferta_inf_cre", "Creche"),
    ("oferta_inf_pre", "Pré-escola"),
    ("oferta_fund_ai", "Anos iniciais do ensino fundamental"),
    ("oferta_fund_af", "Anos finais do ensino fundamental"),
    ("oferta_med", "Ensino médio"),
    ("oferta_eja", "Educação de jovens e adultos"),
    ("oferta_esp", "Educação especial"),
    ("oferta_prof", "Educação profissional"),
]
INFRA_ITEMS = [
    ("IN_BIBLIOTECA", "Biblioteca"),
    ("IN_SALA_LEITURA", "Sala de leitura"),
    ("IN_QUADRA_ESPORTES", "Quadra de esportes"),
    ("IN_LABORATORIO_INFORMATICA", "Laboratório de informática"),
    ("IN_LABORATORIO_CIENCIAS", "Laboratório de ciências"),
    ("IN_INTERNET_ALUNOS", "Internet para os alunos"),
    ("IN_REFEITORIO", "Refeitório"),
    ("IN_BANHEIRO_PNE", "Banheiro acessível (cadeirante)"),
]
IDEB_YEARS = [str(year) for year in range(2005, 2026, 2)]
IDEB_YEARS_BY_STAGE = {"AI": IDEB_YEARS, "AF": IDEB_YEARS, "EM": ["2017", "2019", "2021", "2023", "2025"]}
NETWORKS = {"federal", "estadual", "privada conveniada", "privada não conveniada"}
STATES = {"valor", "zero", "ausente", "nao_aplicavel"}

PHRASE_STAGE_NOT_OFFERED = "— esta etapa não é ofertada pela escola em 2025"
PHRASE_IDEB_PRIVATE = "sem Ideb: a INEP não publica resultado de escola privada depois de 2017"
PHRASE_IDEB_PUBLIC = (
    "sem Ideb em 2025: a INEP não publica quando há menos de 10 alunos na prova "
    "ou participação abaixo de 80%, e não informa qual foi o caso"
)
PHRASE_CENSUS_2024_NO_ROW = "a escola não consta do Censo de 2024"
PHRASE_ENROLLMENT_2024 = "matrícula não declarada no Censo de 2024"
PHRASE_ENROLLMENT_2025 = "matrícula não declarada no Censo de 2025"
PHRASE_NO_INDICATOR = "esta escola não tem Ideb nem taxas publicadas em 2025"
PHRASE_INFRA_NOT_APPLICABLE = (
    "a infraestrutura é publicada para as escolas que oferecem ensino fundamental ou médio"
)
PHRASE_SMALL_N = "nesta etapa — o indicador não é publicado quando a turma é pequena"

# Famílias cujo n é contagem de alunos (e não a própria escola). Só nelas o
# JSON admite n = null e o campo n_referencia.
STUDENT_COUNT_FAMILIES = {"ideb", "fluxo", "tdi", "tnr"}
SLUG_BY_STAGE_LABEL = {
    label: STAGE_SLUG[stage_code] for stage_code, label, _ in STAGES
}


class BuildError(Exception):
    """O build não pode continuar; a mensagem diz o que falta ou diverge."""


# --------------------------------------------------------------------------
# Leitura e validação do insumo público


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _int_or_none(value) -> int | None:
    return None if value is None or pd.isna(value) else int(value)


def _records_by_family(provenance: dict) -> dict[str, dict]:
    records = provenance.get("registros")
    if not isinstance(records, list) or not records:
        raise BuildError("procedencia.json sem a lista 'registros'")
    mapping = {}
    licenses_by_source: dict[str, tuple[str, str | None]] = {}
    for record in records:
        family = record.get("familia")
        if not family or family in mapping:
            raise BuildError(f"procedencia.json com família ausente ou duplicada: {family!r}")
        for field in ("fonte", "arquivo", "calculo", "licenca"):
            if not record.get(field):
                raise BuildError(f"registro {family!r} sem {field}")
        if "licenca_url" not in record:
            raise BuildError(f"registro {family!r} sem licenca_url (pode ser null)")
        if not record.get("limites"):
            raise BuildError(f"registro {family!r} sem limites")
        key = (record["licenca"], record["licenca_url"])
        previous = licenses_by_source.setdefault(record["fonte"], key)
        if previous != key:
            raise BuildError(
                f"famílias da fonte {record['fonte']!r} divergem em licença: "
                f"{previous!r} × {key!r}"
            )
        mapping[family] = record
    return mapping


def load_data(public: Path) -> dict:
    """Lê e valida `data/public/`; devolve o modelo usado por todas as páginas."""
    public = Path(public)
    if not public.is_dir():
        raise BuildError(f"data/public não existe: {public} (rode 06_analysis.py --public)")
    for name in ("escolas.parquet", "indicadores.parquet", "infraestrutura.parquet", "procedencia.json"):
        if not (public / name).is_file():
            raise BuildError(f"falta {public / name} (rode 06_analysis.py --public)")

    provenance = json.loads((public / "procedencia.json").read_text(encoding="utf-8"))
    hashes = provenance.get("sha256")
    if not isinstance(hashes, dict):
        raise BuildError("procedencia.json sem o mapa 'sha256' dos parquets")
    for name in ("escolas.parquet", "indicadores.parquet", "infraestrutura.parquet"):
        if not hashes.get(name):
            raise BuildError(f"procedencia.json sem sha256 de {name}")
        actual = sha256(public / name)
        if actual != hashes[name]:
            raise BuildError(
                f"sha256 de {name} não confere: registrado {hashes[name]}, arquivo {actual}. "
                "Rode 06_analysis.py --public novamente."
            )

    schools_df = pd.read_parquet(public / "escolas.parquet")
    for column in (
        "co_entidade", "nome", "ra", "rede", "rede_cadastro",
        "censo_2024_presente",
        "oferta_inf_cre", "oferta_inf_pre", "oferta_fund_ai", "oferta_fund_af",
        "oferta_med", "oferta_eja", "oferta_esp", "oferta_prof",
        "mat_inf_cre_2024", "mat_fund_ai_2024", "mat_fund_af_2024", "mat_med_2024",
        "mat_inf_cre_2025", "mat_fund_ai_2025", "mat_fund_af_2025", "mat_med_2025",
    ):
        if column not in schools_df:
            raise BuildError(f"escolas.parquet sem a coluna {column}")

    schools = []
    for r in schools_df.to_dict("records"):
        code = str(r["co_entidade"]).strip()
        if not code:
            raise BuildError("escolas.parquet com co_entidade vazio")
        if len(code) < 8:
            code = code.zfill(8)
        if r["rede"] not in NETWORKS:
            raise BuildError(f"escola {code} com rede fora do contrato: {r['rede']!r}")
        if pd.isna(r["censo_2024_presente"]):
            raise BuildError(f"escola {code} sem censo_2024_presente")
        school = {
            "co": code,
            "nome": str(r["nome"]).strip(),
            "ra": str(r["ra"]).strip(),
            "rede": r["rede"],
            "rede_cadastro": str(r["rede_cadastro"]).strip(),
            "censo_2024_presente": bool(r["censo_2024_presente"]),
        }
        for column, _ in OFFERINGS:
            school[column] = int(r[column]) if not pd.isna(r[column]) else 0
        for (stage, year), column in ENROLLMENT_COLUMNS.items():
            school[f"mat_{stage}_{year}"] = _int_or_none(r[column])
        if not school["censo_2024_presente"]:
            filled = [
                stage for stage in ("CRE", "AI", "AF", "EM")
                if school.get(f"mat_{stage}_2024") is not None
            ]
            if filled:
                raise BuildError(
                    f"escola {code} sem linha no Censo 2024 com matrícula de 2024: "
                    + ", ".join(filled)
                )
        schools.append(school)
    schools.sort(key=lambda e: e["co"])

    by_code = {}
    for school in schools:
        if school["co"] in by_code:
            raise BuildError(f"escolas.parquet com CO_ENTIDADE duplicado: {school['co']}")
        by_code[school["co"]] = school

    indicators = {}
    indicators_df = pd.read_parquet(public / "indicadores.parquet")
    for r in indicators_df.to_dict("records"):
        code = str(r["co_entidade"]).strip()
        stage = str(r["etapa"])
        indicator = str(r["indicador"])
        year = str(r["ano"])
        state = str(r["estado"])
        if code not in by_code:
            raise BuildError(f"indicador de escola fora do cadastro: {code}")
        if stage not in STAGE_LABEL:
            raise BuildError(f"indicador com etapa fora do contrato: {stage!r}")
        if state not in STATES:
            raise BuildError(f"indicador com estado fora do contrato: {state!r}")
        value = None if pd.isna(r["valor"]) else float(r["valor"])
        if state in ("valor", "zero") and value is None:
            raise BuildError(f"indicador {code}/{stage}/{indicator}/{year} com estado {state} e valor nulo")
        if state in ("ausente", "nao_aplicavel") and value is not None:
            raise BuildError(f"indicador {code}/{stage}/{indicator}/{year} com estado {state} e valor")
        key = (code, stage, indicator, year)
        if key in indicators:
            raise BuildError(f"indicador duplicado: {key}")
        indicators[key] = {"valor": value, "estado": state}

    infra = {}
    infra_df = pd.read_parquet(public / "infraestrutura.parquet")
    for r in infra_df.to_dict("records"):
        code = str(r["co_entidade"]).strip()
        item = str(r["item"])
        state = str(r["estado"])
        if code not in by_code:
            raise BuildError(f"infraestrutura de escola fora do cadastro: {code}")
        if state not in STATES:
            raise BuildError(f"infraestrutura com estado fora do contrato: {state!r}")
        value = _int_or_none(r["valor"])
        if state == "valor" and value not in (0, 1):
            raise BuildError(f"infraestrutura {code}/{item} com valor fora de 0/1: {value!r}")
        infra[(code, item)] = {"valor": value, "estado": state, "ano": str(r["ano"])}

    execution = provenance.get("execucao") or {}
    skipped_steps = execution.get("etapas_puladas") if isinstance(execution, dict) else None
    if skipped_steps is None:
        skipped_steps = []
    if not isinstance(skipped_steps, list):
        raise BuildError("procedencia.json com execucao.etapas_puladas fora de lista")
    if skipped_steps:
        print(
            "AVISO: o insumo público foi exportado com --parcial e tem etapa(s) "
            "pulada(s): " + ", ".join(str(e) for e in skipped_steps)
        )

    return {
        "escolas": schools,
        "por_co": by_code,
        "indicadores": indicators,
        "infra": infra,
        "procedencia": provenance,
        "registros": _records_by_family(provenance),
        "hashes": hashes,
        "etapas_puladas": [str(e) for e in skipped_steps],
    }


def get_indicator(data: dict, code: str, stage: str, name: str, year: str = "2025") -> dict:
    """Devolve o registro do indicador ou `ausente` quando não existe linha."""
    return data["indicadores"].get((code, stage, name, str(year)), {"valor": None, "estado": "ausente"})


def has_published_ideb(data: dict, school: dict) -> bool:
    return any(
        school[offering]
        and get_indicator(data, school["co"], stage, "ideb_observado")["estado"] == "valor"
        for stage, _, offering in STAGES
    )


def has_rate_row(data: dict, school: dict) -> bool:
    for stage, _, offering in STAGES:
        if not school[offering]:
            continue
        for name in ("tdi", "tnr", "aprovacao", "reprovacao", "abandono"):
            if (school["co"], stage, name, "2025") in data["indicadores"]:
                return True
    return False


# --------------------------------------------------------------------------
# Formatação e HTML


def fmt_int(value) -> str:
    return f"{int(value):,}".replace(",", ".")


def fmt_dec(value) -> str:
    return f"{float(value):.1f}".replace(".", ",")


def fmt_years(years) -> str:
    years = [str(a) for a in years]
    if not years:
        return ""
    if years == IDEB_YEARS:
        return "2005–2025, de dois em dois anos"
    if len(years) == 1:
        return years[0]
    if len(years) == 2 and int(years[1]) - int(years[0]) == 1:
        return f"{years[0]}–{years[1]}"
    return ", ".join(years)


def stage_slug(stage: str) -> str:
    return STAGE_SLUG.get(stage, stage.lower())


def stage_title(label: str) -> str:
    return label[:1].upper() + label[1:]


def student_word(n: int | None) -> str:
    return "aluno" if n == 1 else "alunos"


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


# --------------------------------------------------------------------------
# Páginas fixas


CSS = """
:root {
  --tinta: #1d2433;
  --tinta-suave: #5a6475;
  --papel: #fbfaf7;
  --papel-forte: #ffffff;
  --linha: #d9d6cf;
  --destaque: #245c4a;
  --destaque-claro: #e6f0eb;
  --alerta: #8a4b1f;
  --alerta-claro: #f7ece2;
  --erro: #8a2f2f;
  --sombra: 0 1px 2px rgba(29, 36, 51, .06);
}
* { box-sizing: border-box; }
html { color-scheme: light; }
body {
  margin: 0;
  background: var(--papel);
  color: var(--tinta);
  font: 1rem/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
a { color: var(--destaque); text-underline-offset: .15em; }
a:hover { text-decoration-thickness: .12em; }
.topo {
  max-width: 56rem;
  margin: 0 auto;
  padding: 1.1rem 1.1rem .4rem;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: .4rem 1rem;
}
.topo .marca {
  font-weight: 700;
  letter-spacing: -.01em;
  text-decoration: none;
  color: var(--tinta);
}
.topo .carimbo {
  margin: 0;
  color: var(--tinta-suave);
  font-size: .8rem;
}
main {
  max-width: 56rem;
  margin: 0 auto;
  padding: .4rem 1.1rem 3rem;
}
h1 {
  font-size: clamp(1.6rem, 1.1rem + 2vw, 2.4rem);
  line-height: 1.15;
  letter-spacing: -.02em;
  margin: .8rem 0 .25rem;
}
h2 {
  font-size: 1.15rem;
  letter-spacing: -.01em;
  margin: 0 0 .8rem;
}
h3 { font-size: 1rem; margin: 0 0 .55rem; }
.subtitulo { margin: 0 0 1rem; color: var(--tinta-suave); }
.trilha { margin: .2rem 0 0; font-size: .85rem; }
.bloco {
  background: var(--papel-forte);
  border: 1px solid var(--linha);
  border-radius: 10px;
  box-shadow: var(--sombra);
  padding: 1.1rem 1.1rem 1rem;
  margin: 1rem 0;
}
.etapa {
  border-top: 1px solid var(--linha);
  padding-top: .9rem;
  margin-top: .9rem;
}
.etapa:first-of-type { border-top: 0; padding-top: 0; margin-top: 0; }
.ficha {
  display: grid;
  grid-template-columns: minmax(8rem, 14rem) 1fr;
  gap: .25rem .9rem;
  margin: 0 0 .8rem;
}
.ficha dt { color: var(--tinta-suave); }
.ficha dd { margin: 0; }
.tabela {
  width: 100%;
  border-collapse: collapse;
  margin: .3rem 0 .6rem;
  font-variant-numeric: tabular-nums;
}
.tabela th, .tabela td {
  text-align: left;
  padding: .38rem .5rem;
  border-bottom: 1px solid var(--linha);
  vertical-align: top;
}
.tabela th { font-size: .82rem; color: var(--tinta-suave); font-weight: 600; }
.tabela tr:last-child td { border-bottom: 0; }
.tabela-estreita { max-width: 22rem; }
.num { font-variant-numeric: tabular-nums; font-weight: 600; }
.simbolo { color: var(--tinta-suave); font-weight: 700; }
.fonte, .nota, .rodape-pagina {
  color: var(--tinta-suave);
  font-size: .78rem;
  line-height: 1.45;
  margin: .5rem 0 0;
}
.ausencia {
  background: var(--alerta-claro);
  border-left: 3px solid var(--alerta);
  border-radius: 0 6px 6px 0;
  padding: .55rem .7rem;
  margin: .7rem 0;
  font-size: .9rem;
}
.ausencia .texto { color: var(--tinta); }
.id-limite {
  white-space: nowrap;
  font-size: .78rem;
  font-weight: 600;
  margin-left: .25rem;
}
.suprimido {
  background: var(--alerta-claro);
  border-left: 3px solid var(--alerta);
  border-radius: 0 6px 6px 0;
  padding: .55rem .7rem;
  margin: .4rem 0;
  font-size: .9rem;
}
.n { color: var(--tinta-suave); font-size: .82rem; margin: .1rem 0 .5rem; }
.rodape-pagina { margin-top: 1.6rem; }
.busca { margin: 1rem 0 1.2rem; }
.busca label { display: block; font-weight: 600; margin-bottom: .35rem; }
.busca input {
  width: 100%;
  max-width: 34rem;
  font: inherit;
  padding: .55rem .7rem;
  border: 1px solid var(--linha);
  border-radius: 8px;
  background: var(--papel-forte);
  color: var(--tinta);
}
.busca input:focus { outline: 2px solid var(--destaque); outline-offset: 1px; }
.busca .status { min-height: 1.2em; color: var(--tinta-suave); font-size: .85rem; margin: .35rem 0 0; }
.ra { margin: 1.2rem 0 0; }
.ra h2 { font-size: .95rem; text-transform: none; margin: 0 0 .35rem; }
.ra ul { list-style: none; padding: 0; margin: 0; }
.ra li { padding: .18rem 0; }
.ra .rede { color: var(--tinta-suave); font-size: .82rem; margin-left: .35rem; }
.aviso {
  background: var(--destaque-claro);
  border-left: 3px solid var(--destaque);
  border-radius: 0 6px 6px 0;
  padding: .6rem .75rem;
  margin: .8rem 0;
}
.tabela-estados td:first-child { white-space: nowrap; }
.simbolo-grande { font-size: 1.15rem; font-weight: 700; }
footer.rodape {
  max-width: 56rem;
  margin: 0 auto;
  padding: 0 1.1rem 2.4rem;
  color: var(--tinta-suave);
  font-size: .78rem;
}
footer.rodape a { color: var(--destaque); }
@media (max-width: 38rem) {
  .ficha { grid-template-columns: 1fr; gap: 0; }
  .ficha dt { margin-top: .35rem; }
  .bloco { padding: .9rem .85rem; }
  .tabela th, .tabela td { padding: .35rem .35rem; }
}
@media print {
  body { background: #fff; }
  .topo, footer.rodape, .trilha { display: none; }
  .bloco { box-shadow: none; break-inside: avoid; }
}
"""


def document(title: str, body: str, data_build: str, threshold: int) -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="estilo.css">
</head>
<body>
<header class="topo">
  <a class="marca" href="index.html">Prova dos Nove</a>
  <p class="carimbo">build {html.escape(data_build)} · limiar de n pequeno = {threshold}</p>
</header>
{body}
<footer class="rodape">
  <p>Prova dos Nove · dados públicos de educação, com fonte, ano e cálculo.
  <a href="como-ler.html">Como ler os números</a> ·
  <a href="creditos.html">Créditos e licenças</a>.</p>
</footer>
</body>
</html>
"""


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

    js = r"""
<script>
(async function () {
  const campo = document.getElementById('busca');
  const status = document.getElementById('busca-status');
  const itens = Array.from(document.querySelectorAll('#lista li[data-nome]'));
  const secoes = Array.from(document.querySelectorAll('#lista section[data-ra]'));
  const normaliza = (texto) => String(texto || '')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR').trim();

  let indice;
  try {
    const resposta = await fetch('indice.json');
    if (!resposta.ok) throw new Error(String(resposta.status));
    indice = await resposta.json();
  } catch (erro) {
    status.textContent = 'A busca por nome não carregou; a lista abaixo continua completa.';
    campo.disabled = true;
    return;
  }

  const porCodigo = new Map(indice.map((item) => [String(item.co_entidade), item]));
  campo.addEventListener('input', () => {
    const termo = normaliza(campo.value);
    let encontrou = false;
    for (const item of itens) {
      const dados = porCodigo.get(item.dataset.codigo);
      const nome = normaliza(dados ? dados.nome : item.dataset.nome);
      const mostrar = !termo || nome.includes(termo);
      item.hidden = !mostrar;
      if (mostrar) encontrou = true;
    }
    for (const secao of secoes) {
      secao.hidden = !secao.querySelector('li:not([hidden])');
    }
    status.textContent = termo && !encontrou ? 'Nenhuma escola encontrada.' : '';
  });
})();
</script>
"""
    return document("Prova dos Nove — escolas do Distrito Federal", body + js, data_build, threshold)


def render_how_to_read_page(data_build: str, threshold: int) -> str:
    body = f"""
<main>
<h1>Como ler os números</h1>
<p class="subtitulo">Os quatro estados, as ausências e o limiar de turma pequena, explicados uma vez.</p>

<section class="bloco" id="estados">
<h2>Os quatro estados</h2>
<p>Cada célula da página é uma destas quatro coisas. Zero, ausente e não aplicável
não são a mesma coisa, e a página não os troca.</p>
<table class="tabela tabela-estados">
<thead><tr><th>Estado</th><th>O que é</th><th>Na página</th></tr></thead>
<tbody>
<tr><td><strong>valor</strong></td><td>o dado existe e foi informado</td><td>o número, com unidade e ano</td></tr>
<tr><td><strong>zero</strong></td><td>o valor é zero</td><td><strong>0</strong>, com unidade</td></tr>
<tr><td><strong>ausente</strong></td><td>deveria existir e não foi coletado ou publicado</td><td><span class="simbolo-grande">-</span> e, quando a causa é conhecida, uma linha de motivo</td></tr>
<tr><td><strong>nao_aplicavel</strong></td><td>a categoria não se aplica à escola ou à etapa</td><td><span class="simbolo-grande">—</span>, com “etapa não ofertada” quando é o caso</td></tr>
</tbody>
</table>
<p>O hífen <strong>-</strong> é ausência. O travessão <strong>—</strong> é não aplicável.
Nenhum dos dois vira zero, média ou interpolação.</p>
</section>

<section class="bloco" id="ideb">
<h2>Ideb: por que falta em algumas escolas</h2>
<p>O Ideb por escola só é publicado quando a escola tem pelo menos 10 alunos na
prova do Saeb e participação de pelo menos 80%. Quando uma das duas condições
não é atendida, a INEP não publica o resultado — e não informa, por escola, qual
foi o caso. Por isso a página não atribui a ausência a uma causa que a fonte
não distingue (L-09, L-30).</p>
<p>Escola sem Ideb não é escola com nota zero. A ausência é ausência de resultado
publicado.</p>
</section>

<section class="bloco" id="ideb-privada">
<h2>Escola privada e Ideb</h2>
<p>A INEP não publica Ideb por escola da rede privada depois de 2017 (L-08).
Não é uma falha da escola nem um zero: é uma regra de publicação da fonte. O
agregado privado por UF existe, mas a distribuição entre escolas não.</p>
</section>

<section class="bloco" id="tnr">
<h2>Taxa de não-resposta</h2>
<p>A taxa de não-resposta mede alunos sem informação de rendimento ou movimento
no Censo Escolar. Ela não mede participação no Saeb e não tem campo que separe
não participação de resultado suprimido. Por isso a taxa de não-resposta não
explica, sozinha, a ausência de Ideb (L-09).</p>
</section>

<section class="bloco" id="n">
<h2>Turma pequena: o limiar de n = {threshold}</h2>
<p>Nos indicadores de razão — distorção idade-série, taxa de não-resposta,
aprovação, reprovação e abandono — a página não publica a taxa quando a etapa
tem menos de {threshold} alunos. Nesse tamanho, um valor extremo (0,0% de distorção
ou 100% de aprovação) é mais provável do que o desempenho, e a taxa engana mais
do que informa. A página mostra a matrícula e diz que a amostra é pequena
(D4, L-40).</p>
<p>A regra é aplicada à unidade escola × etapa, não à escola inteira.</p>
</section>

<section class="bloco" id="denominador">
<h2>O denominador de n</h2>
<p>O n dos indicadores é a matrícula da etapa no Censo Escolar de 2025. Para a
distorção e o fluxo, é a mesma coorte do indicador. Para o Ideb, é uma
aproximação: a coorte que fez o Saeb não é a matrícula inteira (L-21).</p>
<p>A matrícula da página vem do Censo da INEP, não da série de matrículas por
modalidade da SEEDF (L-62). Em 2024, célula vazia no Censo é matrícula não
declarada, não zero (L-28); escola sem linha em 2024 é outra ausência (L-63).</p>
<p>No JSON de procedência, <code>n</code> pode ser <code>null</code> quando a
matrícula que serviria de denominador não existe. Quando o <code>n</code> é uma
contagem de alunos de outro ano, o campo <code>n_referencia</code> diz de que
ano é essa matrícula — hoje, o Ideb de 2005–2023 usa a matrícula de 2025.</p>
</section>

<section class="bloco" id="censo">
<h2>Matrícula não declarada</h2>
<p>Quando a escola de 2025 não tem linha no Censo de 2024, a página mostra
<strong>-</strong> e diz “a escola não consta do Censo de 2024” (L-63). A
ausência de linha não diz se a escola não existia, se mudou de código ou se
ficou fora da coleta; a fonte não estabelece a causa.</p>
<p>Quando a escola tem linha no Censo de 2024 mas a célula de matrícula está
vazia, a página mostra <strong>-</strong> e diz “matrícula não declarada no
Censo de 2024”. O motivo da célula vazia também não é informado pela fonte
(L-28). Em 2025, a célula vazia é lida como “matrícula não declarada no Censo de
2025” (L-28).</p>
</section>

<section class="bloco" id="infraestrutura">
<h2>Infraestrutura</h2>
<p>A infraestrutura é publicada para as escolas que oferecem ensino fundamental
ou médio, o universo em que laboratório, quadra e biblioteca são itens
comparáveis. Para as escolas que só oferecem educação infantil, o bloco é não
aplicável: esses itens não são exigência da etapa (L-25).</p>
</section>

<section class="bloco" id="limites">
<h2>Os limites completos</h2>
<p>Cada número cita os ids que o limitam. O registro completo, com evidência e
status, está em
<a href="https://github.com/mtsanaissi/prova-dos-nove/blob/main/docs/LIMITES.md">docs/LIMITES.md</a>.</p>
</section>
</main>
"""
    return document("Como ler os números — Prova dos Nove", body, data_build, threshold)


def render_credits_page(data: dict, data_build: str, threshold: int) -> str:
    by_source: dict[str, tuple[str, str | None]] = {}
    for record in data["registros"].values():
        source = record["fonte"]
        key = (record["licenca"], record.get("licenca_url"))
        previous = by_source.setdefault(source, key)
        if previous != key:
            raise BuildError(
                f"famílias da fonte {source!r} divergem em licença: {previous!r} × {key!r}"
            )

    rows = []
    for source in sorted(by_source):
        license_name, url = by_source[source]
        if url:
            declaration = f'<a href="{html.escape(url, quote=True)}">{html.escape(url)}</a>'
        else:
            declaration = "—"
        rows.append(
            f"<tr><td>{html.escape(source)}</td><td>{html.escape(license_name)}</td>"
            f"<td>{declaration}</td></tr>"
        )
    rows = "".join(rows)
    body = f"""
<main>
<h1>Créditos e licenças</h1>
<p class="subtitulo">Titular, licenças e as fontes usadas em cada número.</p>

<section class="bloco" id="titular">
<h2>Titular e licença do projeto</h2>
<p><strong>Prova dos Nove</strong> — © 2026 Marcelo Anaissi.</p>
<p>Código sob a licença MIT. Textos e dados derivados sob CC BY 4.0, com
atribuição ao projeto e às fontes citadas em cada número. O texto integral da
licença MIT está no arquivo
<a href="https://github.com/mtsanaissi/prova-dos-nove/blob/main/LICENSE">LICENSE</a>.</p>
</section>

<section class="bloco" id="fontes">
<h2>Licença por fonte</h2>
<p>Licença como declarada no catálogo de cada fonte; nenhuma foi inferida.</p>
<table class="tabela">
<thead><tr><th>Fonte</th><th>Licença declarada</th><th>Declaração</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<p>A série de matrículas por modalidade da SEEDF não é usada em nenhum número
desta versão. A matrícula publicada vem do Censo da INEP (L-62).</p>
</section>

<section class="bloco" id="build">
<h2>Este build</h2>
<p>Data do build: <strong>{html.escape(data_build)}</strong>.</p>
<p>Limiar de n pequeno usado neste build: <strong>{threshold}</strong>.</p>
<p><a href="como-ler.html">Como ler os números</a> · <a href="index.html">Todas as escolas</a>.</p>
</section>
</main>
"""
    return document("Créditos e licenças — Prova dos Nove", body, data_build, threshold)


# --------------------------------------------------------------------------
# Build


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


# --------------------------------------------------------------------------
# Verificações do §8


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


# --------------------------------------------------------------------------
# CLI


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
