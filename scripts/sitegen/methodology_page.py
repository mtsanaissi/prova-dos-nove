"""Página de metodologia: fontes, tratamento, limites e como conferir.

Entrada: carimbo do build e limiar de n.
Saída: HTML de `metodologia.html`.
Idempotente: sim — render puro.

A página não publica número de dado: contagem de arquivos e de limites
envelhece na semana seguinte. O único número que vem do build é o limiar.
"""

from __future__ import annotations

from .layout import document

GITHUB = "https://github.com/mtsanaissi/prova-dos-nove"

SOURCES = (
    (
        "SEEDF — dados abertos",
        "Cadastro de unidades escolares, infraestrutura, Ideb e matrículas das redes do DF",
        "2014–2025",
        "https://data.se.df.gov.br/",
    ),
    (
        "INEP — Censo Escolar",
        "Matrícula por escola e etapa, e a presença da escola no Censo de 2024",
        "2024–2025",
        "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos",
    ),
    (
        "INEP — Ideb",
        "Ideb observado por escola, por UF e do Brasil",
        "2005–2025",
        "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos",
    ),
    (
        "INEP — taxas por escola",
        "Distorção idade-série, taxa de não-resposta e rendimento",
        "2025",
        "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos",
    ),
    (
        "IPEDF — PDAD-A",
        "População e frequência escolar por Região Administrativa",
        "2024",
        "https://pdad.ipe.df.gov.br/",
    ),
)


