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
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import tempfile
from pathlib import Path

import pandas as pd

DATA_BUILD_PADRAO = "2026-11-06"
LIMIAR_N_PADRAO = 30
TAMANHO_MAXIMO_SITE = 700 * 1024 * 1024

ETAPAS = [
    ("AI", "anos iniciais", "oferta_fund_ai"),
    ("AF", "anos finais", "oferta_fund_af"),
    ("EM", "ensino médio", "oferta_med"),
]
ETAPA_LABEL = {codigo: label for codigo, label, _ in ETAPAS}
ETAPA_SLUG = {"AI": "ai", "AF": "af", "EM": "em", "CRE": "creche"}
MAT_COLS = {
    ("CRE", "2024"): "mat_inf_cre_2024",
    ("CRE", "2025"): "mat_inf_cre_2025",
    ("AI", "2024"): "mat_fund_ai_2024",
    ("AI", "2025"): "mat_fund_ai_2025",
    ("AF", "2024"): "mat_fund_af_2024",
    ("AF", "2025"): "mat_fund_af_2025",
    ("EM", "2024"): "mat_med_2024",
    ("EM", "2025"): "mat_med_2025",
}
MAT_LABEL = {"CRE": "creche", "AI": "anos iniciais", "AF": "anos finais", "EM": "ensino médio"}
OFERTAS = [
    ("oferta_inf_cre", "Creche"),
    ("oferta_inf_pre", "Pré-escola"),
    ("oferta_fund_ai", "Anos iniciais do ensino fundamental"),
    ("oferta_fund_af", "Anos finais do ensino fundamental"),
    ("oferta_med", "Ensino médio"),
    ("oferta_eja", "Educação de jovens e adultos"),
    ("oferta_esp", "Educação especial"),
    ("oferta_prof", "Educação profissional"),
]
INFRA_ITENS = [
    ("IN_BIBLIOTECA", "Biblioteca"),
    ("IN_SALA_LEITURA", "Sala de leitura"),
    ("IN_QUADRA_ESPORTES", "Quadra de esportes"),
    ("IN_LABORATORIO_INFORMATICA", "Laboratório de informática"),
    ("IN_LABORATORIO_CIENCIAS", "Laboratório de ciências"),
    ("IN_INTERNET_ALUNOS", "Internet para os alunos"),
    ("IN_REFEITORIO", "Refeitório"),
    ("IN_BANHEIRO_PNE", "Banheiro acessível (cadeirante)"),
]
ANOS_IDEB = [str(ano) for ano in range(2005, 2026, 2)]
ANOS_IDEB_ETAPA = {"AI": ANOS_IDEB, "AF": ANOS_IDEB, "EM": ["2017", "2019", "2021", "2023", "2025"]}
REDES = {"federal", "estadual", "privada conveniada", "privada não conveniada"}
ESTADOS = {"valor", "zero", "ausente", "nao_aplicavel"}

FRASE_ETAPA = "— esta etapa não é ofertada pela escola em 2025"
FRASE_IDEB_PRIVADA = "sem Ideb: a INEP não publica resultado de escola privada depois de 2017"
FRASE_IDEB_PUBLICA = (
    "sem Ideb em 2025: a INEP não publica quando há menos de 10 alunos na prova "
    "ou participação abaixo de 80%, e não informa qual foi o caso"
)
FRASE_MATRICULA_2024 = "matrícula não declarada no Censo de 2024"
FRASE_SEM_INDICADOR = "esta escola não tem Ideb nem taxas publicadas em 2025"
FRASE_INFRA_NAO_APLICAVEL = (
    "a infraestrutura é publicada para as escolas que oferecem ensino fundamental ou médio"
)
FRASE_N_PEQUENA = "nesta etapa — o indicador não é publicado quando a turma é pequena"


class BuildError(Exception):
    """O build não pode continuar; a mensagem diz o que falta ou diverge."""


# --------------------------------------------------------------------------
# Leitura e validação do insumo público


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _int_ou_none(valor) -> int | None:
    return None if valor is None or pd.isna(valor) else int(valor)


def _registros_por_familia(procedencia: dict) -> dict[str, dict]:
    registros = procedencia.get("registros")
    if not isinstance(registros, list) or not registros:
        raise BuildError("procedencia.json sem a lista 'registros'")
    mapa = {}
    for registro in registros:
        familia = registro.get("familia")
        if not familia or familia in mapa:
            raise BuildError(f"procedencia.json com família ausente ou duplicada: {familia!r}")
        for campo in ("fonte", "arquivo", "calculo"):
            if not registro.get(campo):
                raise BuildError(f"registro {familia!r} sem {campo}")
        if not registro.get("limites"):
            raise BuildError(f"registro {familia!r} sem limites")
        mapa[familia] = registro
    return mapa


