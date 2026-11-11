# Plan — home page with headline numbers, school list at `escolas.html`, and methodology page

**Date:** 2026-11-11
**Contract:** [docs/FASE-1.md](../../FASE-1.md)
**Rules:** [AGENTS.md](../../../AGENTS.md)
**Input:** [data/public/](../../../data/public/) (two new parquets; three existing ones unchanged in content)
**Worklog:** `docs/worklogs/2026-11-11-NN-home-e-metodologia.md` (new, Portuguese)
**Criterion:** adds criterion **9** to FASE-1 §8; `--check` goes from nine to ten items.

References below are to **modules and symbols**, not line numbers. The site build is the package
[`scripts/sitegen/`](../../../scripts/sitegen/) and `scripts/12_build_site.py` is only its CLI.

---

## 1. Origin and motivation

The site today is a single entry point — `site/index.html` — which is a list of the 1.291 schools,
with name search and a jump by Administrative Region. It publishes no number at all. A first-time
reader arriving at the root URL sees a long alphabetical list and no statement of what the project
is for, why it exists, or where the numbers come from. There is no home page and no dedicated
methodology page; method notes are scattered across `README.md`, `REPORT.md`, `SCHEMA.md`,
`docs/LIMITES.md` and the "Como ler os números" page (`site/como-ler.html`).

This plan adds three things:

1. **A home page** at `site/index.html` with the project's motivation, four headline numbers and one
   chart, and a short methodology summary that links to a full page.
2. **The school list moves** to `site/escolas.html`, unchanged in behaviour and in its contract
   ("no number, alphabetical order").
3. **A methodology page** at `site/metodologia.html` with sources, manifest discipline, key
   matching, the four data states, the small-`n` threshold, reproducibility and links to the
   project's limit registry and report.

The driving problem the numbers have to solve: the sentence that circulates about the Federal
District ("the DF is one of the best in the country") is true only for the **Total** line of the
Ideb in the early years, which includes the private network; in the state network the DF is **last
of 27** in upper secondary. No number in `data/public/` can carry that comparison today, because
the UF-level Ideb sheet lives only in `data/interim/`, which the build never reads.

---

## 2. What blocks it today (facts the implementer must respect)

- **The contract forbids numbers on the entry page.** FASE-1 §2.1: *"O índice **não publica
  número**: nem contagem de escolas por RA, nem média, nem total. Número é coisa da página da
  escola, onde a procedência aparece número a número. Se a contagem for pedida depois, entra com
  bloco de fonte próprio."* FASE-1 §8 criterion 2 repeats it (*"o `index.html` não publica número
  nenhum"*), and `scripts/sitegen/checks/ranking.py` enforces it: it rejects `class="num"`,
  `data-numero=` and any `\d[\d.]*\s+escolas?` in `index.html`.
- **`AGENTS.md` defines `data/public/` as a per-school aggregate.** Its "Convenções" section says
  `data/public/` is *"the minimal per-school aggregate the site build reads (no raw file, no
  microdata, no row that identifies a person), small enough to carry the build in CI"*. A UF-level
  table is not per-school, so putting one there without amending that sentence breaks a written
  rule. The project's data rule — *school- and territory-level data only* — is not broken: a UF is
  territory.
- **The build reads only `data/public/`** and fails if the sha256 recorded in `procedencia.json`
  does not match (`scripts/sitegen/loader.py::load_data`). It never reads `data/interim/` or
  `data/raw/`. Any number shown on the site must therefore exist in a versioned parquet.
- **Every visible number needs a provenance record.** Criterion 1 (`checks/provenance.py`) requires
  `fonte`, `arquivo`, `ano`, `calculo`, `estado`, `n` and `limites` per `data-numero` id. A number
  written as text without an id is not published as far as the contract is concerned.
- **"No school ranking" (D3) is scoped to the school page and the list.** Multiplied by the
  `ranking.py` term list (`p10`, `p90`, `mediana da rede`), it currently forbids network
  distributions anywhere on the site. A chart on the home that compares networks needs that scope
  made explicit in code and in the contract text.
- **`data/interim/q8_df_brasil_uf.csv`** (24 rows: `etapa, ano, rede, df, brasil,
  df_menos_brasil, posicao, n_ufs, mediana_ufs`) already holds the UF comparison, built by
  `scripts/06_analysis.py::q8()`. It is not versioned.

---

## 3. Decisions already made, and the alternatives rejected

### 3.1 Publish the UF number: option A, with a narrow amendment

The comparison is published, and the needed few rows become a versioned table in `data/public/`.
Reason: the project's motivation is to dismantle a headline that exists only as a comparison; with
neither "4,3" (the national state-network value) nor "27 of 27", the reader has no yardstick, and a
sentence with those figures on the home is a published number either way — the build cannot render
it without the export.

Rejected alternative **B** — keep the UF number off the site and support the motivation with words
plus a link to `REPORT.md`: costs nothing in contract, but leaves the strongest claim in the project
without a visible source and forces the copy to avoid all figures.

Rejected alternative **C** — use only what is already in `data/public/`, e.g. "half of the state
upper-secondary schools with an Ideb scored 3,6 or less" (median of 64 schools): no export needed,
but the comparison term and the last-place fact disappear, and a median over schools is not the
network's Ideb, so the sentence invites exactly the confusion the project exists to prevent.

Amendment wording for `AGENTS.md` (replaces the sentence quoted in §2):

> `data/public/` is the minimal aggregate the build reads: per-school parquets plus a closed list of
> context tables — `ideb_uf.parquet` (INEP Ideb by UF, territory level) and `agregados.parquet`
> (counts and distributions by network, derived from the per-school files). No raw file, no
> microdata, no row that identifies a person. Adding a table to this list requires amending this
> file.

