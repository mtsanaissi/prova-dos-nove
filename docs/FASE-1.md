# FASE-1.md — a página por escola

Contrato da fase 1. Este documento **define** a página; não a constrói (D1). O
build é da fase 2 e vive em `scripts/12_build_site.py` (a CLI) e em
`scripts/sitegen/` (o pacote). Toda afirmação aqui tem
arquivo, ano e cálculo, e todo número publicado cita os ids de `docs/LIMITES.md`
que o limitam — a coluna "limites" de cada bloco é a lista fechada.

## 1. Objetivo, escopo e não-escopo

**Objetivo.** Uma página estática por escola, em português comum, gerada por
Python a partir dos parquets, com a série da própria escola e a procedência de
cada número.

**Escopo (D1–D6).**

- D1: a fase 1 entrega este documento; a construção é a fase 2.
- D2: página estática gerada por Python a partir de `data/public/` (recorte de
  `data/interim/`), um HTML por escola, CSS sem framework, build idempotente como
  os demais scripts.
- D3: a página mostra **só a série da própria escola**. Nenhuma faixa p10–p90 da
  rede, nenhuma mediana da rede ao lado da escola.
- D4: limiar de n pequeno = **30**, aplicado a indicadores de razão (TDI, TNR,
  aprovação/reprovação/abandono). Abaixo dele a página mostra a matrícula e a
  nota "amostra pequena", não a taxa.
- D5: publicação no GitHub Pages, primeira versão pública (§7).
- D6: titular do copyright = Marcelo Anaissi (`LICENSE`).

**Não-escopo.** Ranking de escolas (proibido por `AGENTS.md`); lista nominal de
alunos ou fila de creche; dado individual; comparação entre escolas na mesma
página; contato institucional com SEEDF/INEP; mapa (L-46); idade exata em 2025
(L-03); Ideb de escola privada depois de 2017 (L-08).

## 2. Blocos da página

Cada bloco tem fonte, ano, cálculo, n e os ids que o pesam. "n" é o
denominador daquele bloco **naquela escola**; quando o bloco vale para a escola
inteira, n = 1.

| # | bloco | fonte e arquivo | ano | cálculo | n | limites |
|---|---|---|---|---|---|---|
| 1 | identificação | cadastro SEEDF, `escolas__relatorio_escolas_2025.parquet` (`Nome da escola`, `Nome RA`, `Nome Rede`) | 2025 | cópia do campo; a RA sai como rótulo de exibição (§2.1) | 1.291 | L-36, L-37, L-64 |
| 2 | oferta por etapa | mesmo cadastro, vetor `INF_CRE`…`PROF` (8 sinalizadores) | 2025 | flag 1 = oferta; **não** traduzir "é EI" | 1.291 | L-57, L-36 |
| 3 | matrícula por etapa | Censo INEP, `censo_escola_df.parquet` (`QT_MAT_INF_CRE`, `QT_MAT_FUND_AI`, `QT_MAT_FUND_AF`, `QT_MAT_MED`) | 2024–2025 | soma da etapa por escola, como está no campo; a presença em 2024 vem da flag `censo_2024_presente`, nunca da oferta de 2025 | 1.360 linhas em 2024 (76 com célula vazia; 53 escolas de 2025 sem linha) e 1.291 em 2025 | L-28, L-43, L-48, L-62, L-63 |
| 4 | Ideb por etapa | `ideb_escolas_df.parquet`, `indicador = ideb_observado` | 2005–2025, de dois em dois anos | valor observado; **a meta (`ideb_projetado`) não é publicada**; privada só até 2017 | 499 escolas com valor em 2025 | L-08, L-12, L-30, L-33, L-56 |
| 5 | fluxo | `tx_rend_escolas_df.parquet`, `categoria ∈ {aprovacao, reprovacao, abandono}` | 2025 | percentual da etapa, como publicado | 1.355 unidades escola × etapa | L-11, L-59, L-21, D4 |
| 6 | distorção idade-série | `tdi_escolas_df.parquet` | 2025 | percentual da etapa | 1.355 unidades | L-11, L-59, L-40, D4 |
| 7 | não-resposta | `tnr_escolas_df.parquet` | 2025 | percentual da etapa | 1.355 unidades | L-09, L-11, L-59 |
| 8 | infraestrutura | `relatorio_infraestrutura_2025.parquet`, colunas `IN_*` | 2025 | presença do item, nos 8 itens listados abaixo | 927 | L-25, L-29, L-38, L-51 |
| 9 | creche da escola | Censo INEP, `censo_escola_df.parquet` (`QT_MAT_INF_CRE`) | 2024–2025 | matrícula em creche da escola, como está no campo; presença em 2024 pela flag `censo_2024_presente` | unidades com `INF_CRE = 1` (475 em 2025) | L-27, L-28, L-62, L-63 |

**Itens de infraestrutura publicados (decisão do mantenedor, 2026-11-06).**
Oito linhas, ano de 2025, universo das 927 escolas que oferecem ensino
fundamental ou médio. O item é o que a escola declarou ao Censo Escolar; a
coluna é a do arquivo, repetida aqui para o export não ter de adivinhar.

| linha na página | coluna | escolas com o item (927) |
|---|---|---|
| Biblioteca | `IN_BIBLIOTECA` | 39,4% |
| Sala de leitura | `IN_SALA_LEITURA` | 80,5% |
| Quadra de esportes | `IN_QUADRA_ESPORTES` | 85,1% |
| Laboratório de informática | `IN_LABORATORIO_INFORMATICA` | 47,0% |
| Laboratório de ciências | `IN_LABORATORIO_CIENCIAS` | 35,1% |
| Internet para os alunos | `IN_INTERNET_ALUNOS` | 46,4% |
| Refeitório | `IN_REFEITORIO` | 48,3% |
| Banheiro acessível (cadeirante) | `IN_BANHEIRO_PNE` | 94,3% |