def carregar_dados(public: Path) -> dict:
    """Lê e valida `data/public/`; devolve o modelo usado por todas as páginas."""
    public = Path(public)
    if not public.is_dir():
        raise BuildError(f"data/public não existe: {public} (rode 06_analysis.py --public)")
    for nome in ("escolas.parquet", "indicadores.parquet", "infraestrutura.parquet", "procedencia.json"):
        if not (public / nome).is_file():
            raise BuildError(f"falta {public / nome} (rode 06_analysis.py --public)")

    procedencia = json.loads((public / "procedencia.json").read_text(encoding="utf-8"))
    hashes = procedencia.get("sha256")
    if not isinstance(hashes, dict):
        raise BuildError("procedencia.json sem o mapa 'sha256' dos parquets")
    for nome in ("escolas.parquet", "indicadores.parquet", "infraestrutura.parquet"):
        if not hashes.get(nome):
            raise BuildError(f"procedencia.json sem sha256 de {nome}")
        real = _sha256(public / nome)
        if real != hashes[nome]:
            raise BuildError(
                f"sha256 de {nome} não confere: registrado {hashes[nome]}, arquivo {real}. "
                "Rode 06_analysis.py --public novamente."
            )

    escolas_df = pd.read_parquet(public / "escolas.parquet")
    for coluna in (
        "co_entidade", "nome", "ra", "rede", "rede_cadastro",
        "oferta_inf_cre", "oferta_inf_pre", "oferta_fund_ai", "oferta_fund_af",
        "oferta_med", "oferta_eja", "oferta_esp", "oferta_prof",
        "mat_inf_cre_2024", "mat_fund_ai_2024", "mat_fund_af_2024", "mat_med_2024",
        "mat_inf_cre_2025", "mat_fund_ai_2025", "mat_fund_af_2025", "mat_med_2025",
    ):
        if coluna not in escolas_df:
            raise BuildError(f"escolas.parquet sem a coluna {coluna}")

    escolas = []
    for r in escolas_df.to_dict("records"):
        co = str(r["co_entidade"]).strip()
        if not co:
            raise BuildError("escolas.parquet com co_entidade vazio")
        if len(co) < 8:
            co = co.zfill(8)
        if r["rede"] not in REDES:
            raise BuildError(f"escola {co} com rede fora do contrato: {r['rede']!r}")
        escola = {
            "co": co,
            "nome": str(r["nome"]).strip(),
            "ra": str(r["ra"]).strip(),
            "rede": r["rede"],
            "rede_cadastro": str(r["rede_cadastro"]).strip(),
        }
        for coluna, _ in OFERTAS:
            escola[coluna] = int(r[coluna]) if not pd.isna(r[coluna]) else 0
        for (etapa, ano), coluna in MAT_COLS.items():
            escola[f"mat_{etapa}_{ano}"] = _int_ou_none(r[coluna])
        escolas.append(escola)
    escolas.sort(key=lambda e: e["co"])

    por_co = {}
    for escola in escolas:
        if escola["co"] in por_co:
            raise BuildError(f"escolas.parquet com CO_ENTIDADE duplicado: {escola['co']}")
        por_co[escola["co"]] = escola

    indicadores = {}
    indicadores_df = pd.read_parquet(public / "indicadores.parquet")
    for r in indicadores_df.to_dict("records"):
        co = str(r["co_entidade"]).strip()
        etapa = str(r["etapa"])
        indicador = str(r["indicador"])
        ano = str(r["ano"])
        estado = str(r["estado"])
        if co not in por_co:
            raise BuildError(f"indicador de escola fora do cadastro: {co}")
        if etapa not in ETAPA_LABEL:
            raise BuildError(f"indicador com etapa fora do contrato: {etapa!r}")
        if estado not in ESTADOS:
            raise BuildError(f"indicador com estado fora do contrato: {estado!r}")
        valor = None if pd.isna(r["valor"]) else float(r["valor"])
        if estado in ("valor", "zero") and valor is None:
            raise BuildError(f"indicador {co}/{etapa}/{indicador}/{ano} com estado {estado} e valor nulo")
        if estado in ("ausente", "nao_aplicavel") and valor is not None:
            raise BuildError(f"indicador {co}/{etapa}/{indicador}/{ano} com estado {estado} e valor")
        chave = (co, etapa, indicador, ano)
        if chave in indicadores:
            raise BuildError(f"indicador duplicado: {chave}")
        indicadores[chave] = {"valor": valor, "estado": estado}

    infra = {}
    infra_df = pd.read_parquet(public / "infraestrutura.parquet")
    for r in infra_df.to_dict("records"):
        co = str(r["co_entidade"]).strip()
        item = str(r["item"])
        estado = str(r["estado"])
        if co not in por_co:
            raise BuildError(f"infraestrutura de escola fora do cadastro: {co}")
        if estado not in ESTADOS:
            raise BuildError(f"infraestrutura com estado fora do contrato: {estado!r}")
        valor = _int_ou_none(r["valor"])
        if estado == "valor" and valor not in (0, 1):
            raise BuildError(f"infraestrutura {co}/{item} com valor fora de 0/1: {valor!r}")
        infra[(co, item)] = {"valor": valor, "estado": estado, "ano": str(r["ano"])}

    return {
        "escolas": escolas,
        "por_co": por_co,
        "indicadores": indicadores,
        "infra": infra,
        "procedencia": procedencia,
        "registros": _registros_por_familia(procedencia),
        "hashes": hashes,
    }


def indicador(dados: dict, co: str, etapa: str, nome: str, ano: str = "2025") -> dict:
    """Devolve o registro do indicador ou `ausente` quando não existe linha."""
    return dados["indicadores"].get((co, etapa, nome, str(ano)), {"valor": None, "estado": "ausente"})


def tem_ideb_publicado(dados: dict, escola: dict) -> bool:
    return any(
        escola[oferta]
        and indicador(dados, escola["co"], etapa, "ideb_observado")["estado"] == "valor"
        for etapa, _, oferta in ETAPAS
    )


def tem_linha_de_taxa(dados: dict, escola: dict) -> bool:
    for etapa, _, oferta in ETAPAS:
        if not escola[oferta]:
            continue
        for nome in ("tdi", "tnr", "aprovacao", "reprovacao", "abandono"):
            if (escola["co"], etapa, nome, "2025") in dados["indicadores"]:
                return True
    return False


# --------------------------------------------------------------------------
# Formatação e HTML


def fmt_int(valor) -> str:
    return f"{int(valor):,}".replace(",", ".")


def fmt_dec(valor) -> str:
    return f"{float(valor):.1f}".replace(".", ",")


def fmt_anos(anos) -> str:
    anos = [str(a) for a in anos]
    if not anos:
        return ""
    if anos == ANOS_IDEB:
        return "2005–2025, de dois em dois anos"
    if len(anos) == 1:
        return anos[0]
    if len(anos) == 2 and int(anos[1]) - int(anos[0]) == 1:
        return f"{anos[0]}–{anos[1]}"
    return ", ".join(anos)


def slug_etapa(etapa: str) -> str:
    return ETAPA_SLUG.get(etapa, etapa.lower())


def titulo_etapa(rotulo: str) -> str:
    return rotulo[:1].upper() + rotulo[1:]


def palavra_aluno(n: int | None) -> str:
    return "aluno" if n == 1 else "alunos"


