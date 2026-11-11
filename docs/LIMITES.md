# LIMITES.md — registro de limites, ausências, suposições e riscos de leitura

Os ids `L-01`, `L-02`… são citáveis e estáveis: não se reutilizam. Nenhum número
deste projeto deve ser lido sem os ids que o limitam — a seção "onde pesa" diz
qual frase, tabela ou arquivo depende do item. O registro separa **limite da
fonte** (o dado não existe ou não tem o campo), **ausência** (o campo existe e
falta o valor), **suposição** (convenção adotada pelo projeto), **inferência**
(conclusão tirada de evidência indireta), **risco de leitura** (o número muda se
a leitura mudar) e **escopo** (decisão de não fazer).

Item fechado continua no registro com a data e a evidência que o fechou; item
estrutural não é dívida e diz "nada — é limite da fonte". Hipótese derrubada é
veredito (`REPORT.md` §3), não limite: por isso C-02 e C-06 não aparecem como
risco aberto. O registro não introduz número novo: todo valor citado existe em
`REPORT.md`, `SCHEMA.md` ou nos CSVs que eles citam.

| id | item | tipo | onde pesa | evidência | status | o que resolveria |
|---|---|---|---|---|---|---|
| L-01 | A série de matrículas da SEEDF não reproduz o Censo 2024 em EJA e educação profissional; a causa não é determinável nas tabelas por escola | limite-da-fonte | REPORT §2.7(c), tabela de conferência; toda frase sobre EJA e técnico | `data/interim/q15_conferencia_censo.csv`; REPORT §2.7(c); worklog 2026-10-23-02 §5(c) | aberto | base por aluno (Sedap, acesso restrito) ou resposta da SEEDF sobre o extrato; nada por download aberto |
| L-02 | A ponderação cobre só as escolas com valor: o Ideb por escola cobre 89,6% da matrícula de anos iniciais da estadual, 82,3% nos finais e 64,8% no médio | limite-da-fonte | REPORT §2.7(a), tabela de ponderação; leitura do médio estadual | `data/interim/q13_ponderacao_df.csv`; REPORT §2.7(a) | aberto | nada — é cobertura da fonte; declarar a cobertura junto de cada média |
| L-03 | Desde 2024 a INEP publica por estabelecimento: não há linha de aluno, `DT_NASCIMENTO` nem idade simples | limite-da-fonte | REPORT §2.7 e §5; toda promessa de idade exata | SCHEMA, bloco dos microdados do Censo; `data/interim/inep/censo_metodo.csv` | aberto (estrutural) | nada — é limite da fonte; a base por aluno só existe no Sedap, com acesso restrito |
| L-04 | O Censo não tem Região Administrativa: traz `CO_DISTRITO`/`CO_SUBDISTRITO`, que não são RA | limite-da-fonte | REPORT §2.7; qualquer recorte territorial | SCHEMA, bloco `censo_escola_df.parquet`; worklog 2026-10-23-02 §6 | aberto (estrutural) | nada — é limite da fonte; todo recorte territorial continua vindo do cadastro da SEEDF |
| L-05 | A URL dos dois zips do Censo no `MANIFEST` era a canônica do diretório (`/microdados/`), não verificada, e responde 404; o `.xlsx` do médio integrado registrado não é o do servidor (31.398 B locais contra 31.594 B; conteúdo idêntico célula a célula, 2.430 células) | risco-de-leitura | procedência de todo número do Censo 2024/2025 e do médio integrado | `curl -skI` em 2026-11-06: `/dados_abertos/microdados_censo_escolar_2024.zip` 200/33.829.396 B e `..._2025_.zip` 200/537.217.189 B; `MANIFEST.md` → Correções, 2026-11-06 | fechado (2026-11-06) | nada — as URLs foram corrigidas em `07_ingest_inep.py`; o resíduo de sha256 do zip de 2025 está em L-61 |
| L-06 | `11_ingest_censo.py` interrompe com 0,5% de desvio nas âncoras; um erro de leitura menor que isso passaria | risco-de-leitura | todos os totais do Censo; âncoras 40.851 / 42.582 / 1.284 / 1.291 | `scripts/11_ingest_censo.py` (tolerância de 0,5%); `data/interim/inep/censo_metodo.csv`; `data/interim/q15_conferencia_censo.csv` | aberto | tolerância zero para as âncoras conhecidas ou conferência célula a célula; o argumento contra é q15 casar creche, EMI e EE em 1.284 de 1.284 |
| L-07 | O Censo é a mesma operação estatística que a SEEDF republica; concordância entre as duas não é confirmação independente | limite-da-fonte | REPORT §2.7(c); qualquer frase "a SEEDF confere com a INEP" | SCHEMA, bloco `relatorio_matriculas_*` (Fonte: microdados do Censo filtrados); REPORT §2.7(c) | aberto (estrutural) | nada — é a mesma operação; uma fonte independente (Sedap/base por aluno) seria necessária |
| L-08 | A INEP não publica Ideb por escola da rede privada depois de 2017 | ausencia | REPORT §5, primeiro item; README, "O que falta"; §2.4 | `data/interim/q8_escolas_rede.csv`; SCHEMA, bloco dos três zips por escola; REPORT §2.4 | aberto | mudança na divulgação da INEP; não há download que resolva hoje. O agregado privado por UF existe; falta a distribuição entre escolas |
| L-09 | A ausência de Ideb por escola não distingue não participação, participação abaixo do critério da Portaria nº 435/2025 e resultado não publicado; a TNR também não separa | limite-da-fonte | REPORT §2.4 e §5; `q12`; qualquer explicação de Ideb ausente | SCHEMA, blocos do Ideb por escola e da TNR; `data/interim/q12_tnr_ideb_ausente.csv` | aberto (estrutural) | nada — a fonte não tem o campo. Não confundir com C-06: a hipótese "a TNR explica" foi derrubada; o limite da TNR permanece |
| L-10 | A planilha de Ideb por UF tem ausências que mudam o denominador: Roraima não tem rede estadual em 2025 (26 UFs) e a aba do médio não publica "Pública" | limite-da-fonte | REPORT §2.4, tabela DF × Brasil × UFs; "16º de 26" e a comparação pública no médio | SCHEMA, bloco `divulgacao_regioes_ufs_ideb_2025.zip`; worklog 2026-10-22-04 §3 | aberto | nada — é a publicação da INEP; declarar o denominador em cada posição |
| L-11 | As taxas por escola da INEP (`tx_rend`, TDI, TNR) são de 2025 apenas; não há série histórica nesta entrega | limite-da-fonte | REPORT §2.2 e §2.4; qualquer tendência de fluxo, distorção ou não-resposta | SCHEMA, blocos `tx_rend_escolas_2025.zip`, `TDI_2025_ESCOLAS.zip`, `tnr_escolas_2025.zip`; worklogs 2026-10-22-07 §5 e 2026-10-22-08 §5 | aberto | ingerir as edições anteriores dos mesmos arquivos, se publicadas |
| L-12 | A próxima edição do Ideb quebra a série: 2025 é a última na formulação original | limite-da-fonte | REPORT §2.4; qualquer comparação futura 2025→2027 | SCHEMA, bloco `nota_informativa_ideb_2025.pdf`; REPORT §2.4 | aberto | nada — decisão metodológica da INEP; declarar a quebra quando a próxima edição sair |
| L-13 | Há anos parciais na série da SEEDF: matrículas 2023 só rede pública (600 escolas), situação 2025 só totais (2.421 linhas) e situação 2019 inclui a federal (126.672 linhas) | limite-da-fonte | REPORT §2.6; qualquer série histórica que atravesse 2019, 2023 ou 2025 | REPORT §2.6; SCHEMA, blocos `relatorio_matriculas_*` e `relatorio_situacao_aluno_*`; worklog 2026-10-22-02 §3 | aberto | publicação completa pela SEEDF; nada por download |
| L-14 | 2016 de infraestrutura não existe: o arquivo rotulado 2016 contém 2017 e é idêntico a ele (1.124 linhas) | ausencia | REPORT §2.6 e §5; série de infraestrutura 2014–2025 | SCHEMA, bloco `relatorio_infraestrutura_*`; REPORT §2.6; worklog 2026-10-22-02 §3 | aberto | contato institucional; nenhum dado aberto substitui |
| L-15 | 277 códigos de escola somem da série 2014–2025 sem motivo declarado | limite-da-fonte | REPORT §2.6 e §5; churn de unidades | `data/interim/q6_unidades_churn.csv`; REPORT §2.6; worklog 2026-10-22-03 §2 (q6) | aberto | contato institucional com a SEEDF; nenhum dado aberto substitui |
| L-16 | `download.inep.gov.br` serve cadeia TLS incompleta (emissor RNP ICPEdu: `curl` sem `-k` sai 60, `openssl s_client` dá "unable to verify the first certificate", código 21); não é bloqueio da fonte nem `connection reset` | limite-do-ambiente | reprodução de todo número da INEP; README "Fontes"; AGENTS "Workflow" | `curl -skI` em 2026-11-06; download retomado com `curl -sk -C -` completou 33.829.396 B e o sha256 `ae29d81d…d640db` é igual ao do `MANIFEST` | aberto (estrutural) | cadeia de certificados completa no servidor, ou CA da RNP instalada; até lá o caminho é `curl -sk` com conferência de sha256, declarado |
| L-17 | A PDAD é estimativa amostral: a variância é aproximada (Kish, sem estrato nem unidade primária) e o n por RA e faixa é pequeno (0–3: 14 a 184 pessoas; meio-intervalo de 6 a 36 p.p.) | limite-da-fonte | REPORT §2.5 e §5; as taxas e totais por RA da PDAD; o total do DF tem desvio de 0,01% e não é o problema | SCHEMA, bloco dos microdados da PDAD (linhas Variância e Limite); `data/interim/pdad/pdad_metodo.csv` | aberto | PDAD com estrato e unidade primária, ou agregado por setor censitário com chave setor→RA; nada no arquivo atual |
| L-18 | A renda domiciliar da PDAD não é usável: `renda_domiciliar_pc_r` é 99999 em 78,7% dos domicílios, com cobertura válida de 6,7% a 33,9% por RA | limite-da-fonte | nenhum número atual; qualquer análise de renda futura | SCHEMA, bloco dos microdados da PDAD (Sentinela); worklog 2026-10-23-01 §6 | aberto | nada no arquivo publicado; uma PDAD com imputação documentada ou outra fonte de renda |
| L-19 | A rede privada não está em todos os arquivos da SEEDF: situação do aluno e Ideb de anos iniciais só têm a estadual; matrículas 2023 só rede pública | ausencia | REPORT §2.2, tabela de cobertura; qualquer frase sobre cobertura privada | `data/interim/q2_cobertura.csv`; REPORT §2.2 | aberto | publicação da SEEDF para as demais redes; o Censo 2024 cobre a privada com matrícula (100%) |
| L-20 | `AREA RURAL` (7.115 crianças de 0–3) não tem par no cadastro da SEEDF; fica fora dos cruzamentos com matrícula | ausencia | REPORT §2.5; tabelas de população e frequência por RA | SCHEMA, seção "Nomes de Região Administrativa"; REPORT §2.5 | aberto | cadastro da SEEDF com essa localidade ou uma chave escola→Área Rural; não preencher com zero |
| L-21 | O peso é a matrícula da etapa no Censo 2025 como proxy do aluno típico; para TDI e fluxo é a mesma coorte, para o Ideb é aproximação (a coorte do Saeb não é a matrícula inteira) | suposicao | REPORT §2.7(a), tabela de ponderação; `q13` | `scripts/06_analysis.py` (q13); `data/interim/q13_ponderacao_df.csv`; comparação 6,00/4,71/3,70 × 6,0/4,6/3,6 | aberto | nada; declarar a aproximação. O Ideb oficial da rede é calculado sobre a coorte que participou do Saeb, não sobre a matrícula inteira |
| L-22 | "Escola típica × aluno típico": a ponderação corrige composição, não cobertura nem a definição do indicador | suposicao | REPORT §2.7(a); toda comparação entre mediana e ponderada | `data/interim/q13_ponderacao_df.csv`; REPORT §2.7(a) | aberto | nada; as duas leituras devem ser publicadas juntas quando a cobertura não for 100% |
| L-23 | A PDAD dá idade na entrevista; a idade em 31/03/2024 só é calculável para 49,6% das linhas (55,2% da população de 0–3) e não serve de denominador | suposicao | REPORT §2.5 e §2.7(b); toda comparação Censo × PDAD | SCHEMA, bloco dos microdados da PDAD (linha Idade); REPORT §2.5 | aberto | data de nascimento completa na PDAD; hoje a convenção é a idade na entrevista, declarada |
| L-24 | Na PDAD, "rede pública" é a percepção da família (57,8%) e corresponde, quase sempre, à rede conveniada do Censo (57,3%) | suposicao | REPORT §2.5; README, bullet da creche | REPORT §2.5; `data/interim/pdad/pdad_frequencia.parquet`; SCHEMA, bloco da PDAD (`H04_1`) | aberto | cruzamento com o cadastro da escola; a PDAD não pergunta a rede administrativa |
| L-25 | A restrição do universo de infraestrutura a 927 escolas de EF/EM supõe que laboratório, quadra e biblioteca não são exigência para unidades que só ofertam educação infantil | suposicao | REPORT §2.3, as duas colunas da tabela; todas as medidas de biblioteca | REPORT §2.3; SCHEMA, bloco `relatorio_infraestrutura_*`; worklog 2026-10-23-01 §5 | aberto | citar a norma (LDB/CNE) que dispensa esses itens na EI; a premissa hoje não tem fonte citada |
| L-26 | O limite superior de ~10% para a distorção idade-etapa na creche supõe que todo nascimento se distribui uniformemente no ano | suposicao | REPORT §2.5, correção de método | REPORT §2.5; worklog 2026-10-23-01 §5 | aberto | data de nascimento completa (dia/mês) na base; a suposição só afeta o limite superior |
| L-27 | A faixa 0–3 do Censo de 2024 não declara data de referência; a leitura de que usa a última quarta-feira de maio é inferência do teste das escolas só de creche (91,4% × 92,7% × 99,9%) | inferencia | REPORT §2.7(b), tabela de referência; toda comparação Censo × PDAD; README, bullet da creche | `data/interim/q14_creche_referencia.csv`; SCHEMA, bloco do Censo ("Qual é a data de referência de 2024") | aberto | dicionário de 2024 ou confirmação do INEP; o fato medido é que 2024 não é idade no ano e que as duas referências de 2025 diferem em 9,3% |
| L-28 | As 76 escolas do Censo 2024 com a célula de matrícula vazia são lidas como "sem aluno declarado" (ausente, não zero); a fonte não diz o motivo | inferencia | REPORT §2.7(c), nota de leitura; qualquer soma do Censo 2024 | `data/interim/inep/censo_metodo.csv`; `data/interim/inep/censo_escola_df.parquet`; SCHEMA, bloco do Censo; REPORT §2.7(c) | aberto | dicionário/nota técnica da INEP sobre célula vazia. A leitura do parquet mostra que a situação de funcionamento não é uniforme entre as 76; nome não é explicação |
| L-29 | As 139 escolas de infraestrutura 2025 com as colunas `IN_*` vazias são lidas como paralisadas/extintas e o nulo como "não se aplica" | inferencia | REPORT §2.3 (universo de 1.332) e §2.6 | SCHEMA, bloco `relatorio_infraestrutura_*`; REPORT §2.6 | aberto | conferir `TP_SITUACAO_FUNCIONAMENTO` escola a escola; se alguma for ativa, o nulo é ausência, não "não se aplica" |
| L-30 | Escola sem Ideb não é escola com Ideb zero: a ausência tem causa declarada (Portaria nº 435/2025: menos de 10 alunos ou participação abaixo de 80%) | risco-de-leitura | REPORT §2.4, ressalva (b); todo Ideb agregado; README, princípio 2 | SCHEMA, bloco `nota_informativa_ideb_2025.pdf`; REPORT §2.4 | aberto | nada; a regra é de leitura, não um dado a obter. A causa por escola não é distinguível (L-09) |
| L-31 | Há três medidas de cobertura do Ideb e elas não são intercambiáveis: 62,8% das escolas estaduais estão no arquivo da SEEDF (q2), 85,2% das que ofertam anos iniciais têm valor (q8) e 89,6% da matrícula de anos iniciais tem valor (q13) | risco-de-leitura | REPORT §2.2 (tabela), §2.4 (cobertura por escola) e §2.7(a) (cobertura por matrícula) | `data/interim/q2_cobertura.csv`, `data/interim/q8_cobertura_escolas_2025.csv`, `data/interim/q13_ponderacao_df.csv` | aberto | nada; nomear o denominador em cada frase |
| L-32 | A comparação nacional é de UF, não de escola; o recorte interno cobre a rede estadual, 1 escola federal nos anos finais e 11 no médio, e a privada não tem Ideb por escola depois de 2017 | risco-de-leitura | REPORT §2.4, ressalva (a); toda comparação DF × Brasil | REPORT §2.4; `data/interim/q8_df_brasil_uf.csv`; `data/interim/q8_escolas_rede.csv` | aberto | nada; o Ideb nacional é publicado por UF e o recorte interno é o que a fonte permite |
| L-33 | A mediana por escola de 2023 e 2025 não é da mesma coorte: 48 escolas estaduais de médio tinham Ideb em 2023 e 64 em 2025; a queda de 4,0 para 3,6 mistura resultado e conjunto | risco-de-leitura | REPORT §2.4, parágrafo da conferência | REPORT §2.4; `data/interim/q8_escolas_rede.csv`; worklog 2026-10-22-05 §7 | aberto | nada; comparar só escolas presentes nos dois anos ou declarar a mudança de conjunto |
| L-34 | O médio regular e o médio com o integrado à EPT são recortes diferentes do mesmo indicador e não podem ser empilhados sem aviso | risco-de-leitura | REPORT §2.4; `q9_em_integrado.csv`; SCHEMA, bloco do integrado | SCHEMA, bloco `divulgacao_ufs_Ensino_Medio_integrado_ideb_2025.xlsx`; worklog 2026-10-22-06 §2 | aberto | nada; manter `etapa = EM_integrado` separado |
| L-35 | Os marcadores `(1)`–`(7)` no rótulo de rede do Ideb são ressalvas históricas (2009, 2011, 2021), não condições do ano corrente; o DF traz `Total (4)` em 2025, mas o `(4)` é de 2011 | risco-de-leitura | REPORT §2.4; qualquer leitura do rótulo `rede` | SCHEMA, blocos das planilhas de UF e Brasil (linha Marcadores de nota); worklog 2026-10-22-04 §3 | aberto | nada; `rede_base` separa o rótulo do marcador |
| L-36 | `TP_DEPENDENCIA` não distingue conveniada de privada em 2025; é preciso usar `CO_REDE`/`NO_REDE` | risco-de-leitura | REPORT §2.1, §2.2 e §2.3; toda contagem por rede em 2025 | SCHEMA, bloco `relatorio_infraestrutura_*` (Observações d); worklog 2026-10-22-02 §3 | aberto | nada; a coluna correta está no cadastro |
| L-37 | A classificação da privada na INEP (particular, comunitária, confessional, filantrópica) não é a divisão da SEEDF entre conveniada e não conveniada | risco-de-leitura | REPORT §2.2; qualquer tabela que junte as duas classificações | REPORT §2.2; SCHEMA, bloco do Censo (renomes) | aberto | nada; manter as colunas do cadastro e não traduzir uma na outra |
| L-38 | `IN_INTERNET` é existência de internet, não acesso dos alunos; o campo de acesso é `IN_INTERNET_ALUNOS` | risco-de-leitura | REPORT §2.3, linha "internet"; 0,0% × 53,6% | REPORT §2.3; SCHEMA, bloco `relatorio_infraestrutura_*` | aberto | nada; usar o campo nomeado |
| L-39 | A taxa de creche por RA calculada com a escola como denominador não mede atendimento: 74,7% dos alunos de 6–17 anos estudam na própria RA e, em Arniqueira, 44,7% das crianças de 0–3 frequentam creche sem unidade no cadastro | risco-de-leitura | REPORT §2.5; `data/interim/q5_creche.csv`; qualquer leitura "por RA" da oferta | REPORT §2.5; `data/interim/pdad/pdad_fluxo_escolar.parquet`; `data/interim/q5_creche.csv` | aberto | nada; o déficit por RA só pode ser calculado do lado da demanda (RA de moradia) |
| L-40 | Medianas com n pequeno são instáveis: RAs com 1 a 6 escolas nos extremos e a rede federal de médio (11 escolas, 6 com Ideb) | risco-de-leitura | REPORT §2.3 (biblioteca por RA), §2.4 (Ideb por RA) e §2.7(a) (rede federal) | REPORT §2.3 e §2.4; `data/interim/q13_ponderacao_df.csv` | aberto | nada; agrupar RAs ou publicar o n, não a ordenação |
| L-41 | A coluna `icc` de `data/interim/q4_ideb_resumo.csv` é uma razão de quadrados médios (um F), não um coeficiente de correlação intraclasse | risco-de-leitura | nenhum número do REPORT (o relatório usa `eta2_entre_ra`); uso futuro do CSV | worklog 2026-10-22-03 §5; `data/interim/q4_ideb_resumo.csv` | aberto | renomear para `f_entre_ra`; a pendência está declarada no worklog 2026-10-22-03 |
| L-42 | `SITUACAO = SIR` significa sem informação de rendimento e é `ausente`, não reprovação | risco-de-leitura | nenhum número atual; uso futuro de situação do aluno | SCHEMA, bloco `relatorio_situacao_aluno_*`; worklog 2026-10-22-02 §3 | aberto | nada; a classificação está no dicionário |
| L-43 | As colunas do Censo mudam entre 2024 e 2025: `QT_MAT_MED_CT` sai e o médio integrado passa a `QT_MAT_MED_IFTP_CT`, que é outro recorte, não um rename; `TP_SITUACAO_FUNCIONAMENTO` sai da tabela de matrícula | risco-de-leitura | REPORT §2.7; qualquer comparação 2024→2025 de EM integrado ou de situação | SCHEMA, "Mudanças de esquema entre anos" e bloco do Censo; worklog 2026-10-23-02 §3 | aberto | nada; as colunas são declaradas por ano e a ausência entra como ausência |
| L-44 | Não foram lidas as tabelas `Tabela_Escola`, `Tabela_Docente`, `Tabela_Turma`, `Tabela_Gestor`, `Tabela_Curso_Tecnico` (2025) nem o suplemento de cursos técnicos (2024) | escopo | REPORT §1 e §5; nenhum número atual | worklog 2026-10-23-02 §6; REPORT §1 | aberto | decisão de escopo; a `Tabela_Escola` de 2025 traria a situação de funcionamento que a tabela de matrícula não tem |
| L-45 | Não foram baixados JSON/XML/GeoJSON (duplicam o CSV, ~4,9 GB), as séries 2014–2022 de turmas e docentes, os beneficiários do cartão material escolar (dado de família) e a série agregada de matrículas por modalidade | escopo | REPORT §1; nenhum número atual | REPORT §1; worklog 2026-10-22-01 §2 | aberto | decisão de escopo; só reabrir se uma pergunta exigir a série ou o dado de família |
| L-46 | Nenhuma análise usa geometria e não há mapa; `geopandas`/`shapely` seguem fora de `requirements.txt` | escopo | REPORT §1 e §4; README, "O que falta" | REPORT §1; SCHEMA, bloco da malha (Uso); AGENTS.md, Tooling | aberto | uma análise espacial validada; a malha já foi validada por atributo |
| L-47 | A população de 0–3 do Censo 2022 por RA não foi ingerida: a API do IBGE só alcança o DF como um município | escopo | REPORT §5, resíduo de precisão por RA; README, "O que falta" | REPORT §5; worklog 2026-10-22-06 §5; README, "O que falta" | aberto | agregado por setor censitário com chave setor→RA; a API municipal não serve |
| L-48 | O filtro `CO_UF = '53'` poderia não reproduzir o universo da SEEDF; medido, reproduz 1.284 escolas com matrícula em 2024, 1.291 em 2025 e 475 unidades com creche em 2025, escola por escola | risco-de-leitura | REPORT §2.7; base de todos os números do Censo | `data/interim/inep/censo_metodo.csv`; `data/interim/q14_creche_fecho.csv`; SCHEMA, tabela de chaves | fechado (2026-10-23) | nada; medido e fechado |
| L-49 | O resíduo de ~11,6 mil crianças entre Censo e PDAD na creche era convenção de idade, não oferta faltando: 37.595 (Censo 0–3) contra 37.654 (PDAD), 0,16%, dentro do IC | inferencia | REPORT §2.5 e §2.7(b); README, bullet da creche | `data/interim/q14_creche_fecho.csv`, `data/interim/q14_creche_referencia.csv`; REPORT §2.5 e §2.7(b) | fechado (2026-10-23) | nada; fechado. O worklog 2026-10-23-01 §6 ainda descreve o estado anterior — ver nota nele |
| L-50 | "36,2% da matrícula de creche é de 4 anos ou mais = distorção idade-etapa" era artefato de `IDADE` (idade no ano, não em 31/03) | risco-de-leitura | REPORT §2.5, correção de método; README, correções de 2026-10-23 | REPORT §2.5; worklog 2026-10-23-01 §5 | fechado (2026-10-23) | nada; corrigido |
| L-51 | "66,3% sem biblioteca" media o item errado no universo errado; são três itens (biblioteca, sala de leitura e a união) e o universo é o das 927 escolas de EF/EM | risco-de-leitura | REPORT §2.3; README, correções de 2026-10-23 | REPORT §2.3; SCHEMA, bloco de infraestrutura; worklog 2026-10-23-01 §5 | fechado (2026-10-23) | nada; corrigido |
| L-52 | A ausência de população de 0–3 por RA foi fechada pelos microdados da PDAD-A 2024; o resíduo de precisão por RA é L-17 | ausencia | REPORT §5; README, "O que falta" | SCHEMA, bloco dos microdados da PDAD; worklog 2026-10-23-01 §4 | fechado (2026-10-23) | nada quanto à ausência; a precisão por RA está em L-17 |
| L-53 | A regra de `H04_4` (contar o código do próprio município/RA como próprio) corrigiu a leitura de "estuda em outra RA"; o valor atual é 74,7% na própria RA | risco-de-leitura | REPORT §2.5; `data/interim/pdad/pdad_fluxo_escolar.parquet` | SCHEMA, bloco da PDAD (`H04_4`); worklog 2026-10-23-01 §2; sessão `ses_e9712d0b8ffeQzGAMj2sWKwBwE` msg 1581 | fechado (2026-10-23) | nada; a regra está no `10_ingest_pdad.py` |
| L-54 | Os microdados da PDAD estavam no disco com extensão `.pdf` e foram tratados como relatórios; a lacuna de 0–3 era de leitura, não de fonte | risco-de-leitura | REPORT §2.5 e §5 (antes); README, fontes | worklog 2026-10-23-01 §1; `data/raw/MANIFEST.md` → Correções; SCHEMA, bloco dos microdados | fechado (2026-10-23) | nada; corrigido no `05_external_sources.py` e no `10_ingest_pdad.py` |
| L-55 | Havia o risco de a SEEDF não usar `CO_ENTIDADE` e o casamento acabar por nome; a taxa medida é 100% quando os dois arquivos cobrem o mesmo universo | risco-de-leitura | SCHEMA, tabela de chaves; todos os joins | SCHEMA, "Chaves e cruzamentos"; worklog 2026-10-22-03 §1; sessão `ses_e9be9c902ffeaOcVDln02Nzwom` msg 23 | fechado (2026-10-22) | nada; a chave é medida a cada execução por `04_crosswalk.py` e `08_profile_inep.py` |
| L-56 | `ideb_projetado` é a meta do 1º ciclo (2007–2021), não uma previsão; nenhum CSV do projeto o usa como observado ou em média | risco-de-leitura | SCHEMA, bloco dos três zips por escola; nenhum número do REPORT | SCHEMA, "Ideb observado × projetado"; worklog 2026-10-22-05 §5 | fechado (2026-10-22) | nada; a coluna permanece no parquet e o nome diz o que é |
| L-57 | O esquema da SEEDF muda em 2025 (escolas de 74 para 81 colunas, infraestrutura de 114 para 289, turmas viram sinalizadores 0/1, matrículas e situação com rótulos legíveis) e os três arquivos de Ideb usam cabeçalhos e separadores diferentes | risco-de-leitura | REPORT §2.6; qualquer comparação entre anos ou entre as três etapas do Ideb | SCHEMA, "Mudanças de esquema entre anos" e blocos das famílias; worklog 2026-10-22-02 §3 | aberto | nada; ler por ano e conferir o cabeçalho antes de qualquer join; o perfil já detecta |
| L-58 | A malha tem 37 RAs e as séries de educação de 2024/2025 têm 35; o Censo 2022 não delimitou Arapoanga e Água Quente (incluídas em Planaltina e Recanto das Emas) | risco-de-leitura | REPORT §1; qualquer junção por RA ou mapa futuro | SCHEMA, bloco da malha (Cautela); worklog 2026-10-22-06 §4 | aberto | nada; declarar a versão da malha e normalizar nomes por `_common.norm_ra` |
| L-59 | Nas planilhas da INEP, `'-'` (Ideb) é ausente e `'--'` (TDI, TNR, fluxo) é não aplicável; são dois traços, dois significados, e os padrões de código da TDI e da TNR também diferem | risco-de-leitura | REPORT §2.2 e §2.4; qualquer leitura de Ideb, TDI, TNR ou fluxo | SCHEMA, "Vocabulário controlado" e blocos da TDI e da TNR; worklog 2026-10-22-08 §2 | aberto | nada; preservar `valor_bruto` e `estado`; a TDI usa `<recorte>_CAT_0` e a TNR `4_CAT_<recorte>` |
| L-60 | Na aba `Brasil (Anos Finais)`, a célula do código do Ideb de 2023 está vazia, mas a coluna tem valor; ler só a linha de códigos perderia o dado | risco-de-leitura | REPORT §2.4, valor do Brasil em 2023 nos anos finais | SCHEMA, bloco `divulgacao_brasil_ideb_2025.zip` (Armadilha); worklog 2026-10-22-05 §3 | fechado (2026-10-22) | nada; `processar_brasil()` recupera o código da faixa de cabeçalho |
| L-61 | Nenhum byte da INEP foi conferido contra o servidor, exceto o zip do Censo 2024 (conferido em 2026-11-06); o zip de 2025 (537.217.189 B) segue sem conferência | risco-de-leitura | todos os números do Censo 2025 | `data/raw/MANIFEST.md` linha 155; `curl -sk -C -` em 2026-11-06 | aberto | baixar `/dados_abertos/microdados_censo_escolar_2025_.zip` (538 MB) com `curl -sk -C -` e comparar o sha256 com o `MANIFEST`; não bloqueia número atual, porque o parquet casa 100% com o universo da SEEDF |
| L-62 | A série de matrículas por modalidade da SEEDF (`matriculas__relatorio_matriculas_*`) é publicada sob ODbL; derivado dela teria de ser licenciado sob ODbL | escopo | README §Licença; qualquer número publicado que dependa da série | `package_show` de `serie-historica-numero-de-matriculas-por-modalidade-…`; `data/interim/seedf_resources.csv`, coluna `license_id` | fechado (2026-11-06) | decidido: a página publica matrícula pelo Censo da INEP 2024–2025 e a série da SEEDF fica como diagnóstico interno; reabrir só com política de derivado ODbL |
| L-63 | O Censo de 2024 tem 1.360 linhas no DF contra 1.291 escolas no cadastro de 2025: 53 escolas de 2025 não têm linha em 2024 e 3 têm linha com as quatro células de matrícula vazias; "a escola não consta" não é "matrícula não declarada" | ausencia | docs/FASE-1.md §3.1; frase do bloco 3/9; 53 páginas de escola | `data/interim/inep/censo_escola_df.parquet`; `data/public/escolas.parquet`, coluna `censo_2024_presente`; worklog 2026-11-09-01-correcoes-fase-1.md | aberto | dicionário/nota da INEP que diga se a ausência de linha é escola inexistente, código novo ou outro motivo; a flag apenas registra a presença |
| L-64 | O rótulo de exibição da RA ("Águas Claras", "Sol Nascente/Pôr do Sol") é uma tabela escrita à mão em `scripts/sitegen/region.py`, não um campo da fonte: o build falha quando a RA não tem entrada, mas nada garante que a grafia bata com a oficial. O `calculo` do bloco de identificação em `data/public/procedencia.json` segue "cópia dos campos", porque regenerá-lo mudaria `data/public` | suposicao | docs/FASE-1.md §2.1 e bloco 1 do §2; subtítulo e ficha "Região Administrativa" das 1.291 páginas de escola (em SCIA e SIA o rótulo é igual ao valor bruto) | `scripts/sitegen/region.py` (`REGION_LABELS`); `data/public/procedencia.json`, bloco de identificação; `scripts/sitegen/checks/region_toc.py` (o `[ok]` confere as opções contra as seções, não a grafia) | aberto | conferir a grafia contra a fonte oficial da RA (SEGOV-DF ou lei de criação) e alinhar o `calculo` do `06_analysis.py` na próxima regeneração de `data/public`; a grafia não muda número algum, só o texto de tela |
| L-65 | A comparação entre redes da home não controla o perfil socioeconômico dos alunos: o insumo não tem variável de nível socioeconômico, então estadual × privada compara públicos diferentes e a diferença não mede efeito de escola | risco-de-leitura | docs/FASE-1.md §2.3; gráfico de distorção idade-série da home; legenda do gráfico (L-65); `calculo` dos 24 registros `tdi-*` | REPORT.md §2.4; `data/interim/q11_distorcao_df.csv`; plano 2026-11-11 §6.2 | aberto | nada por download aberto: declarar na legenda que as redes atendem públicos diferentes. Reabrir se o INSE por escola entrar no insumo |
| L-66 | A posição "n-ésimo de 27" é conta do projeto (1 + número de UFs com valor maior), não publicação da INEP; o denominador muda entre etapas e anos (L-10) e o DF não tem valor "Pública" no ensino médio | suposicao | docs/FASE-1.md §2.3; cartão do Ideb do ensino médio da home; `data/public/ideb_uf.parquet` | `data/interim/q8_df_brasil_uf.csv`; `data/public/ideb_uf.parquet`; plano 2026-11-11 §5.3 | aberto | nomear o denominador ao lado da posição; a fonte não publica ordenação. O `--check-home` confere "27º de 27" contra `posicao == n_ufs` |
| L-67 | A distribuição de distorção idade-série por rede da home inclui unidades escola × etapa abaixo do limiar de D4, cuja taxa a página da escola não publica: a home usa valores que a página suprime. Efeito medido em 2025: no máximo 0,7 ponto num p90 (anos finais estaduais 29,6 → 28,9) e 0,2 ou menos nas medianas (ensino médio estadual 20,7 → 20,5); o maior grupo é anos iniciais privada (37 de 311 unidades, 27 com `0,0`) | risco-de-leitura | docs/FASE-1.md §2.3; legenda do gráfico (L-67); `calculo` e `limites` dos 24 registros `tdi-*` de `site/dados/home.json` | `data/interim/q16_faixas_n.csv`; plano 2026-11-11 §3.7 e §5.2 | aberto | nada; a diferença é declarada na legenda e no `calculo`. Reabrir só em dois casos: (a) o gráfico deixa de comparar redes — a pergunta “qual é o valor da rede” pede outra forma de gráfico — ou (b) a mediana da home passa a ter de bater com a mediana da página da escola. Mudar o valor de `--limiar-n` não reabre o item (o texto é relativo ao limiar de D4), mas invalida a medição de 0,7/0,2, feita com n = 30: remedir e reescrever antes de citar. Fechar com data quando o gráfico usar só unidades ≥ limiar |

