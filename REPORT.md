# REPORT.md — fase 0: reconhecimento do DF

Sessão de 22/10/2026. Fontes: SEEDF (CKAN), IPEDF (PDAD-A 2024) e INEP (Ideb
2025 por UF, Brasil e escola, e do médio com o integrado à EPT; taxas de
rendimento, distorção idade-série e não-resposta por escola; nota informativa —
tudo por download manual). Malha territorial localizada e validada por atributo
(§1); nenhum mapa. Todo número cita arquivo e ano; detalhe em `SCHEMA.md`,
procedência em `data/raw/MANIFEST.md`.

## 1. Inventário

80 arquivos da SEEDF (458 MB), 53 PDFs da PDAD-A (100 MB), 10 arquivos da INEP
(345 MB) e a malha das RAs (4,6 MB), todos com sha256 no `MANIFEST.md` (144
linhas). Três dos 53 "PDFs" da PDAD-A não são relatórios: são os microdados
(`moradores.csv` e `domicilios.csv`, em ZIP) e o dicionário em XLSX, lidos por
`10_ingest_pdad.py` — a extensão errada está registrada em `MANIFEST.md` →
Correções.

| Conjunto SEEDF | Arquivos | Anos | Usado aqui |
|---|---|---|---|
| Relação de unidades escolares (todas as redes) | 13 CSV | 2014–2025 | sim |
| Matrículas por modalidade (todas as redes) | 11 CSV + 1 XLSX | 2014–2025 | sim |
| Infraestrutura (todas as redes) | 12 CSV | 2014–2025 | sim |
| Situação do aluno | 7 CSV | 2019–2025 | sim |
| IDEB / SAEB por escola | 3 CSV + 3 planilhas | 2005–2025 | sim |
| Distorção, docentes, turmas e tecnologia | 19 CSV | 2014–2025 | perfilado, não usado |
| Unidades de educação infantil e por oferta | 4 CSV | 2023 | conferência |

Não baixados, por decisão registrada: JSON/XML/GeoJSON (duplicam o CSV, ~4,9
GB), séries 2014–2022 de turmas e docentes, `beneficiários do cartão material
escolar` (dado de família, não de escola) e
`serie-historica-numero-de-matriculas-por-modalidade` (só JSON/XML, agregado). O
portal declara 5.422 MB; entraram 907 MB — 458 SEEDF, 100 PDAD-A, 345 INEP e 4,6
malha.

A malha das RAs veio do serviço ArcGIS do IDE/DF e foi validada por atributo em
`09_download_malha.py`: 37 RAs (EPSG:31983; GeoJSON em 4326), 35 com par no
cadastro de 2025 e na PDAD-A 2024; `26 de Setembro` e `Ponte Alta` existem só na
malha. Nenhuma análise usa geometria.

## 2. As seis perguntas

**2.1 Quantas unidades escolares existem no DF, por rede e por etapa?**
1.291 unidades ativas em 2025 (`relatorio_escolas_2025.csv`): 669 rede estadual
vinculada à SEEDF, 476 privadas não conveniadas, 131 privadas conveniadas, 11
federais, 4 estaduais não vinculadas. Por etapa, contando unidades que ofertam
cada uma (uma escola pode ofertar mais de uma):

| Etapa | Estadual | Privada não conv. | Privada conv. | Federal |
|---|---|---|---|---|
| Creche | 7 | 338 | 130 | 0 |
| Pré-escola | 285 | 349 | 25 | 0 |
| Fundamental | 525 | 324 | 2 | 1 |
| Médio | 100 | 150 | 0 | 11 |

A creche inverte o resto: 468 das 475 unidades não são da rede estadual,
majoritária nas outras etapas.

**2.2 A rede privada está coberta em todos os arquivos?**
Não. Cobertura medida contra o cadastro de 2025 (`data/interim/q2_cobertura.csv`):

| Arquivo | Estadual | Privada não conv. | Privada conv. |
|---|---|---|---|
| `relatorio_infraestrutura_2025.csv` | 100% | 100% | 100% |
| `relatorio_matriculas_2024.csv` | 99,0% | 90,3% | 97,7% |
| `relatorio_situacao_aluno_excel_2023.csv` | 98,2% | 0% | 0% |
| `ideb_ef_ai_2005_2025.csv` (2025) | 62,8% | 0% | 0% |