Because the amendment is a written exception to a rule, the list is closed and nominal: two files,
named.

### 3.2 Page layout and file names

- `site/index.html` becomes the home.
- `site/escolas.html` receives the current list (search, jump by RA, list by RA).
- `site/metodologia.html` is new and is the "full methodology" target.
- `site/como-ler.html` **stays** as the reader's guide to the four states and the small-`n`
  threshold. Keeping it means the 1.291 school pages keep their `como-ler.html#…` anchors and no
  page needs rewriting beyond the navigation.
- No redirect file is needed: the root URL is the home, and only the list changes address.

Rejected alternative: folding `como-ler.html` into `metodologia.html` with preserved anchors. More
compact, but it rewrites an anchor target on 1.291 pages and merges two different audiences (a
reader checking one number vs. someone auditing the method).

### 3.3 Scope of the UF export: 2023 and 2025 (24 rows)

Both years go in, so the home can show the movement of the position (18th in 2023 → 27th in 2025
in the state network's upper secondary) without a second export later. Two years of a UF-level
table is still a small, closed addition.

Rejected alternative: 2025 only (12 rows). Smaller, but it drops the movement, which is the part
that shows this is not a one-year artifact.

### 3.4 The "no ranking" check gets a scope, not an exemption

`checks/ranking.py` keeps its term list, applied to **`escolas.html` and the 1.291 school pages** —
the two places where D3 applies. The home gets its own check (§6.4) that requires the network
comparison to be labelled as such, with the reason and the new limit id. The contract text in
FASE-1 §8 criterion 2 and §2.1 is edited to say exactly that.

Rejected alternative: dropping the distribution and keeping only bars of the median. It would leave
`ranking.py` untouched, but it hides the strongest finding: in the final years and in upper
secondary the **p10 of the state network sits above the p90 of the private network**.

### 3.5 Four cards and one chart

The set is: (1) 1.291 schools in 35 Administrative Regions; (2) 7 of 475 creche units belong to the
state network; (3) 27th of 27 in the state network's upper-secondary Ideb; (4) 499 of 927 schools
have an Ideb, decomposed by the state of the data.

Rejected candidates, with reasons:

| candidate | why it stays out |
|---|---|
| 501.999 enrolments | a partial sum: creche + lower + upper secondary. The public slice has no EJA, special or vocational enrolment, so publishing it as a total would be wrong |
| "39.4% of schools declare a library" | misleading alone: the reading-room item is at 80.5% of the same universe, and the pair was the subject of a method correction (2026-10-23) |
| "27.1% of children aged 0–3 in creche, target 50%" | PDAD number, outside `data/public/`, and dependent on an age convention (L-23, L-27, L-39) |
| Ideb timeline 2005–2025 | unbalanced panel: 277 school codes vanish from the series (L-14), so the median per year is not a trend |
| "21,720 values, 11 editions, 8 items" | a backstage count. It describes the archive, not the school; its place is the methodology page, as text, or nowhere |
| "DF is 8th of 27 in early years (Total)" | true and useful, but it is the setup for the motivation, not a headline; it appears in the motivation text with its id and record |

### 3.6 The absence card is decomposed by the state of the data, never by cause

An earlier draft attributed the 91 public schools without an Ideb to Portaria nº 435/2025 (fewer
than 10 students or participation below 80%). That does not survive the data: among those 91, at
least 31 are upper-secondary schools with more than 1.5 thousand enrolments (e.g. CEM 01 de São
Sebastião, CEM 304 de Samambaia, CEM 01 de Planaltina), which cannot be "fewer than 10 students".
L-09 states the source does not separate non-participation, participation below the criterion and
unpublished result. So the card shows **what is verifiable** — with a value, a row with a dash, no
row — cites L-08 for the private network, L-09 for the dash, and presents L-30 only as a rule that
may explain part of it.

### 3.7 The chart distribution uses every published value, with no n threshold (closed 2026-11-11)

The TDI distribution per network and stage includes **every school × stage unit whose rate is
published** (states `valor` and `zero`), including units below the D4 threshold whose rate the
school page does not show. Maintainer decision.

Reasons: (a) the project's published medians (`README.md`, `REPORT.md` §2.2, `REPORT.md` §2.7
table) are computed the same way, so the home and the documents say 9,0 / 17,1 / 20,7 and
1,2 / 3,2 / 4,5, not two slightly different values for the same median; (b) the 30 lives in one
place only, the `--limiar-n` build flag (`docs/FASE-1.md` §5), and an export must not depend on a
build flag or carry a second copy of the constant; (c) the effect is at most one decimal, and the
reading that matters (in the final years and upper secondary the state p10 sits above the private
p90) holds under both cuts.

What it costs, and how it is paid: the chart then uses figures the school page suppresses (private
early years: 37 of 311 units are below the threshold, 27 of them with a `0,0` rate). That mismatch
is declared, not hidden: new limit **L-67** (§6.2), cited in the legend (§4.3) and in the `calculo`
of every `tdi-*` record. The legend says "turma pequena" and never repeats the number 30.

Rejected alternative: filtering to units at or above the threshold. It would match D4 literally, but
it needs the threshold inside the export (or a second export per flag value) and makes the home
disagree with `README.md`/`REPORT.md` (8,9 against 9,0 in early-years state).

### 3.8 "Privada" means conveniada plus não conveniada (closed 2026-11-11)