## Notas

**L-01.** A conferência comparou 13 campos e 16.692 células escola × etapa:
16.480 iguais (98,7%) e 212 divergentes. O volume está no técnico subsequente
(−5.755, −27,9%) e na EJA (−1.381, −5,16%); creche, EM integrado e educação
especial casam 1.284 de 1.284. A hipótese "aluno sem `IDADE` não entra no
cruzamento da SEEDF" não é testável com o arquivo publicado. Ver
`data/interim/q15_conferencia_censo.csv` e REPORT §2.7(c).

**L-02.** A cobertura é 100% em TDI e fluxo e 96,5% na aprovação do médio
privado; no Ideb, 89,6% (iniciais), 82,3% (finais) e 64,8% (médio) da matrícula
estadual. No médio, mediana e ponderada valem para dois terços dos alunos. Ver
`data/interim/q13_ponderacao_df.csv`.

**L-05.** Fechado em 2026-11-06: as URLs `/dados_abertos/` respondem 200 com os
bytes do `MANIFEST` (33.829.396 e 537.217.189). O segundo arquivo continua sem
sha256 conferido contra o servidor (L-61). O `.xlsx` do médio integrado não é o
do servidor — 31.398 B locais contra 31.594 B, `Last-Modified` anterior ao
download —, mas as 2.430 células de A1:BB45 são idênticas: o que mudou foi o
programa que salvou (Excel Online, `docProps/core.xml` local com a data do
download). Bytes e sha256 locais ficam como estão; o caso está em `MANIFEST.md`
→ Correções. O `download()` segue sem revalidar contra o servidor, que é risco
separado e não fecha com esta verificação.

