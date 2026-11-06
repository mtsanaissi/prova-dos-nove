# FASE-1.md — a página por escola

Contrato da fase 1. Este documento **define** a página; não a constrói (D1). O
build é da fase 2 e vive em `scripts/12_build_site.py`. Toda afirmação aqui tem
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
| 1 | identificação | cadastro SEEDF, `escolas__relatorio_escolas_2025.parquet` (`NO_ENTIDADE`, `Nome RA`, `Nome Rede`) | 2025 | cópia do campo | 1.291 | L-36, L-37 |
| 2 | oferta por etapa | mesmo cadastro, vetor `INF_CRE`…`PROF` (8 sinalizadores) | 2025 | flag 1 = oferta; **não** traduzir "é EI" | 1.291 | L-57, L-36 |
| 3 | matrícula por etapa | Censo INEP, `censo_escola_df.parquet` (`QT_MAT_INF_CRE`, `QT_MAT_FUND_AI`, `QT_MAT_FUND_AF`, `QT_MAT_MED`) | 2024–2025 | soma da etapa por escola, como está no campo | 1.360 linhas em 2024 (76 com célula vazia) e 1.291 em 2025 | L-28, L-43, L-48, L-62 |
| 4 | Ideb por etapa | `ideb_escolas_df.parquet`, `indicador = ideb_observado` | 2005–2025, de dois em dois anos | valor observado; **a meta (`ideb_projetado`) não é publicada**; privada só até 2017 | 499 escolas com valor em 2025 | L-08, L-12, L-30, L-33, L-56 |
| 5 | fluxo | `tx_rend_escolas_df.parquet`, `categoria ∈ {aprovacao, reprovacao, abandono}` | 2025 | percentual da etapa, como publicado | 1.355 unidades escola × etapa | L-11, L-59, L-21, D4 |
| 6 | distorção idade-série | `tdi_escolas_df.parquet` | 2025 | percentual da etapa | 1.355 unidades | L-11, L-59, L-40, D4 |
| 7 | não-resposta | `tnr_escolas_df.parquet` | 2025 | percentual da etapa | 1.355 unidades | L-09, L-11, L-59 |
| 8 | infraestrutura | `relatorio_infraestrutura_2025.parquet`, colunas `IN_*` | 2025 | presença do item, nos 8 itens listados abaixo | 927 | L-25, L-29, L-38, L-51 |
| 9 | creche da escola | Censo INEP, `censo_escola_df.parquet` (`QT_MAT_INF_CRE`) | 2024–2025 | matrícula em creche da escola, como está no campo | unidades com `INF_CRE = 1` (475 em 2025) | L-27, L-28, L-62 |

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
o build lê. Quatro arquivos, nenhum com microdado, nenhum com linha de aluno:

| arquivo | grão | colunas | tamanho medido |
|---|---|---|---|
| `escolas.parquet` | escola (1.291) | `co_entidade`, `nome`, `ra`, `rede`, `oferta_inf_cre`…`oferta_prof` (8 flags), `mat_inf_cre_2024`, `mat_fund_ai_2024`, `mat_fund_af_2024`, `mat_med_2024` e as quatro de 2025 | 240 KB |
| `indicadores.parquet` | escola × etapa × indicador × ano | `co_entidade`, `etapa` (`AI`/`AF`/`EM`), `indicador` (`ideb_observado`, `tdi`, `tnr`, `aprovacao`, `reprovacao`, `abandono`), `ano`, `valor`, `estado` | 800 KB |
| `infraestrutura.parquet` | escola × item (8 itens do §2) | `co_entidade`, `item` (nome da coluna `IN_*`), `ano` (2025), `valor` (0/1), `estado` | 25 KB |
| `procedencia.json` | um registro por indicador/família | `fonte`, `arquivo`, `anos`, `calculo`, `limites` e o `sha256` dos três parquets acima | 15 KB |

Regras do export, todas verificáveis:

- `estado` é copiado do parquet de origem, nunca deduzido de `NaN` (§3).
- Matrícula vem do Censo 2024 e 2025; a série ODbL da SEEDF não entra (L-62).
- Só entram os recortes de etapa `FUN_AI`, `FUN_AF` e `MED`; `FUN`, `FUN_01`…`09`,
  `MED_01`…`04` e `MED_NS` ficam fora (a página não desce a série).
- A meta do Ideb (`ideb_projetado`) fica fora do insumo publicado: é meta do
  ciclo 2007–2021, não previsão, e decisão do mantenedor (2026-11-06) é não
  publicá-la nesta versão (L-56).