A falha não é arquivo faltando — é publicação: a situação do aluno só traz a rede
estadual (72.476 linhas, todas `REDE PÚBLICA ESTADUAL VINCULADA À SEEDF`), e o
IDEB de anos iniciais só tem `rede = Estadual`. O médio é exceção:
`ideb_em_2017_2025.csv` tem 1.924 linhas `Privada`.

Os arquivos nacionais de Ideb por escola (`divulgacao_*_escolas_2025.zip`, INEP,
`ideb_escolas_df.parquet`) não mudam o quadro: em anos iniciais e finais **não há
uma linha privada em UF alguma** — só Municipal, Estadual e Federal; no médio há
1.247 linhas privadas no país, nenhuma com valor depois de 2017. No DF, 37
privadas de médio: 19 com Ideb em 2017, nenhuma em 2023 ou 2025.

O fluxo escolar (`tx_rend_escolas_2025.zip`) fecha a lacuna de fluxo: em 2025, no
médio, a mediana de aprovação é 98,3% na privada (139 escolas) e 82,5% na
estadual (101); reprovação 1,5% e 12,4%, abandono 0,0% e 2,4% (`q10_fluxo_df.csv`).
Mesma etapa, fluxos opostos: o mecanismo do Ideb.

Distorção idade-série e não-resposta (`TDI_2025_ESCOLAS.zip`,
`tnr_escolas_2025.zip`, 2025) também cobrem a privada: 336 das 337 escolas
privadas com fundamental ou médio, 575 de 576 estaduais e 11 federais. A TNR
lista 150 privadas com médio, contra 37 no arquivo de Ideb — o Ideb privado
ausente é não publicação.

Outra falha na série: `relatorio_matriculas_2023.csv` traz só rede pública (600
escolas contra ~1.280 nos demais anos).

**2.3 Infraestrutura: que fração das escolas carece de cada item?**
1.332 escolas em funcionamento em 2025 (`relatorio_infraestrutura_2025.csv`,
excluídas 139 paralisadas/extintas). O universo inclui 405 unidades que só
ofertam educação infantil, onde laboratório, quadra e biblioteca não são
exigência de norma nenhuma; por isso a tabela traz as duas leituras.

| Item ausente | Todas as 1.332 | As 927 que ofertam EF/EM |
|---|---|---|
| Biblioteca (`IN_BIBLIOTECA`) | 66,3% | 60,6% |
| Biblioteca nem sala de leitura (`IN_BIBLIOTECA_SALA_LEITURA`) | 17,2% | 6,0% |
| Laboratório de informática | 60,1% | 53,0% |
| Internet **para os alunos** (`IN_INTERNET_ALUNOS`) | 60,5% | 53,6% |
| Quadra de esportes | 33,0% | 14,9% |
| Nenhum recurso de acessibilidade | 2,4% | 2,5% |
| Internet (existência) | 0,0% | 0,0% |
| Água potável | 0,0% | 0,0% |
| Banheiro | 0,2% | 0,1% |

Fonte: `data/interim/q3_infra_itens.csv` (todos os itens, nas duas colunas de
universo) e `data/interim/q3_biblioteca.csv` (biblioteca, que precisa dos três
itens separados e da dimensão do bibliotecário).

A linha "internet" é a que engana: 100% das escolas declaram ter internet, e
53,6% das que ofertam fundamental ou médio não declaram internet **para uso dos
alunos** (o Censo tem campos separados para administrativo, aprendizagem e
alunos; `IN_INTERNET` é existência, não acesso). Na rede estadual de EF/EM, 65,3%
não têm internet para alunos, contra 36,1% na privada.