**L-06.** As âncoras fecham exatas em `data/interim/inep/censo_metodo.csv` (40.851, 42.582, 1.284,
1.291). O argumento contra a tolerância é que creche, EM integrado e educação
especial casam célula a célula em 1.284 de 1.284 escolas (L-01). Desde
2026-11-06 a tolerância é zero e o `censo_metodo.csv` é gravado por ano, antes
de qualquer `RuntimeError` — antes, o "FALHOU" nunca chegava ao arquivo.

**L-08.** Em anos iniciais e finais não há linha privada em UF alguma; no médio
há 1.247 linhas privadas no país, 851 com valor, todas de 2017. No DF, 37
privadas de médio listadas, 19 com Ideb em 2017, nenhuma em 2023 ou 2025. A TNR
lista 150 privadas com médio, contra 37 no arquivo de Ideb — o Ideb privado
ausente é não publicação. Ver REPORT §2.4 e §5.

**L-09.** A TNR mede alunos sem informação de rendimento/movimento no Censo
Escolar; não tem campo de participação no Saeb. As medianas das escolas com e sem
Ideb se sobrepõem (1,3 × 1,3 nos iniciais; 1,9 × 2,5 nos finais; 2,0 × 1,8 no
médio). Em 44 dos 91 casos de iniciais e 38 dos 74 de finais a célula é `'--'`, e
o cadastro confirma etapa não ofertada em 42 e 37. A hipótese do catálogo (C-06)
falhou; o limite da fonte permanece.

