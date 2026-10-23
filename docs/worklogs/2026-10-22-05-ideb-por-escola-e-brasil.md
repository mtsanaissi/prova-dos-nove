# 2026-10-22 — 05. Ideb por escola, linha Brasil e conferência da série

Objetivo: fechar o Ideb por escola de todas as redes do DF, acrescentar a linha
Brasil que a planilha de UF não tem e medir o que os arquivos nacionais
acrescentam ao que a SEEDF já publica. Scripts: `07_ingest_inep.py`,
`08_profile_inep.py` (dois leitores novos) e `q8` de `06_analysis.py`.

## 1. Ingestão declarada (`07_ingest_inep.py`)

Quatro arquivos já estavam em `data/raw/inep/inbox/`, com bytes conferidos contra
o `Content-Length` do servidor. `07` calculou sha256, moveu para
`data/raw/inep/<data>_<nome>`, registrou procedência no `MANIFEST.md` (135 → 139
linhas) e ignorou os quatro `:Zone.Identifier` — que continuam na inbox, como
esperado. Nenhum download automático foi tentado ou alegado:

| Arquivo | Bytes | O que acrescenta |
|---|---|---|
| `divulgacao_brasil_ideb_2025.zip` | 85.519 | Ideb do Brasil por etapa e rede |
| `divulgacao_anos_iniciais_escolas_2025.zip` | 112.185.922 | Ideb por escola, anos iniciais |
| `divulgacao_anos_finais_escolas_2025.zip` | 80.112.586 | idem, anos finais |
| `divulgacao_ensino_medio_escolas_2025.zip` | 18.989.748 | idem, ensino médio |

## 2. Perfil antes do leitor (`08_profile_inep.py`)

O perfil genérico continuou sendo o primeiro passo e continuou dizendo "UF
identificada: NÃO" nos quatro arquivos — o `read_excel` direto lê a linha de
título como cabeçalho. O que ele mostrou:

- todos os zips têm `.xlsx`, `.ods` e `md5_*.txt`; o `.ods` não é lido (falta
  `odfpy`), o `.xlsx` é o insumo;
- cada arquivo por escola tem **uma aba** (`IDEB_Escolas (...)`), 135/124/58
  colunas, com 5 linhas de título, cabeçalho em três faixas (7–9) e os códigos na
  linha 10;
- o zip do Brasil tem 3 abas (`Brasil (Anos Iniciais)`, `Brasil (Anos Finais)`,
  `Brasil (EM)`), 131 colunas, mesmo desenho da planilha de UF.

O recorte do DF nos arquivos por escola é feito em **streaming** (`openpyxl`
`read_only`), não em `pandas`: são 66.154 linhas nacionais em anos iniciais para
426 do DF, 48.021/230 nos finais e 22.185/144 no médio. O script imprime as
contagens nacionais, o conjunto de redes e confere que todo `CO_MUNICIPIO`
resultante é `5300108`. As linhas de fonte e notas ficam na mesma coluna `SG_UF`
e caem no filtro de UF: não viram escola.

## 3. Armadilha: código vazio com valor presente

Na aba `Brasil (Anos Finais)` a célula do código do Ideb de 2023 está **vazia**,
mas a coluna tem valor (5,0). Ler só a linha de códigos perderia o Ideb 2023 do
Brasil nos anos finais. `processar_brasil()` preenche o código a partir da faixa
de cabeçalho (`IDEB 2023 (N x P)`, coluna 111) e imprime o que preencheu. O
mesmo cuidado não foi necessário nas abas de AI e EM nem na planilha de UF.

## 4. O que os arquivos dizem — e o que eles não dizem

A hipótese da sessão era que os arquivos por escola trariam as redes privada e
federal que a SEEDF não publica. A medição desmente a parte privada:

- **Anos iniciais e finais:** não há **nenhuma** linha de rede privada em
  nenhuma UF — só `Municipal`, `Estadual` e `Federal`. No DF, AI tem 426 escolas
  estaduais e AF tem 229 estaduais + 1 federal.
- **Ensino médio:** há 1.247 linhas privadas no país, mas só 851 têm valor, todas
  de 2017; de 2019 em diante a célula é `'-'` em todas. No DF são 37 escolas
  privadas, 19 com Ideb em 2017 e nenhuma em 2023 ou 2025.