Biblioteca é o item mais mal medido até aqui, e a correção é de universo e de
nome. São **três dependências distintas** no dicionário da SEEDF:
`IN_BIBLIOTECA` é biblioteca, `IN_SALA_LEITURA` é sala de leitura e
`IN_BIBLIOTECA_SALA_LEITURA` é "biblioteca e/ou sala de leitura" — o OR exato dos
outros dois, conferido nos 12 anos. Sala de leitura não é biblioteca; somá-las
numa frase só transforma 6,0% em 60,6% e vice-versa. Entre as 927 escolas de
EF/EM: **60,6% sem biblioteca**, 73,4% na estadual e 41,2% na privada não
conveniada; **6,0% sem biblioteca nem sala de leitura** (Fercal 60,0% e Paranoá
32,4% são os extremos, e são RAs pequenas); e, entre as 365 que têm biblioteca,
**48,2% não têm bibliotecário** — 61,4% na estadual. A série 2014–2025, no mesmo
universo, mostra falta de biblioteca estável entre 55,6% (2014) e 60,6% (2025) e
falta de qualquer espaço de leitura entre 6,0% e 7,6%: o que não existe é pouco,
e o que existe é frágil. Por RA a falta de biblioteca vai de 0% (Arniqueira, 1
escola; Varjão, 1) a 100% (SIA, 2 escolas; Park Way, 6; Candangolândia, 4), com
ordenação instável nos extremos; nas grandes, Ceilândia 76,1% (113), Santa Maria
78,8% (33), São Sebastião 72,4% (29) e Plano Piloto 36,4% (118).

**2.4 IDEB: o DF está entre os melhores do país? E a tese das "duas cidades"?**

Não para a primeira pergunta; em parte para a segunda. A comparação nacional tem
duas fontes da INEP, ingeridas em 2026-10-22: `divulgacao_regioes_ufs_ideb_2025.zip`
(27 UFs e 5 regiões, **sem** linha Brasil) e `divulgacao_brasil_ideb_2025.zip`
(a linha Brasil). Recorte em `data/interim/q8_df_brasil_uf.csv`.

| Etapa | Rede | DF 2025 | Brasil 2025 | Mediana das UFs | Posição |
|---|---|---|---|---|---|
| Anos iniciais | Total | 6,4 | 6,3 | 6,1 | 8º de 27 |
| Anos iniciais | Pública | 6,0 | 6,1 | 6,0 | 13º de 27 |
| Anos iniciais | Estadual | 6,0 | 6,4 | 6,15 | 16º de 26 |
| Anos iniciais | Privada | 7,4 | 7,1 | 7,0 | 4º de 27 |
| Anos finais | Total | 5,1 | 5,3 | 5,1 | 11º de 27 |
| Anos finais | Pública | 4,7 | 5,0 | 4,8 | 16º de 27 |
| Anos finais | Estadual | 4,6 | 5,1 | 4,8 | 21º de 27 |
| Anos finais | Privada | 6,2 | 6,4 | 6,2 | 10º de 27 |
| Ensino médio regular | Total | 4,1 | 4,5 | 4,4 | 22º de 27 |
| Ensino médio regular | Estadual | 3,6 | 4,3 | 4,2 | **27º de 27** |
| Ensino médio regular | Privada | 5,7 | 5,8 | 5,7 | 9º de 27 |

A leitura depende da rede:

- **"Total" é a linha que circula como "o DF é um dos melhores do país".** É
  verdade só nos anos iniciais, e por pouco: 6,4 contra 6,3 do Brasil. A privada
  — 4ª do país (7,4), com 26,9% da matrícula de fundamental e 24,3% da de médio
  (`relatorio_matriculas_2024.csv`, 2024) — sustenta a média.
- **Na rede pública o DF não é destaque em etapa alguma.** Anos iniciais, 13º de
  27, abaixo do Brasil (6,0 contra 6,1); finais, 16º de 27 (4,7 contra 5,0);
  médio regular, **último de 27 (3,6 contra 4,3)**. A aba de médio da planilha de
  UF não publica "Pública" (só Total, Privada e Estadual): ali a comparação é a
  estadual — no DF, quase toda a rede pública (4 estaduais não vinculadas, 11
  federais, nenhuma municipal).
- AI/Estadual tem 26 UFs nas duas edições: Roraima não tem resultado estadual.
- O rótulo diz o recorte: as abas são **anos iniciais regulares**, **anos finais
  regulares** e **médio regular**. O médio **com o integrado à EPT** tem planilha
  própria (`divulgacao_ufs_Ensino_Medio_integrado_ideb_2025.xlsx`): o DF segue
  **último de 27** em 2025 (3,6) e 18º em 2023 (3,7), as mesmas posições do
  regular; a inclusão muda 10–11 UFs em 0,1–0,2, não o DF (`q9_em_integrado.csv`).

