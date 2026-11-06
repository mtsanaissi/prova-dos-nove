# 2026-10-23 — 01. Microdados da PDAD-A e duas correções de método

Objetivo: abrir os microdados da PDAD-A 2024 que já estavam no `data/raw/` e
fechar a lacuna da população de 0–3 anos; corrigir duas afirmações do relatório
que o dado não sustentava (creche e biblioteca). Scripts: `10_ingest_pdad.py`
(novo), `05`, `06` e `_common`.

## 1. Três arquivos com a extensão errada

O `05` baixava todo relatório da PDAD como `.pdf` por construção. Três dos 53
arquivos não eram relatório nenhum:

| Arquivo | Formato real | Conteúdo |
|---|---|---|
| `..._base_de_morador.pdf` | ZIP (4.523.063 B) | `moradores.csv`, 69.542 × 134 |
| `..._base_de_domicilios.pdf` | ZIP (1.427.844 B) | `domicilios.csv`, 24.845 × 128 |
| `..._dicionario_de_dados.pdf` | XLSX (473.417 B) | abas `moradores`, `domicilios`, `anexo_1`…`anexo_11` |

O `05` passou a derivar a extensão do sufixo da URL e a conferir o formato pelos
primeiros bytes; os nomes antigos continuam aceitos para não gerar download
duplicado. `data/raw/` não foi renomeado nem reescrito — o conteúdo e o sha256
são os mesmos, e a correção de metadado está em `MANIFEST.md` → Correções.

## 2. Leitura (`10_ingest_pdad.py`)

- ZIP lido em memória (`zipfile`), `;` e vírgula decimal, `utf-8-sig`.
- Nomes de localidade e domínios de código vêm do **dicionário**, não digitados.
- Sentinela `88888` (não sabe) e `99999` (não se aplica) nunca entram em soma.
- `E02_1` (data de nascimento) é usada **em memória** para a idade em 31/03/2024
  e descartada junto com `morador_id`, `A01nficha`, `setor_distrito` e os
  identificadores de vínculo. Saída só agregada por RA.
- `H04_4` (RA/município da escola) usa códigos de 1–36 e 41–52; o respondente às
  vezes informa o código do próprio município em vez de `40`. O leitor compara
  com `localidade % 100` e conta como próprio — sem essa regra, "estuda em outra
  RA" saía em 54% em vez de 24,6%.

## 3. Validação

| Checagem | Resultado |
|---|---|
| Total expandido por RA × `pop_total` dos PDFs (35 RAs) | desvio máximo **0,01%** |
| Total do DF | 2.982.816 no microdado e no documento do DF (0,00%) |
| Localidades e códigos fora do dicionário | nenhum |
| `E02_1` preenchida | 49,6% das linhas; parse em 100% das preenchidas |
| Idempotência | duas execuções, parquets com bytes idênticos |

O script interrompe acima de 5% por RA ou 1% no total — não avisa e segue.

## 4. O que os microdados dizem

DF: 2.982.816 moradores; **139.116 crianças de 0–3** (4,7%) e 81.546 de 4–5.

| Faixa | Frequenta escola |
|---|---|
| 0–3 | 27,1% (±2,5 p.p.) — 37.654 crianças |
| 4–5 | 86,0% (±2,5 p.p.) — 11,4 mil fora |
| 6–10 | 97,5% |
| 11–14 | 97,6% |
| 15–17 | 90,6% |

Das que frequentam creche, 57,8% na rede pública e 42,1% na particular (visão da
família). O Censo 2024 dá 57,3% da matrícula em creche na rede conveniada e 0,3%
em unidades da SEEDF — a mesma estrutura, por outro caminho.

Fluxo: **74,7%** dos alunos de 6–17 anos estudam na própria RA, 24,6% em outra,
0,3% em Goiás. Entorno: **19.523** moradores de 6–17 anos dos 12 municípios
goianos estudam no DF (Novo Gama 26,8%, Planaltina de Goiás 22,9%, Padre Bernardo
21,4%, Valparaíso 8,2%, Águas Lindas 4,9%).

## 5. Duas correções de método

**Creche — "36,2% da matrícula é de 4 anos ou mais" não é distorção.** `IDADE` no
Censo é idade no ano, não idade em 31/03. A prova está no arquivo: no 1º ano do
fundamental, 70,8% aparecem com `IDADE` 7 e 25,0% com 6, exatamente o que o corte
de 31/03 produz. Criança com `IDADE` 4 pode estar legitimamente em creche. Só 270
matrículas de creche têm `IDADE` ≥ 5; a distorção real fica entre 0,7% e ~10%.
Nenhuma conta do projeto usa `IDADE` como idade em 31/03.

**Biblioteca — eram três itens, virou um.** `IN_BIBLIOTECA` é biblioteca;
`IN_SALA_LEITURA` é sala de leitura; `IN_BIBLIOTECA_SALA_LEITURA` é o OR dos dois
(conferido nos 12 anos). O número antigo (66,3%) usava só o primeiro item sobre
**todas** as 1.332 unidades, incluindo creche, onde biblioteca não é exigência.
No universo das 927 escolas de EF/EM: 60,6% sem biblioteca, 6,0% sem biblioteca
nem sala de leitura e 48,2% das que têm biblioteca sem bibliotecário (estadual:
73,4%, 6,4% e 61,4%). Série 2014–2025 no mesmo universo: falta de biblioteca
entre 55,6% e 62,2%; falta de qualquer espaço entre 6,0% e 7,6%.

## 6. Limites

- **Renda não é usável:** `renda_domiciliar_pc_r` é 99999 em 78,7% dos
  domicílios, com cobertura válida de 6,7% a 33,9% por RA. Nenhuma análise de
  renda foi feita.
- **Precisão por RA:** 14 a 184 pessoas de 0–3 por RA, meio-intervalo de 6 a 36
  p.p. As RAs entram como agrupamento, não como taxa.
- **Idade em 31/03** só existe para 49,6% das linhas (55,2% da população de 0–3):
  não substitui a idade na entrevista.
- **Censo × PDAD na creche não fecham:** 26.076 matrículas (Censo, `IDADE` ≤ 3)
  contra 37.654 frequentando (PDAD). Hipóteses (creche não declarada ao Censo
  Escolar, autodeclaração, data de referência) não testadas; o microdado do Censo
  Escolar é o que resolve, e não está ingerido.
- **Área Rural** (7.115 crianças de 0–3) não tem par no cadastro da SEEDF: aparece
  na população e fica fora dos cruzamentos com matrícula.

## Reprodução

```sh
.venv/bin/python scripts/10_ingest_pdad.py --check
.venv/bin/python scripts/10_ingest_pdad.py
.venv/bin/python scripts/06_analysis.py
```

O `10` é offline, lê só `data/raw/pdad/` e reescreve `data/interim/pdad/`. O `06`
passou a ler `pdad_frequencia.parquet` para o denominador de 0–3 em `q5_creche.csv`
e a emitir `q3_biblioteca.csv`, `q3_biblioteca_por_ra.csv` e
`q3_biblioteca_serie.csv`.

> **Nota posterior (2026-10-23).** O item "Censo × PDAD na creche não fecham" de
> §6 foi fechado em 2026-10-23-02: 37.595 contra 37.654, 0,16%, convenção de
> idade (L-49); a hipótese de creche não declarada (C-02) foi superada. Ver
> `docs/LIMITES.md`.
