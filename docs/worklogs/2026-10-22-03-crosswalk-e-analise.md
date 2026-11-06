# 2026-10-22 — 03. Crosswalk e análise

> **Nota posterior (2026-10-23).** Duas conclusões deste registro foram
> corrigidas depois: o "36,2% da matrícula de creche é de 4 anos ou mais" é
> artefato da convenção de `IDADE` (idade no ano, não em 31/03) e a taxa de
> biblioteca foi medida com o item errado e no universo errado. Ver
> [`2026-10-23-01-pdad-e-biblioteca.md`](2026-10-23-01-pdad-e-biblioteca.md) e
> `REPORT.md` §2.3 e §2.5.

Objetivo: responder às seis perguntas da fase 0 com número e arquivo, e medir as
chaves antes de qualquer join. Scripts: `04_crosswalk.py`, `06_analysis.py`.

## 1. Crosswalk (`04_crosswalk.py`)

Chave: `CO_ENTIDADE` (Código INEP do Censo Escolar), presente em todas as séries
da SEEDF. A taxa é medida, nunca estimada; órfão é listado, nunca completado.

Saídas: `data/interim/crosswalk.csv` (38 pares arquivo→arquivo, 10 colunas) e
`data/interim/ra_por_fonte.csv` (como cada fonte escreve o nome da RA).

Amostra do que a medição mostrou:

| De → Para | Casados | Taxa | Órfãos |
|---|---|---|---|
| escolas 2024 → matrículas 2024 | 1.284 de 1.284 | 100% | 0 |
| escolas 2025 → matrículas 2025 | 1.291 de 1.291 | 100% | 41 no outro lado |
| escolas 2025 → situação 2025 | 604 de 1.291 | 46,8% | a situação só cobre a rede estadual |
| escolas 2025 → IDEB 2025 (AI) | 615 de 1.291 | 47,6% | 9 códigos no IDEB sem cadastro |
| escolas 2023 → matrículas 2023 | 600 de 1.264 | 47,5% | arquivo de 2023 só tem rede pública |

A taxa baixa aqui não é erro de chave: é cobertura. Foi essa medição que
transformou "o join não fecha" em "estas redes não estão nesses arquivos" —
a resposta da pergunta 2 do relatório. Sem medir, seria uma suposição.

## 2. As seis perguntas (`06_analysis.py`)

Regra declarada no cabeçalho do script: **nulo é ausente, `0` é zero, e nulo nunca
entra em soma como zero**. Cada função grava um CSV em `data/interim/` e imprime
o número que vai para o `REPORT.md`.

### q1 — unidades escolares (`q1_unidades.csv`)

1.291 unidades ativas em 2025 (`relatorio_escolas_2025.csv`): 669 estaduais
vinculadas à SEEDF, 476 privadas não conveniadas, 131 privadas conveniadas, 11
federais, 4 estaduais não vinculadas. Por etapa, contando unidade que oferta mais
de uma: creche 475 (468 fora da rede estadual), pré-escola 660, fundamental 855,
médio 264.

O retrato invertido da creche é o achado: nas outras etapas a rede estadual é
majoritária; na creche, ela tem 7 das 475 unidades.

### q2 — cobertura da rede privada (`q2_cobertura.csv`)

Cobertura medida contra o cadastro de 2025. Cadastro, infraestrutura e matrículas
de 2024 estão em 90–100%; situação do aluno e IDEB de anos iniciais têm 0% de
privada, porque o arquivo simplesmente não traz essas redes. A falha é de
publicação/participação, não de download.

### q3 — infraestrutura (`q3_infra_itens.csv`, `q3_infra_por_ra.csv`, `q3_infra_por_rede.csv`)

1.332 escolas em funcionamento (1.471 linhas menos 139 paralisadas/extintas).
Biblioteca ausente em 66,3%, laboratório de informática em 60,1%, quadra em
33,0%. Por rede, biblioteca falta em 86,6% da privada conveniada, 75,7% da
estadual e 48,7% da privada não conveniada. Por RA varia de 0% a 100%, mas as RAs
nos extremos têm 2 a 17 escolas — a ordenação é instável e foi dita como instável
em vez de virar ranking.