**L-13.** Matrículas 2023 tem 600 escolas e 42.440 linhas contra ~78 mil; situação
2025 tem 2.421 linhas contra ~72 mil; situação 2019 tem 126.672 linhas porque
inclui a federal. Nenhuma série que atravesse esses anos é comparável sem
declarar a diferença.

**L-17.** A variância usa Kish para proporções, com reposição para totais; o
arquivo não traz estrato nem unidade primária, então o intervalo publicado é um
limite inferior de largura. A leitura trata a amostra como representativa por RA
— é a premissa da PDAD, não um teste feito aqui. Ver SCHEMA, bloco dos
microdados da PDAD.

**L-21.** Ponderado por matrícula, o Ideb das estaduais dá 6,00 / 4,71 / 3,70
contra 6,0 / 4,6 / 3,6 publicados pela INEP para a rede. A diferença residual é
de cobertura e arredondamento, não de conta; a decomposição dessa diferença não
foi medida separadamente. Ver REPORT §2.7(a).

**L-22.** Nas redes estadual e privada a divergência fica em 1,0 p.p. ou menos,
com três exceções: abandono no médio estadual (+1,6), reprovação no médio
estadual (+1,5) e a rede federal de médio (11 escolas), onde a distorção cai
3,0 p.p. e o Ideb sobe 0,5. A rede federal também diverge na reprovação do
médio; a frase do REPORT cita só a distorção e o Ideb. Nenhuma ordem entre redes
se inverte.

