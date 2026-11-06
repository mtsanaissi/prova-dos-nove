# 2026-10-22 — 07. Taxas de rendimento: o fluxo escolar da rede privada

Objetivo: fechar a última lacuna de rede do relatório — aprovação, reprovação e
abandono por escola, inclusive a privada, que a SEEDF só publica para a rede
estadual. Scripts: `07`, `08` (leitor novo) e `q10` de `06_analysis.py`.

## 1. Ingestão (`07`)

`tx_rend_escolas_2025.zip`, 66.870.247 B, entrou pelo caminho manual de sempre
(navegador → `data/raw/inep/inbox/`), com sha256 e linha no `MANIFEST.md`
(142 linhas ao final). O zip traz `.xlsx`, `.ods` e `md5_*.txt`.

## 2. Leitura (`08`): 63 colunas, três categorias

Uma aba (`ESCOLAS`), 5 linhas de título, cabeçalho em três faixas, códigos na
linha 9: nove colunas de identificação e 54 taxas no padrão
`<categoria>_CAT_<recorte>`.

- `1_CAT_*` aprovação, `2_CAT_*` reprovação, `3_CAT_*` abandono;
- `FUN`, `FUN_AI`, `FUN_AF`, `FUN_01`…`FUN_09`, `MED`, `MED_01`…`MED_04`,
  `MED_NS`.

`processar_tx_rend()` lê em streaming (126.686 linhas nacionais, 37,7 MB de
xlsx), filtra `SG_UF == 'DF'` e grava formato longo: 49.950 linhas, uma por
escola × taxa. O token `'--'` é **não aplicável** (escola sem matrícula naquela
etapa/série) e vai para `estado = nao_aplicavel`, com o texto em `valor_bruto`;
`0` continua zero real — abandono zero é o caso comum, e é justamente o que não
pode ser confundido com ausência.

**Conferência que fecha a leitura:** em 7.412 pares escola × recorte com as três
taxas, aprovação + reprovação + abandono = 100, com desvio máximo de 1,4e-14.
Se a ordem das categorias estivesse trocada, isso não fecharia.

## 3. Cobertura

925 escolas do DF: 578 `Estadual`, 336 `Privada` e 11 `Federal`. Todas as 925
casam com o cadastro de 2025 (0 fora). O cadastro tem 1.291 unidades; das 366 sem
linha, 306 só ofertam educação infantil, 58 não têm oferta marcada no cadastro e
2 ofertam fundamental ou médio sem taxa no arquivo.

## 4. O que o fluxo mostra (`q10`)

Medianas por escola, 2025 (`data/interim/q10_fluxo_df.csv`); não são ponderadas
por matrícula, então descrevem a escola típica da rede, não o aluno típico.

| Etapa | Rede | Aprovação | Reprovação | Abandono | Escolas com taxa |
|---|---|---|---|---|---|
| Anos iniciais | Estadual | 96,0% | 3,8% | 0,0% | 386 |
| Anos iniciais | Privada | 100,0% | 0,0% | 0,0% | 269 |
| Anos finais | Estadual | 94,2% | 5,0% | 0,2% | 195 |
| Anos finais | Privada | 99,4% | 0,6% | 0,0% | 183 |
| Ensino médio | Estadual | 82,5% | 12,4% | 2,4% | 101 |
| Ensino médio | Privada | 98,3% | 1,5% | 0,0% | 139 |
| Ensino médio | Federal | 89,5% | 7,5% | 2,8% | 11 |

A leitura: no médio, a distância de Ideb entre privada (5,7) e estadual (3,6)
tem um mecanismo medido — 15,8 pontos de aprovação e 2,4 pontos de abandono de
diferença. Não é "nota" contra "nota"; é fluxo contra fluxo. Nos anos iniciais a
privada tem mediana de aprovação de 100% e reprovação 0%, o que também ajuda a
explicar por que a linha "Total" do DF é alta.

## 5. Limites

- A taxa é da escola, não do aluno: sem denominador de matrícula por série, a
  mediana não é uma taxa agregada da rede. Ponderar exigiria o Censo 2025 por
  escola, que não está ingerido.
- O arquivo é de 2025 apenas; não há série histórica nesta entrega.
- O fluxo explica o Ideb, mas não entra no cálculo dele neste projeto: o Ideb
  publicado pela INEP já embute o indicador de rendimento.

## Reprodução

```sh
.venv/bin/python scripts/07_ingest_inep.py
.venv/bin/python scripts/08_profile_inep.py
.venv/bin/python scripts/06_analysis.py
```

`08` passou a levar ~65 s por causa do xlsx de 37,7 MB; o leitor é streaming e
não carrega a planilha inteira.

> **Nota posterior (2026-10-23).** O Censo 2025 por escola foi ingerido na sessão
> 2026-10-23-02; a ponderação e a cobertura estão em L-02, L-21 e L-22. Ver
> `docs/LIMITES.md`.