- O agregado privado por UF existe (`divulgacao_regioes_ufs_ideb_2025.zip`); o
  que não existe é o recorte por escola depois de 2017.

A conferência valor a valor mostra que os arquivos por escola também **não
acrescentam dado novo do DF**: o recorte da INEP é idêntico à série que a SEEDF
republica — 3.512 valores em AI, 1.542 em AF e 222 em EM, zero divergências
(`q8_conferencia_seedf.csv`). O ganho do lote é outro: a linha Brasil, a prova de
que a republicação da SEEDF é fiel e a medida da cobertura contra o cadastro.

## 5. Normalização (`08`)

Dois parquets novos em `data/interim/inep/`:

- `brasil_ideb_tidy.parquet` — 266 linhas, mesmo esquema de `ideb_uf_tidy`
  (`etapa`, `local`, `rede`, `ano`, `indicador`, `valor`, `rede_base`,
  `marcadores_nota`), para empilhar sem tradução;
- `ideb_escolas_df.parquet` — 13.472 linhas longas, 624 escolas do DF, colunas
  `etapa`, `SG_UF`, `CO_MUNICIPIO`, `NO_MUNICIPIO`, `ID_ESCOLA`, `NO_ESCOLA`,
  `REDE`, `ano`, `indicador`, `valor`, `valor_bruto`, `estado`.

Regra de ausência: `'-'` é **sem resultado divulgado** — não participação,
participantes abaixo do critério da Portaria nº 435/2025 ou resultado não
publicado. Fica em `valor_bruto`, com `valor` nulo e `estado = 'ausente'`; nenhum
zero é imputado. `VL_PROJECAO_YYYY` vira `ideb_projetado` e é a **meta do 1º
ciclo** (2007–2021), nunca um resultado observado.

## 6. `q8` — os números que o relatório cita

| Arquivo | O que traz |
|---|---|
| `q8_df_brasil_uf.csv` | DF × Brasil × mediana das UFs, por etapa, rede e ano (2023 e 2025), com posição |
| `q8_escolas_rede.csv` | por etapa, rede e ano: escolas listadas, com e sem Ideb, mediana, p10, p90, mínimo, máximo |
| `q8_cobertura_escolas_2025.csv` | cadastro de 2025 × arquivo da INEP × Ideb 2025, por etapa e rede |
| `q8_conferencia_seedf.csv` | conferência valor a valor entre a série da SEEDF e o recorte da INEP |

Resultados que passam a ter script atrás: DF Total / Estadual 2025 = 6,4 / 6,0
(AI), 5,1 / 4,6 (AF), 4,1 / 3,6 (EM regular); Brasil 6,3 / 5,3 / 4,5; cobertura
do Ideb 2025 entre as escolas que ofertam a etapa em 2025 = 85,2% (AI estadual),
78,3% (AF), 62,1% (EM), 54,5% (EM federal).

## 7. Decisões e limites

1. A rede privada não tem Ideb por escola depois de 2017 — isso é uma ausência de
   publicação, não um arquivo faltando. O relatório passou a dizer isso com a
   contagem na mão, em vez de prometer o dado para a próxima sessão.
2. A mediana por escola não é comparável entre 2023 e 2025 sem ressalva: o
   conjunto de escolas que divulgou mudou (48 escolas estaduais de EM em 2023, 64
   em 2025).
3. O ensino médio **com o integrado à EPT** continua fora: até ingerir
   `divulgacao_ufs_Ensino_Medio_integrado_ideb_2025.xlsx`, o último lugar do DF
   vale para o médio regular.
4. Nada de ranking: as distribuições por escola entram como mediana, p10 e p90,
   nunca como lista ordenada de escolas.

## Reprodução

```sh
.venv/bin/python scripts/07_ingest_inep.py
.venv/bin/python scripts/08_profile_inep.py
.venv/bin/python scripts/06_analysis.py
```

`07` é o único passo com intervenção humana (download pelo navegador). `08`
roda em ~42 s e reescreve os três parquets da INEP a partir dos zips; `06` é
offline e reescreve todos os `q*.csv`, inclusive os de `q8`.