**L-23.** O corte de 31/03/2024 cobre 49,6% das linhas e 55,2% da população de
0–3; por isso o denominador é a idade na entrevista. A diferença entre 29,4%
(Censo/população PDAD) e 27,1% (PDAD) é a mesma coorte de 3.197 crianças (7,8% da
matrícula) que tinham 4 anos na entrevista e 3 na data de referência. Ver REPORT
§2.7(b).

**L-27.** O teste usa as escolas que só têm creche: 119 em 2024 e 141 em 2025. A
razão faixa 0–3 / creche é 91,4% em 2024, 92,7% em maio/2025 e 99,9% em 31/03/2025.
Se 2024 fosse 31/03, a razão seria ~100%; ela se comporta como maio. As duas
referências de 2025 diferem em 9,3% (39.293 × 42.945).

**L-28.** O Censo 2024 tem 1.360 linhas no DF, das quais 76 com a célula de
matrícula vazia; 1.284 têm matrícula e são o mesmo conjunto da série da SEEDF. A
fonte não declara o motivo da célula vazia. A conferência do parquet mostra que a
situação de funcionamento não é uniforme entre as 76, então "extinta/paralisada"
não explica todas; o registro não usa nome de escola como explicação.

**L-31.** As três medidas: 62,8% é presença no arquivo contra as 669 escolas
estaduais do cadastro; 85,2% é valor contra as 393 que ofertam anos iniciais;
89,6% é matrícula com valor contra a matrícula das escolas que ofertam. A
diferença entre 85,2% e 89,6% é o tamanho das escolas com valor. Ver `q2`, `q8` e
`q13`.

