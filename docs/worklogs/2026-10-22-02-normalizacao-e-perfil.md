# 2026-10-22 — 02. Normalização e perfil

Objetivo: transformar 80 CSV heterogêneos em parquet previsível, sem perder a
distinção entre `0`, ausente e "não aplicável". Script: `03_profile_seedf.py`.

Regra de ouro do script, escrita no docstring: **nada é convertido para número
aqui**. Tudo entra como texto; a conversão acontece na análise, onde cada coluna
tem tratamento explícito. Se o perfil convertesse, `""` viraria `NaN` e um
`0` legítimo poderia virar ausência — exatamente o que o projeto não aceita.

## 1. Detecção de formato, sem assumir

`_common.detect_encoding()`: BOM (`utf-8-sig`) → `utf-8` → `latin-1` (que nunca
falha). Lê até 4 MB de cabeçalho binário.

`_common.detect_separator()`: conta `,`, `;` e `\t` na primeira linha e devolve o
mais frequente.

`header_row()`: alguns arquivos têm linha de título acima do cabeçalho. O script
lê as duas primeiras linhas e decide por `VAR_TOKENS`: se a primeira linha já
trouxer nomes de variável, cabeçalho é 0; senão, 1.

`limpar_colunas()`: colunas repetidas recebem sufixo `_2`, `_3`. Coluna sem nome
vira `col_<i>`.

Leitura efetiva:

```python
pd.read_csv(path, dtype=str, encoding=enc, sep=sep, header=h,
            keep_default_na=False, na_values=[""], engine="python",
            on_bad_lines="warn")
```

`keep_default_na=False` + `na_values=[""]` é o ponto central: só célula vazia é
ausente. A string `"NA"`, se aparecer, continua sendo a string `"NA"`.

## 2. Saídas

- `data/interim/seedf/<familia>__<arquivo>.parquet` — 80 arquivos, 13 famílias:
  `dicionario` (8), `distorcao` (12), `docentes` (3), `escolas` (12),
  `ideb_planilha` (3), `ideb_serie` (3), `infraestrutura` (12), `matriculas` (12),
  `situacao` (7), `tecnologia` (2), `turmas` (2), `unidades_ei` (1),
  `unidades_oferta` (3).
- `data/interim/profile_files.csv` — 80 linhas, colunas: `arquivo`, `familia`,
  `ano_no_nome`, `linhas`, `colunas`, `ano_no_dado`, `coluna_entidade`,
  `entidades_distintas`, `linhas_por_entidade_duplicadas`, `cols_100_nulas`,
  `parquet`.
- `data/interim/profile_columns.csv` — uma linha por coluna, com tipo observado e
  contagem de nulos.

Três colunas do perfil existem para pegar erro de graça: `ano_no_nome` contra
`ano_no_dado` (arquivo dizendo um ano e contendo outro),
`linhas_por_entidade_duplicadas` (grão quebrado) e `cols_100_nulas` (coluna que
não deveria estar vazia).

## 3. O que o perfil encontrou

### Arquivo deslocado de ano

`relatorio_infraestrutura_2016.csv` contém 2017 e é **idêntico** ao de 2017:
1.124 linhas, comparação célula a célula, nenhuma diferença. 2016 não existe na
série. Foi tratado como ausência de 2016, não como dado de 2016.

### Anos parciais

| Família | Ano | O que está faltando |
|---|---|---|
| `matriculas` | 2023 | 600 escolas contra ~1.280; 42.440 linhas contra ~78 mil; só rede pública |
| `situacao` | 2025 | 2.421 linhas contra ~72 mil |
| `situacao` | 2019 | 126.672 linhas, o dobro dos demais anos — inclui rede federal |

### Deriva de esquema em 2025

- `escolas`: 74 → 81 colunas; contagens de turma (`ESC_*`) dão lugar a
  sinalizadores (`INF_*`).
- `infraestrutura`: 114 → 289 colunas.
- `matriculas` e `situacao`: nomes de variável substituídos por rótulos legíveis.
- `distorcao`: 30 → 26 colunas, duas linhas de cabeçalho.
- `TP_DEPENDENCIA` deixa de separar conveniada de privada; é preciso usar
  `CO_REDE`.

### Armadilhas de conteúdo

- **Duplicata de nome, não de código:** "Escola Canadense de Brasília" aparece
  com dois `CO_ENTIDADE` em 2025. Código é a chave; nome não é.
- **Espaço à direita** em `AGUAS CLARAS ` — normalizado só na análise, com
  `norm_ra()`; o parquet preserva o original.
- **Nulo que não é "não tem":** 139 escolas de infraestrutura 2025 têm todas as
  colunas `IN_*` vazias. São paralisadas/extintas: o dado é "não se aplica".
  Contá-las como "sem o item" misturaria três estados e distorceria todo
  percentual de infraestrutura.
- **277 códigos somem da série** (ver registro 03, q6) sem motivo declarado.

### IDEB: três arquivos, três desenhos

`ideb_ef_ai_2005_2025*.csv` usa `;` e `cod_inep`; `ideb_ef_af_2005_2025.csv` e
`ideb_em_2017_2025.csv` usam `,` e `Cód_Inep`. Não há como ler os três com a
mesma chamada, e a diferença não é cosmética: muda o separador de campo e o nome
da chave.

## 4. Verificação

- `03` reexecutado do zero: os 80 parquets são reescritos e o perfil sai
  **idêntico** — sha256 de `profile_files.csv` igual antes e depois da execução.
- `header_row()` conferido nos casos com e sem linha de título.
- `cols_100_nulas` usado como alarme: as colunas sinalizadas foram explicadas
  (paralisadas/extintas em infraestrutura) em vez de descartadas.

## 5. Pendências

- 2016 de infraestrutura: nenhum dado aberto substitui; é a série que um contato
  institucional destravaria.
- `situacao` 2025 parcial: só a rede estadual, e com 1/30 das linhas habituais.