The private group in the chart, in the cards and in the absence decomposition is
`rede in {"privada conveniada", "privada não conveniada"}` (131 + 476 schools). Maintainer
decision. The federal network is a separate group and stays out of the chart (L-32). The legend and
the `calculo` say "privada (conveniada e não conveniada)" and cite L-36 and L-37.

---

## 4. What the home says (copy to be used verbatim)

Numbers in the copy come from `data-numero` spans, never typed. Text is Portuguese; identifiers stay
English.

### 4.1 Hero

> # Prova dos Nove
> Uma página por escola no Distrito Federal, em português comum, com a origem de cada número à
> vista.
> [Encontrar uma escola → `escolas.html`] [Como fazemos → `metodologia.html`]

### 4.2 The four cards

Each card carries, under the figure, a source line with year and limit ids ("Cadastro SEEDF 2025 ·
L-36, L-37, L-64"), and no delta arrow and no good/bad colour.

1. **1.291** — *escolas em 35 Regiões Administrativas. Cada uma tem uma página própria.*
2. **7 de 475** — *unidades que oferecem creche são da rede estadual. Elas têm 149 das 42.582
   matrículas de creche (0,3%); as demais são privadas ou conveniadas.*
3. **27º de 27** — *lugar da rede estadual do DF no Ideb do ensino médio em 2025: 3,6, contra 4,3
   na rede estadual do país. Em 2023: 18º, com 3,7.*
4. **499 de 927** — *escolas de ensino fundamental ou médio têm Ideb em 2025. Nas outras 428 não há
   nota — e isso não é nota zero.* Below it, a single stacked bar with the decomposition, and:
   *A INEP não publica Ideb de escola privada depois de 2017 (L-08). Nas públicas, a fonte não diz
   por que falta (L-09); a regra de participação pode explicar parte dos casos (L-30).*

### 4.3 The chart

*Distorção idade-série em 2025, por rede: mediana e faixa central de 80% das escolas.*

Mandatory legend (constant `PHRASE_HOME_NETWORK_COMPARISON` in `contract.py`):

> Compara redes, não escolas. A página de cada escola não traz média de rede porque comparar
> escolas premia quem já partiu na frente (D3); aqui a pergunta é de política pública. O gráfico não
> controla o perfil socioeconômico dos alunos (L-65): ele mostra que as redes atendem públicos
> diferentes, não que uma escola reduz a distorção. A rede privada reúne escolas conveniadas e não
> conveniadas (L-36, L-37). Entram todas as escolas com taxa publicada, inclusive as de turma
> pequena, cuja taxa a página da escola não mostra (L-67). A rede federal (1 escola nos anos finais,
> 11 no médio) fica fora por n pequeno (L-32).

### 4.4 Motivation (three paragraphs)

> Os dados da educação brasileira são públicos e abundantes, mas quase ilegíveis: dezenas de
> arquivos, colunas em código, séries que mudam de formato a cada ano. Quem mais precisaria deles —
> professores, coordenadores, jornalistas, famílias — é quem tem menos tempo para decifrá-los.
>
> No Distrito Federal isso tem consequência. "O DF está entre os melhores do país" só vale para os
> anos iniciais (8º de 27) e só na linha Total do Ideb, que inclui a rede privada. Na rede
> estadual, o DF ficou em 27º de 27 no ensino médio em 2025: 3,6, contra 4,3. Os dois números estão
> certos; só um deles fala da escola pública.
>
> Prova dos Nove reúne esses dados numa página por escola, em português claro, com a origem de cada
> número à vista. Quando o dado não existe, a página diz isso e não preenche com zero. Não é
> ranking de escolas nem avaliação de professores. O nome vem de um truque de conta que acusa o
> erro, mas não garante o acerto — por isso cada número mostra fonte, ano e limites.

### 4.5 Methodology summary (four blocks, no file names, no "hash" jargon)

> **De onde vêm.** Fontes públicas: o catálogo de dados abertos da SEEDF, o Censo Escolar, o Ideb e
> as taxas de rendimento e distorção da INEP, e a PDAD do IPEDF. Cada arquivo é registrado com
> endereço, data, tamanho e impressão digital, e conferido antes do uso.
>
> **Como são tratados.** Os nomes de campo originais são mantidos e cada renomeação é documentada.
> Antes de cruzar duas fontes, medimos quantas escolas casam e publicamos a taxa. Zero, ausente e
> não aplicável são três coisas diferentes, e aparecem como três.
>
> **O que a página mostra — e o que não mostra.** Com menos de 30 alunos na etapa, não publicamos
> taxa: mostramos a matrícula e explicamos por quê. Não colocamos média de rede ao lado da escola.
> As taxas de rendimento e distorção são de 2025 apenas; a matrícula vem do Censo, e EJA, educação
> especial e profissional não entram nela.
>
> **Como conferir.** Cada número abre fonte, arquivo, ano, cálculo e n. O build confere a impressão
> digital do insumo e falha se ela mudou.
>
> **→ Metodologia completa** (`metodologia.html`)

The last sentence of "Como conferir" is deliberately weaker than "os dados forem idênticos aos
registrados": parquet is not byte-deterministic (`DESENVOLVIMENTO.md` §8), and what the build checks
is the recorded sha256 of the input.

---

## 5. Reference numbers (measured on `data/public` at commit `6371560`)

These are outputs, not constants: the export computes them, the site reads them, the build's home
record cites them. If a value moves, the build shows the new one.

### 5.1 Counts

| what | value | how |
|---|---|---|
| schools | 1.291 | `escolas.parquet` rows |
| Administrative Regions | 35 | distinct `ra` |
| creche units | 475 | `oferta_inf_cre == 1` (estadual 7, federal 0, conveniada 130, não conveniada 338) |
| creche enrolments 2025 | 42.582 | `mat_inf_cre_2025` sum (estadual 149 = 0,3499%, displayed as 0,3%; conveniada 24.525; não conveniada 17.908). No nulls among the 475 units and no enrolment in non-offering units |
| Ideb universe | 927 | schools with `oferta_fund_ai` or `oferta_fund_af` or `oferta_med` == 1 |
| Ideb present 2025 | 499 | any offered stage with `ideb_observado` 2025, `estado == "valor"` |
| public without Ideb | 91 | 80 have a 2025 row with `ausente`, 11 have no row (31 of the 80 offer upper secondary) |
| private without Ideb | 337 | 31 have a 2025 row with `ausente`, 306 have no row |

The three states sum to the universe: 499 + 80 + 11 + 31 + 306 = 927. The stage restriction matters:
counting rows in **any** stage instead of the **offered** stages yields 32/305 instead of 31/306.

### 5.2 Distortion (TDI 2025), published values including `zero`

| stage | network | p10 | median | p90 | n |
|---|---|---|---|---|---|
| anos iniciais | estadual | 4,05 | 8,95 | 15,0 | 386 |
| anos iniciais | privada | 0,0 | 1,2 | 4,8 | 311 |
| anos finais | estadual | 10,9 | 17,1 | 29,6 | 195 |
| anos finais | privada | 1,0 | 3,2 | 8,33 | 200 |
| ensino médio | estadual | 11,7 | 20,7 | 35,8 | 101 |
| ensino médio | privada | 0,98 | 4,5 | 10,55 | 150 |

Linear quantiles, **quantized to four decimals** in the export: enough to keep 8,95 exact and to
store the creche share as 0,3499 (which displays as 0,3%). **Display rule:** the site shows one
decimal, with half-up rounding on the decimal string
(`Decimal(str(v)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)`), which is what the project's
prose already does: 8,95 → 9,0, 4,05 → 4,1, 10,55 → 10,6, 8,33 → 8,3. Do not reuse `fmt_dec`
(`f"{v:.1f}"`) for these: binary floats make it print 8,95 as "8,9" and 4,05 as "4,0", contradicting
`REPORT.md` and the `README.md` bullet. Every stored indicator value already has at most one decimal
(measured: 0 of 11.826 values need two), so `fmt_dec` stays untouched for school pages. The private
group joins conveniada and não conveniada (declared in `calculo`; §3.8; L-36, L-37). The federal
network is excluded from the chart.

The table includes every unit with a published rate (§3.7). Units below the D4 threshold inside it,
for reference (total, of which `0,0`): AI estadual 7 (1), AI privada 37 (27), AF estadual 4 (0),
AF privada 7 (3), EM estadual 2 (0), EM privada 10 (5). Same distribution restricted to n ≥ 30, kept
here only to show the effect (not published): AI estadual 8,9 · 14,72 · 379; AI privada 1,3 · 4,8 ·
274; AF estadual 17,0 · 28,9 · 191; AF privada 3,2 · 8,14 · 193; EM estadual 20,5 · 35,56 · 99;
EM privada 4,5 · 10,31 · 140.

### 5.3 Ideb by UF (the 2025 rows the home uses)

| stage | network | DF | Brasil | position | UFs |
|---|---|---|---|---|---|
| AI | Total | 6,4 | 6,3 | 8 | 27 |
| AF | Estadual | 4,6 | 5,1 | 21 | 27 |
| EM | Total | 4,1 | 4,5 | 22 | 27 |
| EM | Estadual | 3,6 | 4,3 | **27** | 27 |

The EM/Estadual 2025 position is a strict last place, not a tie: the three next-lowest UFs
(Amazonas, Amapá, Roraima) have 3,7, so no other UF shares the DF's 3,6 (checked on
`data/interim/inep/ideb_uf_tidy.parquet`). The export must still compute the position as
`1 + count(UFs with a higher value)` and the copy must say "27º de 27" only because the check below
holds; the build's home check asserts `posicao == n_ufs` for that row.