**2023 × 2025, com o Brasil ao lado.** Em 2023 o DF tinha 6,4 / 5,0 / 4,2 nas
linhas Total contra 6,0 / 5,0 / 4,3 do Brasil; no estadual, 5,9 / 4,6 / 3,7
contra 6,0 / 4,9 / 4,1. O Brasil subiu 0,3, 0,3 e 0,2; o DF não se moveu
(6,4→6,4; 5,0→5,1; 4,2→4,1). A posição caiu (4º→8º, 8º→11º, 10º→22º no Total;
11º→16º, 16º→21º, 18º→último no estadual) porque o país andou. A comparação é
legítima: a `nota_informativa_ideb_2025.pdf` afirma metodologia inalterada desde
2007; 2023 e 2025 não têm metas, e esta é a última divulgação na formulação
original — a próxima quebra a série.

**O recorte por escola fecha a pergunta por dentro.** `ideb_escolas_df.parquet`
normaliza o Ideb por escola do DF a partir dos três `divulgacao_*_escolas_2025.zip`.
Em 2025 a rede estadual tem 335 escolas com Ideb nos anos iniciais (mediana 6,0;
p10 5,3; p90 6,8), 155 nos finais (4,7; 4,0; 5,4) e 64 no médio (3,6; 3,1; 4,5):
o último lugar não vem de poucas escolas — metade está em 3,6 ou abaixo. A
federal tem 11 de médio, 6 com Ideb (mediana 4,6). Faltam 91 das 426 estaduais
de iniciais (21,4%), 74 de 229 nos finais (32,3%) e 32 de 96 no médio (33,3%);
contra o cadastro de 2025, têm Ideb 85,2% das estaduais que ofertam iniciais (335
de 393), 78,3% nos finais (155 de 198), 62,1% no médio (64 de 103) e 54,5% das 11
federais de médio (`q8_cobertura_escolas_2025.csv`).

A conferência valor a valor contra a série da SEEDF fecha com zero divergências
— 3.512 valores em iniciais, 1.542 em finais, 222 no médio
(`q8_conferencia_seedf.csv`) —, mas a mediana por escola não é da mesma coorte:
48 escolas estaduais de médio tinham Ideb em 2023 e 64 em 2025, então a queda de
4,0 para 3,6 mistura resultado e conjunto.

**A desigualdade territorial é real, mas é história de segunda ordem.** Na rede
estadual, anos iniciais (`ideb_ef_ai_2005_2025.csv`): 38,5% da variância de 2025
(42,5% em 2023) está entre Regiões Administrativas; 61,5% fica dentro da mesma
RA. A mediana por RA vai de 5,1 (SCIA, 3 escolas) a 7,05 (Cruzeiro, 4); nas
grandes, de 5,5 (Planaltina, 32) a 6,7 (Plano Piloto, 29). O corte "centro ×
periferia" não separa: Ceilândia (5,9, 52 escolas) empata com a mediana do DF,
Brazlândia (5,9) fica acima de Águas Claras (5,6); Planaltina (5,5), Paranoá
(5,7) e São Sebastião (5,8) ficam abaixo. Nos finais e no médio de 2023 a
desigualdade entre RAs é da mesma ordem (40,1% e 40,3%), com medianas mais baixas
(4,7 e 4,0).

A tese das "duas cidades" pressupunha um patamar alto a dividir. Não é alto: a
rede estadual é 16ª, 21ª e última do país, e em nenhuma etapa alcança a média
nacional da estadual (6,4, 5,1 e 4,3). A desigualdade entre RAs segue medida — só
não é a manchete.

Duas ressalvas que o dado impõe: (a) a comparação nacional é de UF, não de
escola; o recorte interno cobre a rede estadual, 1 escola federal nos anos finais
e 11 no médio, e a privada não tem Ideb por escola depois de 2017; (b) escola sem
Ideb não é escola com Ideb zero — as causas estão na Portaria nº 435/2025 (menos
de 10 alunos, ou participação abaixo de 80% dos matriculados), e nenhuma média
aqui preenche ausência com zero.