**L-39.** A PDAD mostra 74,7% dos alunos de 6–17 anos na própria RA e 24,6% em
outra. Em Arniqueira, 44,7% das crianças de 0–3 frequentam creche e o cadastro
não registra matrícula nem unidade. O denominador "escola no RA" mede onde a
escola está, não onde a criança mora.

**L-44.** A `Tabela_Escola` de 2025 é a que traria `TP_SITUACAO_FUNCIONAMENTO`,
que não está na tabela de matrícula lida. `Tabela_Docente`, `Tabela_Turma`,
`Tabela_Gestor`, `Tabela_Curso_Tecnico` e o suplemento de 2024 não respondem
nenhuma pergunta desta fase.

**L-48.** A interseção de `CO_ENTIDADE` é 1.284 de 1.284 em 2024 e 1.291 de 1.291
em 2025; as 475 unidades com creche de 2025 são as mesmas do cadastro, 0 de cada
lado. Ver `data/interim/q14_creche_fecho.csv` e SCHEMA, tabela de chaves.

**L-49.** O Censo 2024 conta 37.595 crianças de 0–3 na educação básica
(`QT_MAT_BAS_0_3`) contra 37.654 frequentando na PDAD — 59, 0,16%, dentro do IC de
±3,5 mil. Os 26.076 são creche × idade no ano; os 11.519 de diferença são a
coorte com 4 anos no ano e 3 na data de referência. Ver `data/interim/q14_creche_fecho.csv`.

