# SCHEMA.md — dicionário de dados

Preenchido a partir de `scripts/03_profile_seedf.py` (`data/interim/profile_files.csv`,
`data/interim/profile_columns.csv`), `scripts/04_crosswalk.py`
(`data/interim/crosswalk.csv`), `scripts/08_profile_inep.py`
(`data/interim/inep_perfil.csv` e os parquets da INEP) e `scripts/09_download_malha.py`
(`data/interim/malha_ra_validacao.csv`). Uma linha por arquivo bruto em
`MANIFEST.md`; aqui um bloco por família. Perfil coluna a coluna fica em
`profile_columns.csv`.

## Vocabulário controlado

Toda célula vazia precisa ser classificada como uma destas **quatro** coisas — e
o código precisa distinguir as quatro, não colapsar em `NaN`:

| Estado | Significado | Exemplo |
|---|---|---|
| `valor` | o dado existe e está informado | Ideb 6,0 em 2025 |
| `zero` | o valor é zero | escola com 0 matrículas em creche |
| `ausente` | deveria existir e não foi informado ou não foi coletado | escola privada sem IDEB por não participar do SAEB |
| `nao_aplicavel` | a categoria não se aplica ao caso | taxa de abandono no ensino médio em escola que só tem infantil |

O que cada família de fonte pode emitir, medido nos parquets (2026-11-06):

| família | estados presentes | o que falta |
|---|---|---|
| Ideb por escola (`ideb_escolas_df`) | `valor`, `ausente` | não emite `zero` nem `nao_aplicavel`: nota zero não existe na escala e a etapa não ofertada simplesmente não tem linha |
| TDI, TNR e fluxo por escola (`tdi_escolas_df`, `tnr_escolas_df`, `tx_rend_escolas_df`) | `valor`, `zero`, `nao_aplicavel` | não emite `ausente`: a célula vazia da fonte é sempre etapa sem matrícula (`--`) |
| Censo por escola (`censo_escola_df`) | `valor`, `ausente` | matrícula não declarada é ausência: as 76 células vazias de 2024 (L-28) e, em 2025, a célula vazia da escola que existe no arquivo; a escola de 2025 sem linha em 2024 é outra ausência, registrada por `censo_2024_presente = False` (L-63). `zero` existe quando o campo é 0 |

Convenção adotada no código: nulo = `ausente`; `0` = zero; coluna que não existe
naquele ano = `nao_aplicavel`. Onde a fonte usa `"NULL"`, `"-"` ou `""` como
texto, o valor entra como `ausente` — nunca como zero. Na INEP, o traço `'-'` das
planilhas de Ideb significa **sem resultado divulgado** (não participação,
participantes abaixo do critério da Portaria nº 435/2025, ou resultado não
publicado), e por isso o texto original é preservado em `valor_bruto` ao lado do
`valor` nulo e do `estado = 'ausente'`. Já nas planilhas de taxa por escola
(rendimento, TDI e TNR) o token é o traço duplo **`'--'`**, que significa **não
aplicável** — a escola não tem matrícula naquela etapa/série — e entra como
`estado = 'nao_aplicavel'`. São dois traços, dois significados: um não substitui
o outro. Na página, as frases fixas são: `a escola não consta do Censo de 2024`
(L-63), `matrícula não declarada no Censo de 2024` (L-28) e `matrícula não
declarada no Censo de 2025` (L-28).

## Modelo de arquivo

### `relatorio_escolas_*.csv` (família `escolas`)

| Campo | Valor |
|---|---|
| Fonte | SEEDF |
| URL | CKAN `relacao-de-unidades-escolares-abrangendo-todas-as-redes-de-ensino-do-distrito-federal` |
| Data do download | 2026-10-22 |
| Anos cobertos | 2014–2025 (12 arquivos) |
| Granularidade (o que é uma linha?) | uma unidade escolar em um ano do Censo |
| Chave primária | `CO_ENTIDADE` (única em todos os anos; 0 duplicatas) |
| Nº de linhas | 1.148 (2014) a 1.291 (2025) |
| Redes cobertas | todas: federal, estadual vinculada e não vinculada, particular conveniada e não conveniada |
| Observações | trazem `RA`/`Nome RA`, `CRE` e localização. **A oferta muda de forma em 2025:** até 2024 são contagens de turmas (`ESC_EI_CRECHE`, `ESC_EF_INI`, `ESC_EM_TOTAL`…); em 2025 são sinalizadores 0/1 (`INF_CRE`, `INF_PRE`, `FUND_AI`, `MED`…). 2025 também troca nomes de variável por rótulos legíveis ("Nome da escola"), passa de 74 para 81 colunas e traz uma linha de título acima do cabeçalho |

**Colunas principais**

| Coluna | Tipo | Descrição | Domínio observado (2025) |
|---|---|---|---|
| `CO_ENTIDADE` | texto | código INEP da escola | 8 dígitos, 1.291 distintos |
| `Nome Rede` | texto | rede de ensino | 5 valores |
| `RA` / `Nome RA` | texto | Região Administrativa | 36 valores, com inconsistências de espaço (`AGUAS CLARAS `) |
| `Tipologia` | texto | tipo de unidade (PAR, CEPI, CEF, CEI, CEM…) | 18 valores, só existe em 2025 |
| `INF_CRE`, `INF_PRE`, `FUND_AI`, `FUND_AF`, `MED` | 0/1 | oferta da etapa (só em 2025) | `0`/`1` |
| `ESC_EI_CRECHE`, `ESC_EF_INI`, `ESC_EM_TOTAL` | inteiro | turmas por etapa (2014–2024) | 0 a ~40 |

### `relatorio_matriculas_*.csv` (família `matriculas`)

| Campo | Valor |
|---|---|
| Fonte | SEEDF (microdados do Censo Escolar filtrados para o DF) |
| URL | CKAN `quantidade-de-matriculas-das-modalidades-de-ensino-abrangendo-todas-as-redes-de-ensino-do-df` |
| Data do download | 2026-10-22 |
| Anos cobertos | 2014–2024 em CSV; 2025 só em XLSX |
| Granularidade | escola × idade × sexo × cor/raça, com contagens por etapa (`MAT_*`) |
| Chave primária | `CO_ENTIDADE` + `IDADE` + `TP_SEXO` + `TP_COR_RACA` (0 duplicatas em 2024) |
| Nº de linhas | 74.710 (2018) a 81.961 (2014) |
| Redes cobertas | todas — **exceto 2023**, que traz apenas rede pública (600 escolas, 42.440 linhas) |
| Observações | 2025 em XLSX muda o esquema: 73 colunas com rótulos legíveis e `Código INEP` |

**Colunas principais**: `MAT_CRECHE`, `MAT_PRE`, `MAT_EI_TOTAL`, `MAT_EF_*`,
`MAT_EM_*`, `NU_IDADE`. `0` é zero real; nulo não aparece nesses campos.

**Leitura por idade:** `IDADE` acompanha a linha, então a matrícula em creche se
abre por idade simples. Em 2024: 40.851 matrículas em creche, das quais 26.076
com `IDADE` ≤ 3 e 14.775 com `IDADE` ≥ 4 (36,2%).

**26.076 não é "as crianças de 0 a 3 na creche" do Censo.** É creche **× idade no
ano** — uma terceira contagem, que não coincide com a faixa 0–3 que a INEP
publica (37.595 em 2024, medida na data de referência do Censo) nem com as
crianças de 0–3 que frequentam escola na PDAD-A (37.654). As três estão lado a
lado em `q14_creche_fecho.csv`, com o cálculo de cada uma; a diferença de 11.519
entre a primeira e a segunda é a coorte que tinha 4 anos no ano e 3 na data de
referência. Nenhuma das três é "a" contagem certa: são convenções diferentes, e
quem compara precisa dizer qual está usando (ver o bloco dos microdados do Censo
e `REPORT.md` §2.7).

**`IDADE` não é idade em 31/03.** O dicionário do campo diz "idade calculada pelo
ano de nascimento": é a idade no ano do Censo, não a idade na data de corte da
matrícula (31/03). A prova está no próprio arquivo — no 1º ano do fundamental,
70,8% dos alunos aparecem com `IDADE` 7 e 25,0% com 6, exatamente o que o corte
de 31/03 produz sobre idade-por-ano-de-nascimento. Consequência: uma criança com
`IDADE` 4 pode estar legitimamente em creche (nascida depois de 31/03), e a
diferença entre "idade 4" e "4 anos em 31/03" **não é distorção idade-etapa**.
Nenhuma conta de distorção deste projeto usa `IDADE`; a distorção vem da TDI da
INEP, que aplica o corte. Para creche, o numerador é `MAT_CRECHE` (etapa) e o
denominador é a população de 0–3 do microdado da PDAD-A (ver bloco da PDAD).

### `relatorio_infraestrutura_*.csv` (família `infraestrutura`)

