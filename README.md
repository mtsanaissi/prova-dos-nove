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
| [INEP — Censo Escolar](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar) | Microdados censitários de todas as escolas do país, públicas e privadas. | pendente: microdado nacional, só com recorte para o DF documentado |
| [INEP — IDEB](https://www.gov.br/inep/pt-br/areas-de-atuacao/pesquisas-estatisticas-e-indicadores/ideb/resultados/2005-2025) | IDEB por escola e por UF, por dependência administrativa. | download manual pelo navegador, `07`–`08` |
| [INEP — Taxas de Rendimento](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos) | Aprovação, reprovação e abandono por escola, todas as redes. | download manual pelo navegador, `07`–`08` |
| [INEP — Indicadores por escola](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos) | Distorção idade-série e taxa de não-resposta por escola, todas as redes. | download manual pelo navegador, `07`–`08` |
| [PDAD / IPEDF](https://pdad.ipe.df.gov.br/) | Perfil demográfico e socioeconômico por Região Administrativa, inclusive os **microdados** de moradores e domicílios (peso amostral, idade, frequência escolar, RA de estudo). | API de relatórios, `05`; microdados, `10` |
| [IDE/DF — Geoserviços](https://www.geoservicos.ide.df.gov.br/) | Malha das Regiões Administrativas (serviço ArcGIS, 37 RAs). | download automático, `09` |

O `download.inep.gov.br` responde ao navegador, mas não ao `urllib`/`curl` deste
ambiente. Por isso os arquivos da INEP entram por `data/raw/inep/inbox/`, com
hash e registro conferidos por `07_ingest_inep.py`. O caminho é declarado, não
escondido: nenhum script finge que baixou o que não baixou.

## Estado

**Fase 0 — reconhecimento.** A sessão de 2026-10-22 fechou o inventário e
respondeu às seis perguntas da fase; a de 2026-10-23 abriu os microdados da
PDAD-A 2024 e corrigiu duas contas de método (creche e biblioteca). A etapa não
está completa: falta o Ideb por escola das escolas privadas, que a INEP não
publica depois de 2017 (`REPORT.md` §5). Ainda não há produto: há inventário,
dicionário de dados e as respostas que os dados já permitem.

Fontes baixadas e verificadas, todas com sha256 no `MANIFEST.md` (144 linhas):
80 arquivos da SEEDF (458 MB), 53 da PDAD-A (100 MB — 50 relatórios, dois
microdados e o dicionário), 10 da INEP (345 MB) e a malha das RAs (4,6 MB). Os
10 da INEP entraram à mão por `07`–`08`: Ideb 2025 por UF e por Brasil, os três
arquivos por escola (iniciais, finais e médio), o médio com o integrado à EPT,
as taxas de rendimento por escola, a distorção idade-série por escola, a taxa de
não-resposta por escola e a nota informativa. A malha veio do serviço ArcGIS do
IDE/DF (`09_download_malha.py`): 37 RAs, 35 com par no cadastro de 2025 e na
PDAD-A 2024; `26 de Setembro` e `Ponte Alta` existem só na malha.

O escopo, os números e os vereditos estão em [`REPORT.md`](REPORT.md); os campos
de cada arquivo, em [`SCHEMA.md`](SCHEMA.md); o que foi feito em cada etapa, em
[`docs/worklogs/`](docs/worklogs/).

### O que o reconhecimento já mostrou

- **A creche não é da rede estadual.** Em 2025, 468 das 475 unidades que ofertam
  creche no DF são privadas ou conveniadas; a rede estadual tem 7.
  (`relatorio_escolas_2025.csv`)
- **A reputação do DF no IDEB não vale para a rede pública.** Em 2025, a rede
  estadual do DF ficou em 16º de 26 nos anos iniciais, 21º de 27 nos anos finais
  e **última de 27 no ensino médio** (3,6 contra 4,3 do Brasil). O número alto
  que circula é a linha "Total", que mistura a rede privada. Com o integrado à
  EPT a estadual continua última (3,6). (`q8_df_brasil_uf.csv`,
  `q9_em_integrado.csv`)
- **Os arquivos nacionais por escola confirmam a série da SEEDF — e negam a
  privada.** Reproduzem os valores da SEEDF valor por valor (3.512 + 1.542 + 222,
  0 divergências) e não publicam Ideb de escola privada depois de 2017; a
  cobertura privada existe só como agregado de rede nas planilhas de UF e Brasil.
  (`q8_conferencia_seedf.csv`, `q8_escolas_rede.csv`)
- **A desigualdade territorial existe, mas não é a manchete.** 38,5% da variância
  do IDEB de anos iniciais de 2025 está entre Regiões Administrativas — o resto
  está dentro da mesma RA. (`ideb_ef_ai_2005_2025.csv`)
- **27,1% das crianças de 0 a 3 anos frequentam creche; a meta é 50%.** São
  139.116 crianças na faixa e ~37.654 na creche — faltam ~31,9 mil. Quase toda a
  creche pública é conveniada: a rede própria da SEEDF tem 0,3% da matrícula, e
  57,3% está na rede conveniada. (`pdad_frequencia.parquet`, `relatorio_matriculas_2024.csv`)
- **A distorção idade-série separa as redes.** Em 2025, a mediana na rede
  estadual é 9,0% nos anos iniciais, 17,1% nos finais e 20,7% no médio; na
  privada, 1,2%, 3,2% e 4,5% — nos finais e no médio, o p10 da estadual fica
  acima do p90 da privada. (`TDI_2025_ESCOLAS.zip`, `q11_distorcao_df.csv`)
- **O fluxo separa as redes na mesma direção.** Em 2025, no ensino médio, a
  mediana de aprovação é 98,3% na rede privada (139 escolas) contra 82,5% na
  estadual (101), com abandono 0,0% contra 2,4%. (`tx_rend_escolas_2025.zip`,
  `q10_fluxo_df.csv`)
- **A não-resposta não explica o Ideb ausente.** A TNR mede falta de informação
  de rendimento/movimento, não participação no SAEB; não tem campo que separe
  não participação de supressão, e escolas com e sem Ideb têm a mesma
  distribuição. TDI e TNR cobrem as mesmas 925 escolas do DF, todas casadas com
  o censo de 2025 (100%), 336 delas privadas. (`tnr_escolas_2025.zip`,
  `q12_tnr_ideb_ausente.csv`)

Duas correções de método, em 2026-10-23: a leitura "36,2% da matrícula de creche
é de 4 anos ou mais" (idade no ano do censo não é idade em 31/03) e o número de
biblioteca (três itens da INEP — biblioteca, sala de leitura e a união dos dois —
sobre um universo restrito às escolas que ofertam fundamental/médio).

### O que falta

- **Ideb por escola da rede privada.** A INEP não publica valor privado depois de
  2017 em nenhum dos três arquivos por escola (`REPORT.md` §5).
- **População de 0–3 por RA, com precisão.** O total do DF está resolvido pelos
  microdados da PDAD-A; por RA o n vai de 14 a 184 pessoas e o meio-intervalo de
  6 a 36 p.p., então RA entra como agrupamento, nunca como taxa. Só agregado por
  setor censitário com chave setor → RA, ou uma PDAD-A com estrato e unidade
  primária, resolveria. (`10_ingest_pdad.py`)
- **Idade em 31/03.** A data de nascimento (`E02_1`) só está preenchida em 49,6%
  das linhas (55,2% da população de 0–3), então a convenção de 31/03 não
  substitui a idade na entrevista.
- **Microdado do Censo Escolar por escola**, ainda não ingerido: é o que
  resolveria a diferença de ~11,6 mil entre Censo e PDAD na creche.
- **População por RA do Censo 2022**, não ingerida: a API do IBGE só alcança o
  DF como um município.
- **Fechamento de escola e infraestrutura de 2016.** 277 códigos somem da série
  sem motivo declarado e o arquivo de 2016 é cópia de 2017 (`REPORT.md` §2.6).
- **Mapa.** Nenhuma análise usa geometria: `CO_RA` entra como atributo, e as
  bibliotecas geográficas seguem fora de `requirements.txt` até haver análise
  espacial validada.

## Estrutura

```text
.
├── AGENTS.md               # contexto e convenções do projeto
├── REPORT.md               # relatório da fase de reconhecimento
├── SCHEMA.md               # dicionário de dados
├── requirements.txt        # dependências
├── docs/
│   ├── nome.md             # a origem do nome, contada para crianças
│   └── worklogs/           # registro técnico do que foi feito, por data
├── data/
│   ├── raw/                # originais (fora do git) + MANIFEST.md (dentro)
│   │   └── inep/inbox/     # onde o arquivo baixado no navegador é deixado
│   └── interim/            # normalizados e respostas (fora do git)
└── scripts/
    ├── _common.py             # download, hash, detecção de formato, MANIFEST
    ├── 01_inventory_seedf.py  # enumera o CKAN da SEEDF
    ├── 02_download_seedf.py   # baixa e registra hash
    ├── 03_profile_seedf.py    # perfila e converte para parquet
    ├── 04_crosswalk.py        # mede taxa de casamento entre arquivos
    ├── 05_external_sources.py # PDAD-A, INEP e malha territorial
    ├── 06_analysis.py         # as seis perguntas, com número e arquivo
    ├── 07_ingest_inep.py      # ingere o que veio pelo navegador
    ├── 08_profile_inep.py     # perfila e normaliza o que a INEP entrega
    ├── 09_download_malha.py   # malha das RAs (IDE/DF), só validação por atributo
    └── 10_ingest_pdad.py      # microdados da PDAD-A: agregados por RA
```

## Como rodar

Python 3.12, ambiente criado com `uv`:

```bash
uv venv .venv
uv pip install -r requirements.txt

.venv/bin/python scripts/01_inventory_seedf.py   # enumera o CKAN
.venv/bin/python scripts/02_download_seedf.py    # baixa e registra no MANIFEST
.venv/bin/python scripts/03_profile_seedf.py     # parquet + perfil de colunas
.venv/bin/python scripts/04_crosswalk.py         # taxa de casamento das chaves
.venv/bin/python scripts/05_external_sources.py  # PDAD-A e teste das demais fontes
.venv/bin/python scripts/06_analysis.py          # números do REPORT.md

# microdados da PDAD-A (população 0–3, frequência por RA, fluxo RA → RA)
.venv/bin/python scripts/10_ingest_pdad.py --check  # só lê e descreve
.venv/bin/python scripts/10_ingest_pdad.py          # agregados em data/interim/pdad/
```

Depois da parte da SEEDF, a INEP:

```bash
# baixe no navegador e deixe os arquivos em data/raw/inep/inbox/
.venv/bin/python scripts/07_ingest_inep.py --check   # o que falta, com URL
.venv/bin/python scripts/07_ingest_inep.py           # hash, move, registra
.venv/bin/python scripts/08_profile_inep.py          # perfila e normaliza
```

Todos os scripts são idempotentes e abrem com docstring dizendo entrada, saída e
se podem ser reexecutados. `03`, `04` e `06` leem apenas `data/`; `01`, `02` e
`05` acessam a rede, e `02` e `05` pulam o que já está baixado. Os dados não
entram no git; o manifesto, com URL, data, tamanho e sha256 de cada arquivo,
entra.

## Contribuir

Correções de dado e apontamentos de erro são bem-vindos como issue. Se um
número aqui estiver errado, isso é o bug mais grave que o projeto pode ter —
avise.

## Licença

Código sob MIT; textos e dados derivados sob CC BY 4.0. A confirmar antes da
primeira publicação.