**L-50.** O número antigo era 40.851 matrículas em creche, 14.775 com `IDADE` ≥ 4
(36,2%). Só 270 matrículas de creche têm `IDADE` ≥ 5; a distorção real fica entre
0,7% e ~10% (ver L-26). Nenhuma conta do projeto usa `IDADE` como idade em 31/03.

**L-51.** O número antigo (66,3%) usava só `IN_BIBLIOTECA` sobre as 1.332 unidades
em funcionamento, incluindo creche. No universo de 927 escolas de EF/EM: 60,6%
sem biblioteca, 6,0% sem biblioteca nem sala de leitura e 48,2% das que têm
biblioteca sem bibliotecário (estadual: 73,4%, 6,4% e 61,4%). Ver REPORT §2.3.

**L-53.** Sem a regra, "estuda em outra RA" saía inflado em ~30 p.p. A correção
foi feita em `10_ingest_pdad.py`; o valor atual é 74,7% na própria RA. A sessão
que corrigiu registra o erro e a correção em
`ses_e9712d0b8ffeQzGAMj2sWKwBwE` msg 1581.

**L-56.** `VL_OBSERVADO_YYYY` vira `ideb_observado`; `VL_PROJECAO_YYYY` vira
`ideb_projetado`, meta do 1º ciclo (2007–2021). As colunas de projeção terminam
em 2021 e não há meta para 2023 nem 2025. Ver SCHEMA, "Ideb observado ×
projetado".

