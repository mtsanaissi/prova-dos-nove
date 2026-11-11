# data/public/

Exceção declarada à regra "`data/` nunca entra no git" (`AGENTS.md`,
Convenções). Aqui entra **apenas** o recorte mínimo que o build do site lê:
agregado por escola e por etapa, mais a lista fechada de tabelas de contexto,
sem arquivo bruto, sem microdado e sem linha que identifique uma pessoa. Tudo
nesta pasta é gerado por script, versionado e descrito em `SCHEMA.md`.

A lista de arquivos é **fechada e nominal**: `ideb_uf.parquet` (Ideb da INEP por
UF, nível de território) e `agregados.parquet` (contagens e distribuições por
rede, derivadas dos arquivos por escola). Acrescentar uma tabela a esta pasta
exige emendar o `AGENTS.md` primeiro.

A lista é de arquivos, não de linhas: um id novo dentro de `agregados.parquet`
não exige emenda do `AGENTS.md`; tabela nova exige. A fronteira é o `calculo`: se
o texto do `calculo` da família já descreve a conta do id novo, é linha; se não
descreve, é família nova em `procedencia.json` — e família nova é decisão de
fonte, cálculo, limites e licença, não de formato de arquivo.

O agregado é auditado pelo que a home mostra: id exportado e não publicado é id
morto e faz o `--check` falhar (critério 9). Se um número for exportado e
deliberadamente não exibido, a saída é **não exportar o id** — nunca afrouxar o
check.

Gerado por:

```sh
.venv/bin/python scripts/06_analysis.py --public data/public
```

| arquivo | grão | o que traz |
|---|---|---|
| `escolas.parquet` | escola (1.291) | identificação, rede, RA, `censo_2024_presente`, 8 sinalizadores de oferta e matrícula por etapa em 2024 e 2025 |
| `indicadores.parquet` | escola × etapa × indicador × ano | Ideb observado (2005–2025), TDI, TNR, aprovação, reprovação e abandono (2025), com `estado` copiado da fonte |
| `infraestrutura.parquet` | escola × item (8 itens) | presença declarada dos itens de infraestrutura, no universo das 927 escolas que oferecem ensino fundamental ou médio |
| `ideb_uf.parquet` | etapa × ano × rede (24 linhas) | Ideb observado do DF e do Brasil em 2023 e 2025, a posição do DF entre as UFs e o número de UFs com valor no ano; `df_estado`/`brasil_estado` dizem onde o número falta |
| `agregados.parquet` | id do número da home (40 linhas) | contagens e distribuições por rede que a home publica: escolas e RAs, creche, cobertura do Ideb e percentis de distorção idade-série, com `valor`, `n` e `estado` |
| `procedencia.json` | família de indicador (14 famílias) | fonte, arquivo, anos, cálculo, limites, `licenca`, `licenca_url` e o sha256 dos cinco parquets; topo com `execucao.etapas_puladas` |

Tamanhos medidos em 2026-11-11: 61.846 B, 40.420 B, 12.289 B, 5.653 B, 6.030 B
e 7.964 B, na ordem da tabela.

`agregados.parquet` não aplica o limiar de n da página da escola: a distribuição
de distorção inclui as unidades de turma pequena, e a diferença é declarada em
L-67 e no `calculo` de cada registro `tdi-*`. A "privada" da distribuição reúne
conveniada e não conveniada (L-36, L-37), e a rede federal fica fora (L-32).

`censo_2024_presente` é `True` quando a escola de 2025 tem linha no Censo 2024
e `False` quando não tem. As 53 escolas sem linha e as 3 com linha e células
vazias recebem frases diferentes na página (L-63 e L-28).

A licença vem por família: os conjuntos da SEEDF usam `licenca_titulo` e
`licenca_url` do inventário do CKAN; a INEP fica com "público, sem licença
declarada no portal", sem URL. O export falha antes de gravar se uma família
SEEDF resolver para um conjunto ODbL (L-62).

O build **não** lê `data/interim/` nem `data/raw/`; ele confere o sha256
registrado em `procedencia.json` e falha se o insumo não bater. Se o destino já
existir com conteúdo diferente, o export falha e só sobrescreve com `--force`,
para que a mudança apareça no diff. Uma execução com etapa pulada não grava sem
`--parcial`; com `--parcial`, a lista vai para `execucao.etapas_puladas`.