class PaginaEscola:
    """Uma página de escola e o coletor de procedência dos números dela."""

    def __init__(self, dados: dict, escola: dict, data_build: str, limiar: int):
        self.d = dados
        self.e = escola
        self.data_build = data_build
        self.limiar = limiar
        self.numeros: list[dict] = []
        self.por_id: dict[str, dict] = {}
        self.mat_cache: dict[tuple[str, str], str] = {}

    def _add(
        self,
        *,
        id: str,
        familia: str,
        bloco: str,
        etapa: str,
        ano: str,
        valor,
        estado: str,
        n: int | None,
        texto: str,
        limites: list[str] | None = None,
    ) -> str:
        registro = self.d["registros"][familia]
        if id in self.por_id:
            atual = self.por_id[id]
            if atual["valor"] != valor or atual["estado"] != estado:
                raise BuildError(f"número {id} reaparece com valor/estado diferente")
            return f'<span class="num" data-numero="{html.escape(id)}" data-estado="{estado}">{texto}</span>'
        registro_numero = {
            "id": id,
            "bloco": bloco,
            "etapa": etapa,
            "ano": str(ano),
            "valor": valor,
            "estado": estado,
            "fonte": registro["fonte"],
            "arquivo": registro["arquivo"],
            "calculo": registro["calculo"],
            "n": int(n) if n is not None else 1,
            "limites": list(limites if limites is not None else registro["limites"]),
        }
        self.por_id[id] = registro_numero
        self.numeros.append(registro_numero)
        return f'<span class="num" data-numero="{html.escape(id)}" data-estado="{estado}">{texto}</span>'

    def mat_span(self, etapa: str, ano: str) -> str:
        chave = (etapa, str(ano))
        if chave in self.mat_cache:
            return self.mat_cache[chave]
        valor = self.e.get(f"mat_{etapa}_{ano}")
        id_numero = f"matricula-{slug_etapa(etapa)}-{ano}"
        label = MAT_LABEL[etapa]
        if valor is None:
            html_num = self._add(
                id=id_numero, familia="matricula", bloco="matricula", etapa=label,
                ano=ano, valor=None, estado="ausente", n=1, texto="-",
            )
        elif int(valor) == 0:
            html_num = self._add(
                id=id_numero, familia="matricula", bloco="matricula", etapa=label,
                ano=ano, valor=0, estado="zero", n=1, texto="0",
            )
        else:
            html_num = self._add(
                id=id_numero, familia="matricula", bloco="matricula", etapa=label,
                ano=ano, valor=int(valor), estado="valor", n=1, texto=fmt_int(valor),
            )
        self.mat_cache[chave] = html_num
        return html_num

    def rate_span(self, familia: str, nome: str, etapa: str, n: int, reg: dict) -> str:
        valor = reg.get("valor")
        estado = str(reg.get("estado", "ausente"))
        if estado == "nao_aplicavel":
            valor, texto = None, "—"
        elif estado == "ausente" or valor is None:
            estado, valor, texto = "ausente", None, "-"
        elif float(valor) == 0:
            estado, valor, texto = "zero", 0.0, "0,0%"
        else:
            estado, valor, texto = "valor", float(valor), fmt_dec(valor) + "%"
        return self._add(
            id=f"{familia}-{slug_etapa(etapa)}-{nome}-2025",
            familia=familia, bloco=familia, etapa=ETAPA_LABEL[etapa],
            ano="2025", valor=valor, estado=estado, n=n, texto=texto,
        )

    def ideb_cell(self, etapa: str, ano: str, n: int) -> str:
        reg = indicador(self.d, self.e["co"], etapa, "ideb_observado", ano)
        if reg["estado"] == "valor" and reg["valor"] is not None:
            valor = float(reg["valor"])
            estado = "zero" if valor == 0 else "valor"
            texto = fmt_dec(valor)
            return self._add(
                id=f"ideb-{slug_etapa(etapa)}-{ano}", familia="ideb", bloco="ideb",
                etapa=ETAPA_LABEL[etapa], ano=ano, valor=valor, estado=estado, n=n, texto=texto,
            )
        if str(ano) == "2025":
            return self._add(
                id=f"ideb-{slug_etapa(etapa)}-2025", familia="ideb", bloco="ideb",
                etapa=ETAPA_LABEL[etapa], ano="2025", valor=None, estado="ausente", n=n, texto="-",
            )
        return '<span class="simbolo" data-estado="ausente">-</span>'

    def fonte(self, familia: str) -> str:
        r = self.d["registros"][familia]
        return (
            f'<p class="fonte">Fonte: {html.escape(r["fonte"])} · '
            f'{html.escape(fmt_anos(r["anos"]))} · {html.escape(r["calculo"])} · '
            f'limites: {html.escape(", ".join(r["limites"]))} · '
            f'<a href="dados/{self.e["co"]}.json">procedência</a></p>'
        )

    def ausencia(self, texto: str, ids: str, ancora: str, estado: str = "ausente") -> str:
        simbolo = "—" if estado == "nao_aplicavel" else "-"
        prefixo = ""
        if not (texto.startswith("—") or texto.startswith("- ")):
            prefixo = f'<span class="simbolo">{simbolo}</span> '
        return (
            f'<p class="ausencia" data-estado="{estado}">'
            f'{prefixo}'
            f'<span class="texto">{html.escape(texto)}</span> '
            f'<a class="id-limite" href="como-ler.html#{ancora}">{html.escape(ids)}</a>'
            "</p>"
        )

    def pequena(self, etapa: str, n: int) -> str:
        palavra = palavra_aluno(n)
        return (
            '<p class="suprimido" data-estado="suprimido">'
            f'{self.mat_span(etapa, "2025")} '
            f'<span class="texto">{palavra} {FRASE_N_PEQUENA}</span> '
            '<a class="id-limite" href="como-ler.html#n">D4, L-40</a>'
            "</p>"
        )

    def _cabecalho_bloco(self, titulo: str) -> str:
        return f"<h2>{html.escape(titulo)}</h2>"

    def _artigo(self, bloco: str, etapa: str, n: int | None, situacao: str, corpo: str) -> str:
        n_attr = "" if n is None else f' data-n="{int(n)}"'
        return (
            f'<article class="etapa" data-bloco="{bloco}" data-etapa="{etapa}"'
            f'{n_attr} data-situacao="{situacao}">{corpo}</article>'
        )

    def render(self) -> str:
        e = self.e
        co = e["co"]
        tem_ideb = tem_ideb_publicado(self.d, e)
        tem_taxa = tem_linha_de_taxa(self.d, e)

        partes = []
        partes.append(
            '<main>'
            f'<p class="trilha"><a href="index.html">Todas as escolas</a></p>'
            f'<h1>{html.escape(e["nome"])}</h1>'
            f'<p class="subtitulo">{html.escape(e["ra"])} · rede {html.escape(e["rede"])}</p>'
        )

        oferece_etapa_avaliada = any(e[oferta] for _, _, oferta in ETAPAS)
        if oferece_etapa_avaliada and not tem_ideb and not tem_taxa:
            partes.append(self.ausencia(FRASE_SEM_INDICADOR, "L-09", "ideb"))

        # 1. identificação
        partes.append('<section class="bloco" id="identificacao">')
        partes.append(self._cabecalho_bloco("Identificação"))
        partes.append(
            "<dl class=\"ficha\">"
            f"<dt>Escola</dt><dd>{html.escape(e['nome'])}</dd>"
            f"<dt>Região Administrativa</dt><dd>{html.escape(e['ra'])}</dd>"
            f"<dt>Rede</dt><dd>{html.escape(e['rede'])}</dd>"
            f"<dt>Código INEP</dt><dd>{html.escape(co)}</dd>"
            "</dl>"
            f'<p class="fonte">Rede no cadastro: {html.escape(e["rede_cadastro"])}.</p>'
            f'{self.fonte("identificacao")}'
            "</section>"
        )

        # 2. oferta
        partes.append('<section class="bloco" id="oferta">')
        partes.append(self._cabecalho_bloco("Oferta por etapa"))
        partes.append('<table class="tabela"><thead><tr><th>Etapa</th><th>Oferta em 2025</th></tr></thead><tbody>')
        for coluna, rotulo in OFERTAS:
            valor = "oferta" if e[coluna] == 1 else "não oferta"
            partes.append(f"<tr><td>{html.escape(rotulo)}</td><td>{valor}</td></tr>")
        partes.append("</tbody></table>")
        partes.append(self.fonte("oferta"))
        partes.append("</section>")

        # 3. matrícula
        partes.append('<section class="bloco" id="matricula">')
        partes.append(self._cabecalho_bloco("Matrícula por etapa"))
        partes.append(
            '<table class="tabela"><thead><tr><th>Etapa</th><th>2024</th><th>2025</th></tr></thead><tbody>'
        )
        faltam_2024, faltam_2025 = [], []
        for etapa, rotulo in (("CRE", "Creche"), ("AI", "Anos iniciais"), ("AF", "Anos finais"), ("EM", "Ensino médio")):
            if e.get(f"mat_{etapa}_2024") is None:
                faltam_2024.append(rotulo)
            if e.get(f"mat_{etapa}_2025") is None:
                faltam_2025.append(rotulo)
            partes.append(
                f"<tr><td>{rotulo}</td><td>{self.mat_span(etapa, '2024')}</td>"
                f"<td>{self.mat_span(etapa, '2025')}</td></tr>"
            )
        partes.append("</tbody></table>")
        if faltam_2024:
            partes.append(self.ausencia(FRASE_MATRICULA_2024, "L-28", "censo"))
        if faltam_2025:
            partes.append(self.ausencia("matrícula não declarada no Censo de 2025", "L-28", "censo"))
        partes.append(self.fonte("matricula"))
        partes.append("</section>")

        # 4. Ideb
        partes.append('<section class="bloco" id="ideb">')
        partes.append(self._cabecalho_bloco("Ideb por etapa"))
        for etapa, rotulo, oferta in ETAPAS:
            if not e[oferta]:
                corpo = (
                    f"<h3>{titulo_etapa(rotulo)}</h3>"
                    + self.ausencia(FRASE_ETAPA, "L-59", "estados", estado="nao_aplicavel")
                )
                partes.append(self._artigo("ideb", etapa, None, "nao_ofertada", corpo))
                continue
            n = e.get(f"mat_{etapa}_2025")
            n_exibir = n if n is not None else 1
            ano_2025 = indicador(self.d, co, etapa, "ideb_observado")
            situacao = "publicado" if ano_2025["estado"] == "valor" else "ausente"
            corpo = [f"<h3>{titulo_etapa(rotulo)}</h3>"]
            if n is None:
                corpo.append('<p class="n">n = - alunos em 2025 (matrícula da etapa)</p>')
            else:
                corpo.append(
                    f'<p class="n">n = {self.mat_span(etapa, "2025")} '
                    f'{palavra_aluno(n)} em 2025 (matrícula da etapa)</p>'
                )
            corpo.append('<table class="tabela tabela-estreita"><thead><tr><th>Ano</th><th>Ideb</th></tr></thead><tbody>')
            for ano in ANOS_IDEB_ETAPA[etapa]:
                corpo.append(f"<tr><td>{ano}</td><td>{self.ideb_cell(etapa, ano, n_exibir)}</td></tr>")
            corpo.append("</tbody></table>")
            if ano_2025["estado"] != "valor":
                if e["rede"].startswith("privada"):
                    corpo.append(self.ausencia(FRASE_IDEB_PRIVADA, "L-08", "ideb-privada"))
                else:
                    corpo.append(self.ausencia(FRASE_IDEB_PUBLICA, "L-09, L-30", "ideb"))
            partes.append(self._artigo("ideb", etapa, n, situacao, "".join(corpo)))
        partes.append(self.fonte("ideb"))
        partes.append("</section>")

        # 5. fluxo
        partes.append('<section class="bloco" id="fluxo">')
        partes.append(self._cabecalho_bloco("Fluxo escolar"))
        for etapa, rotulo, oferta in ETAPAS:
            if not e[oferta]:
                corpo = f"<h3>{titulo_etapa(rotulo)}</h3>" + self.ausencia(
                    FRASE_ETAPA, "L-59", "estados", estado="nao_aplicavel"
                )
                partes.append(self._artigo("fluxo", etapa, None, "nao_ofertada", corpo))
                continue
            n = e.get(f"mat_{etapa}_2025")
            if n is not None and n < self.limiar:
                corpo = f"<h3>{titulo_etapa(rotulo)}</h3>" + self.pequena(etapa, n)
                partes.append(self._artigo("fluxo", etapa, n, "suprimido", corpo))
                continue
            linhas = []
            tem_valor = False
            for nome, label in (("aprovacao", "Aprovação"), ("reprovacao", "Reprovação"), ("abandono", "Abandono")):
                reg = indicador(self.d, co, etapa, nome)
                if reg["estado"] in ("valor", "zero"):
                    tem_valor = True
                linhas.append(
                    f"<tr><td>{label}</td><td>{self.rate_span('fluxo', nome, etapa, n or 1, reg)}</td></tr>"
                )
            corpo = f"<h3>{titulo_etapa(rotulo)}</h3>"
            corpo += f'<p class="n">n = {self.mat_span(etapa, "2025")} {palavra_aluno(n)} em 2025</p>'
            corpo += '<table class="tabela"><thead><tr><th>Indicador</th><th>2025</th></tr></thead><tbody>'
            corpo += "".join(linhas) + "</tbody></table>"
            partes.append(self._artigo("fluxo", etapa, n, "publicado" if tem_valor else "ausente", corpo))
        partes.append(self.fonte("fluxo"))
        partes.append("</section>")

        # 6. distorção idade-série
        partes.append('<section class="bloco" id="tdi">')
        partes.append(self._cabecalho_bloco("Distorção idade-série"))
        for etapa, rotulo, oferta in ETAPAS:
            if not e[oferta]:
                corpo = f"<h3>{titulo_etapa(rotulo)}</h3>" + self.ausencia(
                    FRASE_ETAPA, "L-59", "estados", estado="nao_aplicavel"
                )
                partes.append(self._artigo("tdi", etapa, None, "nao_ofertada", corpo))
                continue
            n = e.get(f"mat_{etapa}_2025")
            if n is not None and n < self.limiar:
                corpo = f"<h3>{titulo_etapa(rotulo)}</h3>" + self.pequena(etapa, n)
                partes.append(self._artigo("tdi", etapa, n, "suprimido", corpo))
                continue
            reg = indicador(self.d, co, etapa, "tdi")
            corpo = (
                f"<h3>{titulo_etapa(rotulo)}</h3>"
                f'<p class="n">n = {self.mat_span(etapa, "2025")} {palavra_aluno(n)} em 2025</p>'
                '<table class="tabela"><thead><tr><th>Indicador</th><th>2025</th></tr></thead><tbody>'
                f"<tr><td>Distorção idade-série</td><td>{self.rate_span('tdi', 'tdi', etapa, n or 1, reg)}</td></tr>"
                "</tbody></table>"
            )
            partes.append(self._artigo("tdi", etapa, n, "publicado" if reg["estado"] in ("valor", "zero") else "ausente", corpo))
        partes.append(self.fonte("tdi"))
        partes.append("</section>")

        # 7. não-resposta
        partes.append('<section class="bloco" id="tnr">')
        partes.append(self._cabecalho_bloco("Taxa de não-resposta"))
        for etapa, rotulo, oferta in ETAPAS:
            if not e[oferta]:
                corpo = f"<h3>{titulo_etapa(rotulo)}</h3>" + self.ausencia(
                    FRASE_ETAPA, "L-59", "estados", estado="nao_aplicavel"
                )
                partes.append(self._artigo("tnr", etapa, None, "nao_ofertada", corpo))
                continue
            n = e.get(f"mat_{etapa}_2025")
            if n is not None and n < self.limiar:
                corpo = f"<h3>{titulo_etapa(rotulo)}</h3>" + self.pequena(etapa, n)
                partes.append(self._artigo("tnr", etapa, n, "suprimido", corpo))
                continue
            reg = indicador(self.d, co, etapa, "tnr")
            corpo = (
                f"<h3>{titulo_etapa(rotulo)}</h3>"
                f'<p class="n">n = {self.mat_span(etapa, "2025")} {palavra_aluno(n)} em 2025</p>'
                '<table class="tabela"><thead><tr><th>Indicador</th><th>2025</th></tr></thead><tbody>'
                f"<tr><td>Taxa de não-resposta</td><td>{self.rate_span('tnr', 'tnr', etapa, n or 1, reg)}</td></tr>"
                "</tbody></table>"
            )
            partes.append(self._artigo("tnr", etapa, n, "publicado" if reg["estado"] in ("valor", "zero") else "ausente", corpo))
        partes.append(
            '<p class="nota">A taxa de não-resposta mede falta de informação de rendimento '
            'e movimento, não participação no Saeb. <a href="como-ler.html#tnr">Como ler</a>.</p>'
        )
        partes.append(self.fonte("tnr"))
        partes.append("</section>")

        # 8. infraestrutura
        partes.append('<section class="bloco" id="infraestrutura">')
        partes.append(self._cabecalho_bloco("Infraestrutura"))
        universo_infra = e["oferta_fund_ai"] == 1 or e["oferta_fund_af"] == 1 or e["oferta_med"] == 1
        if not universo_infra:
            partes.append(
                self.ausencia(
                    FRASE_INFRA_NAO_APLICAVEL, "L-25", "infraestrutura", estado="nao_aplicavel"
                )
            )
        else:
            partes.append('<table class="tabela"><thead><tr><th>Item</th><th>Declarado em 2025</th></tr></thead><tbody>')
            for item, rotulo in INFRA_ITENS:
                reg = self.d["infra"].get((co, item), {"valor": None, "estado": "ausente"})
                if reg["estado"] == "valor" and reg["valor"] is not None:
                    texto = "tem" if reg["valor"] == 1 else "não tem"
                    celula = self._add(
                        id=f"infra-{item.lower()}", familia="infraestrutura", bloco="infraestrutura",
                        etapa="", ano="2025", valor=int(reg["valor"]), estado="valor", n=1, texto=texto,
                    )
                else:
                    celula = self._add(
                        id=f"infra-{item.lower()}", familia="infraestrutura", bloco="infraestrutura",
                        etapa="", ano="2025", valor=None, estado="ausente", n=1, texto="-",
                    )
                partes.append(f"<tr><td>{html.escape(rotulo)}</td><td>{celula}</td></tr>")
            partes.append("</tbody></table>")
            partes.append('<p class="nota">O item é o que a escola declarou ao Censo Escolar de 2025.</p>')
        partes.append(self.fonte("infraestrutura"))
        partes.append("</section>")

        # 9. creche (só quando a escola oferta creche)
        if e["oferta_inf_cre"] == 1:
            partes.append('<section class="bloco" id="creche">')
            partes.append(self._cabecalho_bloco("Creche da escola"))
            partes.append('<table class="tabela tabela-estreita"><thead><tr><th>Ano</th><th>Matrícula em creche</th></tr></thead><tbody>')
            faltam = False
            for ano in ("2024", "2025"):
                valor = e.get(f"mat_CRE_{ano}")
                if valor is None:
                    faltam = True
                    celula = self._add(
                        id=f"creche-{ano}", familia="creche", bloco="creche", etapa="creche",
                        ano=ano, valor=None, estado="ausente", n=1, texto="-",
                    )
                elif int(valor) == 0:
                    celula = self._add(
                        id=f"creche-{ano}", familia="creche", bloco="creche", etapa="creche",
                        ano=ano, valor=0, estado="zero", n=1, texto="0",
                    )
                else:
                    celula = self._add(
                        id=f"creche-{ano}", familia="creche", bloco="creche", etapa="creche",
                        ano=ano, valor=int(valor), estado="valor", n=1, texto=fmt_int(valor),
                    )
                partes.append(f"<tr><td>{ano}</td><td>{celula}</td></tr>")
            partes.append("</tbody></table>")
            if faltam:
                partes.append(self.ausencia(FRASE_MATRICULA_2024, "L-28", "censo"))
            partes.append(self.fonte("creche"))
            partes.append("</section>")

        partes.append(
            f'<p class="rodape-pagina">Procedência de cada número: '
            f'<a href="dados/{co}.json">dados/{co}.json</a>. '
            '<a href="como-ler.html">Como ler os números</a> · '
            '<a href="creditos.html">Créditos e licenças</a>.</p>'
        )
        partes.append("</main>")
        return "".join(partes)


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