2023 rows used in the card sub-line: EM Estadual 3,7, position 18 of 27. EM/Pública has no DF value
in the sheet (L-10) and must be exported as `ausente`, with the Brasil value present.

---

## 6. Files, interfaces and existing code involved

### 6.1 Data layer — `scripts/06_analysis.py`

- **Extract the UF table.** The DF × Brasil × UFs table is built inside `q8()` by a
  `for etapa → for ano ("2023","2025") → for rede ("Total","Pública","Estadual","Privada")` loop
  over `data/interim/inep/ideb_uf_tidy.parquet` and `brasil_ideb_tidy.parquet`, appending dicts to
  `linhas` and writing `data/interim/q8_df_brasil_uf.csv`. Move that block into
  `_ideb_uf_tabela() -> pd.DataFrame`, returning the same DataFrame with the same columns and
  order; `q8()` keeps writing the CSV from it. The CSV's sha256 must be identical before and after
  the refactor.
- **New `_ideb_uf_publica() -> pd.DataFrame`** — 24 rows, columns: `etapa`, `ano`, `rede`, `df`,
  `df_estado` (`valor`/`ausente`), `brasil`, `brasil_estado`, `posicao` (`Int64`), `n_ufs`
  (`Int64`). Drop `df_menos_brasil` and `mediana_ufs` (derived, not needed by the site). If
  `data/interim/inep/*_tidy.parquet` is missing, raise `ExportError` (an export must not silently
  drop a table).