| Campo | Valor |
|---|---|
| Fonte | SEEDF |
| URL | CKAN `dados-de-infraestrutura-abrangendo-todas-as-redes-de-ensino-df` |
| Data do download | 2026-10-22 |
| Anos cobertos | 2014–2025 (12 arquivos) |
| Granularidade | uma unidade escolar em um ano |
| Chave primária | `CO_ENTIDADE` (0 duplicatas) |
| Nº de linhas | 1.050 (2014) a 1.471 (2025) |
| Redes cobertas | todas |
| Observações | **(a)** o arquivo rotulado 2016 contém ano 2017 e é idêntico ao de 2017 — 2016 não existe; **(b)** 2025 tem 289 colunas contra 114 dos anos anteriores; **(c)** 2025 inclui 139 escolas paralisadas/extintas (`TP_SITUACAO_FUNCIONAMENTO` 2 e 3), por isso 1.471 linhas contra 1.291 do cadastro; **(d)** `TP_DEPENDENCIA` não distingue conveniada de privada em 2025 — é preciso usar `CO_REDE`/`NO_REDE` |

**Colunas principais**: `IN_BIBLIOTECA`, `IN_LABORATORIO_INFORMATICA`,
`IN_INTERNET`, `IN_QUADRA_ESPORTES`, `IN_ACESSIBILIDADE_*`, `IN_BANHEIRO`,
`IN_ESGOTO_*`, `IN_AGUA_*`. São 0/1: `1` = existe. **Exceção:** colunas com
sufixo `_INEXISTENTE` marcam a ausência com `1`.

**Biblioteca e sala de leitura são três itens, não um.** O dicionário da própria
SEEDF (`dicionario_de_dados_infraestrutura.csv`, campos 123, 124 e 144) define:
`IN_BIBLIOTECA` = "Dependências físicas existentes e utilizadas na escola -
Biblioteca"; `IN_SALA_LEITURA` = "... - Sala de Leitura";
`IN_BIBLIOTECA_SALA_LEITURA` = "... - Biblioteca e/ou Sala de leitura". O
terceiro é **exatamente o OR dos outros dois** — conferido nos 12 anos. Sala de
leitura **não é** biblioteca, e nenhuma frase do projeto pode tratá-las como a
mesma coisa. Além disso, o universo importa: biblioteca não é exigência para
creche, então as medidas do projeto são calculadas só entre as escolas que
ofertam fundamental ou médio (927 em 2025), nunca sobre as 1.332 unidades em
funcionamento. Três medidas nomeadas saem em `q3_biblioteca.csv`,
`q3_biblioteca_por_ra.csv` e `q3_biblioteca_serie.csv`:
`sem_biblioteca_pct` (`IN_BIBLIOTECA = 0`),
`sem_biblioteca_nem_sala_leitura_pct` (`IN_BIBLIOTECA_SALA_LEITURA = 0`) e
`biblioteca_sem_bibliotecario_pct` (`QT_PROF_BIBLIOTECARIO = 0` entre as que têm
biblioteca). Em 2025, entre as escolas de EF/EM: 60,6% sem biblioteca, 6,0% sem
biblioteca nem sala de leitura, 48,2% das que têm biblioteca não têm
bibliotecário; na rede estadual, 73,4%, 6,4% e 61,4%.

### `relatorio_situacao_aluno_excel_*.csv` (família `situacao`)

| Campo | Valor |
|---|---|
| Fonte | SEEDF |
| URL | CKAN `situacao-do-aluno-serie-historica` |
| Data do download | 2026-10-22 |
| Anos cobertos | 2019–2024 (2025 em versão reduzida: 2.421 linhas, 27 colunas, só totais) |
| Granularidade | escola × idade × sexo × cor/raça × situação × concluinte |
| Chave primária | `CO_ENTIDADE` + `IDADE` + `TP_SEXO` + `TP_COR_RACA` + `TP_SITUACAO` + `CONCLUINTE` (0 duplicatas em 2023) |
| Nº de linhas | 126.672 (2019) a 71.122 (2020) |
| Redes cobertas | **apenas rede pública estadual vinculada à SEEDF**; 2019 inclui também federal |
| Observações | `SITUACAO` ∈ {APROVADO, REPROVADO, SIR, DEIXOU DE FREQUENTAR, FALECIDO}; `SIR` = sem informação de rendimento, é `ausente`, não reprovação |

### `relatorio_distorcao_idade_serie_*.csv` (família `distorcao`)

| Campo | Valor |
|---|---|
| Fonte | SEEDF |
| Anos cobertos | 2014–2025 |
| Granularidade | escola × etapa/série (taxas `TDI_*`) |
| Chave primária | `CO_ENTIDADE` (0 duplicatas em 2023) |
| Redes cobertas | todas |
| Observações | 2014–2023 com nomes de variável; 2024–2025 com duas linhas de cabeçalho e rótulos legíveis. Baixado e perfilado, **não usado** nas respostas desta sessão |

### `relatorio_docentes_*.csv`, `*_educa_dados_docente-alt.csv` (família `docentes`)

| Campo | Valor |
|---|---|
| Fonte | SEEDF |
| Anos cobertos | 2023, 2024, 2025 (só os três mais recentes foram baixados) |
| Granularidade | escola × idade × sexo (contagens de docentes) |
| Chave primária | não única por escola — o grão é escola × características do docente |
| Observações | 2025 com rótulos legíveis, 79 colunas. Não usado nas respostas desta sessão |

### `*_educa_dados_turma.csv` (família `turmas`)

| Campo | Valor |
|---|---|
| Fonte | SEEDF |
| Anos cobertos | 2024 e 2025 (só os dois mais recentes foram baixados; há CSV de 2015 a 2022 no portal) |
| Granularidade | escola × turno/turma (`ID_TURMA`) |
| Chave primária | `ID_TURMA` (0 duplicatas em 2024) |
| Observações | 2015 em `latin-1` com `;` — caso concreto de que não se pode assumir encoding |

### `ideb_ef_ai_2005_2025*.csv`, `ideb_ef_af_2005_2025.csv`, `ideb_em_2017_2025.csv` (família `ideb_serie`)

| Campo | Valor |
|---|---|
| Fonte | SEEDF (republicação dos resultados do SAEB/IDEB) |
| Anos cobertos | 2005–2025 (bienal; EM a partir de 2017) |
| Granularidade | escola × ano × etapa × indicador |
| Chave primária | `cod_inep` + `ano` + `etapa_modalidade` + `indicador` |
| Redes cobertas | **Estadual** em anos iniciais; Estadual + Federal em anos finais; Estadual + Privada + Federal no médio |
| Observações | formato longo: `indicador` ∈ {IDEB, Nota SAEB, Taxa de Aprovação, Meta}. `valor` pode ser `-` = `ausente` (não participou), nunca zero. **Cabeçalhos diferentes entre as três etapas** (`cod_inep` minúsculo no AI, `Cód_Inep` no AF/EM) e separador `;` só no AI |

### `planilha_ideb_*_2019_2021_2023.csv` (família `ideb_planilha`)

| Campo | Valor |
|---|---|
| Fonte | SEEDF, formato largo (uma coluna por ano/indicador) |
| Granularidade | escola (rede pública) |
| Observações | 734 linhas nas três etapas; usado como conferência do formato longo |

### `*_educa_escola_infraestrutura_tecnologia_*.csv` (família `tecnologia`)

| Campo | Valor |
|---|---|
| Fonte | SEEDF |
| Anos cobertos | 2023 e 2024 |
| Granularidade | escola × turno |
| Chave primária | `Cód. Inep` |
| Observações | 41 colunas com rótulos legíveis (`Computadores`, `Lousa digital`). Não usado nas respostas desta sessão |

### `lista_unidades_educacao_infantil_csv_2023.csv` (família `unidades_ei`)

| Campo | Valor |
|---|---|
| Fonte | SEEDF |
| Granularidade | unidade com oferta de educação infantil (pública, conveniada e privada) |
| Nº de linhas | 468 |
| Observações | traz coordenadas e e-mail institucional; e-mail **não** é usado (dado de contato, fora do escopo) |

### `unidades-ef-*.csv`, `unidades-em.csv` (família `unidades_oferta`)

| Campo | Valor |
|---|---|
| Fonte | SEEDF |
| Granularidade | unidade × etapa ofertada (rede pública) |
| Nº de linhas | 420 (EF anos iniciais), 224 (EF anos finais), 90 (EM) |
| Observações | o mesmo conjunto é republicado em outro dataset (`unidades-escolares-...-por-oferta`) |

### `pdad_a_2024_*.pdf` (IPEDF, fora da SEEDF)

| Campo | Valor |
|---|---|
| Fonte | IPEDF — PDAD-A 2024 (`https://pdad.ipe.df.gov.br/`) |
| Granularidade | Região Administrativa (relatório por RA) |
| Dado extraído | população por faixa etária e sexo, tabela 2 de cada relatório |
| Faixa disponível | **`até 4 anos`** — o PDF não abre 0–3; o microdado abre (bloco seguinte) |
| Observações | 53 PDFs, medidos: 35 RAs do DF, 12 municípios goianos da área de influência e 6 documentos que não são RA (total do DF, DF rural, dicionário de dados, base de domicílios, base de morador, questionário). Só as 35 RAs entram em `pdad_populacao.csv`. População é **estimativa amostral**, não contagem censitária. **Três desses "PDFs" são os microdados** (dois ZIP e um XLSX, com extensão errada) e são lidos por `10_ingest_pdad.py` — ver o bloco abaixo |