A distorção idade-série em 2025 separa as redes na mesma direção
(`q11_distorcao_df.csv`; `TDI_2025_ESCOLAS.zip`): a mediana da estadual é 9,0%
nos anos iniciais (p10–p90 4,1–15,0; 386 escolas), 17,1% nos finais (10,9–29,6;
195) e 20,7% no médio (11,7–35,8; 101); na privada, 1,2% (0,0–4,8; 311), 3,2%
(1,0–8,3; 200) e 4,5% (1,0–10,6; 150). Nos finais e no médio o p10 da estadual
supera o p90 da privada; a federal de médio (11 escolas) tem mediana 17,2%.

A taxa de não-resposta não explica o Ideb ausente em 2025: mede alunos sem
informação de rendimento/movimento, não participação no Saeb, e não separa não
participação de supressão (`q12_tnr_ideb_ausente.csv`; `tnr_escolas_2025.zip`).
Nas estaduais sem Ideb que têm taxa na TNR (39, 34 e 32 escolas), a mediana é 1,3,
2,5 e 1,8 contra 1,3, 1,9 e 2,0 nas com Ideb. O ganho é outro: em 44 dos 91 casos de
iniciais e 38 dos 74 de finais a célula é `'--'`, e o cadastro de 2025 confirma
etapa não ofertada em 42 e 37 — sem coorte, não é não participação. A hipótese do
catálogo falhou.

**2.5 Creche: oferta por RA contra população 0–3 permite estimar déficit?**

Agora com 0–3 dos dois lados. A PDAD-A 2024 entra pelos microdados
(`base_de_morador.pdf`, que é ZIP com `moradores.csv`; ver SCHEMA.md), não pela
tabela "até 4 anos" dos PDFs: `10_ingest_pdad.py` lê idade simples e peso
amostral. O DF tem **139.116 crianças de 0–3 anos** (4,7% dos 2.982.816
moradores; IC do total ±5,1 mil) e **81.546 de 4–5 anos**.

Duas convenções de idade, e a comparação depende delas: a PDAD dá **idade na
entrevista**, e o corte de 31/03/2024 — o critério de matrícula — só é calculável
para 49,6% das linhas, que cobrem 55,2% da população de 0–3, então **não serve de
denominador**; o Censo dá **idade no ano** (`IDADE`). Quem comparar os dois lados
tem de dizer qual convenção está em cada um (detalhe em `SCHEMA.md`, blocos da
PDAD e de `relatorio_matriculas_*`).

**Quantas frequentam.** 27,1% das crianças de 0–3 (±2,5 p.p.), ou ~37.654
crianças; dessas, 57,8% na rede pública (na percepção da família) e 42,1% na
particular. A estrutura é a mesma que o Censo mostra em 2024: 57,3% da matrícula
em creche está na rede **conveniada**, 42,3% na privada não conveniada e 0,3% em
unidades da própria SEEDF — a família que responde "pública" está, quase sempre,
falando da conveniada. Aos 4–5 anos, 86,0% frequentam (±2,5 p.p.): cerca de 11,4
mil crianças em idade de pré-escola obrigatória estão fora da escola.

**O que falta para a meta.** A meta usual de cobertura de creche é 50% da faixa:
69.558 crianças, contra 37.654 frequentando — faltam **~31,9 mil (±3,5 mil)**. O
número é do DF inteiro, não de RA: é onde a amostra sustenta o intervalo.

**A taxa por RA de escola não mede atendimento.** Por escola
(`data/interim/q5_creche.csv`), SCIA 4,1%, Sol Nascente/Pôr do Sol 4,7% e Paranoá
11,2%, contra Plano Piloto 60,7%, Park Way 86,8% e Lago Sul 97,5%. Mas 74,7% dos
alunos de 6–17 anos estudam na própria RA e 24,6% em outra, e na creche o
fenômeno reaparece: em **Arniqueira 44,7% das crianças de 0–3 frequentam creche
(PDAD) e o cadastro não registra nenhuma matrícula nem unidade** — as crianças
atravessam a fronteira da RA. Por isso o déficit por RA só pode ser calculado do
lado da demanda (RA de moradia, PDAD), e ali o n por RA vai de 14 a 184 pessoas:
meio-intervalo de 6 a 36 p.p. Serve para agrupar RAs (SCIA, Fercal, Área Rural,
Recanto das Emas e São Sebastião embaixo; Sobradinho, Águas Claras, Sudoeste e
Núcleo Bandeirante em cima), não para mapa por RA.