- **New `_agregados_publicos(escolas, indicadores) -> pd.DataFrame`** — long format, columns:
  `id` (str, unique), `bloco`, `grupo`, `etapa`, `ano`, `metrica`, `valor` (float), `n` (`Int64`),
  `estado` (`valor`/`ausente`). Built from the exported DataFrames, never from `data/interim/`.
  Required ids:

  | bloco | ids |
  |---|---|
  | contagem | `escolas-total`, `ras-total` |
  | creche | `creche-unidades-total`, `creche-unidades-estadual`, `creche-mat-total`, `creche-mat-estadual`, `creche-mat-estadual-pct` |
  | ausencia | `ideb-universo`, `ideb-com-valor`, `ideb-sem-valor`, `ideb-publica-com-valor`, `ideb-publica-linha-sem-valor`, `ideb-publica-sem-linha`, `ideb-privada-com-valor`, `ideb-privada-linha-sem-valor`, `ideb-privada-sem-linha` |
  | tdi | `tdi-{ai,af,em}-{estadual,privada}-{p10,mediana,p90,n}` — 24 ids |

  Computation rules:
  - "has value" = any **offered** stage (`oferta_fund_ai`, `oferta_fund_af`, `oferta_med`) with
    `ideb_observado` 2025 in state `valor`. "row with dash" = has a row for an offered stage and
    none with `valor`. "no row" = no row for any offered stage. Public = estadual + federal.
  - TDI distribution uses states `valor` and `zero` (a `0,0` rate is a valid value and must not be
    dropped); `ausente` and `nao_aplicavel` stay out. **No enrolment threshold is applied** (§3.7).
    Percentiles by `DataFrame.quantile` (linear); `n` is the count of units used, not students.
    Group `privada` = `rede` in `{"privada conveniada", "privada não conveniada"}` (§3.8); group
    `estadual` = `rede == "estadual"`; `federal` is not exported. `indicadores.parquet` stores
    `ano` as a string (`"2025"`): filter on the string.
  - The `calculo` text of every `tdi-*` record (family `home_tdi_rede`) is, verbatim:
    *"Percentil (interpolação linear) da distorção idade-série de 2025 entre as unidades escola ×
    etapa da rede, com taxa publicada (estados valor e zero). Inclui unidades de turma pequena, cuja
    taxa a página da escola não publica (D4). Rede privada = conveniada + não conveniada. Rede
    federal fora."*
  - All `valor` are quantized to 4 decimals before writing (8,95 stays 8,95; 149/42.582 × 100 =
    0,3499; counts stay exact). `n` is `Int64`, never a float.
  - `creche-mat-estadual-pct` is `creche-mat-estadual / creche-mat-total × 100`; it must read 0,3%
    on the page (one-decimal half-up display), not 0,4%.
  - `escolas-total` counts cadastro rows (1.291), not the Ideb universe.
- **Export wiring.** `_grava_parquets` writes five parquets and returns five hashes;
  `export_public` builds the two new frames, includes them in the `novos` map (and in the diff
  check that requires `--force`), and reports them in the summary line. Update both docstrings
  (module header list of outputs, `export_public` outputs).
- **`REGISTROS_PUBLICOS`** gains five families, each with `familia`, `bloco`, `fonte`, `arquivo`,
  `anos`, `calculo` and non-empty `limites`; `FAMILIAS_INEP` gains the INEP ones so the licence
  resolves to `LICENCA_INEP` ("público, sem licença declarada no portal"), and the SEEDF ones go
  through `_licencas_seedf()` as the existing families do:

  | family | fonte | arquivo | limites |
  |---|---|---|---|
  | `ideb_uf` | INEP — Ideb divulgação por UF e Brasil 2023–2025 | `data/public/ideb_uf.parquet` | L-10, L-32, L-66 |
  | `home_contagem` | SEEDF — Cadastro de Unidades Escolares 2025 | `data/public/agregados.parquet` | L-36, L-37, L-64 |
  | `home_creche` | INEP — Censo Escolar 2024–2025 | `data/public/agregados.parquet` | L-27, L-28, L-36, L-62, L-63 |
  | `home_ideb_cobertura` | INEP — Ideb por Escola 2025 + Censo Escolar 2025 | `data/public/agregados.parquet` | L-08, L-09, L-30, L-31 |
  | `home_tdi_rede` | INEP — Distorção Idade-Série por Escola 2025 | `data/public/agregados.parquet` | L-11, L-32, L-36, L-37, L-59, L-65, L-67 |

L-40 (medians with small `n`) is **not** cited for `home_tdi_rede`: it covers RAs with few schools
and the federal network, not the enrolment threshold. The threshold effect is L-67.

### 6.2 `data/public/` contract documents

- `data/public/README.md`: two rows in the file table, with grain, key and content; keep the
  "generated by" command block. Mention the closed-list rule.
- `SCHEMA.md`: two blocks, with grain, key, types, states and years, in the same style as the
  existing blocks.
- `docs/LIMITES.md`: three new ids (last used is L-64; ids are never reused):
  - **L-65** (`risco-de-leitura`) — the network comparison on the home does not control for
    socioeconomic profile; the archive has no INSE variable, so state × private compares different
    publics. Evidence: REPORT §2.4; `q11_distorcao_df.csv`. Open. Action: declare it in the chart
    legend.
  - **L-66** (`suposicao`) — the "nth of 27" position is computed by the project (1 + the number of
    UFs with a higher value), not published by INEP. The denominator varies (L-10) and the DF has
    no "Pública" value in upper secondary. Evidence: `q8_df_brasil_uf.csv`. Open. Action: name the
    denominator next to the position.
  - **L-67** (`risco-de-leitura`) — the network distribution on the home includes school × stage
    units below the D4 threshold, whose rate the school page does not publish; the home therefore
    uses values the school page suppresses. Effect measured on 2025 data: at most 0,7 point on a p90
    (AF estadual 29,6 → 28,9), medians move by 0,2 or less (EM estadual 20,7 → 20,5); the largest group is private early
    years (37 of 311 units, 27 with `0,0`). Evidence: `q16_faixas_n.csv`; §3.7 and §5.2 of this
    plan. Open. Action: declare it in the chart legend and in the `calculo`; reopen if the
    threshold or the chart's purpose changes.