### `pdad_a_2024_base_de_morador.pdf`, `..._base_de_domicilios.pdf`, `..._dicionario_de_dados.pdf` (IPEDF — microdados)

| Campo | Valor |
|---|---|
| Fonte | IPEDF — PDAD-A 2024, os mesmos arquivos que o 05 baixou como "relatório"; a extensão está errada (ver `MANIFEST.md` → Correções) |
| Formato real | `..._base_de_morador.pdf` = **ZIP** com `moradores.csv` (69.542 × 134); `..._base_de_domicilios.pdf` = **ZIP** com `domicilios.csv` (24.845 × 128); `..._dicionario_de_dados.pdf` = **XLSX** (abas `moradores`, `domicilios` e `anexo_1`…`anexo_11` com os domínios de código) |
| Granularidade | uma linha por **morador** (não é escola, não é RA) — e é por isso que nada individual sai do script |
| Chave | `morador_id` (morador) e `A01nficha` (domicílio) — **descartadas** na leitura |
| Pesos | `peso_mor` (morador) e `peso_dom` (domicílio). Soma de `peso_mor`: 4.255.724 nas 48 localidades, 2.982.816 no DF |
| Geografia | `localidade` = RA do DF (5301–5335), Área Rural (5336) ou município goiano (5241–5252); `setor_distrito` é mais fino e **é descartado** |
| Idade | `idade_calculada` (na entrevista, completa) e `E02_1` (data de nascimento, preenchida em **49,6%** das linhas). A idade em 31/03/2024 — o critério de matrícula — só existe para essa subamostra, que cobre 55,2% da população de 0–3: **não serve de denominador**; o denominador do projeto é a idade na entrevista, com a convenção declarada |
| Campos usados | `idade_calculada`, `H02` (frequenta creche/escola), `H04_1` (pública/particular), `H04_4` (RA/município da escola), `E05` (cor/raça), `peso_mor` |
| Sentinela | `88888` = não sabe, `99999` = não se aplica. Nunca entram em soma, média ou contagem; em categoria, viram rótulo explícito. `renda_domiciliar_pc_r` é 99999 em **78,7%** dos domicílios (cobertura válida de 6,7% a 33,9% por RA) e **não é usada** |
| H04_4 | `0` = na própria RA; `40` = no próprio município; `1`–`36` = RA (`5300 + código`); `41`–`52` = município goiano (`5200 + código`). O respondente às vezes informa o código do próprio município em vez de `40`: o leitor compara com `localidade % 100` e conta como próprio. Sem essa regra, "estuda em outra RA" sai inflado em ~30 p.p. |
| Saídas (`data/interim/pdad/`) | `pdad_populacao.parquet` (RA × idade simples 0–17, × faixa, e × faixa em 31/03; `escopo` separa as três convenções), `pdad_frequencia.parquet` (RA × faixa × frequência × rede; a linha `ra = "DF"` é o agregado e não se soma às RAs), `pdad_fluxo_escolar.parquet` (RA de moradia × destino × rede, 6–17 anos), `pdad_entorno.parquet` (município goiano × destino), `pdad_conferencia.csv` (microdado × tabela do PDF, por RA) e `pdad_metodo.csv` (as checagens) |
| Variância | aproximada: Kish para proporções, com reposição para totais. O arquivo **não traz estrato nem unidade primária**, então o intervalo publicado é um limite inferior de largura |
| Validação | total expandido por RA × `pop_total` dos PDFs: desvio máximo **0,01%** em 35 RAs; total do DF 2.982.816 contra 2.982.816 do documento do DF (0,00%). `10_ingest_pdad.py` interrompe acima de 5% por RA ou 1% no total |
| Idempotência | reescreve os parquets a partir do raw; duas execuções geram bytes idênticos; não acessa a rede |
| Achados que o arquivo já entrega | DF com 139.116 crianças de 0–3 (4,7% da população); 27,1% frequentam creche (IC ±2,5 p.p.), 57,8% na rede pública — a mesma proporção que o Censo 2024 dá para a rede conveniada (57,3% da matrícula em creche); 4–5 anos: 86,0% frequentam; 6–10 e 11–14: 97,5% e 97,6%; 15–17: 90,6%. Fluxo: 74,7% dos alunos de 6–17 anos estudam na própria RA, 24,6% em outra. Entorno: 19.523 moradores de 6–17 anos dos 12 municípios goianos estudam no DF (Novo Gama 26,8%, Planaltina de Goiás 22,9%, Padre Bernardo 21,4%) |
| Limite | o n por RA e por faixa é pequeno (0–3: 14 a 184 pessoas); o meio-intervalo por RA vai a 6–36 p.p. — serve para agrupar RAs, não para mapa fino |

### `2026-10-22_regioes_administrativas_df.geojson` (GDF/IDE, fora da SEEDF)

| Campo | Valor |
|---|---|
| Fonte | GDF — Geoserviços do IDE/DF, camada "Regiões Administrativas" (`https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/LIMITES/FeatureServer/1`), baixada em 2026-10-22 por `09_download_malha.py` |
| Conteúdo | GeoJSON em EPSG:4326 com 37 feições (4,58 MB); o serviço declara EPSG:31983 (SIRGAS 2000 / UTM 23S) |
| Atributos | `ra_nome`, `ra_codigo` (`RA-IX`…), `ra_cira` (1–37), `ra_areakm2`, `ra_path` (link da monografia da RA) |
| Granularidade | uma feição por Região Administrativa |
| Validação | `data/interim/malha_ra_validacao.csv`: 35 das 37 RAs aparecem no cadastro da SEEDF de 2025 e na PDAD-A 2024; `26 DE SETEMBRO` (RA-XXXVI) e `PONTE ALTA` (XXXVII) existem só na malha; nenhuma RA presente nas duas fontes falta na malha. Nomes normalizados com a mesma regra de `06_analysis.py` |
| Uso | **nenhum uso geoespacial nesta sessão**: nenhuma análise usa geometria e não há mapa. A validação é de procedência, CRS e concordância de nome/código — a condição que o projeto exige antes de `geopandas`/`shapely` entrar em `requirements.txt` |
| Cautela | a malha é de 2025 e tem 37 RAs; o Censo 2022 não delimitou Arapoanga e Água Quente (incluídas em Planaltina e Recanto das Emas, segundo o Informe Demográfico do IPEDF), e as séries de educação de 2024/2025 têm 35 RAs. Qualquer junção por RA precisa declarar a versão da malha |

### `divulgacao_regioes_ufs_ideb_2025.zip` (INEP)

| Campo | Valor |
|---|---|
| Fonte | INEP — divulgação do Ideb 2025 (`download.inep.gov.br/ideb/resultados/`), ingerida em 2026-10-22 pelo caminho manual descrito em "INEP: catálogo e o que entrou" |
| Conteúdo do zip | `.xlsx` e `.ods` equivalentes, mais `md5_divulgacao_regioes_ufs_ideb_2025.txt` |
| Granularidade | `etapa × local × rede × ano`; `local` é uma das 27 UFs ou uma das 5 regiões. **Não existe linha "Brasil"** neste arquivo |
| Etapas | três abas: `UF e Regiões (AI)`, `UF e Regiões (AF)`, `UF e Regiões (EM)`. Os rótulos internos dizem o recorte: "Ensino Fundamental Regular - Anos Iniciais/Finais" e "Ensino Médio Regular". O médio **com o integrado à EPT** tem arquivo próprio, com bloco abaixo |
| Variáveis | `VL_OBSERVADO_2005` … `VL_OBSERVADO_2025` (Ideb observado) e `VL_PROJECAO_2007` … `VL_PROJECAO_2021` (meta). As outras ~100 colunas são taxa de aprovação, indicador de rendimento e notas de português/matemática do SAEB |
| Layout | planilha formatada: 5 linhas de título, cabeçalho em três faixas (linhas 7–9), códigos de variável na linha 10, dados da linha 11 em diante. `read_excel` direto devolve a linha de título como cabeçalho e não serve |
| Normalização | `scripts/08_profile_inep.py` (`processar_ideb_uf`) → `data/interim/inep/ideb_uf_tidy.parquet`: 6.688 linhas, colunas `etapa`, `local`, `rede`, `ano`, `indicador`, `valor`, `rede_base`, `marcadores_nota` |
| Nomes de campo | só os da INEP, verbatim. `rede` preserva o rótulo completo (`Total (3)(4)`); `rede_base` remove o marcador e `marcadores_nota` guarda o dígito |
| Marcadores de nota | `(1)`–`(7)` no rótulo de `rede` são **ressalvas históricas**, não condições de todos os anos: `(1)`/`(2)`/`(3)` tratam de 2009, `(4)` de 2011 (SAEB 2011 sem as escolas federais), `(5)` da pandemia em 2021. O DF traz `Total (4)` em 2025, mas o `(4)` se refere a 2011 |
| Ausências | UF sem resultado simplesmente não tem valor (`NaN`) naquele ano e naquela rede. `AI`/`Estadual` tem 26 UFs porque Roraima não tem Ideb de rede estadual em 2025; a aba do ensino médio não publica linha `Pública` para nenhuma UF |
| Recorte | **todas as UFs foram mantidas**, não só o DF: a tabela inteira tem 152 linhas e sem as outras 26 não existe comparação. É exceção documentada à regra de recorte no DF (que vale para microdados) |
| Idempotência | 08 reescreve o parquet a partir do zip; 07 não reingere arquivo já registrado (confere sha256) |