Três decisões embutidas nesta lista, todas com motivo:

- **Biblioteca e sala de leitura são duas linhas, não uma.** A fonte separa os
  dois itens (39,4% e 80,5%) e 94,0% das escolas têm pelo menos um. Mostrar só
  "biblioteca" diria "não tem espaço de leitura" para escola que tem sala de
  leitura — exatamente o erro que L-51 fechou. A linha combinada
  (`IN_BIBLIOTECA_SALA_LEITURA`, 94,0%) não substitui as duas.
- **Fora da lista por não informarem nada:** água potável (100%), internet sem
  qualificação (100%) e banheiro (99,9%). Um "sim" em toda escola não descreve
  escola nenhuma.
- **Quadra é a geral (`IN_QUADRA_ESPORTES`, 85,1%), não a coberta** (63,1%): a
  pergunta que o leitor faz é "tem quadra?", e o detalhe de cobertura fica para
  quando houver espaço na página.

Regras que valem para todos os blocos:

- Nenhum bloco publica média, mediana ou distribuição de rede (D3).
- A ordem dos blocos é fixa e não é ordenável por indicador: a página não vira
  ranking por clique.
- Matrícula da etapa é o denominador de n do bloco de razão (L-21: para TDI e
  fluxo é a mesma coorte; para o Ideb é aproximação, e o bloco diz isso).
- Cada número carrega, no JSON de procedência (§5), fonte, arquivo, ano, cálculo,
  n e ids.

### 2.1 A lista de escolas (`escolas.html`)

A lista de todas as escolas, com três formas de chegar na mesma página (decisão
do mantenedor, 2026-11-06; desde 2026-11-11 ela fica em `escolas.html`, e a raiz
do site passou a ser a home do §2.3). Três formas de chegar, na mesma página:

- **busca por nome**: campo que filtra enquanto se digita, sem servidor, lendo
  `indice.json` no navegador;
- **salto por Região Administrativa**: um `<select id="ir-ra">` com as 35 RAs em
  ordem de rótulo, que leva à seção `#ra-<slug>` da RA escolhida;
- **lista por Região Administrativa**: as 35 RAs em ordem alfabética, e dentro de
  cada uma as escolas em ordem alfabética, com nome e rede (estadual, privada
  conveniada, privada não conveniada, federal).