### 6.3 Site package — `scripts/sitegen/`

| file | change |
|---|---|
| `loader.py` | add `ideb_uf.parquet` and `agregados.parquet` to the required-file list and to the sha256 loop; validate their columns, uniqueness of `id`, and that `estado` in (`valor`, `ausente`) matches a present/absent `valor`; return `data["ideb_uf"]` keyed by `(etapa, ano, rede)` and `data["agregados"]` keyed by `id` |
| `build.py` | `_clean_output` also removes `escolas.html` and `metodologia.html` (`dados/*.json` already covers `home.json`); write `index.html` = home, `escolas.html` = list, `metodologia.html`, and `dados/home.json` = `{"pagina": "home", "gerado_em": <data_build>, "numeros": [...]}` with the same per-number shape as `dados/<CO_ENTIDADE>.json` |
| `index_page.py` → `schools_page.py` | rename module and `render_index_page` → `render_schools_page`; the page title describes a list of schools; behaviour, markup, `id="ir-ra"`, `noscript` block and `indice.json` stay exactly as they are (`static/search.js` fetches `indice.json` relatively, so it keeps working) |
| `home_page.py` (new) | `render_home_page(data, data_build, threshold) -> tuple[str, list[dict]]` returning the HTML body and the provenance records. A local helper mirroring `SchoolPage._add` (`<span class="num" data-numero="…" data-estado="…">`, same record shape, same guard that a repeated id keeps the same value and state), using `fmt_int`, `fmt_dec` and `fmt_pct` from `fmt.py`. The same id repeats in the markup (card and motivation) with one record in the JSON list |
| `home_chart.py` (new) | `render_tdi_chart(data) -> str`: inline SVG, no JavaScript, no new dependency. Three stage groups; per group two rows (estadual, privada); a segment from p10 to p90, a tick at the median, values printed at the ends; common scale 0 → ceiling (largest p90 rounded up to a multiple of 10; today 40). Coordinates formatted with `f"{x:.1f}"` so the second build is byte-identical (criterion 5). Text labels plus neutral tones, with `role="img"`, `aria-label`, and a `<details>` block containing the same numbers as a table |
| `methodology_page.py` (new) | `render_methodology_page(data_build, threshold) -> str`. Sections with `id` and `class="bloco"`, in this order: (1) sources — table of source, what is used, year, official link from `data/raw/MANIFEST.md`; (2) how data enters — download → `MANIFEST.md` (URL, date, bytes, sha256) → profile → `SCHEMA.md`, including why `download.inep.gov.br` needs a declared manual path; (3) keys and joins — matching rate measured before every join; the SEEDF Ideb series matches INEP value by value but is a republication (L-07); the SEEDF enrolment series diverges from the Censo and understates EJA/vocational (L-01), which is why enrolment comes from the Censo; (4) the four states — summary plus link to `como-ler.html`; (5) what the school page shows and does not (D3, D4, no ranking, no network average); (6) the network comparison on the home — why it exists, why the school page does not show it, L-65; that the distribution includes small-turma units the school page suppresses, L-67; that "privada" is conveniada plus não conveniada; (7) how to check — `dados/<código>.json`, `dados/home.json`, input sha256, deterministic build, `--check`; (8) limits and reproduction — links to `docs/LIMITES.md`, `REPORT.md`, `SCHEMA.md`, `README.md`, and the repository. **No data numbers on this page** (no counts of files or limits, which age badly); the threshold comes from `threshold` |
| `layout.py` | header keeps `marca → index.html` and gains `Escolas` → `escolas.html` and `Metodologia` → `metodologia.html`; footer lists Escolas, Metodologia, Como ler, Créditos |
| `school_page.py` | the breadcrumb `Todas as escolas` points to `escolas.html` |
| `info_pages.py` | the `Todas as escolas` link in `creditos.html` points to `escolas.html`; add a `Metodologia` link |
| `contract.py` | add `PHRASE_HOME_NETWORK_COMPARISON` (the legend text of §4.3) and the chart ceiling rule as a named constant; no existing constant changes |
| `fmt.py` | add `fmt_pct(v)` — one decimal, half-up on the decimal string (`Decimal`, `ROUND_HALF_UP`), for the aggregates only; `fmt_dec`/`fmt_int` keep their behaviour so no school page changes |
| `static/style.css` | `.cartoes` grid (one column up to ~40rem, two above), `.cartao`, `.grande-numero`, `.fonte-linha`, `.barra-ausencia`, chart classes; reuse `--tinta`, `--tinta-suave`, `--linha`, `--destaque` |
| `12_build_site.py` | docstring output list gains the new files |

### 6.4 Checks — `scripts/sitegen/checks/`

- `ranking.py` — today the forbidden-term loop is `for path in sorted(site.glob("*.html"))`, i.e.
  **every** HTML at the site root. Replace that glob with an explicit set: `escolas.html` plus the
  school pages (`[0-9]*.html`, 1.291 files). `index.html` (home) and `metodologia.html` are then out
  of the term sweep by construction, because they must name `p10`/`p90` (legend, `<details>` table,
  method text). `como-ler.html` and `creditos.html` stay out too; confirmed today that
  `info_pages.py` has none of the three terms, but nothing then keeps them out, so the scope
  decision goes in the docstring and in `FASE-1.md` §8 criterion 2. Replace `index.html` with
  `escolas.html` in the number / `class="num"` / `data-numero` / count-of-schools assertions and in
  the messages; the docstring ("nenhum ranking, percentil ou contagem no índice") now says `escolas.html`.