### `divulgacao_brasil_ideb_2025.zip` (INEP)

| Campo | Valor |
|---|---|
| Fonte | INEP — divulgação do Ideb 2025 (`download.inep.gov.br/ideb/resultados/`), ingerida em 2026-10-22 pelo caminho manual de "INEP: catálogo e o que entrou" |
| Conteúdo do zip | `.xlsx` e `.ods` equivalentes, mais `md5_divulgacao_brasil_ideb_2025.txt` |
| Granularidade | `etapa × rede × ano`; a primeira coluna é sempre `Brasil` — é a linha que a planilha de UF não tem |
| Etapas | três abas: `Brasil (Anos Iniciais)`, `Brasil (Anos Finais)`, `Brasil (EM)` — fundamental regular e médio regular, os mesmos recortes da planilha de UF |
| Redes | AI e AF: `Total`, `Estadual`, `Municipal`, `Pública`, `Privada`; EM: `Total`, `Estadual`, `Pública`, `Privada` (não há `Municipal`) |
| Layout | 5 linhas de título, cabeçalho em três faixas (7–9), códigos na linha 10, dados da 11 em diante |
| **Armadilha** | na aba `Brasil (Anos Finais)` a célula de código do Ideb de 2023 está **vazia**, mas a coluna tem valor (5,0). `processar_brasil()` preenche o código a partir da faixa de cabeçalho (`IDEB 2023 (N x P)`, coluna 111). Ler só a linha de códigos perderia o Ideb de 2023 do Brasil nos anos finais |
| Variáveis | `VL_OBSERVADO_YYYY` (Ideb observado) e `VL_PROJECAO_YYYY` (meta do 1º ciclo, 2007–2021); o resto são taxa de aprovação, indicador de rendimento e notas do SAEB |
| Normalização | `scripts/08_profile_inep.py` (`processar_brasil`) → `data/interim/inep/brasil_ideb_tidy.parquet`: 266 linhas, mesmo esquema de `ideb_uf_tidy.parquet` (`etapa`, `local`, `rede`, `ano`, `indicador`, `valor`, `rede_base`, `marcadores_nota`), para empilhar sem tradução |
| Marcadores de nota | `Privada (1)` na aba de anos iniciais: o `(1)` é ressalva de 2009 (SAEB só urbano), não de 2025. Preservado em `rede`, separado em `rede_base` e `marcadores_nota` |
| Ausências | rede/ano sem resultado publicado simplesmente não tem valor. As linhas de fonte e notas ocupam a mesma primeira coluna e são descartadas pelo filtro `local == 'Brasil'` |

### `divulgacao_anos_iniciais_escolas_2025.zip`, `divulgacao_anos_finais_escolas_2025.zip`, `divulgacao_ensino_medio_escolas_2025.zip` (INEP)

| Campo | Valor |
|---|---|
| Fonte | INEP — Ideb por escola 2025, download manual, ingerido em 2026-10-22 |
| Conteúdo do zip | `.xlsx`, `.ods` e `md5_*.txt`; uma aba por arquivo (`IDEB_Escolas (...)`) |
| Granularidade | escola × ano × indicador, depois de normalizado (a planilha original é escola × ano em colunas) |
| Chave primária | `ID_ESCOLA` + `ano` + `indicador` (0 duplicatas nos três arquivos) |
| Layout | 5 linhas de título, cabeçalho em três faixas (7–9), códigos na linha 10 (`SG_UF`, `CO_MUNICIPIO`, `NO_MUNICIPIO`, `ID_ESCOLA`, `NO_ESCOLA`, `REDE`, `VL_*`), dados da 11 em diante; fonte e notas no rodapé, na mesma coluna `SG_UF`, descartadas pelo filtro de UF |
| Linhas lidas | AI: 66.154 nacionais, 426 do DF; AF: 48.021 e 230; EM: 22.185 e 144 |
| Redes no DF | AI: 426 `Estadual`; AF: 229 `Estadual` + 1 `Federal`; EM: 96 `Estadual` + 11 `Federal` + 37 `Privada`. Não há rede municipal no DF |
| Anos | AI e AF: 2005–2025 (bienal); EM: 2017–2025 |
| Recorte | `SG_UF == 'DF'` em leitura streaming (`openpyxl` `read_only`), sem carregar a planilha inteira; conferido que todo `CO_MUNICIPIO` resultante é `5300108` (o DF tem um município). As 26 outras UFs são lidas e descartadas; nenhum parquet nacional é gravado |
| Vocabulário de ausência | `'-'` = **sem resultado divulgado** (não participou do Saeb, participação abaixo do critério da Portaria nº 435/2025, ou resultado não publicado). Fica preservado em `valor_bruto`; `valor` é nulo; `estado = 'ausente'`. Não há `nao_aplicavel`: a planilha só publica a coluna do ano em que a etapa é avaliada. Nenhum zero foi imputado. No recorte do DF o único token não numérico encontrado é `'-'`; célula vazia, se aparecesse, entraria como `ausente` pelo mesmo caminho |
| Renomes | campos espelhados mantêm o nome da INEP (`SG_UF`, `CO_MUNICIPIO`, `NO_MUNICIPIO`, `ID_ESCOLA`, `NO_ESCOLA`, `REDE`). Derivados: `etapa` (AI/AF/EM), `ano` (sufixo de `VL_*_YYYY`), `indicador` (`ideb_observado`/`ideb_projetado`), `valor` (numérico), `valor_bruto` (texto: `'-'` ou o número formatado, ex. `6.4`), `estado` (`valor`/`zero`/`ausente`) |
| Normalização | `data/interim/inep/ideb_escolas_df.parquet`: 13.472 linhas longas, 624 escolas distintas, só DF |
| Achado de cobertura | a rede privada **não existe** nas planilhas de AI/AF em nenhuma UF (só `Municipal`, `Estadual`, `Federal`); na de EM há 1.247 linhas privadas no país, 851 com valor, todas de 2017 — de 2019 em diante a célula é `'-'` em todas. No DF: 37 escolas privadas de médio, 19 com Ideb em 2017, nenhuma em 2023 ou 2025 |
| Conferência | o recorte da INEP bate valor a valor com a série que a SEEDF republica: 3.512 valores em AI, 1.542 em AF, 222 em EM, 0 divergências (`data/interim/q8_conferencia_seedf.csv`) |

**Ideb observado × projetado.** `VL_OBSERVADO_YYYY` vira `indicador = 'ideb_observado'`;
`VL_PROJECAO_YYYY` vira `indicador = 'ideb_projetado'`, que é a **meta do 1º ciclo**
(2007–2021), não uma projeção de resultado futuro. As colunas de projeção terminam
em 2021 e não há meta para 2023 nem 2025, coerente com a nota informativa. Em
nenhum CSV do projeto `ideb_projetado` entra como valor observado ou em média.

### `divulgacao_ufs_Ensino_Medio_integrado_ideb_2025.xlsx` (INEP)

| Campo | Valor |
|---|---|
| Fonte | INEP — Ideb do ensino médio **com o integrado à EPT**, por UF (`download.inep.gov.br/ideb/resultados/`), ingerida em 2026-10-22 pelo caminho manual |
| Conteúdo | planilha solta (não vem em zip), 31.398 B — o catálogo previa 21.287 B; vale o tamanho do arquivo que entrou, registrado no `MANIFEST.md` |
| Granularidade | `local × rede × ano`; `local` é uma das 27 UFs, sem regiões e **sem linha Brasil**; `rede` é sempre `Estadual` |
| Layout | uma aba (`UF (EM_integrado)`), 5 linhas de título, cabeçalho em três faixas (7–9), códigos na linha 10, dados da 11 em diante. A primeira coluna é o **nome da UF por extenso**, sem código |
| Anos | 2017–2025 (bienal); só `VL_OBSERVADO_YYYY`, sem projeções nem metas |
| Diferença de recorte | inclui, no Saeb, os estudantes do médio propedêutico **e** da educação profissional técnica integrada ao médio; a divulgação regular exclui os do integrado para preservar a comparabilidade histórica (nota `*` da própria planilha) |
| Normalização | `processar_uf_em_integrado()` (08) → `data/interim/inep/ideb_uf_em_integrado_tidy.parquet`: 135 linhas (27 UFs × 5 anos), colunas `etapa` (`EM_integrado`), `local`, `local_base`, `rede`, `ano`, `indicador`, `valor`, `valor_bruto` |
| Nomes | três UFs mudam de forma entre as planilhas: `R. G. do Norte` ↔ `Rio Grande do Norte`, `R. G. do Sul` ↔ `Rio Grande do Sul`, `M. G. do Sul` ↔ `Mato Grosso do Sul`. `local` mantém o nome do arquivo; `local_base` normaliza, com o mapa em `UFS_POR_EXTENSO` no 08 |
| Resultado | DF `Estadual`: 3,7 em 2023 (18º de 27) e 3,6 em 2025 (**27º de 27**) — as mesmas posições do médio regular. A inclusão muda 10–11 UFs em 0,1–0,2, não o DF (`data/interim/q9_em_integrado.csv`) |
| Uso | `q9` de `06_analysis.py`; §2.4 do relatório cita os dois recortes lado a lado |