O rótulo de exibição da RA ("Águas Claras", "Ceilândia", "Sol Nascente/Pôr do
Sol") é só de tela e vive numa tabela escrita à mão em `scripts/sitegen/region.py`
(L-64): `data-ra`, `indice.json` e `data/public/escolas.parquet`
mantêm o valor bruto do cadastro (`AGUAS CLARAS`, `CEILANDIA`,
`SOL NASCENTE / POR DO SOL`), e o `#ra-<slug>` (`#ra-aguas-claras`,
`#ra-ceilandia`) deriva desse valor bruto.

Regras:

- A lista **não publica número**: nem contagem de escolas por RA, nem média,
  nem total. Número é coisa da página da escola, onde a procedência aparece
  número a número. Se a contagem for pedida depois, entra com bloco de fonte
  próprio.
- Nenhuma ordenação por indicador; a ordem é alfabética em todos os níveis.
- Sem JavaScript a lista por RA continua legível: o HTML é gerado com as 1.291
  escolas; o JavaScript filtra e salta. O `<select>` fica escondido sem
  JavaScript (`<noscript><style>` no `<head>` de `escolas.html`) e o aviso do
  corpo diz que busca e salto precisam de JavaScript, com a lista completa logo
  abaixo.
- `indice.json` é `[{co_entidade, nome, ra, rede}]`, ordenado por `nome`, e é o
  único insumo da busca.

### 2.2 O sumário da página da escola

Cada página de escola tem, logo depois do subtítulo e antes do aviso da página e
da primeira seção, um sumário das seções (critério 8). É um
`<nav class="sumario-escola" aria-label="Seções desta página">` com um
`<details>` fechado por padrão, `<summary>Nesta página</summary>` e uma lista sem
numeração:

```html
<nav class="sumario-escola" aria-label="Seções desta página"><details><summary>Nesta página</summary><ul role="list"><li><a href="#identificacao">Identificação</a></li>…</ul></details></nav>
```

As nove âncoras, na ordem fixa do §2, são `identificacao`, `oferta`, `matricula`,
`ideb`, `fluxo`, `tdi`, `tnr`, `infraestrutura` e `creche`; o link e a seção da
creche só existem quando `oferta_inf_cre == 1` (475 escolas em 2025). O rótulo de
cada link é o mesmo `<h2>` da seção.

Regras:

- O sumário é só rótulo: não publica número, contagem, ranking, `data-numero` nem
  `class="num"`, e não entra em `dados/<CO_ENTIDADE>.json` — não é bloco de dado,
  não tem fonte, n nem limite próprio.
- Os ids são âncoras públicas e não são renomeados; a ordem é a ordem fixa do §2,
  não ordenável por indicador.
- Fecha por padrão e abre sem JavaScript (`<details>` nativo, por teclado e por
  clique, com foco visível); a impressão esconde o sumário.
- A lista é `<ul role="list">`: `list-style: none` (no CSS) tira a semântica de
  lista no Safari/VoiceOver, e o papel explícito a devolve; o `<nav>` mantém o
  `aria-label` do marco de navegação.
- As seções e o sumário saem da mesma lista no gerador
  (`school_page.SCHOOL_SECTIONS`); o `--check` compara o HTML com uma cópia
  congelada do contrato (`checks/school_toc.py`), para que renomear um id quebre o
  build.

### 2.3 A home (`index.html`)

A raiz do site passou a ser a home (decisão do mantenedor, 2026-11-11). Ela
publica número — é o único lugar, junto da página da escola, onde isso acontece —
e por isso cada número visível é um `data-numero` com registro em
`site/dados/home.json`, com o mesmo formato do registro da página da escola
(`fonte`, `arquivo`, `ano`, `calculo`, `estado`, `n`, `limites`), e é conferido
pelo critério 9.

O conteúdo é fixo, nesta ordem:

1. **Cabeçalho e chamada**: o nome do projeto, uma frase sobre o que ele é, e os
   dois links de entrada (`escolas.html` e `metodologia.html`).
2. **Quatro cartões**, cada um com `data-cartao` (o critério 9 conta quatro), o
   número grande, o texto e uma linha de fonte com ano e limites. Sem seta de
   variação e sem cor de bom/ruim:
   - `escolas-total` e `ras-total`: escolas e Regiões Administrativas do
     cadastro SEEDF de 2025 (L-36, L-37, L-64);
   - `creche-unidades-estadual`, `creche-unidades-total`, `creche-mat-estadual`,
     `creche-mat-total` e `creche-mat-estadual-pct`: unidades que ofertam creche
     e a matrícula delas por rede, do Censo (L-27, L-28, L-36, L-62, L-63);
   - `ideb-uf-em-2025-estadual-*` e `ideb-uf-em-2023-estadual-*`: posição e valor
     do DF no Ideb do ensino médio da rede estadual, contra o Brasil e contra
     2023 (L-10, L-32, L-66);
   - `ideb-*`: cobertura do Ideb em 2025 no universo de escolas com anos
     iniciais, finais ou médio, decomposta por estado do dado — com Ideb, com
     linha e sem valor, sem linha — e por rede (L-08, L-09, L-30, L-31).
3. **Gráfico de distorção idade-série por rede**: mediana e faixa central de 80%
   das escolas, por etapa, em SVG inline (sem JavaScript), com uma tabela
   equivalente em `<details>` e a legenda de rede obrigatória
   (`contract.PHRASE_HOME_NETWORK_COMPARISON`), que cita L-65, L-67, L-36, L-37 e
   L-32. A comparação entre redes existe só aqui: D3 continua valendo na página
   da escola e na lista, e o escopo está no critério 2 do §8.
4. **Motivação** em três parágrafos, com os mesmos ids do cartão do Ideb e o
   `ideb-uf-ai-2025-total-posicao` da linha Total dos anos iniciais.
5. **Resumo de método** em quatro blocos, com link para `metodologia.html`.

Regras da home:

- Número só aparece em `data-numero`; o texto não digita número de dado. O único
  número fora de `data-numero` é o limiar de n, que vem de `--limiar-n` e já
  aparece no carimbo de todas as páginas.
- A decomposição da ausência de Ideb é por **estado do dado**, nunca por causa:
  a fonte não separa não participação, participação abaixo do critério e
  resultado não publicado (L-09), e a regra de participação entra como explicação
  possível de parte dos casos (L-30), nunca como causa por escola.
- Zero, ausente e não aplicável continuam distintos; linha com o Ideb ausente
  (`df_estado = "ausente"`) nunca é renderizada como número.
- Nada de seta de variação, cor de juízo ou link para página de escola: a home
  não é ranking nem índice.
- A distribuição entre redes usa **todos** os valores publicados, inclusive as
  unidades de turma pequena que a página da escola suprime (L-67), e por isso a
  mediana da home é a mesma de `README.md` e `REPORT.md`.
- Percentual e percentil mostram **um decimal, com arredondamento half-up sobre a
  string decimal** (`fmt_pct`): 8,95 → 9,0; 4,05 → 4,1; 0,3499 → 0,3. As páginas
  de escola continuam com `fmt_dec`.

Se o limiar for aplicado ao agregado, as cinco peças mudam no mesmo commit:
`06_analysis.py` (o export passa a receber o limiar e `CALCULO_TDI_REDE` perde a
ressalva da turma pequena), `contract.py` (`PHRASE_HOME_NETWORK_COMPARISON`),
`README.md` e `REPORT.md` (medianas 8,9 / 17,0 / 20,5 e 1,3 / 3,2 / 4,5), L-67 em
`docs/LIMITES.md` e `data/public/` (`agregados.parquet` e `procedencia.json`). O
critério 9 falha até as peças se alinharem, porque confere a legenda e a ressalva
da turma pequena em cada registro `tdi-*`.

### 2.4 A metodologia (`metodologia.html`)

Página de método para quem audita, separada de `como-ler.html`, que continua
sendo o guia do leitor de um número (os 1.291 links de âncora das páginas de
escola apontam para lá e não mudaram). Oito seções, cada uma com `id` e
`class="bloco"`:

| # | id | assunto |
|---|---|---|
| 1 | `fontes` | tabela de fonte, o que é usado, ano e portal oficial |
| 2 | `entrada` | download → `MANIFEST.md` → perfil → `SCHEMA.md`, com o caminho manual declarado da INEP (L-16) |
| 3 | `chaves` | taxa de casamento medida antes de cada join (L-55); a série da SEEDF é republicação (L-07) e a de matrículas diverge do Censo (L-01) |
| 4 | `estados` | os quatro estados, com link para `como-ler.html` |
| 5 | `escola` | o que a página da escola mostra e não mostra (D3, D4, sem ranking, sem média de rede) |
| 6 | `redes` | por que a home compara redes, L-65, L-67 e "privada" = conveniada + não conveniada |
| 7 | `conferir` | `dados/<código>.json`, `dados/home.json`, sha256 do insumo, build determinístico, `--check` |
| 8 | `limites` | links para `docs/LIMITES.md`, `REPORT.md`, `SCHEMA.md`, `README.md` e o repositório |

A página **não publica número de dado**: contagem de arquivos e de limites
envelhece na semana seguinte. O único número que vem do build é o limiar de n,
lido de `--limiar-n`.

## 3. Contrato de dados

Quatro estados, três símbolos na tela. Nenhum vira `NaN` na saída e nenhum é
substituído por zero.

| estado | o que é | na página |
|---|---|---|
| `valor` | o dado existe e foi informado | o número, com unidade e ano |
| `zero` | o valor é zero | `0` (com unidade) |
| `ausente` | deveria existir e não foi coletado ou não foi publicado | `-` e, quando a causa é conhecida, uma linha de motivo (ex.: "a INEP não publica Ideb de escola privada depois de 2017", L-08) |
| `nao_aplicavel` | a categoria não se aplica à escola | `—` (travessão), com "etapa não ofertada" quando é o caso (L-59) |

O que cada fonte pode emitir, medido nos parquets em 2026-11-06 (`SCHEMA.md`,
"Vocabulário controlado"):

| fonte | estados possíveis |
|---|---|
| Ideb por escola | `valor`, `ausente` |
| TDI, TNR e fluxo | `valor`, `zero`, `nao_aplicavel` |
| Censo por escola | `valor`, `ausente` |

Consequência para o código de build: `ausente` **não** é deduzido de `NaN` no
parquet do Ideb sem checar `estado`; e `nao_aplicavel` **não** pode ser lido como
"não oferta EF/EM" — a oferta vem do vetor do bloco 2, não do indicador.

### 3.1 O texto de cada ausência

A frase é fixa por caso — não é redigida escola por escola. Cada uma termina com
o id que a sustenta, e todas são explicadas uma vez em `site/como-ler.html`
(decisão do mantenedor, 2026-11-06).

| situação | onde aparece | texto na página | id |
|---|---|---|---|
| etapa não ofertada | blocos 4–7, quando a etapa não está no vetor de oferta | `— esta etapa não é ofertada pela escola em 2025` | L-59 |
| Ideb ausente, rede privada | bloco 4, escola privada sem valor no ano | `sem Ideb: a INEP não publica resultado de escola privada depois de 2017` | L-08 |
| Ideb ausente, rede pública | bloco 4, escola pública sem valor no ano | `sem Ideb em 2025: a INEP não publica quando há menos de 10 alunos na prova ou participação abaixo de 80%, e não informa qual foi o caso` | L-09, L-30 |
| matrícula não declarada, 2024 | bloco 3 e 9, Censo de 2024 com a célula vazia | `matrícula não declarada no Censo de 2024` | L-28 |
| escola fora do Censo de 2024 | bloco 3 e 9, escola de 2025 sem linha no Censo de 2024 | `a escola não consta do Censo de 2024` | L-63 |
| matrícula não declarada, 2025 | bloco 3, 5, 6, 7 e 9, Censo de 2025 com a célula vazia | `matrícula não declarada no Censo de 2025` | L-28 |
| infraestrutura fora do universo | bloco 8, escola que não oferece ensino fundamental nem médio | `a infraestrutura é publicada para as escolas que oferecem ensino fundamental ou médio` | L-25 |
| nenhum indicador | página sem Ideb e sem taxas | `esta escola não tem Ideb nem taxas publicadas em 2025` | L-09 |
| n abaixo do limiar | blocos 5, 6 e 7 quando n < 30 | `16 alunos nesta etapa — o indicador não é publicado quando a turma é pequena` (o número é o n da escola) | D4, L-40 |

Regras:

- Nenhuma frase nomeia causa que a fonte não distingue (L-09): não se escreve
  "não participou" nem "participou pouco".
- O ano da frase do Ideb é o ano do bloco; a frase da rede privada vale para
  qualquer ano.
- O símbolo (`-` ou `—`) vem antes do texto, que entra em corpo menor (§3).
- `site/como-ler.html` reúne, uma vez: os quatro estados e o que cada símbolo
  significa; a regra dos 10 alunos e 80% (L-30); por que a rede privada não tem
  Ideb (L-08); por que a TNR não explica a ausência (L-09); o limiar de n = 30
  (D4) e a aproximação do denominador (L-21). É linkada de cada frase de
  ausência; `creditos.html` continua sendo só licença e titular.

## 4. Perfis-piloto

Sete perfis escolhidos por **condição em coluna**, nunca por nome, com desempate
pelo menor `CO_ENTIDADE`. Servem para provar que a página funciona nos casos
difíceis antes de gerar 1.291.

| perfil | condição | CO_ENTIDADE | o que a página tem de mostrar |
|---|---|---|---|
| a | `Rede = 2` e Ideb AI **e** AF em 2025 | **53000854** | duas séries de Ideb (247 alunos em AI, 138 em AF) |
| b | `Rede = 2`, `MED = 1` e Ideb EM em 2025 | **53000986** | série do médio com 614 alunos |
| c | `Rede = 2`, TDI e fluxo, sem Ideb 2025 | **53000862** | fluxo e distorção com `-` no Ideb, motivo L-30 |
| d | `Rede = 4`, TDI e sem Ideb (335 candidatas) | **53000781** | igual ao (c), com o motivo L-08; 194 alunos em AI |
| e | vetor de oferta sem `FUND_AI`, `FUND_AF` e `MED` (364) | **53000226** | `—` nas três etapas, oferta EJA + ESP; **não tem linha em TDI/TNR/fluxo** — é o caso que prova que `nao_aplicavel` não sai de indicador |
| f | unidade com `n < 30` e TDI `valor`/`zero` (67) | **53001419** | 15 alunos em AI e TDI 0,0% **não** aparecem como taxa: mostra n e a nota de amostra pequena (D4) |
| g | `Rede = 1`, `MED = 1` e Ideb EM em 2025 | **53001354** | série do médio na rede federal (1.212 alunos; 1.445 em AF) |

Os dois casos sem indicador nenhum — **53020529** (estadual) e **53000331**
(privada conveniada) — entram como teste de página vazia: oferta no vetor,
nenhum Ideb e nenhuma taxa. A página mostra a oferta e diz o que falta.

## 5. Arquivos gerados e build

### 5.1 Insumo versionado: `data/public/`

`06_analysis.py --public data/public` exporta, de `data/interim/`, o recorte que
o build lê. Seis arquivos, nenhum com microdado, nenhum com linha de aluno: três
por escola e dois de contexto, na lista fechada do `AGENTS.md` (tabela nova ali
exige emenda lá).

| arquivo | grão | colunas | tamanho medido |
|---|---|---|---|
| `escolas.parquet` | escola (1.291) | `co_entidade`, `nome`, `ra`, `rede`, `rede_cadastro`, `censo_2024_presente`, `oferta_inf_cre`…`oferta_prof` (8 flags), `mat_inf_cre_2024`, `mat_fund_ai_2024`, `mat_fund_af_2024`, `mat_med_2024` e as quatro de 2025 | 61.846 B |
| `indicadores.parquet` | escola × etapa × indicador × ano | `co_entidade`, `etapa` (`AI`/`AF`/`EM`), `indicador` (`ideb_observado`, `tdi`, `tnr`, `aprovacao`, `reprovacao`, `abandono`), `ano`, `valor`, `estado` | 40.420 B |
| `infraestrutura.parquet` | escola × item (8 itens do §2) | `co_entidade`, `item` (nome da coluna `IN_*`), `ano` (2025), `valor` (0/1), `estado` | 12.289 B |
| `ideb_uf.parquet` | etapa × ano × rede (24 linhas, 2023 e 2025) | `etapa`, `ano`, `rede` (`Total`/`Pública`/`Estadual`/`Privada`), `df`, `df_estado`, `brasil`, `brasil_estado`, `posicao`, `n_ufs` | 5.653 B |
| `agregados.parquet` | id do número da home (40 linhas) | `id`, `bloco` (`contagem`/`creche`/`ausencia`/`tdi`), `grupo`, `etapa`, `ano`, `metrica`, `valor`, `n`, `estado` | 6.030 B |
| `procedencia.json` | um registro por indicador/família (14 famílias) | `fonte`, `arquivo`, `anos`, `calculo`, `limites`, `licenca`, `licenca_url`; topo com `sha256` dos cinco parquets e `execucao.etapas_puladas` | 7.964 B |

Regras do export, todas verificáveis:

- `estado` é copiado do parquet de origem, nunca deduzido de `NaN` (§3).
- Matrícula vem do Censo 2024 e 2025; a série ODbL da SEEDF não entra (L-62).
- Só entram os recortes de etapa `FUN_AI`, `FUN_AF` e `MED`; `FUN`, `FUN_01`…`09`,
  `MED_01`…`04` e `MED_NS` ficam fora (a página não desce a série).
- A meta do Ideb (`ideb_projetado`) fica fora do insumo publicado: é meta do
  ciclo 2007–2021, não previsão, e decisão do mantenedor (2026-11-06) é não
  publicá-la nesta versão (L-56).
- Mapa de etapa entre fontes: Ideb `AI`/`AF`/`EM` ↔ recorte `FUN_AI`/`FUN_AF`/`MED`.
- `censo_2024_presente` é um fato do Censo 2024: `True` quando o `CO_ENTIDADE`
  tem linha em 2024, `False` quando não tem. A flag só escolhe a frase da
  ausência; ela não converte matrícula positiva em `nao_aplicavel` e não afirma
  que a escola é nova (L-63).
- A licença vai por família em `procedencia.json`: a SEEDF usa `licenca_titulo`
  e `licenca_url` do conjunto no inventário do CKAN; a INEP usa "público, sem
  licença declarada no portal", com `licenca_url` nulo. O export falha antes de
  gravar se uma família SEEDF resolver para ODbL (L-62).
- `execucao.etapas_puladas` é vazio numa execução completa. Com `--parcial`, o
  export grava a lista de etapas puladas e o build avisa; sem `--parcial`, uma
  etapa pulada faz o `06` sair 1 **sem** gravar.
- O export falha se `data/public/` já existir com `sha256` diferente do que vai
  gravar e o `--force` não for passado: mudança no insumo aparece no diff.
- `data/public/` é gerado e **commitado** (exceção declarada em `AGENTS.md`).
- `ideb_uf.parquet` e `agregados.parquet` são as duas tabelas de contexto da lista
  fechada: a primeira é de território (UF), não de escola; a segunda é derivada
  dos arquivos por escola, na mesma execução. As duas existem para a home e
  nenhuma página de escola as lê.
- `agregados.parquet` não aplica o limiar de n: a distribuição de distorção inclui
  as unidades de turma pequena, e a diferença em relação à página da escola é
  declarada em L-67. Filtrar pelo limiar exigiria o valor da flag dentro do
  export e faria a home discordar de `README.md` e `REPORT.md`.
- `valor` de `agregados.parquet` é quantizado a 4 decimais; `n` é `Int64` e
  significa o denominador da métrica (unidades, matrículas), `null` quando o
  valor já é a contagem. O texto de exibição é responsabilidade da home
  (`fmt_int` para contagem, `fmt_pct` para percentual e percentil).

### 5.2 Saída: `site/`

```text
site/
├── index.html                     # home: motivação, quatro cartões, gráfico por rede e resumo de método (§2.3)
├── escolas.html                   # busca por nome + salto por RA + lista por RA, sem número (§2.1)
├── metodologia.html               # fontes, tratamento, limites e como conferir (§2.4)
├── indice.json                    # [{co_entidade, nome, ra, rede}] — alimenta a busca de escolas.html
├── estilo.css                     # sem framework
├── creditos.html                  # licença por fonte e titular (critério 6)
├── como-ler.html                  # estados, ausências e limiar de n, explicados uma vez
├── <CO_ENTIDADE>.html             # uma página por escola (1.291), com o sumário das seções (§2.2)
└── dados/
    ├── <CO_ENTIDADE>.json         # procedência de cada número daquela página
    └── home.json                  # procedência de cada número da home (§2.3)
```

Formato do `dados/<CO_ENTIDADE>.json`:

```json
{
  "escola": "53000854",
  "gerado_em": "2026-11-06",
  "numeros": [
    {
      "bloco": "ideb",
      "etapa": "anos iniciais",
      "ano": "2025",
      "valor": 6.1,
      "estado": "valor",
      "fonte": "INEP — Ideb por escola",
      "arquivo": "data/public/indicadores.parquet",
      "calculo": "valor observado da etapa, como publicado",
      "id": "ideb-ai-2025",
      "n": 247,
      "limites": ["L-30", "L-33"]
    }
  ]
}
```

O `id` é obrigatório e único na página: é o valor do `data-numero` do HTML, e o
`--check` falha quando um número visível não tem entrada (§8, critério 1).

`dados/home.json` tem a mesma lista, com dois campos a mais no topo:

```json
{
  "pagina": "home",
  "gerado_em": "2026-11-06",
  "numeros": [
    {
      "id": "tdi-ai-estadual-mediana",
      "bloco": "tdi",
      "etapa": "anos iniciais",
      "ano": "2025",
      "valor": 8.95,
      "estado": "valor",
      "fonte": "INEP — Distorção Idade-Série por Escola 2025",
      "arquivo": "data/public/agregados.parquet",
      "calculo": "Percentil (interpolação linear) da distorção idade-série de 2025 …",
      "n": 386,
      "limites": ["L-11", "L-32", "L-36", "L-37", "L-59", "L-65", "L-67"]
    }
  ]
}
```

O mesmo `id` pode aparecer mais de uma vez no HTML (o cartão e a motivação, o
gráfico e a tabela), mas entra **uma vez** no JSON; repetição com valor ou estado
diferente interrompe o build. O critério 9 confere a lista inteira.

Onde `n` sai: é a matrícula da etapa de 2025 em `escolas.parquet`; `q16`
(`data/interim/q16_presenca_escola_etapa.csv`) é o artefato que prova a conta, não
o insumo do build.

`n` é inteiro ou `null`. É `null` quando a matrícula que serviria de denominador
não existe; nesse caso a página mostra a matrícula `-` e as taxas da unidade não
são publicadas; o Ideb, se existir, mantém o valor com `n: null`. `n_referencia`
só aparece quando o `n` é contagem de alunos e o ano da matrícula usada difere
do ano do número: hoje, o Ideb de 2005–2023 leva `"n_referencia": "2025"`; o
Ideb de 2025, matrícula, creche, oferta e infraestrutura não levam o campo.
Quando o `n` é `null`, não existe contagem de alunos e `n_referencia` também
não aparece. Matrícula, creche, oferta e infraestrutura têm `n = 1` (a escola),
não uma contagem de alunos.

### 5.3 Interface do build

```bash
# local, depois de 06 --public
python scripts/12_build_site.py \
  --public data/public --out site --data-build 2026-11-06 --limiar-n 30

# verificação dos critérios do §8 (sai != 0 se algum falhar)
python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check

# só o critério 8 (sumário da página da escola)
python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-sumario-escola
```

O build vive em `scripts/sitegen/`; `scripts/12_build_site.py` é a CLI e mantém
o comando acima. O `--check` roda as dez verificações na ordem do registro
(`procedencia`, `ranking`, `sumario`, `limiar`, `estados`, `sumario_escola`,
`home`, `reprodutibilidade`, `licencas`, `casos_limite`) e para no primeiro que
falhar. A ordem documentada é a de `CHECKS`, em
`scripts/sitegen/checks/__init__.py`, e cada verificação com flag tem o seu
`--check-*` (`--check-casos` é a décima).

- Sem dependência nova: só `pandas` e `pyarrow` (já em `requirements.txt`) e
  HTML montado por f-string. O ambiente de CI instala apenas o `requirements.txt`;
  `jinja2` não está lá e não entra por causa do build.
- Determinismo: iteração em ordem fixa (escola por `co_entidade`, indicador por
  nome, anos crescentes), JSON com `sort_keys=True`, e o único carimbo de tempo é
  `--data-build`. O build **não** chama `datetime.now()`.
- Não lê `data/interim/` nem `data/raw/`; falha com mensagem clara se
  `data/public/` não existir ou se o `sha256` registrado não bater.
- `--limiar-n` é o único lugar onde mora o 30 de D4; o valor usado vai para o
  `creditos.html` e para o cabeçalho de cada página.

## 6. `q16` — a medida que sustenta o contrato

`q16` (em `scripts/06_analysis.py`) grava:

- `data/interim/q16_presenca_escola_etapa.csv`: uma linha por escola × etapa,
  com oferta no vetor da SEEDF, matrícula do Censo 2025, Ideb, TDI, TNR e
  aprovação, cada um com o seu `estado`. O denominador é a matrícula da etapa no
  Censo 2025 (mesma proxy do q13, L-21).
- `data/interim/q16_faixas_n.csv`: distribuição de n por etapa e por faixa, com
  a taxa de valor extremo (TDI = 0,0 e aprovação = 100) e a meia-largura de
  Wilson a 95% em p = 10%.

Medido em 2026-11-06 (1.355 unidades com TDI `valor` ou `zero`):

| faixa de n | unidades | TDI = 0,0 | aprovação = 100% | meia-largura de Wilson (p = 10%) |
|---|---|---|---|---|
| 1–9 | 17 | 47,1% | 64,7% | ±26,3 p.p. (n mediano = 5) |
| 10–19 | 23 | 65,2% | 52,2% | ±15,8 p.p. (n = 15) |
| 20–29 | 27 | 48,1% | 59,3% | ±12,2 p.p. (n = 25) |
| 30–49 | 62 | 25,8% | 54,8% | ±9,7 p.p. (n = 39) |
| 50–99 | 184 | 14,1% | 44,6% | ±6,9 p.p. (n = 74,5) |
| 100+ | 1.042 | 2,2% | 17,2% | ±3,3 p.p. (n = 330) |

67 unidades em 61 escolas ficam abaixo de 30; 129 em 115 abaixo de 50. É esse
número que sustenta D4 = 30: abaixo de 30 o valor extremo é o mais provável, não
o desempenho.

`67` é o recorte das unidades com TDI `valor` ou `zero` — a matriz de
`q16_faixas_n.csv`. `80` é o recorte do build: as mesmas unidades mais as 13
unidades ofertadas que não têm linha de TDI, e que também precisam de supressão
quando não há denominador. São recortes diferentes; não se somam nem se
comparam como se fossem o mesmo conjunto.

## 7. Publicação (D5, D-B)

Repo: `https://github.com/mtsanaissi/prova-dos-nove`. Fonte de publicação por
branch aceita apenas `/` ou `/docs` (a documentação oficial do GitHub Pages);
`/docs` já é a pasta de documentação do projeto. Por isso a publicação usa
**GitHub Actions**: `actions/upload-pages-artifact` + `actions/deploy-pages`, com
`pages: write`, `id-token: write` e o environment `github-pages`.

O workflow está em `.github/workflows/pages.yml` e é ele que roda o `--check`
antes do upload. O extrato abaixo reproduz o arquivo para leitura offline; o
arquivo é a fonte quando os dois divergirem:

```yaml
name: pages
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python scripts/12_build_site.py --public data/public --out site --data-build 2026-11-06 --check
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

Antes do primeiro deploy: ativar Pages em "GitHub Actions" nas configurações do
repo. Tamanho: 1.291 páginas + o JSON por escola + a home, a lista e a
metodologia; o limite de site publicado é 1 GB, e o build mede o total e falha se
passar de 700 MB.

**Escopo real do gate.** O passo do workflow roda `--check` e constrói `site/`
antes do upload. Ele cobre os critérios 1–4 e 6–9, a metade de build do
critério 5 (idempotência) e os casos de limite. A outra metade do critério 5 —
`06` sem etapa pulada — continua verificação local, porque `data/interim/` está
fora do git (`.gitignore`) e o CI não tem como rodar as etapas. O `--check`
falha antes do upload quando um critério executável regride.

## 8. Critérios de saída da fase 1

`--check` roda os critérios executáveis e os casos de limite e para no primeiro
que falhar. Cada um tem o comando manual equivalente, para quando o `--check`
discordar de uma pessoa. O `--check` varre todas as 1.291 páginas nos critérios
1, 3, 4 e 8, `escolas.html` e as 1.291 páginas de escola no critério 2,
`escolas.html` no critério 7, a home e `dados/home.json` no critério 9, todo o
`site/dados` no critério 6 e faz um segundo build no critério 5; não há amostra
de 10 páginas. Os sete perfis do §4 entram na conferência manual e os casos de
limite no `check_edge_cases`.

**1. Procedência completa.** Todo número visível tem entrada em
`dados/<CO_ENTIDADE>.json` com `fonte`, `arquivo`, `ano`, `calculo`, `n` e
`limites` não vazios. `n` é inteiro ou `null`; quando é `null`, o número é de
família cujo n é contagem de alunos e a página mostra a matrícula ausente. Nas
taxas (fluxo, TDI, TNR), o estado é `ausente`; no Ideb, o valor observado pode
continuar com `n: null`. `n_referencia` é exigido exatamente quando o n é
contagem de alunos de outro ano (Ideb de 2005–2023 → `"2025"`) e não aparece
quando o n é `null`.

```bash
python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-procedencia
```

**2. Sem ranking.** Nenhuma página ordena escolas por indicador, nenhuma exibe
faixa p10–p90 ou mediana da rede, `indice.json` está em ordem alfabética e o
`escolas.html` não publica número nenhum (§2.1). O escopo do termo é
`escolas.html` mais as 1.291 páginas de escola — os dois lugares onde D3 vale. A
home compara redes por decisão do mantenedor (§2.3) e por isso nomeia p10 e p90
na legenda e na tabela do gráfico; `metodologia.html` e `como-ler.html` explicam
o mesmo. Os três ficam fora da varredura por construção, e o critério 9 cobre a
legenda da home.

```bash
grep -c "p10\|p90\|mediana da rede" site/escolas.html site/[0-9]*.html  # 0 em todas
python -c "import json; d=json.load(open('site/indice.json')); \
  assert [x['nome'] for x in d]==sorted(x['nome'] for x in d)"
```

**3. n pequeno.** Unidade com `n < --limiar-n` não publica TDI, TNR nem taxa de
aprovação; publica a matrícula e a nota de amostra pequena. Unidade sem
matrícula de 2025 (`n is None`) também não publica a taxa: mostra a matrícula
`-` e a frase de 2025.

```bash
python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-limiar          # usa 53001419 (perfil f) e a matriz do q16
```

**4. Estados.** `ausente` sai `-`, `nao_aplicavel` sai `—`, `zero` sai `0`; os
três não se confundem em nenhuma página dos perfis, e as frases do §3.1 —
inclusive as duas de matrícula (2024 e 2025), a de escola fora do Censo de 2024
(L-63) e a de infraestrutura — aparecem como estão, sem variação de redação por
escola.

```bash
python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-estados
```

**5. Reprodutibilidade.** `06` sem etapa pulada (verificação local) e o build
idempotente (CI). O workflow do Pages cobre a metade do build; a outra metade
não roda no CI porque `data/interim/` não está no repositório.

```bash
python scripts/06_analysis.py                       # sai 0; q0_execucao.csv sem "pulado"
python scripts/12_build_site.py --public data/public --out site --data-build 2026-11-06
find site -type f -exec sha256sum {} + | sort > /tmp/site_a.txt
python scripts/12_build_site.py --public data/public --out site --data-build 2026-11-06
find site -type f -exec sha256sum {} + | sort > /tmp/site_b.txt
diff /tmp/site_a.txt /tmp/site_b.txt                # vazio
```

**6. Licença.** Nenhum número publicado cita família ODbL como fonte, e
`creditos.html` traz a licença de cada fonte usada, lida de `procedencia.json`
(`licenca` e, quando houver, `licenca_url`). O export falha antes de gravar
quando uma família SEEDF resolve para conjunto ODbL (L-62).

```bash
python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-licencas
```

**7. Sumário por RA.** O `escolas.html` tem um `<select id="ir-ra">` com uma opção
para cada `#ra-<slug>` das 35 seções, na mesma ordem e com o mesmo rótulo, e
nenhuma âncora se repete. O rótulo é de exibição; `data-ra` e `indice.json`
mantêm o valor bruto (§2.1).

```bash
python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-sumario
```

**8. Sumário da página da escola.** Cada uma das 1.291 páginas de escola tem um
único `<nav class="sumario-escola">` com `aria-label` entre o subtítulo e a
primeira seção, com um `<details>` fechado e um `<ul role="list">`; os links
apontam, na ordem, para as seções renderizadas e repetem o rótulo do `<h2>`; cada
`href="#x"` casa com um único `id="x"`; o link e a seção da creche existem se e
somente se `oferta_inf_cre == 1`; e o sumário não publica número. A comparação usa
uma cópia congelada do contrato (`checks/school_toc.py`), e o próprio check testa
seis mutações que precisam falhar.

```bash
python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-sumario-escola
```

**9. A home.** Todo `data-numero` de `index.html` tem registro em
`dados/home.json` com `fonte`, `arquivo` (dentro de `data/public/`), `ano`,
`calculo`, `estado`, `n` inteiro ou `null` e `limites` não vazios; todo registro
aparece no HTML e nenhum id se repete no JSON. Todo id de `agregados.parquet` é
publicado — id exportado e não usado é id morto e faz o check falhar. O texto
renderizado bate com o parquet pelo mesmo formatador da página (pt-BR, um decimal
half-up). As somas da
ausência fecham (com valor + sem valor = universo; pública + privada = universo;
linha sem valor + sem linha = sem valor), a contagem de escolas bate com o
cadastro e a porcentagem da creche é estadual ÷ total. Há exatamente quatro
cartões, a legenda do gráfico é a do contrato e cita L-65, L-67, L-36, L-37 e
L-32, e todo registro `tdi-*` cita L-65 e L-67 e traz "turma pequena" no
`calculo`. Não há seta de variação nem link para página de escola; há link para
`metodologia.html`; uma linha de Ideb ausente (`df_estado = "ausente"`) não é
renderizada como número; e "27º de 27" só vale porque a linha do EM/Estadual de
2025 tem `posicao == n_ufs` (hoje 27 de 27, com o DF isolado no último lugar).

```bash
python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-home
```

**Casos de limite.** O `--check` também roda a cópia do insumo com 2024 sem
linha/2024 com célula vazia, 2025 e creche ausentes, o `53014618` com 493 em
2024 e a renderização a `--limiar-n 0`:

```bash
python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-casos
```
