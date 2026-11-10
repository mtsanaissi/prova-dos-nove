# Prova dos Nove

**Os números da educação brasileira, em português comum.**

> [Por que esse nome?](docs/nome.md)

## O problema

Os dados da educação brasileira são públicos, abundantes e praticamente
ilegíveis. Estão espalhados em dezenas de arquivos, com nomes de colunas em
código, séries que mudam de esquema a cada ano e indicadores que só fazem
sentido para quem já sabe lê-los. Quem mais precisaria deles — professoras,
coordenadoras, jornalistas, famílias, conselheiros municipais — é exatamente
quem tem menos tempo e menos ferramenta para decifrá-los.

Este projeto existe para encurtar essa distância.

## O que é

Uma página por escola, em português comum, que responde perguntas sobre aquela
escola e mostra de onde veio cada número.

- **Profissionais de educação** veem a própria escola no dado e o que mudou ao
  longo dos anos.
- **Jornalistas** encontram o fato, a fonte e o ano em um só lugar.
- **Público geral** entende o que os números dizem sem precisar de planilha.

Começa pelo Distrito Federal — onde a rede é única e os dados são mais
consolidados — mas é desenhado para o Brasil.

## O que não é

- **Não é ranking de escolas.** Ordenar escolas por indicador premia quem já
  partiu na frente e pune quem atende quem mais precisa.
- **Não é avaliação de professores.** Nenhum dado público permite isso.
- **Não é previsão.** O projeto descreve o que aconteceu e diz o que não sabe.

## O que os números não dizem

Todo número desta página tem procedência, mas nenhum é ilimitado. O registro
completo, com evidência e status, está em [`docs/LIMITES.md`](docs/LIMITES.md);
os ids abaixo apontam para ele.

- **Escola sem Ideb não é escola com nota zero.** A ausência tem causa — menos de
  10 alunos no Saeb ou participação abaixo de 80% — e a fonte não distingue, por
  escola, não participação de resultado não publicado (L-09, L-30).
- **O Ideb por escola cobre parte da matrícula.** Na rede estadual, a mediana do
  médio vale para 64,8% dos alunos; a rede privada não tem Ideb por escola depois
  de 2017 (L-02, L-08).
- **A comparação nacional é de UF, não de escola**, e o DF no médio é comparado
  pela rede estadual porque a planilha não publica "Pública" (L-10, L-32).
- **Creche depende da convenção de idade e do denominador.** A faixa 0–3 do
  Censo de 2024 não declara a data de referência; a leitura de que usa maio é
  inferência declarada (L-27). A taxa por RA calculada pela escola não mede
  atendimento, porque as crianças atravessam a fronteira da RA (L-39); a
  estimativa da PDAD por RA tem n pequeno e agrupa RAs (L-17).
- **A série da SEEDF é republicação do Censo.** Concordância entre as duas não é
  confirmação independente; e a SEEDF subestima EJA e educação profissional
  (L-01, L-07).
- **Ponderar corrige composição, não cobertura.** O peso é a matrícula da etapa;
  para o Ideb é uma aproximação da coorte que fez o Saeb (L-21, L-22).

## Princípios

1. **Todo número tem endereço.** Cada valor exibido aponta para o arquivo, o
   ano e o cálculo que o produziu. Número sem procedência não entra.
2. **Zero, ausente e não aplicável são coisas diferentes.** Escola sem IDEB por
   não ter participado do SAEB não é escola com desempenho zero. Confundir os
   três é o erro mais comum — e o mais danoso — em dados educacionais.
3. **Português comum primeiro.** Se a frase precisa de glossário, ela ainda não
   está pronta.
4. **A escola é a unidade.** O recorte é o objeto, não a audiência: a mesma
   página serve a todos os públicos.
5. **Dado público, pessoa privada.** Nada de dado individual de estudante.
   Nenhuma raspagem de listas nominais.