### `tx_rend_escolas_2025.zip` (INEP)

| Campo | Valor |
|---|---|
| Fonte | INEP — Taxas de Rendimento Escolar 2025 (`download.inep.gov.br/informacoes_estatisticas/indicadores_educacionais/2025/`), ingerido em 2026-10-22 pelo caminho manual |
| Conteúdo | `.xlsx`, `.ods` e `md5_tx_rend_escolas_2025.txt`; uma aba (`ESCOLAS`) |
| Granularidade | escola × etapa/série × categoria de rendimento (formato longo depois da normalização) |
| Chave primária | `CO_ENTIDADE` + `campo` (0 duplicatas) |
| Layout | 5 linhas de título, cabeçalho em três faixas (6–8), códigos na linha 9, dados da 10 em diante; 63 colunas |
| Campos | identificação `NU_ANO_CENSO`, `NO_REGIAO`, `SG_UF`, `CO_MUNICIPIO`, `NO_MUNICIPIO`, `CO_ENTIDADE`, `NO_ENTIDADE`, `NO_CATEGORIA` (localização), `NO_DEPENDENCIA`; 54 taxas `1_CAT_*` (aprovação), `2_CAT_*` (reprovação), `3_CAT_*` (abandono), nos recortes `FUN`, `FUN_AI`, `FUN_AF`, `FUN_01`…`FUN_09`, `MED`, `MED_01`…`MED_04`, `MED_NS` |
| Linhas lidas | 126.686 nacionais, 925 do DF (578 `Estadual`, 336 `Privada`, 11 `Federal`); as 925 casam com o cadastro de 2025 |
| Vocabulário | `'--'` = **não aplicável** (sem matrícula naquela etapa/série), `estado = nao_aplicavel`; célula vazia = `ausente`; `0` = zero real (abandono zero é comum). O texto fica em `valor_bruto` |
| Normalização | `processar_tx_rend()` (08) → `data/interim/inep/tx_rend_escolas_df.parquet`: 49.950 linhas longas, colunas `NU_ANO_CENSO`, `SG_UF`, `CO_MUNICIPIO`, `NO_MUNICIPIO`, `CO_ENTIDADE`, `NO_ENTIDADE`, `NO_CATEGORIA`, `NO_DEPENDENCIA`, `campo`, `categoria`, `recorte`, `valor`, `valor_bruto`, `estado` |
| Conferência | aprovação + reprovação + abandono = 100 em 7.412 pares escola × recorte (desvio máximo 1,4e-14) |
| Uso | `q10` de `06_analysis.py`; §2.2 do relatório |

### `TDI_2025_ESCOLAS.zip` (INEP)

| Campo | Valor |
|---|---|
| Fonte | INEP — Taxa de Distorção Idade-Série por Escola 2025 (`download.inep.gov.br/informacoes_estatisticas/indicadores_educacionais/2025/`), ingerida em 2026-10-22 pelo caminho manual |
| Conteúdo | 34.465.795 B; quatro membros: pasta `TDI_2025_ESCOLAS/`, `MD5_TDI_ESCOLAS_2025.txt`, `TDI_ESCOLAS_2025.ods` e `TDI_ESCOLAS_2025.xlsx` (18.462.946 B, o lido) |
| Aba | uma (`ESCOLAS`) |
| Layout | 8 linhas de título (faixas de cabeçalho nas 6–7), **códigos na linha 9**, dados da 10 em diante; 26 colunas com código |
| Campos | identificação `NU_ANO_CENSO`, `NO_REGIAO`, `SG_UF`, `CO_MUNICIPIO`, `NO_MUNICIPIO`, `CO_ENTIDADE`, `NO_ENTIDADE`, `NO_CATEGORIA` (localização), `NO_DEPENDENCIA`; 17 taxas no padrão `<recorte>_CAT_0`: `FUN`, `FUN_AI`, `FUN_AF`, `FUN_01`…`FUN_09`, `MED`, `MED_01`…`MED_04`. **Não tem `MED_NS`** — a TNR tem, e por isso o leitor não pode compartilhar a lista de colunas entre os dois arquivos |
| Granularidade | escola × recorte (uma taxa por célula; formato longo depois da normalização) |
| Chave primária | `CO_ENTIDADE` + `campo` (0 duplicatas) |
| Anos | 2025 apenas |
| Linhas lidas | 126.607 nacionais, 925 do DF (578 `Estadual`, 336 `Privada`, 11 `Federal`); as 925 casam com o cadastro de 2025 (`CO_ENTIDADE`, 100%, 0 fora) |
| Vocabulário | `'--'` = **não aplicável** (sem matrícula naquele recorte), `estado = nao_aplicavel`; célula vazia = `ausente`; `0` = zero medido e entra nas estatísticas. No DF: 7.920 `nao_aplicavel`, 1.787 zeros, 0 ausentes |
| Normalização | `processar_indicador_escola()` (08) → `data/interim/inep/tdi_escolas_df.parquet`: 15.725 linhas longas, colunas `indicador`, `NU_ANO_CENSO`, `NO_REGIAO`, `SG_UF`, `CO_MUNICIPIO`, `NO_MUNICIPIO`, `CO_ENTIDADE`, `NO_ENTIDADE`, `NO_CATEGORIA`, `NO_DEPENDENCIA`, `campo`, `recorte`, `valor`, `valor_bruto`, `estado` |
| Renomes | nenhum campo de origem renomeado; derivados `indicador` (`distorcao_idade_serie`), `recorte` (extraído do código), `valor` (numérico), `valor_bruto` (texto) e `estado` |
| Uso | `q11` de `06_analysis.py`; §2.2, §2.4 e §2.6 do relatório |
| Limite | taxa por escola, não ponderada por matrícula: a mediana descreve a escola típica da rede, não o aluno típico |

### `tnr_escolas_2025.zip` (INEP)

| Campo | Valor |
|---|---|
| Fonte | INEP — Taxa de Não-Resposta (TNR) por Escola 2025 (`download.inep.gov.br/informacoes_estatisticas/indicadores_educacionais/2025/`), ingerida em 2026-10-22 pelo caminho manual |
| Conteúdo | 30.600.051 B; quatro membros: pasta `tnr_escolas_2025/`, `md5_tnr_escolas_2025.txt`, `tnr_escolas_2025.ods` e `tnr_escolas_2025.xlsx` (17.727.021 B, o lido) |
| Aba | uma (`ESCOLAS`) |
| Layout | 8 linhas de título, **códigos na linha 9**, dados da 10 em diante; 27 colunas com código |
| Campos | as mesmas nove colunas de identificação da TDI; 18 taxas no padrão **`4_CAT_<recorte>`** — `FUN`, `FUN_AI`, `FUN_AF`, `FUN_01`…`FUN_09`, `MED`, `MED_01`…`MED_04`, `MED_NS`. A categoria (4 = não-resposta) vem antes do recorte; na TDI vem depois (`FUN_AI_CAT_0`). São padrões diferentes, e o leitor é parametrizado por eles |
| O que mede | percentual de alunos **sem informação de rendimento/movimento escolar** no Censo Escolar 2025. **Não é participação no SAEB** e não tem campo que separe não participação de resultado suprimido |
| Granularidade | escola × recorte |
| Chave primária | `CO_ENTIDADE` + `campo` (0 duplicatas) |
| Anos | 2025 apenas |
| Linhas lidas | 126.687 nacionais, 925 do DF (578 `Estadual`, 336 `Privada`, 11 `Federal`); as 925 casam com o cadastro de 2025 (100%, 0 fora) |
| Vocabulário | `'--'` = **não aplicável**, `estado = nao_aplicavel`; célula vazia = `ausente`; `0` = zero medido (não-resposta zero é comum). No DF: 8.845 `nao_aplicavel`, 3.545 zeros, 0 ausentes |
| Normalização | `processar_indicador_escola()` (08) → `data/interim/inep/tnr_escolas_df.parquet`: 16.650 linhas longas, mesmo esquema de `tdi_escolas_df.parquet`, com `indicador = 'taxa_nao_resposta'` |
| Hipótese testada | o catálogo previa que a TNR dissesse, por escola, se o Ideb ausente é não participação ou resultado suprimido. **Falhou:** a TNR não tem esse campo, e as distribuições das escolas com e sem Ideb se sobrepõem (medianas 1,3 × 1,3 nos anos iniciais, 1,9 × 2,5 nos finais, 2,0 × 1,8 no médio; as sem Ideb são 39, 34 e 32 escolas com taxa). O que ela acrescenta é a distinção `'--'` = etapa não ofertada, confirmada pelo cadastro em 42 de 44 e 37 de 38 casos |
| Uso | `q12` de `06_analysis.py`; §2.2, §2.4 e §5 do relatório |