def render_methodology_page(data_build: str, threshold: int) -> str:
    rows = "".join(
        f"<tr><td>{source}</td><td>{use}</td><td>{years}</td>"
        f'<td><a href="{url}">{url}</a></td></tr>'
        for source, use, years, url in SOURCES
    )
    body = f"""
<main>
<h1>Metodologia</h1>
<p class="subtitulo">De onde vêm os dados, como entram, o que a página mostra e o que
ela deixa de fora. Cada afirmação aqui tem um id em
<a href="{GITHUB}/blob/main/docs/LIMITES.md">docs/LIMITES.md</a>.</p>

<section class="bloco" id="fontes">
<h2>1. As fontes</h2>
<p>Só fontes públicas. Cada linha da tabela é um conjunto que o projeto baixa,
registra e confere; o endereço é o portal oficial da fonte.</p>
<table class="tabela">
<thead><tr><th>Fonte</th><th>O que é usado</th><th>Ano</th><th>Portal</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<p class="nota">A mesma operação estatística pode aparecer em duas fontes. O Censo
Escolar é a operação que a SEEDF republica: concordância entre as duas não é
confirmação independente (L-07).</p>
</section>

<section class="bloco" id="entrada">
<h2>2. Como o dado entra</h2>
<p>O caminho é sempre o mesmo: baixar, registrar, perfilar, documentar e só então
usar. Nenhum arquivo é aberto antes de ter endereço, data de download, tamanho e
impressão digital (sha256) no <code>MANIFEST.md</code>; nenhuma coluna entra sem
estar descrita no <code>SCHEMA.md</code>, com grão, chave, tipo e o que a célula
vazia significa.</p>
<p>Quando a fonte não aceita download por script, o caminho manual é declarado, não
escondido: o arquivo é baixado no navegador (ou com a verificação de certificado
desligada), deixado numa pasta de entrada, ingerido por um script que confere o
sha256 contra o manifesto e registrado como qualquer outro. O servidor de
download da INEP serve cadeia de certificados incompleta (L-16), e é por isso que
esse caminho existe.</p>
<p>Um arquivo que não foi conferido não é registrado. Se um download falhou, o
manifesto diz que faltou — não se infere o conteúdo.</p>
</section>

<section class="bloco" id="chaves">
<h2>3. Chaves e cruzamentos</h2>
<p>A chave de escola é o código INEP (<code>CO_ENTIDADE</code>). Antes de cruzar
duas fontes, o projeto mede quantas escolas casam e publica a taxa; um cruzamento
não medido é um palpite (L-55).</p>
<p>Duas fontes exigem cuidado especial. A série de Ideb da SEEDF é a republicação
fiel do Ideb por escola da INEP, valor a valor, e por isso não confirma
independentemente o número (L-07). A série de matrículas por modalidade da SEEDF
divergiu do Censo em EJA e educação profissional (L-01), e por isso a matrícula da
página vem do Censo, não da série da SEEDF.</p>
</section>

<section class="bloco" id="estados">
<h2>4. Os quatro estados</h2>
<p>Cada célula é uma de quatro coisas: <strong>valor</strong> (o dado existe),
<strong>zero</strong> (o valor é zero), <strong>ausente</strong> (deveria existir e
não foi coletado ou publicado) e <strong>não aplicável</strong> (a categoria não se
aplica à escola ou à etapa). Na tela, ausência é <strong>-</strong> e não aplicável
é <strong>—</strong>. Nenhum dos dois vira zero, média ou interpolação.</p>
<p>Escola sem Ideb não é escola com nota zero: é ausência de resultado publicado.
Os casos, as frases e os símbolos estão explicados uma vez em
<a href="como-ler.html">Como ler os números</a>.</p>
</section>

<section class="bloco" id="escola">
<h2>5. O que a página da escola mostra — e o que não mostra</h2>
<p>A página mostra só a série da própria escola (D3). Ela não traz média, mediana
nem faixa de percentil da rede ao lado da escola, e não ordena escolas por
indicador: comparar escolas premia quem já partiu na frente, e a página não é
ranking.</p>
<p>Nos indicadores de razão — distorção idade-série, taxa de não-resposta,
aprovação, reprovação e abandono — a taxa não é publicada quando a etapa tem menos
de {threshold} alunos (D4). Nesse tamanho, um valor extremo é mais provável do que
o desempenho; a página mostra a matrícula e diz que a turma é pequena. A regra vale
para a unidade escola × etapa, não para a escola inteira.</p>
<p>O denominador dessas taxas é a matrícula da etapa no Censo de 2025. Para a
distorção e o fluxo, é a mesma coorte do indicador; para o Ideb, é uma aproximação,
porque a coorte que fez o Saeb não é a matrícula inteira (L-21).</p>
</section>

<section class="bloco" id="redes">
<h2>6. A comparação entre redes na página inicial</h2>
<p>A home compara redes — estadual e privada, por etapa — e é o único lugar do site
que faz isso. A pergunta ali é de política pública: como as redes se distribuem,
não como uma escola se compara à vizinha. A página de cada escola continua sem
média de rede (D3).</p>
<p>Três ressalvas acompanham o gráfico. Ele não controla o perfil socioeconômico
dos alunos (L-65): o arquivo não tem essa variável, e o gráfico mostra que as redes
atendem públicos diferentes, não que uma escola reduz a distorção. Ele inclui todas
as unidades escola × etapa com taxa publicada, inclusive as de turma pequena, cuja
taxa a página da escola não mostra — o efeito é declarado em L-67. E "privada"
reúne as escolas conveniadas e as não conveniadas (L-36, L-37), duas categorias do
cadastro da SEEDF que não se traduzem na classificação da INEP; a rede federal fica
fora da comparação (L-32).</p>
</section>

<section class="bloco" id="conferir">
<h2>7. Como conferir cada número</h2>
<p>Cada número visível carrega um identificador e abre a sua procedência: fonte,
arquivo, ano, cálculo, n e os ids de limite que o pesam. Na página da escola, esse
registro é <code>dados/&lt;código&gt;.json</code>; na home, é
<code>dados/home.json</code>.</p>
<p>O build lê apenas o insumo versionado, confere o sha256 registrado para cada
arquivo e falha se ele mudou. O build é determinístico: o único carimbo de tempo é
o <code>--data-build</code>, e um segundo build produz os mesmos bytes. A
verificação roda os critérios do contrato antes de qualquer publicação e para no
primeiro que falhar.</p>
</section>

<section class="bloco" id="limites">
<h2>8. Limites, relatório e reprodução</h2>
<p>Todo número publicado cita os limites que o afetam. O registro completo, com
evidência, status e o que resolveria cada item, está em
<a href="{GITHUB}/blob/main/docs/LIMITES.md">docs/LIMITES.md</a>; o relatório com
as respostas e os números medidos, em
<a href="{GITHUB}/blob/main/REPORT.md">REPORT.md</a>; o dicionário de dados, em
<a href="{GITHUB}/blob/main/SCHEMA.md">SCHEMA.md</a>; e o estado do projeto, em
<a href="{GITHUB}/blob/main/README.md">README.md</a>.</p>
<p>O código, os scripts e o plano de reprodução estão em
<a href="{GITHUB}">{GITHUB}</a>. Tudo roda de uma máquina limpa com
<code>requirements.txt</code>, sem passo manual não documentado.</p>
</section>
</main>
"""
    return document("Metodologia — Prova dos Nove", body, data_build, threshold)
