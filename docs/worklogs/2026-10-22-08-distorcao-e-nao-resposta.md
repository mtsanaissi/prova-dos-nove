# 2026-10-22 — 08. Distorção idade-série e não-resposta: duas lacunas testadas

Objetivo: entrar com os dois últimos indicadores por escola da INEP e testar,
com número, se eles explicam o Ideb ausente. Scripts: `07`, `08` (leitor novo) e
`q11`–`q12` de `06_analysis.py`.

## 1. Ingestão (`07`)

Dois arquivos entraram pelo caminho manual de sempre (navegador →
`data/raw/inep/inbox/`), com sha256 e linha nova no `MANIFEST.md`:

| Arquivo | Bytes | O que é |
|---|---|---|
| `TDI_2025_ESCOLAS.zip` | 34.465.795 | distorção idade-série por escola, 2025 |
| `tnr_escolas_2025.zip` | 30.600.051 | taxa de não-resposta por escola, 2025 |

O `MANIFEST.md` foi de 142 para 144 linhas. Os dois `bytes_conhecidos` que o
catálogo do 07 trazia como `None` foram preenchidos com o tamanho observado (e
também os do PDF da nota informativa e do `tx_rend`), então `--check` não mostra
mais `?` em nenhuma linha.

## 2. Leitura (`08`): membros, abas, cabeçalho e colunas

O perfil genérico do 08 lê a linha 1 como cabeçalho e, por isso, nos dois zips
novos só conseguiu dizer "1 aba, 26/27 colunas, UF não identificada" — a linha de
códigos está na 9. Foi o perfil honesto do que o leitor genérico enxerga, não um
diagnóstico do arquivo. O leitor específico então mediu:

- **Membros:** pasta, `MD5`/`md5`, `.ods` e `.xlsx` (o `.xlsx` é o lido).
- **Abas:** uma, `ESCOLAS`, nos dois.
- **Cabeçalho:** 8 linhas de título (faixas nas 6–7), **códigos na linha 9**,
  dados da 10 em diante.
- **Colunas:** TDI com 26 códigos e 17 taxas; TNR com 27 e 18.
- **Linhas lidas:** 126.607 nacionais na TDI e 126.687 na TNR; 925 do DF em cada,
  filtradas em streaming por `SG_UF == 'DF'` (sem carregar a planilha inteira).

**O que não é comum aos dois:** o padrão do código da taxa. A TDI escreve
`<recorte>_CAT_0` (`FUN_AI_CAT_0`); a TNR escreve `4_CAT_<recorte>`
(`4_CAT_FUN_AI`) e tem `MED_NS`, que a TDI não tem. Um leitor que assumisse um
dos padrões leria zero colunas no outro — `processar_indicador_escola()` recebe o
padrão por arquivo e falha com mensagem explícita se ele não casar.

**Vocabulário:** `'--'` = não aplicável (escola sem matrícula naquele recorte),
`estado = nao_aplicavel`; célula vazia = `ausente`; `0` = zero medido. No DF não
apareceu célula vazia: TDI com 7.920 `nao_aplicavel` e 1.787 zeros; TNR com 8.845
e 3.545. Zero de TNR é comum (escola em que nenhum aluno ficou sem informação), e
é justamente o que não pode virar ausência.

**Junção medida** (`medir_juncao_cadastro()`): 925 de 925 escolas do DF casadas
com o cadastro de 2025 por `CO_ENTIDADE` (100%, 0 fora), nos dois arquivos. As
925 são as que ofertam fundamental ou médio: 575 de 576 estaduais, 336 de 337
privadas e 11 de 11 federais. As duas sem linha são uma estadual e uma conveniada.

**Saídas:** `tdi_escolas_df.parquet` (15.725 linhas longas) e
`tnr_escolas_df.parquet` (16.650), esquema de `tx_rend_escolas_df.parquet` sem a
coluna `categoria` e com `NO_REGIAO` preservada — aqui há uma medida por célula,
não três.

