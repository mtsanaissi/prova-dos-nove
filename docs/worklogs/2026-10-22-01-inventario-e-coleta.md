# 2026-10-22 — 01. Inventário e coleta

> **Nota posterior (2026-10-23).** A frase "a faixa etária mais fina é `até 4
> anos`" vale para os **PDFs**; entre os 53 arquivos baixados estão dois ZIP com
> os microdados de moradores e domicílios, que abrem idade simples. Ver
> [`2026-10-23-01-pdad-e-biblioteca.md`](2026-10-23-01-pdad-e-biblioteca.md).

Objetivo: descobrir o que a SEEDF publica, baixar sem duplicar, e registrar
procedência. Entrada de rede, saída de bytes. Nenhuma análise aqui.

Scripts: `01_inventory_seedf.py`, `02_download_seedf.py`,
`05_external_sources.py`, `_common.py`.

## 1. Enumeração do CKAN

`https://data.se.df.gov.br/api/3/action/package_list` e
`package_show?id=<nome>` — a API expõe metadados completos, então não foi preciso
raspar HTML.

Saídas:

- `data/interim/seedf_datasets.csv` — 18 conjuntos × 9 colunas.
- `data/interim/seedf_resources.csv` — 378 recursos × 8 colunas (`dataset`,
  `recurso`, `formato`, `bytes`, `url`, `arquivo`, `anos_no_nome`,
  `modificado_em`).

O portal declara 5.422 MB no total. Só 558 MB entraram, e a diferença é
deliberada, não falha.

## 2. O que foi recusado, e por quê

| Recusado | Motivo |
|---|---|
| JSON/XML/GeoJSON do mesmo dado | duplicam o CSV e somam ~4,9 GB |
| `turmas` e `docentes` fora dos 3 anos recentes | série longa não é necessária para o recorte atual |
| `beneficiários do cartão material escolar` | dado de família, não de escola |
| `serie-historica-numero-de-matriculas-por-modalidade` | só JSON/XML, grão agregado |

Regra que ficou: o que não foi baixado é nomeado em `REPORT.md` §1, com o motivo.
Silêncio sobre ausência não é permitido no projeto.

## 3. Download idempotente

Decisões em `_common.py`:

- `download()` grava em `.part` e só então `replace()` no destino — arquivo
  truncado nunca é confundido com arquivo completo. A idempotência é por
  existência do destino: se ele está lá, o download foi atômico e terminou.
  Limitação conhecida: não há revalidação contra o servidor, então um recurso
  republicado com o mesmo nome só é rebaixado com `force=True`.
- sha256 calculado em streaming, no mesmo laço da escrita.
- `append_manifest()` insere linhas antes da seção `## Regras` do
  `data/raw/MANIFEST.md` e é idempotente por sha256: mesmo arquivo + mesmo hash
  não gera segunda linha; hash diferente gera segunda versão preservando a
  primeira.

Resultado: 80 arquivos em `data/raw/seedf/` (458 MB) — CSV, mais os XLSX que não
têm CSV equivalente —, nomeados `<data>_<nome>`, todos com URL, data, bytes e
sha256 no MANIFEST. Nomes de arquivo com prefixo de data resolvem o caso de o
mesmo recurso ser republicado em outro dataset
(`unidades-escolares-...-por-oferta`).

## 4. Fontes externas (`05_external_sources.py`)

`https://pdad.ipe.df.gov.br/api/upts_reports/` lista os relatórios por RA. Foram
53 PDFs (100 MB), e a composição foi medida, não suposta: **35 RAs do DF**, 12
municípios goianos da área de influência e **6 documentos que não são RA** (total
do DF, DF rural, dicionário de dados, base de domicílios, base de morador e
questionário). Só as 35 RAs entram na análise; os outros 18 aparecem em
`pdad_populacao.csv` porque o extrator é genérico. A tabela 2 de cada PDF é
extraída para `data/interim/pdad_populacao.csv` (53 linhas, 6 colunas).

`data/interim/fontes_externas_status.csv` registra seis tentativas, com o erro
literal. É o documento que impede a versão "não deu, pronto":

| Fonte | Recurso | Resultado | Detalhe registrado |
|---|---|---|---|
| IPEDF/PDAD-A 2024 | PDFs por RA | ok | 53 relatórios; faixa mais fina é `até 4 anos` |
| INEP Censo Escolar | `microdados_censo_escolar_2024.zip` | inacessível | `SSL: CERTIFICATE_VERIFY_FAILED` |
| INEP Censo Escolar | `microdados_censo_escolar_2025_.zip` | inacessível | idem |
| malha RA | `dados.df.gov.br/api/3/action/package_list` | inacessível | HTTP 404 — o catálogo CKAN não existe mais |
| malha RA | `geoportal.segov.df.gov.br/arcgis/rest/services` | inacessível | hostname do certificado não confere |
| malha RA | `sisdia.df.gov.br` | inacessível | idem |

## 5. A armadilha que virou método: a INEP

Dois modos de falha distintos, ambos registrados:

- `urllib` no zip de microdados do Censo: `CERTIFICATE_VERIFY_FAILED` (cadeia
  incompleta no ambiente).
- `urllib`/`curl` nos zips de resultado do Ideb: connection reset.

No navegador, os mesmos URLs respondem HTTP 200/206, com CORS liberado. Ou seja,
o bloqueio é do caminho de download do script, não da rede nem do servidor.

Consequência operacional, escrita em `AGENTS.md` e em `REPORT.md` §5: o arquivo
da INEP entra por `data/raw/inep/inbox/`, com `07_ingest_inep.py` fazendo hash,
MANIFEST e catálogo do que falta. Nunca se declara que um download automático
funcionou. Na sessão, os dois arquivos de 2025 chegaram assim.

## 6. Malha territorial

Não localizada: CKAN do GDF despublicado (404), geoportal e SISDIA com
certificado inválido. Não bloqueou nada, porque todas as análises usam `CO_RA` e
`NO_RA` como atributo. Ficou decidido que `geopandas`/`shapely` só entram em
`requirements.txt` quando a malha for validada (proveniência, CRS e concordância
de nome/código com SEEDF e PDAD). Até então, análise não-espacial.

## 7. Verificação

- `01` e `02` reexecutados: nenhum download repetido, nenhuma linha duplicada no
  MANIFEST.
- Contagem de recursos: 378 no CSV, batendo com o que a API devolve por dataset.
- `MANIFEST.md` fechou o dia com 135 linhas (133 de SEEDF+PDAD, 2 de INEP).

## 8. Pendências deste registro

- INEP: `divulgacao_brasil_ideb_2025.zip` (linha Brasil), três zips de escola por
  etapa (~112 MB cada), `tx_rend_escolas_2025.zip`, `TDI_2025_ESCOLAS.zip`,
  `tnr_escolas_2025.zip`.
- Malha das RAs, para qualquer mapa futuro.
- Censo 2022 (IBGE) com idade simples por RA: resolveria o denominador 0–3.
