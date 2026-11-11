"""Página inicial: motivação, quatro cartões, gráfico e resumo de método.

Entrada: modelo de `loader.load_data`, carimbo do build e limiar de n.
Saída: o corpo HTML da home e a lista de números com procedência (os mesmos
registros que `dados/home.json` publica).
Idempotente: sim — render puro sobre o modelo."""

from __future__ import annotations

import html

from .contract import PHRASE_HOME_NETWORK_COMPARISON, STAGE_LABEL
from .errors import BuildError
from .fmt import fmt_dec, fmt_int, fmt_pct
from .home_chart import number_id as tdi_id, render_tdi_chart

AGGREGATE_FAMILY = {
    "contagem": "home_contagem",
    "creche": "home_creche",
    "ausencia": "home_ideb_cobertura",
    "tdi": "home_tdi_rede",
}

IDEB_UF_SLUG = {
    "Total": "total",
    "Pública": "publica",
    "Estadual": "estadual",
    "Privada": "privada",
}

COUNTER_METRICS = {"escolas", "ras", "unidades", "matriculas"}


def fmt_aggregate(row: dict) -> str:
    """Texto do agregado: contagem com `fmt_int`, percentual e percentil com `fmt_pct`."""
    if row["metrica"] in COUNTER_METRICS:
        return fmt_int(row["valor"])
    return fmt_pct(row["valor"])


def ideb_uf_id(stage: str, year: str, network: str, field: str) -> str:
    return f"ideb-uf-{stage.lower()}-{year}-{IDEB_UF_SLUG[network]}-{field}"


def fmt_ideb_uf(field: str, entry: dict) -> str:
    if field == "posicao":
        return fmt_int(entry["posicao"]) + "º"
    if field == "n_ufs":
        return fmt_int(entry["n_ufs"])
    return fmt_dec(entry[field])


class HomeNumbers:
    """Coletor de procedência da home, espelho do `SchoolPage._add`."""

    def __init__(self, data: dict):
        self.d = data
        self.records: list[dict] = []
        self.by_id: dict[str, dict] = {}

    def _span(self, identifier: str, state: str, text: str) -> str:
        return (
            f'<span class="num" data-numero="{html.escape(identifier)}" '
            f'data-estado="{state}">{text}</span>'
        )

    def _add(
        self,
        *,
        id: str,
        family: str,
        bloco: str,
        etapa: str,
        ano: str,
        value,
        state: str,
        n: int | None,
        text: str,
        limites: list[str] | None = None,
        calculo: str | None = None,
    ) -> str:
        record = self.d["registros"][family]
        if id in self.by_id:
            current = self.by_id[id]
            if current["valor"] != value or current["estado"] != state:
                raise BuildError(f"número {id} reaparece com valor/estado diferente")
            return self._span(id, state, text)
        number_record = {
            "id": id,
            "bloco": bloco,
            "etapa": etapa,
            "ano": str(ano),
            "valor": value,
            "estado": state,
            "fonte": record["fonte"],
            "arquivo": record["arquivo"],
            "calculo": calculo if calculo is not None else record["calculo"],
            "n": int(n) if n is not None else None,
            "limites": list(limites if limites is not None else record["limites"]),
        }
        self.by_id[id] = number_record
        self.records.append(number_record)
        return self._span(id, state, text)

    def aggregate(self, identifier: str, text: str | None = None) -> str:
        """Renderiza um id de `agregados.parquet`, registrando a procedência."""
        try:
            row = self.d["agregados"][identifier]
        except KeyError:
            raise BuildError(f"agregados.parquet sem o id {identifier!r}") from None
        if text is None:
            if row["estado"] != "valor":
                raise BuildError(f"agregado {identifier} com estado {row['estado']!r} na página")
            text = fmt_aggregate(row)
        return self._add(
            id=identifier,
            family=AGGREGATE_FAMILY[row["bloco"]],
            bloco=row["bloco"],
            etapa=row["etapa"],
            ano=row["ano"],
            value=row["valor"],
            state=row["estado"],
            n=row["n"],
            text=text,
        )

    def ideb_uf(self, stage: str, year: str, network: str, field: str) -> str:
        """Renderiza um número de `ideb_uf.parquet` (UF contra Brasil)."""
        try:
            entry = self.d["ideb_uf"][(stage, year, network)]
        except KeyError:
            raise BuildError(f"ideb_uf.parquet sem {stage}/{year}/{network}") from None
        if field in ("df", "brasil") and entry[f"{field}_estado"] != "valor":
            raise BuildError(
                f"Ideb de {stage}/{year}/{network} ausente em {field} não vira número"
            )
        return self._add(
            id=ideb_uf_id(stage, year, network, field),
            family="ideb_uf",
            bloco="ideb_uf",
            etapa=STAGE_LABEL[stage],
            ano=year,
            value=entry[field],
            state="valor",
            n=entry["n_ufs"],
            text=fmt_ideb_uf(field, entry),
        )


