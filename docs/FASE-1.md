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
| 4 | Ideb por etapa | `ideb_escolas_df.parquet`, `indicador ∈ {ideb_observado, ideb_projetado}` | 2005–2025, de dois em dois anos | valor observado e meta em séries separadas; privada só até 2017 | 499 escolas com valor em 2025 | L-08, L-12, L-30, L-33, L-56 |
| 5 | fluxo | `tx_rend_escolas_df.parquet`, `categoria ∈ {aprovacao, reprovacao, abandono}` | 2025 | percentual da etapa, como publicado | 1.355 unidades escola × etapa | L-11, L-59, L-21, D4 |
| 6 | distorção idade-série | `tdi_escolas_df.parquet` | 2025 | percentual da etapa | 1.355 unidades | L-11, L-59, L-40, D4 |
| 7 | não-resposta | `tnr_escolas_df.parquet` | 2025 | percentual da etapa | 1.355 unidades | L-09, L-11, L-59 |
| 8 | infraestrutura | `relatorio_infraestrutura_*`, colunas `IN_*` | 2025 | presença do item; universo de 927 escolas de EF/EM | 927 | L-25, L-29, L-38, L-51 |
| 9 | creche da escola | `matriculas__relatorio_matriculas_2024` (`MAT_CRECHE`) e Censo 2025 (`QT_MAT_INF_CRE`) | 2024–2025 | matrícula em creche por escola | unidades com `INF_CRE = 1` | L-27, L-28, L-50 |

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

```text
site/
├── index.html                     # busca por nome/RA, sem ordenação por indicador
├── estilo.css                     # sem framework
├── <CO_ENTIDADE>.html             # uma página por escola
└── dados/<CO_ENTIDADE>.json       # procedência de cada número daquela página
```

Formato do JSON de procedência (uma entrada por número publicado):

```json
{
  "escola": "53000854",
  "gerado_em": "2026-11-06T00:00:00",
  "numeros": [
    {
      "bloco": "ideb",
      "etapa": "anos iniciais",
      "ano": "2025",
      "valor": 6.1,
      "estado": "valor",
      "fonte": "INEP — Ideb por escola",
      "arquivo": "data/interim/inep/ideb_escolas_df.parquet",
      "calculo": "valor observado da etapa, como publicado",
      "n": 247,
      "limites": ["L-30", "L-33"]
    }
  ]
}
```

Build (`scripts/12_build_site.py`, fase 2): lê `data/public/`, escreve `site/`,
não acessa a rede e não lê `data/raw`. Idempotente: mesma entrada, mesma saída
byte a byte (ordenação fixa de JSON e de páginas; sem carimbo de hora variável —
`gerado_em` vem da data do build declarada por argumento). Rodar duas vezes
seguidas e comparar `sha256sum` de `site/**` é o teste de idempotência.

O que vai para `data/public/`: só o agregado por escola × etapa que os blocos
leem, sem microdado e sem linha que identifique pessoa (regra em `AGENTS.md`).

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

1. **Procedência completa**: em 10 páginas sorteadas (os 7 perfis + 3 aleatórias
   por hash do código), todo número visível tem entrada correspondente em
   `dados/<CO_ENTIDADE>.json` com fonte, arquivo, ano, cálculo, n e ids.
2. **Sem ranking**: nenhuma página ordena escolas por indicador e nenhuma exibe
   faixa p10–p90 ou mediana da rede (D3).
3. **n pequeno**: unidade com n < 30 não publica TDI, TNR nem taxa de
   aprovação; mostra a matrícula e a nota de amostra pequena (D4).
4. **Estados**: `ausente` sai como `-`, `nao_aplicavel` como `—`, `zero` como
   `0`; nenhum dos três vira o outro em nenhuma página dos perfis.
5. **Reprodutibilidade**: `06` sem etapa pulada (`q0_execucao.csv`) e `12`
   rodando duas vezes com `site/**` idêntico por sha256.
6. **Licença**: nenhum número publicado depende de fonte ODbL (L-62); a página
   de créditos cita a licença de cada fonte usada.