6. **Se o dado não existe, dizemos que não existe** — e o que existiria no
   lugar dele.

## Fontes

| Fonte | O que traz | Como entra |
|---|---|---|
| [Dados Abertos SEEDF](https://data.se.df.gov.br/) | Séries históricas por escola: unidades, matrículas, turmas, docentes, fluxo escolar, infraestrutura, distorção idade/série, IDEB/SAEB. CKAN, com GeoJSON e dicionário. | API CKAN, `01`–`02` |
| [INEP — Censo Escolar](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar) | Microdados censitários de todas as escolas do país, públicas e privadas. Desde 2024 a publicação é **por escola**, não por aluno: matrícula por etapa e faixa etária. | download manual pelo navegador, `07`; recorte do DF em streaming, `11` |
| [INEP — IDEB](https://www.gov.br/inep/pt-br/areas-de-atuacao/pesquisas-estatisticas-e-indicadores/ideb/resultados/2005-2025) | IDEB por escola e por UF, por dependência administrativa. | download manual pelo navegador, `07`–`08` |
| [INEP — Taxas de Rendimento](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos) | Aprovação, reprovação e abandono por escola, todas as redes. | download manual pelo navegador, `07`–`08` |
| [INEP — Indicadores por escola](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos) | Distorção idade-série e taxa de não-resposta por escola, todas as redes. | download manual pelo navegador, `07`–`08` |
| [PDAD / IPEDF](https://pdad.ipe.df.gov.br/) | Perfil demográfico e socioeconômico por Região Administrativa, inclusive os **microdados** de moradores e domicílios (peso amostral, idade, frequência escolar, RA de estudo). | API de relatórios, `05`; microdados, `10` |
| [IDE/DF — Geoserviços](https://www.geoservicos.ide.df.gov.br/) | Malha das Regiões Administrativas (serviço ArcGIS, 37 RAs). | download automático, `09` |

O `download.inep.gov.br` serve **cadeia TLS incompleta** — o certificado é emitido
sob a RNP ICPEdu e `curl`/`urllib` sem a CA correspondente recusam a conexão
(`curl` sai 60, `openssl s_client` devolve 21). Não é bloqueio da fonte: com
`curl -sk` o arquivo de 33,8 MB do Censo 2024 foi baixado em 2026-11-06 e o
sha256 confere com o `MANIFEST`. Por isso os arquivos da INEP entram por
`data/raw/inep/inbox/`, com hash e registro conferidos por `07_ingest_inep.py`,
e a conferência de sha256 contra o `MANIFEST` é obrigatória antes de qualquer
uso. O caminho é declarado, não escondido: nenhum script finge que baixou o que
não baixou.

## Estado

**Fase 0 — reconhecimento.** A sessão de 2026-10-22 fechou o inventário e
respondeu às seis perguntas da fase; a de 2026-10-23 abriu os microdados da
PDAD-A 2024 e corrigiu duas contas de método (creche e biblioteca), e depois
ingeriu o **Censo Escolar 2024 e 2025** com recorte do DF: as taxas por escola
agora têm versão ponderada pela matrícula, o resíduo de 11,6 mil crianças na
creche foi explicado (era convenção de idade, não oferta faltando) e a série de
matrículas da SEEDF foi conferida valor a valor contra a INEP. A etapa não está
completa: falta o Ideb por escola das escolas privadas, que a INEP não publica
depois de 2017 (`REPORT.md` §5). Naquele momento ainda não havia produto: havia
inventário, dicionário de dados e as respostas que os dados já permitem.

**Build da fase 1 — página por escola (2026-11-07).** O contrato está em
[`docs/FASE-1.md`](docs/FASE-1.md) e o build em `scripts/12_build_site.py` (a
CLI) e `scripts/sitegen/`.
`06_analysis.py --public data/public` exporta o recorte versionado (1.291
escolas, indicadores com `estado`, infraestrutura das 927 escolas de EF/EM e a
flag `censo_2024_presente`) e o build gera `site/`: índice alfabético sem número,
uma página por escola, a procedência de cada número em
`site/dados/<CO_ENTIDADE>.json` e as páginas `como-ler.html` e
`creditos.html`. O workflow `.github/workflows/pages.yml` publica o resultado
no GitHub Pages com `--check` antes do upload; antes do primeiro deploy, é
preciso ativar Pages em "GitHub Actions" nas configurações do repositório. O
site não é versionado; o insumo `data/public/` é.

Fontes baixadas e verificadas, todas com sha256 no `MANIFEST.md` (146 linhas):
80 arquivos da SEEDF (458 MB), 53 da PDAD-A (100 MB — 50 relatórios, dois
microdados e o dicionário), 12 da INEP (916 MB) e a malha das RAs (4,6 MB). Os
12 da INEP entraram à mão por `07`–`08` (e os dois do Censo por `07` e `11`):
Ideb 2025 por UF e por Brasil, os três arquivos por escola (iniciais, finais e
médio), o médio com o integrado à EPT, as taxas de rendimento por escola, a
distorção idade-série por escola, a taxa de não-resposta por escola, a nota
informativa e os **microdados do Censo Escolar de 2024 e 2025**. A malha veio do
serviço ArcGIS do IDE/DF (`09_download_malha.py`): 37 RAs, 35 com par no cadastro
de 2025 e na PDAD-A 2024; `26 de Setembro` e `Ponte Alta` existem só na malha.

O escopo, os números e os vereditos estão em [`REPORT.md`](REPORT.md); os campos
de cada arquivo, em [`SCHEMA.md`](SCHEMA.md); o que foi feito em cada etapa, em
[`docs/worklogs/`](docs/worklogs/).

**Critério de saída da fase 0 (2026-11-06).** Em cópia limpa — só o que está no
git, com `data/raw` por symlink e sem `data/interim/` — rodar na ordem `01 → 02 →
05 → 09 → 07 → 08 → 11 → 10 → 03 → 04 → 06` e comparar: parquets por hash de
conteúdo ordenado (`hash_pandas_object` sobre linhas ordenadas pela chave), CSVs
por `sha256`. Conteúdo igual em todos é o critério; bytes de parquet não servem,
porque o arquivo carrega metadados de escrita e não é byte-determinístico (medido
em 2026-11-06). Dependem de rede: `01`, `02`, `05`, `09`. Dependem de download
manual: `07` e, por ele, `08` e `11` na primeira vez. Rodam offline: `03`, `04`,
`08`, `10`, `11`, `06` e `05 --offline` (reconstrói `pdad_populacao.csv` de
`data/raw/pdad` sem tocar a API).

```bash
mkdir -p /tmp/replay && cd /tmp/replay
git clone https://github.com/mtsanaissi/prova-dos-nove.git repo && cd repo
ln -s /caminho/para/prova-dos-nove/data/raw data/raw
```

### O que o reconhecimento já mostrou

Os limites que pesam sobre estes números estão no bloco "O que os números não
dizem" e no registro `docs/LIMITES.md`; cada bullet abaixo fecha com os ids que o
limitam.

- **A creche não é da rede estadual.** Em 2025, 468 das 475 unidades que ofertam
  creche no DF são privadas ou conveniadas; a rede estadual tem 7.
  (`relatorio_escolas_2025.csv`; L-36)
- **A reputação do DF no IDEB não vale para a rede pública.** Em 2025, a rede
  estadual do DF ficou em 16º de 26 nos anos iniciais, 21º de 27 nos anos finais
  e **última de 27 no ensino médio** (3,6 contra 4,3 do Brasil). O número alto
  que circula é a linha "Total", que mistura a rede privada. Com o integrado à
  EPT a estadual continua última (3,6). (`q8_df_brasil_uf.csv`,
  `q9_em_integrado.csv`; L-10, L-31, L-32)
- **Os arquivos nacionais por escola confirmam a série da SEEDF — e negam a
  privada.** Reproduzem os valores da SEEDF valor por valor (3.512 + 1.542 + 222,
  0 divergências) e não publicam Ideb de escola privada depois de 2017; a
  cobertura privada existe só como agregado de rede nas planilhas de UF e Brasil.
  (`q8_conferencia_seedf.csv`, `q8_escolas_rede.csv`; L-07,
  L-08)
- **A desigualdade territorial existe, mas não é a manchete.** 38,5% da variância
  do IDEB de anos iniciais de 2025 está entre Regiões Administrativas — o resto
  está dentro da mesma RA. (`ideb_ef_ai_2005_2025.csv`; L-40)
- **27,1% das crianças de 0 a 3 anos frequentam creche; a meta é 50%.** São
  139.116 crianças na faixa e ~37.654 frequentando creche ou escola — faltam
  ~31,9 mil. Quase toda a creche pública é conveniada: a rede própria da SEEDF
  tem 0,3% da matrícula, e 57,3% está na rede conveniada.
  (`pdad_frequencia.parquet`, `relatorio_matriculas_2024.csv`; L-17,
  L-23, L-24, L-39)
- **A diferença entre Censo e PDAD na creche era convenção de idade.** O Censo
  conta 37.595 crianças de 0–3 matriculadas contra 37.654 frequentando na PDAD
  (0,16%, dentro do intervalo da amostra); os 26.076 que circulavam eram creche ×
  idade no ano, não a faixa 0–3. E a creche é oferta privada: 475 unidades em
  2025, 7 da rede estadual, 99,7% da matrícula na privada. (`REPORT.md` §2.7,
  `q14_creche_fecho.csv`; L-27, L-49, L-50)
- **As medianas por escola descrevem a escola típica, e a versão ponderada quase
  não muda o número.** Com o peso de matrícula do Censo 2025, estadual e privada
  ficam em 1,0 p.p. ou menos, com três exceções (abandono e reprovação no médio
  estadual, +1,6 e +1,5 p.p.; distorção no médio da pequena rede federal, −3,0).
  Nenhuma ordem entre redes se inverte. O ganho real é saber a cobertura: o Ideb
  por escola cobre 65% da matrícula do médio estadual. (`q13_ponderacao_df.csv`; L-02, L-21, L-22, L-31)
- **A distorção idade-série separa as redes.** Em 2025, a mediana na rede
  estadual é 9,0% nos anos iniciais, 17,1% nos finais e 20,7% no médio; na
  privada, 1,2%, 3,2% e 4,5% — nos finais e no médio, o p10 da estadual fica
  acima do p90 da privada. (`TDI_2025_ESCOLAS.zip`, `q11_distorcao_df.csv`; L-11, L-59)
- **O fluxo separa as redes na mesma direção.** Em 2025, no ensino médio, a
  mediana de aprovação é 98,3% na rede privada (139 escolas) contra 82,5% na
  estadual (101), com abandono 0,0% contra 2,4%. (`tx_rend_escolas_2025.zip`,
  `q10_fluxo_df.csv`; L-11, L-36, L-59)
- **A não-resposta não explica o Ideb ausente.** A TNR mede falta de informação
  de rendimento/movimento, não participação no SAEB; não tem campo que separe
  não participação de supressão, e escolas com e sem Ideb têm a mesma
  distribuição. TDI e TNR cobrem as mesmas 925 escolas do DF, todas casadas com
  o censo de 2025 (100%), 336 delas privadas. (`tnr_escolas_2025.zip`,
  `q12_tnr_ideb_ausente.csv`; L-09, L-11, L-59)

Duas correções de método, em 2026-10-23: a leitura "36,2% da matrícula de creche
é de 4 anos ou mais" (idade no ano do censo não é idade em 31/03) e o número de
biblioteca (três itens da INEP — biblioteca, sala de leitura e a união dos dois —
sobre um universo restrito às escolas que ofertam fundamental/médio).

### O que falta

- **Ideb por escola da rede privada (L-08).** A INEP não publica valor privado
  depois de 2017 em nenhum dos três arquivos por escola (`REPORT.md` §5).
- **População de 0–3 por RA, com precisão (L-17).** O total do DF está
  resolvido pelos microdados da PDAD-A; por RA o n vai de 14 a 184 pessoas e o
  meio-intervalo de 6 a 36 p.p., então RA entra como agrupamento, nunca como
  taxa. Só agregado por setor censitário com chave setor → RA, ou uma PDAD-A com
  estrato e unidade primária, resolveria. (`10_ingest_pdad.py`)
- **Idade em 31/03 (L-23).** A data de nascimento (`E02_1`) só está preenchida em
  49,6% das linhas (55,2% da população de 0–3), então a convenção de 31/03 não
  substitui a idade na entrevista.
- **Causa das divergências entre SEEDF e Censo na matrícula (L-01).** A série da
  SEEDF subestima EJA e educação profissional; a base por aluno que explicaria
  não é pública.
- **População por RA do Censo 2022 (L-47)**, não ingerida: a API do IBGE só
  alcança o DF como um município.
- **Fechamento de escola e infraestrutura de 2016 (L-14, L-15).** 277 códigos
  somem da série sem motivo declarado e o arquivo de 2016 é cópia de 2017
  (`REPORT.md` §2.6).
- **Mapa (L-46).** Nenhuma análise usa geometria: `CO_RA` entra como atributo, e
  as bibliotecas geográficas seguem fora de `requirements.txt` até haver análise
  espacial validada.

## Estrutura

```text
.
├── AGENTS.md               # contexto e convenções do projeto
├── LICENSE                 # MIT; textos e dados derivados sob CC BY 4.0
├── REPORT.md               # relatório da fase de reconhecimento
├── SCHEMA.md               # dicionário de dados
├── requirements.txt        # dependências, pinadas
├── docs/
│   ├── nome.md             # a origem do nome, contada para crianças
│   ├── FASE-1.md           # contrato da página por escola (fase 1)
│   ├── LIMITES.md          # registro de limites, suposições e riscos
│   └── worklogs/           # registro técnico do que foi feito, por data
├── data/
│   ├── raw/                # originais (fora do git) + MANIFEST.md (dentro)
│   │   └── inep/inbox/     # onde o arquivo baixado no navegador é deixado
│   ├── interim/            # normalizados e respostas (fora do git)
│   └── public/             # recorte mínimo que o build lê (dentro do git)
├── site/                   # build estático (fora do git; ver docs/FASE-1.md)
├── .github/workflows/      # pages.yml: publicação do site no GitHub Pages
└── scripts/
    ├── _common.py             # download, hash, detecção de formato, MANIFEST
    ├── 01_inventory_seedf.py  # enumera o CKAN da SEEDF
    ├── 02_download_seedf.py   # baixa e registra hash
    ├── 03_profile_seedf.py    # perfila e converte para parquet
    ├── 04_crosswalk.py        # mede taxa de casamento entre arquivos
    ├── 05_external_sources.py # PDAD-A, INEP e malha territorial
    ├── 06_analysis.py         # as perguntas, com número, arquivo e procedência
    ├── 07_ingest_inep.py      # ingere o que veio pelo navegador
    ├── 08_profile_inep.py     # perfila e normaliza o que a INEP entrega
    ├── 09_download_malha.py   # malha das RAs (IDE/DF), só validação por atributo
    ├── 10_ingest_pdad.py      # microdados da PDAD-A: agregados por RA
    ├── 11_ingest_censo.py     # recorte do DF dos microdados do Censo Escolar
    ├── 12_build_site.py       # CLI do build estático da página por escola (FASE-1)
    └── sitegen/               # pacote do build: loader, páginas, checks e assets
```

## Como rodar

Python 3.12, ambiente criado com `uv`:

```bash
uv venv .venv
uv pip install -r requirements.txt

# rede: catálogo, download e fontes externas
.venv/bin/python scripts/01_inventory_seedf.py   # enumera o CKAN
.venv/bin/python scripts/02_download_seedf.py    # baixa e registra no MANIFEST
.venv/bin/python scripts/05_external_sources.py  # PDAD-A, INEP e malha
.venv/bin/python scripts/09_download_malha.py    # malha das RAs (IDE/DF)

# manual: baixe no navegador e deixe em data/raw/inep/inbox/
.venv/bin/python scripts/07_ingest_inep.py --check   # o que falta, com URL
.venv/bin/python scripts/07_ingest_inep.py           # hash, move, registra
.venv/bin/python scripts/08_profile_inep.py          # perfila e normaliza

# offline, a partir daqui
.venv/bin/python scripts/11_ingest_censo.py          # Censo 2024–2025 por escola
.venv/bin/python scripts/10_ingest_pdad.py           # agregados da PDAD-A por RA
.venv/bin/python scripts/03_profile_seedf.py         # parquet + perfil de colunas
.venv/bin/python scripts/04_crosswalk.py             # taxa de casamento das chaves
.venv/bin/python scripts/06_analysis.py              # números do REPORT.md
.venv/bin/python scripts/06_analysis.py --public data/public  # insumo do site

# site: só data/public/, sem rede
.venv/bin/python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06
.venv/bin/python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check
```

`06` é o último: lê o parquet do `11`, os agregados do `10` e o perfil do `03`.
Ele grava `data/interim/q0_execucao.csv` com o estado de cada etapa e sai com
código diferente de zero se alguma pulou; `--parcial` aceita o resultado
incompleto e sai com zero.

Todos os scripts são idempotentes e abrem com docstring dizendo entrada, saída e
se podem ser reexecutados. `03`, `04`, `06`, `08`, `10` e `11` leem apenas
`data/`; `01`, `02`, `05` e `09` acessam a rede, e `02` e `05` pulam o que já
está baixado. Os dados não entram no git; o manifesto, com URL, data, tamanho e
sha256 de cada arquivo, entra.

## Contribuir

Correções de dado e apontamentos de erro são bem-vindos como issue. Se um
número aqui estiver errado, isso é o bug mais grave que o projeto pode ter —
avise.

## Licença

Código sob MIT (`LICENSE`), © 2026 Marcelo Anaissi. Textos e dados derivados
sob CC BY 4.0, com atribuição ao projeto e às fontes citadas em cada número.

Licença por fonte, como ela é declarada no catálogo — nenhuma foi inferida:

| fonte | licença declarada | onde |
|---|---|---|
| SEEDF/CKAN, 12 conjuntos | CC BY (Creative Commons Atribuição) | `license_id=cc-by` |
| SEEDF/CKAN, 5 conjuntos | ODbL (Open Data Commons Open Database License) | `license_id=odc-odbl` |
| INEP | público, sem licença declarada no portal | — |
| PDAD/IPEDF | não declarado | — |
| IDE/DF (malha) | não declarado | — |

Os 5 conjuntos ODbL são os de Ideb/SAEB por unidade e as listas de unidades com
oferta (anos iniciais, finais, médio e educação infantil), mais a série de
matrículas por modalidade. Política: **nenhum número publicado depende dos CSVs
ODbL de Ideb e unidades** — eles entram só como diagnóstico interno (L-45). A
série de matrículas por modalidade também é ODbL, e por isso a página publica
matrícula pelo Censo da INEP (2024–2025): a série da SEEDF continua ingerida
como diagnóstico e não sustenta número publicado.