### `nota_informativa_ideb_2025.pdf` (INEP)

| Campo | Valor |
|---|---|
| Fonte | INEP — Nota informativa do Ideb 2025 (`download.inep.gov.br/ideb/resultados/`), ingerida em 2026-10-22 |
| Granularidade | documento (8 páginas), não é tabela; lido manualmente, não convertido |
| Fatos usados | metodologia inalterada desde 2007; 2023 e 2025 comparáveis às edições anteriores e **sem metas**; última divulgação na formulação original (a próxima edição quebra a série) |
| Critérios de não-cálculo | Portaria nº 435/2025: (H) menos de 10 estudantes presentes no SAEB; (I) participantes abaixo de 80% dos matriculados na etapa. O Quadro 1 do documento dá o número de escolas com e sem Ideb por motivo |
| Uso no relatório | base da regra de três estados: escola sem Ideb é ausência com causa declarada, nunca zero |

### `microdados_censo_escolar_2024.zip`, `microdados_censo_escolar_2025_.zip` (INEP — Censo Escolar)

| Campo | Valor |
|---|---|
| Fonte | INEP — Microdados do Censo Escolar da Educação Básica, download manual pelo navegador (o `download.inep.gov.br` reseta a conexão de `urllib`/`curl` neste ambiente); ingeridos em 2026-10-23 por `07_ingest_inep.py` |
| Arquivos | `data/raw/inep/2026-10-23_microdados_censo_escolar_2024.zip` (33.829.396 B) e `..._2025_.zip` (537.217.189 B). O sublinhado final do segundo é do nome que veio do servidor e foi preservado |
| Conteúdo do zip | 2024: `dados/microdados_ed_basica_2024.csv` (217.925.280 B, 426 colunas) e `suplemento_cursos_tecnicos_2024.csv`; 2025 (v2): `Tabela_Matricula_2025_V2.csv` (123.318.048 B, 263 colunas), `Tabela_Escola`, `Tabela_Docente`, `Tabela_Turma`, `Tabela_Gestor`, `Tabela_Curso_Tecnico`, cada uma com o seu dicionário na aba correspondente do Anexo I |
| **Grão** | **uma linha por estabelecimento de ensino**, não por aluno — ver "A publicação mudou de grão em 2024" |
| Chave | `CO_ENTIDADE` (0 duplicatas no DF nas duas edições) |
| Leitura | `scripts/11_ingest_censo.py`: zip aberto em memória, CSV em streaming, filtro `CO_UF == '53'`, nada do nacional materializado. Filtro por UF porque as duas tabelas têm `CO_UF` (não foi preciso usar o conjunto de códigos do cadastro) |
| Linhas lidas | 2024: 215.545 nacionais, 1.360 do DF (0,63%); 2025: 178.766 e 1.291 (0,72%) |
| Escolas no DF | 2024: 1.360 linhas, das quais **76 com a célula de matrícula vazia** (existência sem aluno declarado: CEEs, escolas extintas/paralisadas, unidades sem matrícula) — **ausente, não zero**; 1.284 com matrícula, o mesmo conjunto da série da SEEDF. 2025: 1.291, todas com matrícula, o mesmo conjunto do cadastro |
| Saída | `data/interim/inep/censo_escola_df.parquet` (2.651 linhas = 1.360 + 1.291; 137.688 B) e `data/interim/inep/censo_metodo.csv` (as checagens) |
| Encoding e separador | os dois são `latin-1` com `;` — detectados, não assumidos: a primeira passagem tenta `utf-8` e recomeça em `latin-1` quando um byte falha (o cabeçalho dos dois arquivos é ASCII puro e não denuncia o encoding do corpo) |
| Renomes | nenhum campo de origem renomeado; derivados `ano` (do arquivo, não de coluna), `rede` (de `TP_DEPENDENCIA`: 1 Federal, 2 Estadual, 3 Municipal, 4 Privada — o mesmo vocabulário de `NO_DEPENDENCIA` na TDI/TNR) |
| Colunas usadas | `CO_ENTIDADE`, `NO_ENTIDADE`, `CO_UF`, `SG_UF`, `CO_MUNICIPIO`, `TP_DEPENDENCIA`, `TP_CATEGORIA_ESCOLA_PRIVADA`, `TP_SITUACAO_FUNCIONAMENTO` (só 2024), `QT_MAT_BAS`, `QT_MAT_INF`, `QT_MAT_INF_CRE`, `QT_MAT_INF_PRE`, `QT_MAT_FUND`, `QT_MAT_FUND_AI`, `QT_MAT_FUND_AF`, `QT_MAT_MED`, `QT_MAT_MED_PROP`, `QT_MAT_MED_NM`, `QT_MAT_MED_CT` (só 2024), `QT_MAT_PROF_TEC_CONC`, `QT_MAT_PROF_TEC_SUBS`, `QT_MAT_PROF_FIC_CONC`, `QT_MAT_EJA`, `QT_MAT_ESP`, `QT_MAT_BAS_0_3`, `QT_MAT_BAS_4_5`, `QT_MAT_BAS_6_10`…`QT_MAT_BAS_18_MAIS`, `QT_MAT_BAS_0_3_REF_31_03` e `QT_MAT_BAS_4_5_REF_31_03` (só 2025) |
| Idempotência | reescreve os parquets a partir do raw; duas execuções geram bytes idênticos; não acessa a rede |

**A publicação mudou de grão em 2024 — e isso muda o que se pode perguntar.** O
manual do usuário de 2024 diz que as bases passaram a ser "dimensionadas ao nível
de escolas" e trazem matrícula por etapa, turno, tempo integral, sexo, cor/raça e
faixa etária. **Não existe linha de aluno, `DT_NASCIMENTO` nem idade simples** em
nenhuma das duas edições — conferido no cabeçalho das duas tabelas, e registrado
em `censo_metodo.csv`. Consequências para o projeto:

- O recorte é escola × etapa. Nenhuma linha de estudante sai deste script, e não
  há parquet intermediário por pessoa a excluir: a fonte já é agregada.
- **Idade simples só existe na série da SEEDF** (bloco `relatorio_matriculas_*`),
  que republica o Censo. Do lado da INEP, o que há é faixa etária.
- As faixas `QT_MAT_BAS_0_3` etc. **não são idade no ano**: são idade na data de
  referência do Censo. Em 2025 o dicionário declara duas referências e publica as
  duas colunas: `QT_MAT_BAS_0_3` (última quarta-feira de maio, 28/05/2025) e
  `QT_MAT_BAS_0_3_REF_31_03` (31/03, Resolução CNE/CEB nº 05/2009). No DF:
  39.293 e 42.945, 3.652 a mais em 31/03 (+9,3%) — a mesma criança conta em uma faixa
  e não na outra. Em 2024 o dicionário **não declara** a referência e só a de maio
  é publicada; o teste que a identifica está em "Qual é a data de referência de
  2024".

**Qual é a data de referência de 2024.** O arquivo de 2024 não diz, então a
resposta é medida (`q14_creche_referencia.csv`). Nas escolas que só têm creche,
toda a matrícula é de criança pequena, e a razão faixa 0–3 / creche mede a
proporção de alunos com ≤ 3 anos na data da faixa. Se a faixa fosse em 31/03 essa
razão seria ~100%, porque creche não tem criança de 4 anos em 31/03; se for na
data do Censo (maio), fica abaixo disso porque parte da turma fez 4 anos entre
abril e maio:

| Edição | Referência | Escolas só de creche | Razão faixa 0–3 / creche |
|---|---|---|---|
| 2024 | não declarada no dicionário | 119 | **91,4%** |
| 2025 | última quarta-feira de maio | 141 | **92,7%** |
| 2025 | 31/03 | 141 | **99,9%** |

A edição de 2024 se comporta como a de maio (91,4% ≈ 92,7%), não como a de 31/03
(99,9%). É inferência, e está declarada como inferência: o que é fato é que a
faixa de 2024 não é idade no ano (37.595 contra 26.076 de creche × idade ≤ 3) e
que as duas referências de 2025 diferem em 9,3%.

**Conferência das âncoras.** O script para se o recorte não reproduzir o que o
projeto já publica: creche 2024 = 40.851 e creche 2025 = 42.582 (exatos), 1.284 e
1.291 escolas com matrícula (exatos), e as seis faixas etárias somando
`QT_MAT_BAS` em 1.284 de 1.284 e 1.291 de 1.291 escolas. Tolerância de 0,5%; acima
disso, erro de leitura, não de fonte.

### `censo_escola_df.parquet` (recorte do DF, derivado)

