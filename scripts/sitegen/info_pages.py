"""Páginas fixas: como ler e créditos.

Entrada: modelo de `loader.load_data` (créditos), carimbo e limiar.
Saída: HTML de `como-ler.html` e `creditos.html`.
Idempotente: sim — render puro."""

from __future__ import annotations

import html

from .layout import document
from .errors import BuildError


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
