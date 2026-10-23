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
| [PDAD / IPEDF](https://pdad.ipe.df.gov.br/) | Perfil demográfico e socioeconômico por Região Administrativa. | API de relatórios, `05` |
| [IDE/DF — Geoserviços](https://www.geoservicos.ide.df.gov.br/) | Malha das Regiões Administrativas (serviço ArcGIS, 37 RAs). | download automático, `09` |

O `download.inep.gov.br` responde ao navegador, mas não ao `urllib`/`curl` deste
ambiente. Por isso os arquivos da INEP entram por `data/raw/inep/inbox/`, com
hash e registro conferidos por `07_ingest_inep.py`. O caminho é declarado, não
escondido: nenhum script finge que baixou o que não baixou.

## Estado

**Fase 0 — reconhecimento.** A sessão de 2026-10-22 fechou o inventário e
respondeu às seis perguntas da fase, mas a etapa não está completa: faltam o Ideb
por escola das escolas privadas (que a INEP não publica depois de 2017) e a
população de 0–3 anos por RA — as duas nomeadas em `REPORT.md` §5. Ainda não há
produto: há inventário, dicionário de dados e as respostas que os dados já
permitem. Fontes baixadas e verificadas: 80 arquivos da SEEDF, 53 relatórios da
PDAD-A, 10 arquivos da INEP e a malha das RAs, todos com sha256 no manifesto. O
escopo, os números e os vereditos estão em [`REPORT.md`](REPORT.md); os campos de
cada arquivo, em [`SCHEMA.md`](SCHEMA.md); o que foi feito em cada etapa, em
[`docs/worklogs/`](docs/worklogs/).

O que o reconhecimento já mostrou:

- **A creche não é da rede estadual.** Em 2025, 468 das 475 unidades que ofertam
  creche no DF são privadas ou conveniadas; a rede estadual tem 7.
  (`relatorio_escolas_2025.csv`)
- **A reputação do DF no IDEB não vale para a rede pública.** Em 2025, a rede
  estadual do DF ficou em 16º de 26 nos anos iniciais, 21º de 27 nos anos finais
  e **última de 27 no ensino médio** (3,6 contra 4,3 do Brasil). O número alto
  que circula é a linha "Total", que mistura a rede privada.
  (`divulgacao_regioes_ufs_ideb_2025.zip`, `divulgacao_brasil_ideb_2025.zip`)
- **A desigualdade territorial existe, mas não é a manchete.** 38,5% da variância
  do IDEB de anos iniciais de 2025 está entre Regiões Administrativas — o resto
  está dentro da mesma RA. (`ideb_ef_ai_2005_2025.csv`)
- **Mais de um terço da matrícula em creche é de criança de 4 anos ou mais**
  (36,2%), quando essa criança já deveria estar na pré-escola.
  (`relatorio_matriculas_2024.csv`)
- **A distorção idade-série separa as redes.** Em 2025, a mediana na rede
  estadual é 9,0% nos anos iniciais, 17,1% nos finais e 20,7% no médio; na
  privada, 1,2%, 3,2% e 4,5% — nos finais e no médio, o p10 da estadual fica
  acima do p90 da privada. (`TDI_2025_ESCOLAS.zip`)

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
    └── 09_download_malha.py   # malha das RAs (IDE/DF), só validação por atributo
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