- Mapa de etapa entre fontes: Ideb `AI`/`AF`/`EM` ↔ recorte `FUN_AI`/`FUN_AF`/`MED`.
- O export falha se `data/public/` já existir com `sha256` diferente do que vai
  gravar e o `--force` não for passado: mudança no insumo aparece no diff.
- `data/public/` é gerado e **commitado** (exceção declarada em `AGENTS.md`).

### 5.2 Saída: `site/`

```text
site/
├── index.html                     # busca por nome ou RA; lista em ordem alfabética
├── indice.json                    # [{co_entidade, nome, ra, rede}] — alimenta a busca
├── estilo.css                     # sem framework
├── creditos.html                  # licença por fonte e titular (critério 6)
├── <CO_ENTIDADE>.html             # uma página por escola (1.291)
└── dados/<CO_ENTIDADE>.json       # procedência de cada número daquela página
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
      "n": 247,
      "limites": ["L-30", "L-33"]
    }
  ]
}
```

Onde `n` sai: é a matrícula da etapa de 2025 em `escolas.parquet`; `q16`
(`data/interim/q16_presenca_escola_etapa.csv`) é o artefato que prova a conta, não
o insumo do build.

### 5.3 Interface do build

```bash
# local, depois de 06 --public
python scripts/12_build_site.py \
  --public data/public --out site --data-build 2026-11-06 --limiar-n 30

# verificação dos critérios do §8 (sai != 0 se algum falhar)
python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check
```

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

## 7. Publicação (D5, D-B)

Repo: `https://github.com/mtsanaissi/prova-dos-nove`. Fonte de publicação por
branch aceita apenas `/` ou `/docs` (a documentação oficial do GitHub Pages);
`/docs` já é a pasta de documentação do projeto. Por isso a publicação usa
**GitHub Actions**: `actions/upload-pages-artifact` + `actions/deploy-pages`, com
`pages: write`, `id-token: write` e o environment `github-pages`.

O workflow entra na fase 2, junto de `scripts/12_build_site.py` — criá-lo antes
deixaria um job quebrado no `main`. O conteúdo é este:

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
      - run: python scripts/12_build_site.py --public data/public --out site
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
repo. Tamanho: 1.291 páginas + o JSON por escola; o limite de site publicado é
1 GB, e o build mede o total e falha se passar de 700 MB.

## 8. Critérios de saída da fase 1

`--check` roda os seis critérios e para no primeiro que falhar. Cada um tem o
comando manual equivalente, para quando o `--check` discordar de uma pessoa. A
amostra de 10 páginas é determinística: os 7 perfis do §4 mais as 3 primeiras
escolas, em ordem de `sha256(co_entidade)`, que não sejam perfis — outra pessoa
chega às mesmas 10.

**1. Procedência completa.** Todo número visível tem entrada em
`dados/<CO_ENTIDADE>.json` com `fonte`, `arquivo`, `ano`, `calculo`, `n` e
`limites` não vazios.

```bash
python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-procedencia
```

**2. Sem ranking.** Nenhuma página ordena escolas por indicador, nenhuma exibe
faixa p10–p90 ou mediana da rede, e `indice.json` está em ordem alfabética.

```bash
grep -c "p10\|p90\|mediana da rede" site/*.html    # 0 em todas
python -c "import json; d=json.load(open('site/indice.json')); \
  assert [x['nome'] for x in d]==sorted(x['nome'] for x in d)"
```

**3. n pequeno.** Unidade com `n < --limiar-n` não publica TDI, TNR nem taxa de
aprovação; publica a matrícula e a nota de amostra pequena.

```bash
python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-limiar          # usa 53001419 (perfil f) e a matriz do q16
```

**4. Estados.** `ausente` sai `-`, `nao_aplicavel` sai `—`, `zero` sai `0`; os
três não se confundem em nenhuma página dos perfis.

```bash
python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-estados
```

**5. Reprodutibilidade.** `06` sem etapa pulada e o build idempotente.

```bash
python scripts/06_analysis.py                       # sai 0; q0_execucao.csv sem "pulado"
python scripts/12_build_site.py --public data/public --out site --data-build 2026-11-06
find site -type f -exec sha256sum {} + | sort > /tmp/site_a.txt
python scripts/12_build_site.py --public data/public --out site --data-build 2026-11-06
find site -type f -exec sha256sum {} + | sort > /tmp/site_b.txt
diff /tmp/site_a.txt /tmp/site_b.txt                # vazio
```

**6. Licença.** Nenhum número publicado cita família ODbL como fonte, e
`creditos.html` traz a licença de cada fonte usada (L-62).

```bash
python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-licencas
```