**Correção de método: os 36,2% não são distorção idade-etapa.** A versão anterior
dizia que 14.775 das 40.851 matrículas em creche (36,2%) eram de criança de "4
anos ou mais", lidas como criança que já deveria estar na pré-escola. `IDADE` no
Censo é **idade no ano**, não idade em 31/03, que é a data de corte da matrícula.
A prova está no próprio arquivo: no 1º ano do fundamental, 70,8% dos alunos
aparecem com `IDADE` 7 e 25,0% com 6 — exatamente o que o corte de 31/03 produz
sobre idade por ano de nascimento. Uma criança com `IDADE` 4 pode estar
legitimamente em creche (nascida depois de 31/03), e só 270 matrículas de creche
têm `IDADE` ≥ 5, que nenhuma convenção explica. A distorção real fica entre 0,7%
e ~10% (o limite superior supõe que todo nascimento se distribui uniformemente no
ano) — não 36,2%. Nenhuma conta deste relatório usa `IDADE` como idade em 31/03;
a distorção idade-série do §2.4 vem da TDI da INEP, que aplica o corte.

**O que não fecha, e por quê.** O Censo conta 26.076 matrículas em creche de
criança com `IDADE` ≤ 3; a PDAD implica ~37.654 frequentando. A diferença de
~11,6 mil não é explicada por nenhuma das duas fontes sozinha. Hipóteses, nenhuma
testada: creches que não declaram o Censo Escolar (assistenciais, não escolares),
autodeclaração da família e a diferença de data de referência. Quem resolve é o
microdado do Censo Escolar por escola, que não está ingerido (§5). Até então, o
projeto publica as duas contagens lado a lado e não escolhe uma.

**2.6 Qualidade: mudanças de esquema, códigos, duplicatas, anos parciais**

- **Esquema:** 2025 muda tudo — escolas de 74 para 81 colunas, infraestrutura de
  114 para 289, matrículas e situação com rótulos legíveis. As três etapas do IDEB
  usam cabeçalhos diferentes (`cod_inep` × `Cód_Inep`, `;` × `,`); a TDI e a TNR
  põem os códigos na linha 9, com `'--'` = não aplicável e padrões
  `FUN_AI_CAT_0` × `4_CAT_FUN_AI`.
- **Ano fantasma:** `relatorio_infraestrutura_2016.csv` contém 2017 e é idêntico
  ao de 2017 (1.124 linhas): 2016 não existe.
- **Ano parcial:** matrículas 2023 (600 escolas, só rede pública, 42.440 linhas
  contra ~78 mil); situação 2025 (2.421 contra ~72 mil) e 2019 (126.672, o dobro,
  por incluir a federal).
- **Unidades, chaves e nomes:** 1.568 códigos em 2014–2025; 41 só em 2025, 277
  desaparecem antes. Nenhuma duplicata de `CO_ENTIDADE` nos arquivos de escola; em
  situação do aluno a chave só fecha com `CONCLUINTE` (5.537 linhas parecem
  duplicadas e não são). Um nome repetido com dois códigos (Escola Canadense de
  Brasília), `AGUAS CLARAS ` com espaço, e `TP_DEPENDENCIA` que não separa
  conveniada em 2025 — usar `CO_REDE`.
- **Dado ausente explícito:** as 139 escolas de infraestrutura 2025 com as colunas
  `IN_*` vazias são as paralisadas/extintas: nulo ali é "não se aplica".

## 3. Veredito