def _source_line(data: dict, family: str) -> str:
    record = data["registros"][family]
    return (
        f'<p class="fonte-linha">{html.escape(record["fonte"])} · '
        f'{html.escape(", ".join(str(ano) for ano in record["anos"]))} · '
        f'limites: {html.escape(", ".join(record["limites"]))}</p>'
    )


def _absence_bar(numbers: HomeNumbers, parts: list[tuple[str, str, str]]) -> str:
    """Barra empilhada da ausência de Ideb; as larguras saem dos próprios ids."""
    total = numbers.d["agregados"]["ideb-universo"]["valor"]
    segments = []
    for identifier, _, modifier in parts:
        value = numbers.d["agregados"][identifier]["valor"]
        width = 100 * value / total
        segments.append(
            f'<span class="parte parte-{modifier}" style="width:{width:.2f}%"></span>'
        )
    return (
        '<div class="barra-ausencia" role="img" '
        'aria-label="Composição do universo de escolas de ensino fundamental ou médio: '
        'com Ideb, com linha e sem nota, e sem linha no Ideb, por rede.">'
        + "".join(segments)
        + "</div>"
    )


def render_home_page(data: dict, data_build: str, threshold: int) -> tuple[str, list[dict]]:
    """Monta a home; devolve o corpo HTML e os registros de procedência."""
    numbers = HomeNumbers(data)

    escolas = numbers.aggregate("escolas-total")
    regioes = numbers.aggregate("ras-total")
    creche_estadual = numbers.aggregate("creche-unidades-estadual")
    creche_unidades = numbers.aggregate("creche-unidades-total")
    creche_mat_estadual = numbers.aggregate("creche-mat-estadual")
    creche_mat_total = numbers.aggregate("creche-mat-total")
    creche_pct = numbers.aggregate("creche-mat-estadual-pct")

    posicao_em = numbers.ideb_uf("EM", "2025", "Estadual", "posicao")
    ufs_em = numbers.ideb_uf("EM", "2025", "Estadual", "n_ufs")
    df_em = numbers.ideb_uf("EM", "2025", "Estadual", "df")
    brasil_em = numbers.ideb_uf("EM", "2025", "Estadual", "brasil")
    posicao_em_2023 = numbers.ideb_uf("EM", "2023", "Estadual", "posicao")
    df_em_2023 = numbers.ideb_uf("EM", "2023", "Estadual", "df")

    universo = numbers.aggregate("ideb-universo")
    com_valor = numbers.aggregate("ideb-com-valor")
    sem_valor = numbers.aggregate("ideb-sem-valor")
    publica_linha = numbers.aggregate("ideb-publica-linha-sem-valor")
    publica_sem_linha = numbers.aggregate("ideb-publica-sem-linha")
    publica_com_valor = numbers.aggregate("ideb-publica-com-valor")
    privada_linha = numbers.aggregate("ideb-privada-linha-sem-valor")
    privada_sem_linha = numbers.aggregate("ideb-privada-sem-linha")
    privada_com_valor = numbers.aggregate("ideb-privada-com-valor")

    # Os 24 ids do gráfico entram uma vez no JSON; o SVG só repete o span.
    for stage in ("AI", "AF", "EM"):
        for network in ("estadual", "privada"):
            for metric in ("p10", "mediana", "p90", "n"):
                numbers.aggregate(tdi_id(stage, network, metric))
    chart = render_tdi_chart(data)

    posicao_ai = numbers.ideb_uf("AI", "2025", "Total", "posicao")
    ufs_ai = numbers.ideb_uf("AI", "2025", "Total", "n_ufs")

    bar = _absence_bar(
        numbers,
        [
            ("ideb-com-valor", "com Ideb", "com-valor"),
            ("ideb-publica-linha-sem-valor", "pública, com linha e sem nota", "publica-linha"),
            ("ideb-publica-sem-linha", "pública, sem linha no Ideb", "publica-sem-linha"),
            ("ideb-privada-linha-sem-valor", "privada, com linha e sem nota", "privada-linha"),
            ("ideb-privada-sem-linha", "privada, sem linha no Ideb", "privada-sem-linha"),
        ],
    )

    parts = [
        "<main>",
        "<h1>Prova dos Nove</h1>",
        '<p class="subtitulo">Uma página por escola no Distrito Federal, em português '
        "comum, com a origem de cada número à vista.</p>",
        '<p class="acoes"><a class="botao" href="escolas.html">Encontrar uma escola →</a> '
        '<a class="botao-secundario" href="metodologia.html">Como fazemos →</a></p>',
        '<section class="cartoes" aria-label="Números de destaque">',
        '<article class="cartao" data-cartao="escolas">',
        f'<p class="grande-numero">{escolas}</p>',
        f'<p class="cartao-texto">escolas em {regioes} Regiões Administrativas. '
        "Cada uma tem uma página própria.</p>",
        _source_line(data, "home_contagem"),
        "</article>",
        '<article class="cartao" data-cartao="creche">',
        f'<p class="grande-numero">{creche_estadual} de {creche_unidades}</p>',
        f'<p class="cartao-texto">unidades que oferecem creche são da rede estadual. '
        f"Elas têm {creche_mat_estadual} das {creche_mat_total} matrículas de creche "
        f"({creche_pct}%); as demais são privadas ou conveniadas.</p>",
        _source_line(data, "home_creche"),
        "</article>",
        '<article class="cartao" data-cartao="ideb-uf">',
        f'<p class="grande-numero">{posicao_em} de {ufs_em}</p>',
        f'<p class="cartao-texto">lugar da rede estadual do DF no Ideb do ensino médio '
        f"em 2025: {df_em}, contra {brasil_em} na rede estadual do país. "
        f"Em 2023: {posicao_em_2023}, com {df_em_2023}.</p>",
        _source_line(data, "ideb_uf"),
        "</article>",
        '<article class="cartao" data-cartao="ideb-cobertura">',
        f'<p class="grande-numero">{com_valor} de {universo}</p>',
        f'<p class="cartao-texto">escolas de ensino fundamental ou médio têm Ideb em 2025. '
        f"Nas outras {sem_valor} não há nota — e isso não é nota zero.</p>",
        bar,
        '<ul class="legenda-ausencia">',
        f"<li>{com_valor} com Ideb: {publica_com_valor} públicas e "
        f"{privada_com_valor} privadas</li>",
        f"<li>{publica_linha} públicas com linha no Ideb e sem nota</li>",
        f"<li>{publica_sem_linha} públicas sem linha no Ideb</li>",
        f"<li>{privada_linha} privadas com linha no Ideb e sem nota</li>",
        f"<li>{privada_sem_linha} privadas sem linha no Ideb</li>",
        "</ul>",
        '<p class="nota">A INEP não publica Ideb de escola privada depois de 2017 (L-08). '
        "Nas públicas, a fonte não diz por que falta (L-09); a regra de participação pode "
        "explicar parte dos casos (L-30).</p>",
        _source_line(data, "home_ideb_cobertura"),
        "</article>",
        "</section>",
        '<section class="bloco" id="distorcao">',
        "<h2>Distorção idade-série em 2025, por rede: mediana e faixa central de 80% "
        "das escolas.</h2>",
        chart,
        f'<p class="legenda-rede">{html.escape(PHRASE_HOME_NETWORK_COMPARISON)}</p>',
        "</section>",
        '<section class="bloco" id="motivacao">',
        "<h2>Por que existe</h2>",
        "<p>Os dados da educação brasileira são públicos e abundantes, mas quase "
        "ilegíveis: dezenas de arquivos, colunas em código, séries que mudam de formato a "
        "cada ano. Quem mais precisaria deles — professores, coordenadores, jornalistas, "
        "famílias — é quem tem menos tempo para decifrá-los.</p>",
        "<p>No Distrito Federal isso tem consequência. “O DF está entre os melhores do "
        f"país” só vale para os anos iniciais ({posicao_ai} de {ufs_ai}) e só na linha "
        "Total do Ideb, que inclui a rede privada. Na rede estadual, o DF ficou em "
        f"{posicao_em} de {ufs_em} no ensino médio em 2025: {df_em}, contra {brasil_em}. "
        "Os dois números estão certos; só um deles fala da escola pública.</p>",
        "<p>Prova dos Nove reúne esses dados numa página por escola, em português claro, "
        "com a origem de cada número à vista. Quando o dado não existe, a página diz isso "
        "e não preenche com zero. Não é ranking de escolas nem avaliação de professores. "
        "O nome vem de um truque de conta que acusa o erro, mas não garante o acerto — "
        "por isso cada número mostra fonte, ano e limites.</p>",
        "</section>",
        '<section class="bloco" id="metodo">',
        "<h2>Como fazemos, em resumo</h2>",
        "<p><strong>De onde vêm.</strong> Fontes públicas: o catálogo de dados abertos da "
        "SEEDF, o Censo Escolar, o Ideb e as taxas de rendimento e distorção da INEP, e a "
        "PDAD do IPEDF. Cada arquivo é registrado com endereço, data, tamanho e impressão "
        "digital, e conferido antes do uso.</p>",
        "<p><strong>Como são tratados.</strong> Os nomes de campo originais são mantidos e "
        "cada renomeação é documentada. Antes de cruzar duas fontes, medimos quantas "
        "escolas casam e publicamos a taxa. Zero, ausente e não aplicável são três coisas "
        "diferentes, e aparecem como três.</p>",
        "<p><strong>O que a página mostra — e o que não mostra.</strong> Com menos de "
        f"{threshold} alunos na etapa, não publicamos taxa: mostramos a matrícula e "
        "explicamos por quê. Não colocamos média de rede ao lado da escola. As taxas de "
        "rendimento e distorção são de 2025 apenas; a matrícula vem do Censo, e EJA, "
        "educação especial e profissional não entram nela.</p>",
        "<p><strong>Como conferir.</strong> Cada número abre fonte, arquivo, ano, cálculo e "
        "n. O build confere a impressão digital do insumo e falha se ela mudou.</p>",
        '<p><a href="metodologia.html">→ Metodologia completa</a></p>',
        "</section>",
        "</main>",
    ]
    return "".join(parts), numbers.records