def documento(titulo: str, corpo: str, data_build: str, limiar: int) -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(titulo)}</title>
<link rel="stylesheet" href="estilo.css">
</head>
<body>
<header class="topo">
  <a class="marca" href="index.html">Prova dos Nove</a>
  <p class="carimbo">build {html.escape(data_build)} · limiar de n pequeno = {limiar}</p>
</header>
{corpo}
<footer class="rodape">
  <p>Prova dos Nove · dados públicos de educação, com fonte, ano e cálculo.
  <a href="como-ler.html">Como ler os números</a> ·
  <a href="creditos.html">Créditos e licenças</a>.</p>
</footer>
</body>
</html>
"""


def pagina_index(dados: dict, data_build: str, limiar: int) -> str:
    escolas = dados["escolas"]
    por_ra: dict[str, list[dict]] = {}
    for escola in escolas:
        por_ra.setdefault(escola["ra"], []).append(escola)
    for lista in por_ra.values():
        lista.sort(key=lambda e: (e["nome"], e["co"]))

    partes = [
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
    for ra in sorted(por_ra):
        partes.append(f'<section class="ra" data-ra="{html.escape(ra)}">')
        partes.append(f"<h2>{html.escape(ra)}</h2><ul>")
        for escola in por_ra[ra]:
            partes.append(
                f'<li data-codigo="{escola["co"]}" data-nome="{html.escape(escola["nome"])}">'
                f'<a href="{escola["co"]}.html">{html.escape(escola["nome"])}</a>'
                f'<span class="rede">{html.escape(escola["rede"])}</span></li>'
            )
        partes.append("</ul></section>")
    partes.append("</div></main>")
    corpo = "".join(partes)

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
    return documento("Prova dos Nove — escolas do Distrito Federal", corpo + js, data_build, limiar)


def pagina_como_ler(data_build: str, limiar: int) -> str:
    corpo = f"""
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
<h2>Turma pequena: o limiar de n = {limiar}</h2>
<p>Nos indicadores de razão — distorção idade-série, taxa de não-resposta,
aprovação, reprovação e abandono — a página não publica a taxa quando a etapa
tem menos de {limiar} alunos. Nesse tamanho, um valor extremo (0,0% de distorção
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
declarada, não zero (L-28).</p>
</section>

<section class="bloco" id="censo">
<h2>Matrícula não declarada</h2>
<p>Quando o Censo de 2024 não tem a matrícula da escola, a página mostra
<strong>-</strong> e diz “matrícula não declarada no Censo de 2024”. O motivo da
célula vazia não é informado pela fonte (L-28).</p>
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
    return documento("Como ler os números — Prova dos Nove", corpo, data_build, limiar)


def pagina_creditos(dados: dict, data_build: str, limiar: int) -> str:
    fontes = sorted({r["fonte"] for r in dados["registros"].values()})

    def licenca(fonte: str) -> str:
        if fonte.startswith("SEEDF"):
            return "CC BY (Creative Commons Atribuição)"
        if fonte.startswith("INEP"):
            return "público, sem licença declarada no portal"
        return "não declarada"

    linhas = "".join(
        f"<tr><td>{html.escape(fonte)}</td><td>{html.escape(licenca(fonte))}</td></tr>"
        for fonte in fontes
    )
    corpo = f"""
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
<thead><tr><th>Fonte</th><th>Licença declarada</th></tr></thead>
<tbody>{linhas}</tbody>
</table>
<p>A série de matrículas por modalidade da SEEDF não é usada em nenhum número
desta versão. A matrícula publicada vem do Censo da INEP (L-62).</p>
</section>

<section class="bloco" id="build">
<h2>Este build</h2>
<p>Data do build: <strong>{html.escape(data_build)}</strong>.</p>
<p>Limiar de n pequeno usado neste build: <strong>{limiar}</strong>.</p>
<p><a href="como-ler.html">Como ler os números</a> · <a href="index.html">Todas as escolas</a>.</p>
</section>
</main>
"""
    return documento("Créditos e licenças — Prova dos Nove", corpo, data_build, limiar)


# --------------------------------------------------------------------------
# Build


def _limpar_saida(site: Path) -> None:
    for nome in ("index.html", "creditos.html", "como-ler.html", "estilo.css", "indice.json"):
        alvo = site / nome
        if alvo.is_file():
            alvo.unlink()
    for alvo in site.glob("[0-9]" * 8 + ".html"):
        alvo.unlink()
    dados_dir = site / "dados"
    if dados_dir.is_dir():
        for alvo in dados_dir.glob("*.json"):
            alvo.unlink()


def _tamanho(site: Path) -> int:
    return sum(p.stat().st_size for p in site.rglob("*") if p.is_file())


def construir_site(public: Path, out: Path, data_build: str, limiar: int, quiet: bool = False) -> dict:
    """Gera o site inteiro; devolve contagens e tamanho."""
    dados = carregar_dados(public)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "dados").mkdir(parents=True, exist_ok=True)
    _limpar_saida(out)

    (out / "estilo.css").write_text(CSS, encoding="utf-8")

    indice = [
        {"co_entidade": e["co"], "nome": e["nome"], "ra": e["ra"], "rede": e["rede"]}
        for e in dados["escolas"]
    ]
    indice.sort(key=lambda x: (x["nome"], x["co_entidade"]))
    (out / "indice.json").write_text(
        json.dumps(indice, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    (out / "index.html").write_text(pagina_index(dados, data_build, limiar), encoding="utf-8")
    (out / "como-ler.html").write_text(pagina_como_ler(data_build, limiar), encoding="utf-8")
    (out / "creditos.html").write_text(pagina_creditos(dados, data_build, limiar), encoding="utf-8")

    for escola in dados["escolas"]:
        pagina = PaginaEscola(dados, escola, data_build, limiar)
        corpo = pagina.render()
        (out / f'{escola["co"]}.html').write_text(
            documento(f'{escola["nome"]} — Prova dos Nove', corpo, data_build, limiar),
            encoding="utf-8",
        )
        (out / "dados" / f'{escola["co"]}.json').write_text(
            json.dumps(
                {"escola": escola["co"], "gerado_em": data_build, "numeros": pagina.numeros},
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    total = _tamanho(out)
    if total > TAMANHO_MAXIMO_SITE:
        raise BuildError(
            f"site com {total / (1024 * 1024):.1f} MB passa do limite de "
            f"{TAMANHO_MAXIMO_SITE / (1024 * 1024):.0f} MB"
        )
    if not quiet:
        print(
            f"site: {len(dados['escolas']):,} páginas de escola, "
            f"{total / (1024 * 1024):.1f} MB em {out}"
        )
    return {"escolas": len(dados["escolas"]), "bytes": total, "dados": dados}


# --------------------------------------------------------------------------
# Verificações do §8


def _html(site: Path, co: str) -> str:
    return (site / f"{co}.html").read_text(encoding="utf-8")


def _json_escola(site: Path, co: str) -> dict:
    caminho = site / "dados" / f"{co}.json"
    if not caminho.is_file():
        raise BuildError(f"falta {caminho}")
    return json.loads(caminho.read_text(encoding="utf-8"))


def _ids_numeros(markup: str) -> list[str]:
    return re.findall(r'data-numero="([^"]+)"', markup)


def check_procedencia(site: Path, dados: dict, data_build: str) -> str:
    for escola in dados["escolas"]:
        markup = _html(site, escola["co"])
        registro = _json_escola(site, escola["co"])
        if registro.get("escola") != escola["co"]:
            raise BuildError(f"{escola['co']}: JSON de procedência com escola diferente")
        if registro.get("gerado_em") != data_build:
            raise BuildError(f"{escola['co']}: JSON de procedência com gerado_em diferente")
        numeros = registro.get("numeros")
        if not isinstance(numeros, list) or not numeros:
            raise BuildError(f"{escola['co']}: JSON de procedência sem números")
        por_id = {}
        for numero in numeros:
            identificador = numero.get("id")
            if not identificador or identificador in por_id:
                raise BuildError(f"{escola['co']}: número sem id ou id duplicado")
            por_id[identificador] = numero
        for identificador in _ids_numeros(markup):
            if identificador not in por_id:
                raise BuildError(f"{escola['co']}: número {identificador} sem procedência")
            numero = por_id[identificador]
            for campo in ("fonte", "arquivo", "ano", "calculo", "estado"):
                if not numero.get(campo):
                    raise BuildError(f"{escola['co']}: {identificador} sem {campo}")
            if not isinstance(numero.get("n"), int):
                raise BuildError(f"{escola['co']}: {identificador} sem n inteiro")
            if not numero.get("limites"):
                raise BuildError(f"{escola['co']}: {identificador} sem limites")
            if numero["estado"] not in ESTADOS:
                raise BuildError(f"{escola['co']}: {identificador} com estado fora do contrato")
            if numero["estado"] in ("valor", "zero") and numero.get("valor") is None:
                raise BuildError(f"{escola['co']}: {identificador} com estado {numero['estado']} e valor nulo")
            if numero["estado"] in ("ausente", "nao_aplicavel") and numero.get("valor") is not None:
                raise BuildError(f"{escola['co']}: {identificador} com estado {numero['estado']} e valor")
            if not str(numero["arquivo"]).startswith("data/public/"):
                raise BuildError(f"{escola['co']}: {identificador} aponta para fora de data/public")
    return f"{len(dados['escolas']):,} páginas com procedência completa"


def check_sem_ranking(site: Path) -> str:
    proibidos = ("p10", "p90", "mediana da rede")
    for caminho in sorted(site.glob("*.html")):
        texto = caminho.read_text(encoding="utf-8").lower()
        for termo in proibidos:
            if termo in texto:
                raise BuildError(f"{caminho.name} publica {termo!r}")
    indice = json.loads((site / "indice.json").read_text(encoding="utf-8"))
    nomes = [x["nome"] for x in indice]
    if nomes != sorted(nomes):
        raise BuildError("indice.json não está em ordem alfabética por nome")
    index = (site / "index.html").read_text(encoding="utf-8")
    if 'class="num"' in index or "data-numero=" in index:
        raise BuildError("index.html publica número de escola")
    if re.search(r"\b\d[\d.]*\s+escolas?\b", index, re.IGNORECASE):
        raise BuildError("index.html publica contagem de escolas")
    return f"{len(indice):,} entradas alfabéticas, sem número no índice"


def check_limiar(site: Path, dados: dict, limiar: int) -> str:
    unidades = 0
    com_tdi = 0
    for escola in dados["escolas"]:
        markup = _html(site, escola["co"])
        for etapa, _, oferta in ETAPAS:
            if not escola[oferta]:
                continue
            n = escola.get(f"mat_{etapa}_2025")
            if n is None or n >= limiar:
                continue
            unidades += 1
            if indicador(dados, escola["co"], etapa, "tdi")["estado"] in ("valor", "zero"):
                com_tdi += 1
            palavra = "aluno" if n == 1 else "alunos"
            nota = f"{n} {palavra} {FRASE_N_PEQUENA}"
            for bloco in ("fluxo", "tdi", "tnr"):
                achado = re.search(
                    rf'<article class="etapa" data-bloco="{bloco}" data-etapa="{etapa}"[^>]*>(.*?)</article>',
                    markup,
                    re.S,
                )
                if not achado:
                    raise BuildError(f"{escola['co']}/{etapa}/{bloco}: falta o cartão da etapa")
                trecho = achado.group(1)
                if 'data-situacao="suprimido"' not in achado.group(0):
                    raise BuildError(f"{escola['co']}/{etapa}/{bloco}: n < {limiar} não foi suprimido")
                if nota not in re.sub(r"<[^>]+>", "", trecho):
                    raise BuildError(f"{escola['co']}/{etapa}/{bloco}: falta a nota de amostra pequena")
                if re.search(rf'data-numero="{bloco}-[^"]+"', trecho):
                    raise BuildError(f"{escola['co']}/{etapa}/{bloco}: publica taxa com n < {limiar}")

    alvo = "53001419"
    markup = _html(site, alvo)
    if 15 < limiar:
        if "15 alunos nesta etapa — o indicador não é publicado quando a turma é pequena" not in re.sub(
            r"<[^>]+>", "", markup
        ):
            raise BuildError(f"{alvo}: falta a nota de 15 alunos")
        if "0,0%" in markup:
            raise BuildError(f"{alvo}: TDI 0,0% aparece como taxa mesmo com 15 alunos")
    return (
        f"{unidades:,} unidades escola × etapa com n < {limiar} suprimidas "
        f"({com_tdi:,} delas com TDI valor/zero, a matriz do q16)"
    )


def check_estados(site: Path, dados: dict, limiar: int) -> str:
    frases = {
        "53000862": [FRASE_IDEB_PUBLICA],
        "53000781": [FRASE_IDEB_PRIVADA],
        "53000226": [FRASE_ETAPA],
        "53020529": [FRASE_MATRICULA_2024, FRASE_SEM_INDICADOR],
        "53000331": [FRASE_SEM_INDICADOR],
    }
    if 15 < limiar:
        frases["53001419"] = [
            "15 alunos nesta etapa — o indicador não é publicado quando a turma é pequena"
        ]
    for co, lista in frases.items():
        markup = _html(site, co)
        texto_visivel = re.sub(r"<[^>]+>", "", markup)
        for frase in lista:
            if frase not in texto_visivel:
                raise BuildError(f"{co}: frase ausente ou com redação diferente: {frase!r}")

    for escola in dados["escolas"]:
        markup = _html(site, escola["co"])
        if "NaN" in markup:
            raise BuildError(f"{escola['co']}: NaN na página")
        for estado, trecho in re.findall(
            r'data-estado="(ausente|nao_aplicavel|zero|valor)"[^>]*>([^<]*)<', markup
        ):
            texto = html.unescape(trecho).strip()
            if estado == "ausente" and texto and not texto.startswith("-"):
                raise BuildError(f"{escola['co']}: estado ausente sem hífen: {texto!r}")
            if estado == "nao_aplicavel" and texto and not texto.startswith("—"):
                raise BuildError(f"{escola['co']}: estado nao_aplicavel sem travessão: {texto!r}")
            if estado == "zero" and texto and not texto.startswith("0"):
                raise BuildError(f"{escola['co']}: estado zero sem 0: {texto!r}")
    return "símbolos e frases de ausência conferidos"


def _hashes_site(site: Path) -> dict[str, str]:
    return {
        str(p.relative_to(site)): _sha256(p)
        for p in sorted(site.rglob("*"))
        if p.is_file()
    }


def check_reprodutibilidade(public: Path, site: Path, data_build: str, limiar: int) -> str:
    base_temporaria = Path("/tmp/opencode") if Path("/tmp/opencode").is_dir() else None
    with tempfile.TemporaryDirectory(prefix="prova-dos-nove-site-", dir=base_temporaria) as tmp:
        construir_site(public, Path(tmp), data_build, limiar, quiet=True)
        a = _hashes_site(site)
        b = _hashes_site(Path(tmp))
        if a != b:
            diferentes = sorted(set(a) ^ set(b)) or sorted(k for k in a if a.get(k) != b.get(k))
            raise BuildError(f"build não é idempotente; arquivos diferentes: {diferentes[:5]}")
    return "segundo build produz os mesmos bytes"


def check_licencas(site: Path, dados: dict) -> str:
    fontes = set()
    for caminho in sorted((site / "dados").glob("*.json")):
        registro = json.loads(caminho.read_text(encoding="utf-8"))
        for numero in registro["numeros"]:
            fonte = numero["fonte"]
            fontes.add(fonte)
            minusculo = fonte.lower()
            for termo in ("odbl", "odc", "open data commons", "matriculas__relatorio_matriculas"):
                if termo in minusculo:
                    raise BuildError(f"{caminho.name}: fonte ODbL/matrículas proibida: {fonte}")
    creditos = (site / "creditos.html").read_text(encoding="utf-8")
    for fonte in fontes:
        if fonte not in creditos:
            raise BuildError(f"creditos.html não lista a fonte {fonte!r}")
    for obrigatorio in ("MIT", "CC BY 4.0", "Marcelo Anaissi"):
        if obrigatorio not in creditos:
            raise BuildError(f"creditos.html sem {obrigatorio!r}")
    return f"{len(fontes)} fontes com licença declarada nos créditos"


# --------------------------------------------------------------------------
# CLI


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build estático da página por escola (FASE-1).")
    ap.add_argument("--public", type=Path, default=Path("data/public"), help="diretório do insumo público")
    ap.add_argument("--out", type=Path, default=Path("site"), help="diretório de saída")
    ap.add_argument("--data-build", default=DATA_BUILD_PADRAO, help="único carimbo de tempo do build")
    ap.add_argument("--limiar-n", type=int, default=LIMIAR_N_PADRAO, help="limiar de n pequeno (D4)")
    ap.add_argument("--check", action="store_true", help="roda os seis critérios do §8 e para no primeiro erro")
    ap.add_argument("--check-procedencia", action="store_true", help="critério 1: procedência de todo número")
    ap.add_argument("--check-limiar", action="store_true", help="critério 3: n < limiar não publica taxa")
    ap.add_argument("--check-estados", action="store_true", help="critério 4: valor, zero, ausente e não aplicável")
    ap.add_argument("--check-licencas", action="store_true", help="critério 6: licenças e fontes")
    args = ap.parse_args(argv)
    if args.limiar_n < 0:
        ap.error("--limiar-n não pode ser negativo")

    try:
        resultado = construir_site(args.public, args.out, args.data_build, args.limiar_n)
    except (BuildError, FileNotFoundError, ValueError) as exc:
        print(f"ERRO: {exc}")
        return 1

    selecionados = []
    if args.check:
        selecionados = ["procedencia", "ranking", "limiar", "estados", "reprodutibilidade", "licencas"]
    else:
        if args.check_procedencia:
            selecionados.append("procedencia")
        if args.check_limiar:
            selecionados.append("limiar")
        if args.check_estados:
            selecionados.append("estados")
        if args.check_licencas:
            selecionados.append("licencas")

    verificacoes = {
        "procedencia": lambda: check_procedencia(args.out, resultado["dados"], args.data_build),
        "ranking": lambda: check_sem_ranking(args.out),
        "limiar": lambda: check_limiar(args.out, resultado["dados"], args.limiar_n),
        "estados": lambda: check_estados(args.out, resultado["dados"], args.limiar_n),
        "reprodutibilidade": lambda: check_reprodutibilidade(
            args.public, args.out, args.data_build, args.limiar_n
        ),
        "licencas": lambda: check_licencas(args.out, resultado["dados"]),
    }
    for nome in selecionados:
        try:
            detalhe = verificacoes[nome]()
        except BuildError as exc:
            print(f"[falhou] {nome}: {exc}")
            return 1
        print(f"[ok] {nome}: {detalhe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