| Hipótese | Veredito | Evidência |
|---|---|---|
| O IDEB médio do DF esconde duas cidades | **premissa falsa, efeito real** — "o DF está entre os melhores do país" só vale para a linha "Total" dos anos iniciais (8º de 27, 6,4 contra 6,3 do Brasil), e só porque a privada entra na conta (4ª do país, 26,9% da matrícula de fundamental). Na rede pública o DF é 13º de 27 em anos iniciais (6,0 contra 6,1 do Brasil), 16º em anos finais (4,7 contra 5,0) e **último de 27 no ensino médio regular (3,6 contra 4,3)**. A desigualdade entre RAs é grande (38,5–42,5% da variância), mas 58–62% fica dentro da RA e o corte centro/periferia não separa | `divulgacao_regioes_ufs_ideb_2025.zip` + `divulgacao_brasil_ideb_2025.zip` → `q8_df_brasil_uf.csv`; `divulgacao_*_escolas_2025.zip` → `q8_escolas_rede.csv`; `ideb_ef_ai_2005_2025.csv` 2023/2025; `relatorio_matriculas_2024.csv`; `q11_distorcao_df.csv` |
| Déficit de creche concentrado em RAs específicas | **sustenta** a concentração e agora **tem valor**: 139.116 crianças de 0–3, 27,1% frequentando (±2,5 p.p.), déficit de ~31,9 mil (±3,5 mil) para a meta de 50% — no DF, não por RA. A concentração territorial segue visível (SCIA 10,6%, Fercal 12,7% contra Sobradinho 45,2%, Águas Claras 46,0%), mas o n por RA é de 14 a 184 pessoas: agrupa RAs, não desenha mapa | `10_ingest_pdad.py` → `pdad_frequencia.parquet`; `relatorio_matriculas_2024.csv` |

O que não se sustenta: tratar a média do DF como retrato da cidade e o DF como
referência nacional — a reputação vem de uma média que mistura redes e olha só os
anos iniciais; a creche, que se sustenta, é ofertada por privada e conveniada (7
de 475 unidades em 2025).

## 4. O gráfico único mais forte permitido pelos dados hoje

**IDEB 2025 dos anos iniciais, uma escola por ponto, agrupadas por Região
Administrativa e ordenadas pela mediana da RA**, com a linha da mediana do DF
(6,0). Fonte: `ideb_ef_ai_2005_2025.csv` + `relatorio_escolas_2025.csv`. Mostra o
deslocamento entre RAs, a sobreposição entre elas e os casos que contrariam a
intuição (Ceilândia na mediana, Planaltina abaixo). Nenhum mapa faz isso melhor:
a variável não é contínua no território.

## 5. O que continua invisível

- **Ideb 2023/2025 das escolas privadas.** Não é falta de download: os três
  arquivos nacionais por escola não publicam valor privado depois de 2017 — em
  iniciais e finais não há linha privada em UF alguma, e no médio as 1.247 linhas
  do país têm valor só em 2017. No DF, 37 privadas de médio listadas, nenhuma com
  Ideb em 2023 ou 2025 (`q8_escolas_rede.csv`); a TNR não fecha a lacuna — mede
  não-resposta de rendimento, não participação no Saeb. O agregado por UF, região
  e Brasil existe (§2.4); falta a distribuição entre escolas privadas. **Correção:**
  a versão anterior esperava que os arquivos por escola trouxessem a rede privada;
  eles trouxeram a confirmação da série da SEEDF e nenhum dado privado.
- **População de 0–3 anos por RA — resolvida, com resíduo de precisão.** Não
  falta o dado: faltava abrir três arquivos que o 05 tinha baixado como "PDF".
  Os microdados da PDAD-A 2024 dão 139.116 crianças de 0–3 no DF (4,7% da
  população) e frequência a creche por RA; o total expandido reproduz as tabelas
  publicadas com desvio máximo de 0,01% por RA (§2.5). O que continua fora é a
  **precisão por RA**: 14 a 184 pessoas por RA, meio-intervalo de 6 a 36 p.p. Por
  isso nenhuma taxa por RA entra como número, só como agrupamento. Para reduzir a
  variância seria preciso o agregado por setor censitário (Censo 2022) com chave
  setor → RA, ou a própria PDAD-A com estrato e unidade primária, que o arquivo
  não publica. E a idade em 31/03/2024 só existe para 49,6% das linhas (55,2% da
  população de 0–3); por isso o projeto usa a idade na entrevista e declara a
  convenção, em vez de fingir o corte.
- **Fechamento de escola e infraestrutura de 2016.** 277 códigos somem da série
  sem motivo declarado, e o arquivo de 2016 é cópia de 2017 (§2.6). Um contato
  institucional destravaria os dois; nenhum dado aberto substitui isso.