## 3. Distorção idade-série por rede (`q11`)

Medianas por escola, 2025 (`data/interim/q11_distorcao_df.csv`); não ponderadas
por matrícula, então descrevem a escola típica da rede, não o aluno típico.

| Etapa | Estadual | Privada | Federal |
|---|---|---|---|
| Anos iniciais | 9,0% (p10–p90 4,1–15,0; 386) | 1,2% (0,0–4,8; 311) | sem taxa (0 de 11) |
| Anos finais | 17,1% (10,9–29,6; 195) | 3,2% (1,0–8,3; 200) | 3,5% (1) |
| Ensino médio | 20,7% (11,7–35,8; 101) | 4,5% (1,0–10,6; 150) | 17,2% (9,4–22,0; 11) |

Nos anos finais e no médio, o p10 da estadual fica acima do p90 da privada: a
separação não depende de poucas escolas. A federal de médio (11 escolas) tem
mediana próxima da estadual, o que impede ler o resultado como "público ×
privado" puro. A rede federal não tem anos iniciais no DF (todas as 11 células são
`'--'`), e isso é não aplicável, não zero. Os valores da tabela estão
arredondados a uma casa decimal; os exatos, a duas, estão no CSV.

## 4. A hipótese da não-resposta falhou (`q12`)

A previsão do catálogo era que a TNR dissesse, por escola, se o Ideb ausente é
não participação no Saeb ou resultado suprimido. **Não é o que o arquivo faz:** a
TNR mede o percentual de alunos sem informação de rendimento/movimento no Censo
Escolar, e não tem campo de participação no Saeb nem de supressão. Antes da
comparação, a junção foi medida: 611 dos 624 IDs de escola do Ideb 2025 estão na
TNR (97,9%) e 615 estão no cadastro de 2025 (98,6%). O teste empírico confirma o
que a definição já dizia:

| Etapa (estadual) | Sem Ideb | Mediana TNR com Ideb | Mediana TNR sem Ideb |
|---|---|---|---|
| Anos iniciais | 91 de 426 | 1,3% | 1,3% |
| Anos finais | 74 de 229 | 1,9% | 2,5% |
| Ensino médio | 32 de 96 | 2,0% | 1,8% |

As distribuições se sobrepõem; a TNR não separa os grupos. As medianas sem Ideb
usam as escolas com taxa na TNR (39, 34 e 32); das ausências, 83, 72 e 32 estão no
arquivo. O que a TNR acrescenta é outra distinção: em 44 dos 91 casos de anos
iniciais e 38 dos 74 de anos finais a célula é `'--'`, e o cadastro de 2025 confirma
etapa não ofertada em 42 e 37 desses casos. Ali não há coorte a avaliar — é não
aplicável, não não participação.
No médio estadual nenhuma das 32 ausências é `'--'`: a causa segue sem dado por
escola.

**Cobertura da privada:** a TNR cobre 336 das 337 escolas privadas com
fundamental ou médio, e lista 150 privadas com médio. O arquivo de Ideb do médio
lista 37. Ou seja: o Ideb privado ausente é não publicação, não não-resposta — e
a TNR não fecha essa lacuna.

Saídas: `q12_tnr_ideb_ausente.csv` e `q12_tnr_nao_aplicavel.csv`.

## 5. Limites

- As taxas são por escola e não ponderadas: sem matrícula por etapa/escola
  ingerida, a mediana não é a taxa da rede. Ponderar exigiria o Censo 2025 por
  escola.
- Os dois arquivos são de 2025 apenas; não há série histórica nesta entrega.
- A TNR não é indicador de participação no Saeb. Nenhuma leitura deste projeto a
  usa como tal.

## Reprodução

```sh
.venv/bin/python scripts/07_ingest_inep.py
.venv/bin/python scripts/08_profile_inep.py
.venv/bin/python scripts/06_analysis.py
```

`08` lê os dois xlsx em streaming (`openpyxl` `read_only`) e leva ~80 s no total,
incluindo os seis arquivos anteriores.