- `region_toc.py` — read `escolas.html` instead of `index.html` (`id="ir-ra"`, `noscript` block,
  options, sections, anchors, labels); messages included.
- `edge_cases.py` — the temporary copy of the input lists four files by name; add
  `ideb_uf.parquet` and `agregados.parquet`, otherwise `load_data` fails inside the check.
- `home.py` (new) — `check_home(site, data) -> str`, registered in `checks/__init__.py` as
  `Check("home", "--check-home", "critério 9: números, procedência e legenda da home", …)`, placed
  after `sumario_escola` and before `reprodutibilidade`. It verifies:
  1. every `data-numero` in `index.html` has a record in `dados/home.json` with non-empty `fonte`,
     `arquivo` starting with `data/public/`, `ano`, `calculo`, `estado`, `n` (integer or null) and
     `limites`; every record id appears in the markup; no id is duplicated in the JSON;
  2. the rendered text matches the parquet value formatted with the same formatter the page uses
     (`fmt_pct` for the aggregates, `fmt_int` for counts), in pt-BR;
  3. arithmetic invariants derived from the ids, never typed as constants: com valor + sem valor =
     universe (499 + 428 = 927); pública sem valor + privada sem valor = sem valor (91 + 337 =
     428); linha sem valor + sem linha = sem valor; each network's parts sum to its total;
     estadual + others = 1.291 for the school count; the creche share equals estadual ÷ total;
  4. exactly four cards in the markup (a `data-cartao` attribute on each, count asserted);
  5. the legend contains `PHRASE_HOME_NETWORK_COMPARISON` and cites L-65, L-67, L-36, L-37 and
     L-32; every `tdi-*` record's `limites` contains L-65 and L-67 and its `calculo` contains
     "turma pequena";
  6. no delta glyph (`▲ ▼ ↑ ↓`) and no link matching `\d{8}\.html` on the home; a link to
     `metodologia.html` is present;
  7. a row with `df_estado == "ausente"` is never rendered as a number;
  8. the copy says "27º de 27" only if the exported row has `posicao == n_ufs` (EM, Estadual,
     2025); otherwise the check fails (§5.3: today the DF is strictly last, Amazonas, Amapá and
     Roraima have 3,7).
- No change needed in `provenance.py` (it iterates schools), `licenses.py` (it already globs
  `site/dados/*.json`, and `home.json` carries `numeros`, so the new sources must appear in
  `creditos.html`, which the existing licence walk produces automatically), `states.py`,
  `threshold.py`, `school_toc.py`, `reproducibility.py`.

### 6.5 Docs and CI

- `DESENVOLVIMENTO.md` §3 (module table gains `schools_page`, `home_page`, `home_chart`,
  `methodology_page`), §5 (checks table grows to ten rows, file count and size refreshed from a real
  run), §6 (URL list of the local check gains `escolas.html`, `metodologia.html`,
  `dados/home.json`).
- `docs/FASE-1.md`: §2.1 renamed to the list (`escolas.html`) with the same rules; new §2.3 (home)
  and §2.4 (methodology); §5.1 gains the two parquets; §5.2 gains the output tree and the
  `dados/home.json` shape; §8 criterion 2 and 7 point at `escolas.html`; new criterion 9 with its
  manual command.
- `README.md`: the site section and the structure tree, plus the creche/Ideb sentences that cite the
  home numbers.
- `.github/workflows/pages.yml`: update the comment listing which criteria `--check` runs.
- Worklog in Portuguese recording the decisions, the measurements and the verification performed.

---

## 7. Implementation order

1. Contract and rules: `AGENTS.md`, `docs/LIMITES.md` (L-65, L-66, L-67), `docs/FASE-1.md`,
   `SCHEMA.md`, `data/public/README.md`.
2. Export: refactor `q8()`, add `_ideb_uf_publica`, `_agregados_publicos`, wire
   `_grava_parquets`/`export_public`, add the five provenance families, regenerate with
   `--public data/public --force`. `export_public` already rewrites `procedencia.json` with the
   sha256 of every parquet it writes (and its `novos` map includes it), so the regenerated
   `procedencia.json` carries the new hashes of the three existing parquets too, even if only bytes
   moved (§11).
3. Loader: read and validate the two new parquets; fix `edge_cases.py`'s copy list.

   **Steps 2 and 3 land in one commit.** Between them `load_data` does not know the new parquets
   and `--check`/`casos_limite` fail; no intermediate state is a valid commit. Step 2 alone may be
   run locally to produce the files, never committed.
4. Build: `schools_page` rename, home and methodology modules, `build.py` outputs, `home.json`.
5. Navigation: `layout.py`, `school_page.py`, `info_pages.py`, CSS, chart styles.
6. Checks: scope `ranking.py`, retarget `region_toc.py`, add `home.py` and its registry entry.
7. Docs and CI, then the worklog.

---

## 8. Acceptance criteria

- `python scripts/06_analysis.py --public data/public --force` exits 0 with no skipped step, and
  `data/public/` gains exactly `ideb_uf.parquet` (24 rows) and `agregados.parquet`; the three
  existing parquets have unchanged **content** (`hash_pandas_object` over rows sorted by key);
  `procedencia.json` is regenerated in the same run and its `sha256` map lists all five parquets,
  so `load_data` passes on the committed `data/public/`.