**L-63.** O Censo de 2024 tem 1.360 linhas no DF; o cadastro de 2025 tem 1.291
escolas. 53 dessas escolas não têm linha no Censo de 2024 e 3 (`53013662`,
`53015665`, `53019415`) têm linha com as quatro células de matrícula vazias. A
frase "a escola não consta do Censo de 2024" descreve a ausência de linha;
"matrícula não declarada no Censo de 2024" continua sendo a leitura da célula
vazia (L-28). A flag `censo_2024_presente` é o critério: ela não afirma que a
escola é nova nem converte matrícula positiva em `nao_aplicavel`. A leitura da
matrícula continua sujeita a L-28 (célula vazia), L-43 (mudança de colunas
entre 2024 e 2025) e L-62 (a série ODbL da SEEDF não entra). Ver
`data/public/escolas.parquet` e o worklog 2026-11-09.

## Reconciliação dos itens provisórios

Os itens `P-01`…`P-13` e `C-01`…`C-06` usados na sessão de recapitulação foram
reconciliados um por um no worklog
[`2026-10-23-03-limites.md`](worklogs/2026-10-23-03-limites.md) §4, com o motivo
e o id correspondente. `C-02` e `C-06` são veredito, não limite: por isso não
têm linha aqui. Nenhum `P-xx` foi descartado.