| Campo | Valor |
|---|---|
| Gerado por | `scripts/11_ingest_censo.py` a partir dos dois zips acima |
| Grão | escola × ano (2.651 linhas: 1.360 em 2024, 1.291 em 2025) |
| Conteúdo | as colunas de identificação e de matrícula listadas acima, em formato largo, mais `ano` e `rede` |
| Uso | peso das taxas por escola em `q13_ponderacao_df.csv`; oferta de creche e faixas etárias em `q14_creche_*.csv`; conferência da série da SEEDF em `q15_conferencia_censo.csv` |
| Limite | não tem RA nem geometria: a tabela da INEP traz `CO_DISTRITO`/`CO_SUBDISTRITO`, que não são Regiões Administrativas. Todo recorte territorial deste projeto continua vindo do cadastro da SEEDF |

## Chaves e cruzamentos

Taxas medidas por `scripts/04_crosswalk.py`, chave `CO_ENTIDADE`. "Órfãos em
para" = códigos no outro arquivo que não existem no cadastro daquele ano.

| De → Para | Campo de origem | Campo de destino | Casados | Taxa | Órfãos notáveis |
|---|---|---|---|---|---|
| escolas 2024 → matrículas 2024 | `CO_ENTIDADE` | `CO_ENTIDADE` | 1.284 de 1.284 | 100% | 0 |
| escolas 2025 → matrículas 2025 | `CO_ENTIDADE` | `Código INEP` | 1.291 de 1.291 | 100% | 41 no arquivo de matrículas (escolas fora do cadastro de 2025) |
| escolas 2023 → matrículas 2023 | `CO_ENTIDADE` | `CO_ENTIDADE` | 600 de 1.264 | 47,5% | o arquivo de 2023 só tem rede pública |
| escolas 2024 → infraestrutura 2024 | `CO_ENTIDADE` | `CO_ENTIDADE` | 1.284 de 1.284 | 100% | 41 |
| escolas 2025 → infraestrutura 2025 | `CO_ENTIDADE` | `CO_ENTIDADE` | 1.291 de 1.291 | 100% | 180 (inclui paralisadas e extintas) |
| escolas 2025 → situação 2025 | `CO_ENTIDADE` | `CO_ENTIDADE` | 604 de 1.291 | 46,8% | a situação só cobre a rede estadual |
| escolas 2023 → situação 2023 | `CO_ENTIDADE` | `CO_ENTIDADE` | 658 de 1.264 | 52,1% | idem |
| escolas 2025 → IDEB 2025 (AI) | `CO_ENTIDADE` | `cod_inep` | 615 de 1.291 | 47,6% | 9 códigos no IDEB sem cadastro em 2025 |
| escolas 2023 → IDEB 2023 (AI) | `CO_ENTIDADE` | `cod_inep` | 613 de 1.264 | 48,5% | 11 |
| escolas 2023 → unidades EI 2023 | `CO_ENTIDADE` | `CO_ENTIDADE` | 445 de 1.264 | 35,2% | 20 |
| escolas 2025 → TDI 2025 | `CO_ENTIDADE` | `CO_ENTIDADE` | 925 de 925 | 100% | 0 no arquivo da INEP; das 366 escolas do cadastro sem linha, 364 não ofertam fundamental nem médio e 2 ofertam (uma estadual, uma conveniada) |
| escolas 2025 → TNR 2025 | `CO_ENTIDADE` | `CO_ENTIDADE` | 925 de 925 | 100% | idem |
| escolas 2024 → Censo 2024 | `CO_ENTIDADE` | `CO_ENTIDADE` | 1.284 de 1.284 | 100% | 0; o Censo lista 76 escolas do DF a mais, todas com matrícula vazia |
| escolas 2025 → Censo 2025 | `CO_ENTIDADE` | `CO_ENTIDADE` | 1.291 de 1.291 | 100% | 0 |
| TDI/TNR/fluxo 2025 → Censo 2025 | `CO_ENTIDADE` | `CO_ENTIDADE` | 925 de 925 | 100% | 0 — todas as escolas com taxa têm peso de matrícula (`q13_ponderacao_df.csv`) |
| Ideb 2025 (por escola) → Censo 2025 | `ID_ESCOLA` | `CO_ENTIDADE` | 624 de 624 | 100% | 0 |
| Ideb 2025 (por escola) → TNR 2025 | `ID_ESCOLA` | `CO_ENTIDADE` | 611 de 624 | 97,9% | 13 fora da TNR: 8 estaduais de iniciais, 2 de finais e 5 privadas de médio; 9 dessas 13 também não estão no cadastro de 2025; 615 de 624 estão |

Leitura: a chave não é o problema — `CO_ENTIDADE` casa 100% quando os dois
arquivos cobrem o mesmo universo. As taxas baixas medem **cobertura**, não falha
de chave. Nenhum join nesta sessão foi feito sem taxa medida. As 925 escolas da
TDI/TNR são exatamente as que ofertam fundamental ou médio em 2025: 575 de 576
estaduais, 336 de 337 privadas e 11 de 11 federais — as duas sem linha são uma
estadual e uma conveniada.

### Nomes de Região Administrativa

36 valores no cadastro de 2025 para 35 RAs (a PDAD-A e o GDF usam 35). Fontes
escrevem diferente e é preciso normalizar. A regra única está em
`_common.norm_ra` (maiúscula, sem acento, espaço simples, sem numeral romano de
prefixo, e a tabela `TROCAS_RA`): os scripts 05, 06 e 10 usam a mesma função, e
nenhum cruzamento por nome de RA passa por outra regra.

| Cadastro SEEDF | PDAD-A 2024 | Normalizado |
|---|---|---|
| `SOL NASCENTE / POR DO SOL` | `SOL NASCENTE E PÔR DO SOL` | `SOL NASCENTE / POR DO SOL` |
| `SUDOESTE / OCTOGONAL` | `SUDOESTE/OCTOGONAL`, `Sudoeste e Octogonal` | `SUDOESTE / OCTOGONAL` |
| `SCIA` | `SCIA/ESTRUTURAL`, `SCIA` | `SCIA` |
| `AGUAS CLARAS ` (com espaço) | `XX - ÁGUAS CLARAS` | `AGUAS CLARAS` |
| — (não existe no cadastro) | `Área Rural`, `Distrito Federal (Área rural)` | `AREA RURAL` |

`AREA RURAL` é a única localidade da PDAD sem par no cadastro da SEEDF: 121.759
moradores e 7.115 crianças de 0–3, sem escola estadual cadastrada com essa RA.
Ela aparece nas tabelas de população e frequência e fica **fora** dos
cruzamentos com matrícula por escola — declarada, não preenchida com zero.

## Mudanças de esquema entre anos

| Arquivo | Ano | O que mudou |
|---|---|---|
| escolas | 2025 | 74 → 81 colunas; nomes de variável → rótulos legíveis; nova coluna `Tipologia`; linha de título acima do cabeçalho |
| escolas | 2014–2023 | esquema estável em 74 colunas |
| matrículas | 2024 | 64 → 63 colunas (sai uma coluna `MAT_*`) |
| matrículas | 2025 | 73 colunas com rótulos legíveis; `Código INEP` no lugar de `CO_ENTIDADE`; só em XLSX |
| matrículas | 2023 | arquivo parcial: apenas rede pública (600 escolas contra ~1.280 nos demais anos); coluna extra `MATRÍCULA` |
| infraestrutura | 2016 | arquivo rotulado 2016 contém 2017 e é idêntico ao de 2017 — **2016 não existe** |
| infraestrutura | 2025 | 114 → 289 colunas; inclui escolas paralisadas/extintas; `TP_DEPENDENCIA` deixa de separar conveniada |
| situação | 2025 | 73 → 27 colunas; só totais por escola (2.421 linhas contra ~72.000) |
| situação | 2019 | 126.672 linhas contra ~72.000 nos demais anos; inclui rede federal |
| distorção | 2024 | nomes de variável → rótulos legíveis, duas linhas de cabeçalho, 30 → 26 colunas |
| IDEB | — | cabeçalho e separador diferentes entre anos iniciais (`;`, `cod_inep`) e anos finais/médio (`,`, `Cód_Inep`) |
| Censo Escolar | 2024 | **muda o grão**: de aluno para estabelecimento; um CSV (`microdados_ed_basica_2024.csv`, 426 colunas) no lugar da base por aluno, sem `DT_NASCIMENTO` e sem idade simples |
| Censo Escolar | 2025 | arquivo e nome mudam (`Tabela_Matricula_2025_V2.csv`, 263 colunas, versão v2); sai `QT_MAT_MED_CT` e o médio integrado passa a `QT_MAT_MED_IFTP_CT` (recorte diferente, não renomeação); entram `QT_MAT_BAS_*_REF_31_03`; `TP_SITUACAO_FUNCIONAMENTO` sai da tabela de matrícula e fica só na de escola |

## INEP: catálogo e o que entrou

