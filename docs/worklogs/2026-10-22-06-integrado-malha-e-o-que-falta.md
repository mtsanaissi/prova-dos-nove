# 2026-10-22 — 06. Médio com o integrado à EPT, malha das RAs e o que não abriu

Objetivo: testar se o último lugar do DF no ensino médio sobrevive à inclusão do
integrado à EPT; localizar a malha das Regiões Administrativas; e tentar fechar
os outros itens de `REPORT.md` §5. Scripts: `07`, `08`, `09` (novo) e `q9` de
`06_analysis.py`.

## 1. O arquivo do integrado entrou (`07`)

`divulgacao_ufs_Ensino_Medio_integrado_ideb_2025.xlsx`, 31.398 B — o catálogo
previa 21.287 B. Vale o tamanho do arquivo que entrou, e o `MANIFEST.md` registra
a diferença. `07` calculou sha256 e o moveu para `data/raw/inep/`; o catálogo foi
corrigido para 31.398 B.

## 2. Leitura (`08`): mesma receita, um recorte novo

Planilha solta, uma aba (`UF (EM_integrado)`), 5 linhas de título, cabeçalho em
três faixas, códigos na linha 10. 27 UFs, rede sempre `Estadual`, anos 2017–2025
(bienal), só `VL_OBSERVADO_YYYY`, sem meta nem linha Brasil/regiões. A primeira
coluna é o nome da UF por extenso, sem código — três UFs mudam de forma em
relação à planilha regular (`R. G. do Norte`, `R. G. do Sul`, `M. G. do Sul`), e
o mapa `UFS_POR_EXTENSO` normaliza em `local_base`.

`processar_uf_em_integrado()` gera `ideb_uf_em_integrado_tidy.parquet` (135
linhas = 27 UFs × 5 anos). `etapa = EM_integrado`, de propósito: é outro recorte
do mesmo indicador e não pode ser empilhado com `EM` sem aviso.

## 3. O último lugar sobrevive (`q9`)

| Ano | DF integrado | Posição | DF regular | Posição |
|---|---|---|---|---|
| 2023 | 3,7 | 18º de 27 | 3,7 | 18º de 27 |
| 2025 | 3,6 | **27º de 27** | 3,6 | **27º de 27** |

A inclusão do integrado muda 10–11 UFs em 0,1–0,2 e **não muda o DF**: o valor é
o mesmo nos dois recortes, e a posição também. Em 2025 o DF fica sozinho em 3,6;
Roraima, Amapá, Amazonas e Rio de Janeiro vêm em 3,7. Saída:
`data/interim/q9_em_integrado.csv`.

## 4. Malha das RAs localizada e validada (`09_download_malha.py`)

A sessão anterior não a havia encontrado porque os portais do GDF estavam
fechados (certificado). O serviço ArcGIS do IDE/DF respondeu:

- `https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/LIMITES/FeatureServer/1`,
  camada "Regiões Administrativas", 37 feições, EPSG:31983 no serviço;
- GeoJSON em EPSG:4326, 4,58 MB, guardado em `data/raw/malha/` e registrado no
  `MANIFEST.md` (download automático, sem bloqueio).

Validação por atributo, sem geometria (`malha_ra_validacao.csv`):

- 35 das 37 RAs aparecem **nas duas** fontes de educação (cadastro SEEDF 2025 e
  PDAD-A 2024);
- `26 DE SETEMBRO` (RA-XXXVI) e `PONTE ALTA` (XXXVII) existem só na malha —
  não aparecem no cadastro de 2025 nem na PDAD-A 2024;
- nenhuma RA presente nas duas fontes falta na malha;
- o Censo 2022 não delimitou Arapoanga e Água Quente (incluídas em Planaltina e
  Recanto das Emas), então a malha de 37 RAs não é comparável a qualquer tabela
  censitária por RA sem essa ressalva.

Nenhuma análise passou a usar geometria e não há mapa; `geopandas`/`shapely`
continuam fora de `requirements.txt`.

## 5. O que **não** abriu

- **População de 0–3 anos por RA.** A API do IBGE responde (Censo 2022, tabela
  9514), mas o DF é um único município (`5300108`): não há recorte por RA. As
  tabelas por RA existem apenas nos agregados por setor censitário, que exigiriam
  a malha de setores e uma chave setor → RA — fora do escopo desta sessão. O
  Informe Demográfico do IPEDF (Censo 2022) trabalha densidade, não idade por RA,
  e avisa que Arapoanga e Água Quente ainda não estavam delimitadas. A PDAD-A não
  expõe microdados por API (só os 53 relatórios). A taxa de creche continua sendo
  um limite superior com denominador 0–4.
- **Fluxo escolar da rede privada.** Só existe em `tx_rend_escolas_2025.zip`
  (INEP), que depende do mesmo caminho manual pelo navegador.
- **Infraestrutura de 2016 e os 277 códigos que desaparecem.** Nenhum dado aberto
  resolve; é contato institucional.

## Reprodução

```sh
.venv/bin/python scripts/07_ingest_inep.py
.venv/bin/python scripts/08_profile_inep.py
.venv/bin/python scripts/09_download_malha.py
.venv/bin/python scripts/06_analysis.py
```

`09` é o único script que baixa a malha; rodar de novo não rebaixa (o arquivo
existe) e reescreve a validação.

> **Nota posterior (2026-10-23).** A população de 0–3 por RA foi resolvida pelos
> microdados da PDAD-A (L-52), com resíduo de precisão (L-17); a taxa de creche
> não usa mais denominador 0–4. Ver `docs/LIMITES.md`.