### q4 — IDEB por escola (`q4_ideb_resumo.csv`, `q4_ideb_por_ra.csv`)

Anos iniciais, rede estadual: 335 escolas com resultado em 2025 (344 em 2023).
Mediana 6,0; p10 5,3; p90 6,8; mínimo 4,5; máximo 7,7. Variância decomposta:
38,5% entre RAs em 2025 (42,5% em 2023), 61,5% dentro da RA. O recorte
"centro × periferia" não separa (Ceilândia na mediana do DF, Águas Claras abaixo).

### q5 — creche (`q5_creche.csv`)

Matrículas 2024 × população 0–4 da PDAD-A 2024. 40.851 matrículas para 170.243
crianças de 0–4 = 24,0% aparente. O numerador foi aberto por `IDADE` na própria
linha: 26.076 matrículas são de 0–3 anos e 14.775 (36,2%) de 4 anos ou mais.
Achado que muda a leitura: mais de um terço da matrícula em creche é de criança
que já deveria estar na pré-escola — distorção idade-etapa, não excesso de
demanda.

O denominador é o limite: a PDAD-A para em "até 4 anos". A taxa de 24,0% usa 0–4
nos dois lados; com o numerador de 0–3 daria 15,3%, número que só faria sentido
com a população de 0–3 no divisor. Nenhuma das duas é publicada como "taxa de
atendimento em 0–3", porque essa taxa não é estimável com esta fonte.

### q6 — qualidade (`q6_unidades_churn.csv`)

1.568 códigos distintos em 2014–2025; 41 aparecem só em 2025; 277 desaparecem
antes de 2025 sem motivo declarado. Zero duplicatas de `CO_ENTIDADE` nos arquivos
de escola. Em situação do aluno, a chave só fecha incluindo `CONCLUINTE`: sem
ela, 5.537 linhas parecem duplicadas (7,6% de 2023) e não são.

## 3. Vereditos internos

| Hipótese | Antes da INEP | Depois (registro 04) |
|---|---|---|
| O Ideb do DF esconde duas cidades | parcialmente: desigualdade territorial real e grande, mas 58–62% da variação é dentro da RA | premissa falsa: a média não é alta para a rede pública |
| Déficit de creche concentrado | sustenta a concentração; o valor em 0–3 não é estimável | inalterado |

O que não se sustenta em nenhuma leitura: tratar a média do DF como retrato da
cidade. O que se sustenta com folga: a creche é ofertada por privada e conveniada,
não pela rede estadual.

## 4. Gráfico proposto (não produzido)

IDEB 2025 dos anos iniciais, uma escola por ponto, agrupadas por RA e ordenadas
pela mediana da RA, com a linha da mediana do DF. Mostra de uma vez o
deslocamento entre RAs, a sobreposição enorme entre elas e os casos que
contrariam a intuição. Nenhum mapa faz isso melhor, porque a variável não é
contínua no território. Ficou descrito em `REPORT.md` §4, não desenhado.

## 5. Verificação

- `04` reexecutado: `crosswalk.csv` sai byte a byte igual (sha256 conferido
  antes e depois).
- `06` roda com exit 0 e reescreve todos os `q*.csv`.
- Cada número do `REPORT.md` §2 confere com o CSV correspondente por leitura
  direta.
- `eta2_entre_ra` é a razão de soma de quadrados entre grupos pela total. A coluna
  vizinha `icc` **não é um coeficiente de correlação intraclasse**: é a razão de
  quadrados médios (MSB/MSW, ou seja, um F). Nome ruim, herdado; renomear para
  `f_entre_ra` está na lista de pendências, e o `REPORT.md` não usa esse número.

## 6. Pendências

- IDEB por escola das redes privada e federal: só a INEP publica (registro 04).
- Fluxo escolar da rede privada: só a estadual é publicada.
- Fechamento de escola: 277 códigos sem motivo.
- Renomear `icc` → `f_entre_ra` em `q4_ideb_resumo.csv` (é um F, não um ICC).

> **Nota posterior (2026-10-23).** Os dois números corrigidos neste registro
> estão no registro: L-50 (36,2%) e L-51 (biblioteca), fechados em
> 2026-10-23-01; a coluna `icc` é L-41. Ver `docs/LIMITES.md`.