Catálogo declarado em `scripts/07_ingest_inep.py`; a ingestão é manual porque
`download.inep.gov.br` bloqueia o `urllib`/`curl` deste ambiente e responde pelo
navegador. `data/raw/inep/inbox/` recebe os arquivos, 07 registra procedência e
sha256 no `MANIFEST.md`, 08 perfila o conteúdo e normaliza. Doze entraram e têm
bloco próprio acima; não falta nenhum item do catálogo. Os dois últimos são lidos
por `11_ingest_censo.py`, não pelo 08: são grandes demais para perfil e o recorte
tem de acontecer em streaming.

| Arquivo | O que acrescenta | Situação |
|---|---|---|
| `divulgacao_regioes_ufs_ideb_2025.zip` | Ideb por UF: situa o DF no país | **ingerido** (2026-10-22) |
| `nota_informativa_ideb_2025.pdf` | metodologia e escala do Ideb 2025 | **ingerido** (2026-10-22, 551.360 B) |
| `divulgacao_brasil_ideb_2025.zip` | Ideb do Brasil (a planilha de UF não tem a linha Brasil) | **ingerido** (2026-10-22) |
| `divulgacao_ufs_Ensino_Medio_integrado_ideb_2025.xlsx` | ensino médio **com o integrado à EPT**, rede estadual por UF: testa o último lugar do DF no médio regular | **ingerido** (2026-10-22, 31.398 B) |
| `divulgacao_anos_iniciais_escolas_2025.zip` | Ideb por escola, todas as redes (AI) | **ingerido** (2026-10-22) |
| `divulgacao_anos_finais_escolas_2025.zip` | idem, anos finais | **ingerido** (2026-10-22) |
| `divulgacao_ensino_medio_escolas_2025.zip` | idem, ensino médio | **ingerido** (2026-10-22) |
| `tx_rend_escolas_2025.zip` | aprovação/reprovação/abandono por escola, todas as redes | **ingerido** (2026-10-22, 66.870.247 B) |
| `TDI_2025_ESCOLAS.zip` | distorção idade-série por escola, todas as redes | **ingerido** (2026-10-22, 34.465.795 B) |
| `tnr_escolas_2025.zip` | taxa de não-resposta por escola; **não** distingue não participação de supressão (ver bloco) | **ingerido** (2026-10-22, 30.600.051 B) |
| `microdados_censo_escolar_2024.zip` | matrícula por escola × etapa e faixa etária, todas as redes; confere a série da SEEDF de 2024 | **ingerido** (2026-10-23, 33.829.396 B) |
| `microdados_censo_escolar_2025_.zip` | o peso das taxas por escola de 2025 e as duas datas de referência da faixa etária | **ingerido** (2026-10-23, 537.217.189 B) |

Chave de ligação com o que já existe: `CO_ENTIDADE`. A INEP nem sempre usa esse
nome (`CO_ESCOLA` aparece em indicadores por escola) — conferir no cabeçalho e
registrar aqui antes de qualquer join. Nenhum join com a INEP é feito sem taxa de
casamento medida, como os demais. Os três arquivos de Ideb por escola usam
`ID_ESCOLA` (o mesmo código de 8 dígitos); a ligação com o cadastro de 2025 foi
medida em `data/interim/q8_cobertura_escolas_2025.csv`. A TDI e a TNR usam
`CO_ENTIDADE`: 925 de 925 escolas do DF casadas (100%, 0 fora) com o cadastro de
2025, medido por `medir_juncao_cadastro()` no 08 a cada execução.

O Censo Escolar usa `CO_ENTIDADE` e casa 1.284 de 1.284 (2024) e 1.291 de 1.291
(2025); as 76 escolas que a edição de 2024 lista a mais têm matrícula vazia e
ficam fora de qualquer soma. As 925 escolas com TDI/TNR têm peso de matrícula em
2025 — medido em `q13_ponderacao_df.csv`, não suposto.

## Artefatos de execução e de presença (2026-11-06)

Dois CSVs de `data/interim/` não são resposta de pergunta, são controle:

| arquivo | grão | colunas | para que serve |
|---|---|---|---|
| `q0_execucao.csv` | etapa (`q1`…`q16`) | `etapa`, `status` (`executado`/`pulado`), `motivo`, `segundos` | prova que `06_analysis.py` rodou inteiro; `main()` sai com 1 se alguma etapa pulou, a menos de `--parcial` |
| `q16_presenca_escola_etapa.csv` | escola × etapa (anos iniciais, finais, médio) | `co_entidade`, `rede`, `etapa`, `oferta_seedf`, `matriculas_censo_2025`, `ideb_2025`, `ideb_estado`, `tdi_2025`, `tdi_estado`, `tnr_2025`, `tnr_estado`, `aprovacao_2025`, `aprovacao_estado` | a matriz de presença e o denominador de n de cada indicador; é a base do contrato de `docs/FASE-1.md` |
| `q16_faixas_n.csv` | etapa × faixa de n | `unidades`, `n_min`, `n_mediana`, `n_max`, `tdi_zero_pct`, `aprovacao_100_pct`, `wilson_hw_p10_pp` | a evidência do limiar de n pequeno (D4 = 30) |

A etapa entra na matriz quando o vetor de oferta da SEEDF diz 1 **ou** quando o
Censo declara matrícula maior que zero: a divergência fica visível em
`oferta_seedf`, não resolvida. Indicador sem linha para uma etapa ofertada entra
como `ausente`; o estado que veio da fonte é copiado como está (L-59).

## Insumo publicado do site (`data/public/`, 2026-11-09)

Quatro arquivos gerados por `scripts/06_analysis.py --public data/public` a
partir de `data/interim/`; nenhum tem microdado ou linha de aluno. O build
`scripts/12_build_site.py` lê **só** esta pasta e confere o sha256 registrado em
`procedencia.json`.

| arquivo | grão | colunas | regra |
|---|---|---|---|
| `escolas.parquet` | escola (1.291) | `co_entidade`, `nome`, `ra`, `rede`, `rede_cadastro`, `censo_2024_presente`, `oferta_inf_cre`…`oferta_prof` (8 flags), `mat_inf_cre_2024`…`mat_med_2025` (8 matrículas) | `ra` normalizada por `norm_ra`; `rede` é a categoria do site (`federal`, `estadual`, `privada conveniada`, `privada não conveniada`) e `rede_cadastro` guarda o `Nome Rede` original. `censo_2024_presente` é `True` quando o `CO_ENTIDADE` tem linha no Censo 2024 e `False` quando não tem: as 53 escolas de 2025 sem linha ficam com a flag `False` e as quatro matrículas de 2024 nulas; as 3 com linha e células vazias ficam com a flag `True` e as células nulas (L-28, L-63). Matrícula vem do Censo 2024–2025, nunca da série ODbL da SEEDF (L-62) |
| `indicadores.parquet` | escola × etapa × indicador × ano | `co_entidade`, `etapa` (`AI`/`AF`/`EM`), `indicador` (`ideb_observado`, `tdi`, `tnr`, `aprovacao`, `reprovacao`, `abandono`), `ano`, `valor`, `estado` | só `FUN_AI`, `FUN_AF` e `MED`; `ideb_projetado` fica fora; `estado` é copiado da fonte e nunca deduzido de `NaN` (L-59) |
| `infraestrutura.parquet` | escola × item (8 itens) | `co_entidade`, `item`, `ano`, `valor` (0/1), `estado` | universo das 927 escolas que oferecem ensino fundamental ou médio; não há linha para as demais, e a página mostra o bloco como `nao_aplicavel` (L-25) |
| `procedencia.json` | família de indicador | `familia`, `bloco`, `fonte`, `arquivo`, `anos`, `calculo`, `limites`, `licenca`, `licenca_url`; topo com `sha256` dos três parquets e `execucao.etapas_puladas` | uma família por bloco do contrato; o build usa fonte, limites e licença daqui. A licença SEEDF vem de `license_title`/`license_url` do conjunto no inventário do CKAN; a INEP declara "público, sem licença declarada no portal", com URL nula. O export falha antes de gravar se uma família SEEDF resolver para ODbL (L-62). `execucao.etapas_puladas` é vazio na execução completa e só é preenchido com `--parcial` |

Tamanhos medidos em 2026-11-09: `escolas.parquet` 61 KB, `indicadores.parquet`
40 KB, `infraestrutura.parquet` 13 KB e `procedencia.json` 4.7 KB.

No `site/dados/<CO_ENTIDADE>.json`, cada número traz `n` inteiro ou `null`.
`n = null` ocorre quando a matrícula que serviria de denominador não existe
(famílias Ideb, fluxo, TDI e TNR); nas taxas o número é `ausente`, e o Ideb, se
existir, mantém o valor observado com `n: null`. A página mostra a matrícula `-`.
`n_referencia` só aparece quando o `n` é contagem de alunos de outro ano: o Ideb
de 2005–2023 leva `"n_referencia": "2025"`; Ideb de 2025, matrícula, creche,
oferta e infraestrutura não levam o campo. O `n = 1` dessas quatro últimas
famílias é a escola, não uma contagem de alunos.

O export é determinístico e idempotente. Se o destino já tem um arquivo com
sha256 diferente do que seria gravado, ele falha; `--force` sobrescreve e a
mudança aparece no diff. O build não usa `datetime.now()`: o único carimbo é
`--data-build`.