- Medians on the home match the documents: `tdi-ai-estadual-mediana` displays 9,0 (as in
  `README.md` and `REPORT.md`), and the distribution includes every published unit (§3.7): the
  `n` of each `tdi-*` group equals the 386/311/195/200/101/150 of §5.2.
- The sha256 of `data/interim/q8_df_brasil_uf.csv` is identical before and after the `q8` refactor.
- `python scripts/12_build_site.py --public data/public --out site --data-build 2026-11-06 --check`
  prints ten `[ok]` lines, including `home`, and exits 0.
- `site/index.html` shows four cards, the chart and the legend; every number in it has a record in
  `site/dados/home.json`.
- `site/escolas.html` keeps search, jump by RA, the 35 sections and the full list without
  JavaScript; `site/index.html` no longer contains `id="ir-ra"`.
- No page has a root-absolute path (`grep -R --include='*.html' -e 'href="/' -e 'src="/' site` is
  empty), and the site stays under `MAX_SITE_BYTES`.
- `site/` is not added to git; `data/public/` is committed in the same change.
- `docs/FASE-1.md` §8 documents criterion 9 with a manual command; `DESENVOLVIMENTO.md` §3/§5/§6
  match the code.

---

## 9. Verification and mutation tests

Local server (from `DESENVOLVIMENTO.md` §6, same subpath as production):

```sh
work=/tmp/opencode/pdn-serve-live
mkdir -p "$work"; ln -sfn "$PWD/site" "$work/prova-dos-nove"
.venv/bin/python -m http.server 8000 --bind 127.0.0.1 --directory "$work"
```

Check `200` for `/prova-dos-nove/`, `/escolas.html`, `/metodologia.html`, `/dados/home.json`,
`/indice.json`, `/estilo.css`, `/como-ler.html`, `/creditos.html`, one school page.

Mutation tests — inject the defect, confirm the `[falhou]`, revert:

| mutation | must fail |
|---|---|
| `"limites": []` in one `home.json` record | `home` |
| a `data-numero` id with no record | `home` |
| delete the chart legend, or drop L-65 or L-67 from it | `home` |
| drop L-67 from one `tdi-*` record's `limites`, or "turma pequena" from its `calculo` | `home` |
| set `posicao` to 26 on the EM/Estadual 2025 row of a scratch export while the copy says "27º de 27" | `home` |
| add a `p90` to `como-ler.html` (must stay **out** of the term sweep: expect `ranking` to pass, and note it in the worklog) | none |
| `▲` in a card | `home` |
| a `53000854.html` link on the home | `home` |
| sum the parts of the absence bar wrongly in a scratch copy of the export | `home` |
| `p90` in the text of a school page | `ranking` |
| `p90` in `escolas.html` | `ranking` |
| remove `<noscript><style>.sumario` from `escolas.html` | `sumario` |
| remove one parquet from the temp copy list in `edge_cases.py` | `casos_limite` |

Browser-only checks: home at 360 px and at desktop width; chart legible without colour; `<details>`
table opens; `escolas.html` search without accents and without case (`ceilandia`), the RA select,
the list without JavaScript; navigation present on one school page.

---

## 10. Questions

Closed on 2026-11-11 (maintainer):

1. **Small-`n` threshold inside the chart distribution** — all published values, no threshold in
   the export; the inclusion is declared in the legend and in the `calculo`, and recorded as L-67.
   See §3.7.
2. **Private group label** — "privada" is conveniada plus não conveniada. See §3.8.

Open:

3. **`agregados.parquet` growth.** If a later home needs per-stage enrolment or network coverage,
   the long format absorbs it. The closed list in `AGENTS.md` refers to the file, not the rows, so
   new ids inside the file do not need a new amendment — confirm that this is acceptable when the
   first new id is added.

## 11. Risks

- **Parquet bytes.** Regenerating `data/public` may change the sha256 of the three existing files
  without changing content (`DESENVOLVIMENTO.md` §8). Compare content with `hash_pandas_object`;
  if only bytes moved, record it in the worklog and accept.
- **Precedent.** The amendment opens `data/public/` to context tables. Mitigated by a closed,
  named list and by the wording that adding a table requires amending the file.
- **Reading the chart as judgement.** A range bar can read as good/bad if colour becomes semantic.
  Keep tones neutral, label both series in text, and never colour a network with the "error" tone.
- **The 91 public schools without an Ideb.** The text must not attribute cause per school; the
  decomposition is by state of the data, and L-30 is presented as a possible explanation for part.
- **Navigation touches every page.** The header changes on 1.291 school pages; the full `--check`
  covers it, and `site/` is not versioned, so the only visible effect is a larger diff in the
  build.
- **Home and school page disagree at the margin.** The chart uses small-turma units whose rate the
  school page suppresses (§3.7). A reader may notice. Mitigation: L-67 in the legend and in every
  `tdi-*` record; the methodology page (section 6) explains it in plain words.
- **Two numbers for the same thing — resolved.** Because the distribution keeps every published
  unit, the home's medians equal `README.md`'s and `REPORT.md`'s (9,0 / 17,1 / 20,7 and
  1,2 / 3,2 / 4,5). If the export ever applies a threshold, those documents must change in the same
  commit.

## 12. Out of scope

- A search box on the home (it links to `escolas.html`, which already has search).
- The PDAD creche deficit (27,1%) and any other indicator that is not in `data/public/`.
- Changes to the school page beyond the breadcrumb link and the shared header.
- A site-wide redesign, a favicon, a client-side router or a 404 page.
