# Prova dos Nove

Public-interest project: make Brazilian public education data legible. Product is
one page per school, in plain Portuguese, where every number traces back to
source, year and computation. Audience: educators, journalists, general public.
Solo maintainer, no institutional access, open data only. Starts in DF; designed
for Brazil.

## Data rules

- Every published number carries file, year and computation. Internal reports
  included.
- Zero, absent and not-applicable are three distinct states. Never collapse them
  into NaN, and never fill a gap with zero, a mean or silent interpolation. A
  private school without IDEB did not sit the SAEB — that is absence, not
  zero performance.
- School- and territory-level data only. Never scrape nominal lists, including
  the ieducar creche queue.
- No school rankings.
- If data does not exist, say so and name what would exist in its place. If a
  hypothesis fails, report that instead of hunting for a slice that saves it.

## Conventions

- Code is in English: identifiers, filenames, functions, modules. Docs
  (`REPORT.md`, `SCHEMA.md`, `MANIFEST.md`, `README.md`), comments and docstrings
  are in Portuguese.
- Keep original source field names verbatim when mirroring them (`CO_ENTIDADE`,
  `NO_ENTIDADE`); record every rename in `SCHEMA.md`.
- Scripts numbered by run order: `01_inventory_seedf.py`, `02_download_seedf.py`.
- `data/raw/` is immutable. Normalized output goes to `data/interim/` as
  parquet.
- `data/` never enters git; `data/raw/MANIFEST.md` does.
- Every script runs from scratch with no undocumented manual step, and opens
  with a docstring naming input, output and whether it is idempotent.

## Tooling

Python 3.12. Environment created with `uv`; dependencies pinned in
`requirements.txt`:

```sh
uv venv .venv
uv pip install -r requirements.txt
.venv/bin/python scripts/01_inventory_seedf.py
```

Geo libraries (`geopandas`, `shapely`) enter `requirements.txt` only after the RA
mesh is validated: provenance, CRS, and name/code agreement with SEEDF and PDAD.
Until then, analyses are non-spatial.

## Sources and traps

- **SEEDF (CKAN)** — `https://data.se.df.gov.br/`. Enumerate with
  `api/3/action/package_list`, fetch with `api/3/action/package_show?id=<name>`,
  download each resource's `url`. Historic series cover all networks (public,
  conveniada, private). Detect CSV separator and encoding; do not assume.
- **INEP Censo Escolar** — school key `CO_ENTIDADE`, `CO_UF=53`,
  `CO_MUNICIPIO=5300108`. National microdata is large: filter to DF, discard the
  rest, document the procedure.
- **IDEB by school** — the INEP BI filters by administrative dependency,
  including private. Private SAEB coverage is irregular, so absence of a result
  is absence of participation.
- **Keys** — SEEDF series may not use `CO_ENTIDADE`. Build the crosswalk and
  measure the match rate before any join. An unmeasured join is a guess.
- **PDAD/IPEDF** — `https://pdad.ipe.df.gov.br/`, aggregated by Região
  Administrativa. Confirm an age band of 0–3 exists before promising a creche
  deficit map.

## Workflow

Download → `MANIFEST.md` (URL, date, bytes, sha256) → profile → `SCHEMA.md`
(grain, key, types, nulls, years) → analysis → `REPORT.md` with sourced numbers.

When a source blocks scripted download (`download.inep.gov.br`: connection reset
from `urllib`/`curl` in this environment, HTTP 200 from the browser), the path is
declared, not hidden: browser download → `data/raw/inep/inbox/` →
`scripts/07_ingest_inep.py` (hash, MANIFEST, catalogue of what is missing) →
`scripts/08_profile_inep.py` (profile and DF slice). Never imply that an
automated download worked, and never register a file that was not verified.

## Done

Script runs clean from scratch, `SCHEMA.md` describes what entered, `REPORT.md`
cites every number, gaps are named. Missing any of these, it is not done.

## State

Phase 0 — DF reconnaissance. Nothing published. Recon session of 2026-10-22 done:
80 SEEDF files, 53 PDAD-A 2024 reports, 10 INEP files and the RA mesh (144
MANIFEST rows) downloaded, profiled and analysed in `REPORT.md`; `SCHEMA.md`
covers grain, keys and measured crosswalk. INEP is reachable from the browser but
not from the script environment, so its files come in by hand through
`data/raw/inep/inbox/` (catalogue in `07_ingest_inep.py`, profile and DF slice in
`08_profile_inep.py`); ten ingested — Ideb 2025 by UF, by Brasil, the three
school-level files, the ensino médio with the integrado à EPT, the taxas de
rendimento por escola, the distorção idade-série por escola, the taxa de
não-resposta por escola and the nota informativa. The RA mesh came from the
IDE/DF ArcGIS service (`09_download_malha.py`): 37 RAs, 35 with a match in the
2025 school census and PDAD-A 2024; `26 de Setembro` and `Ponte Alta` exist only in
the mesh.

Established finding (source of truth: `q8_df_brasil_uf.csv`; all UFs, 2023 and
2025), DF total / state network, 2025: anos iniciais 6,4 / 6,0 (8th of 27, 16th of
26), anos finais 5,1 / 4,6 (11th, 21st of 27), ensino médio regular 4,1 / 3,6
(22nd, last of 27). Brasil 6,3 / 5,3 / 4,5. With the integrado à EPT the state
network is still last of 27 (3,6, same as the regular cut; `q9_em_integrado.csv`).
The school-level files reproduce the SEEDF series value for value (3.512 + 1.542 +
222 values, 0 divergences) and publish no private-school Ideb after 2017 — private
coverage exists only as a network aggregate in the UF/Brasil spreadsheets.
Private-school flow is now visible (`tx_rend_escolas_2025.zip`): in ensino médio
the median approval is 98.3% in the private network (139 schools) against 82.5% in
the state network (101), with dropout 0.0% against 2.4% (`q10_fluxo_df.csv`).
Age-grade distortion (`TDI_2025_ESCOLAS.zip`, 2025) separates the networks in the
same direction: state median 9.0% / 17.1% / 20.7% (AI/AF/EM) against 1.2% / 3.2% /
4.5% in the private network, and in AF/EM the state p10 sits above the private p90
(`q11_distorcao_df.csv`). The non-response rate (`tnr_escolas_2025.zip`) does not
explain the missing Ideb: it measures missing rendimento/movimento information,
not SAEB participation, it has no field separating non-participation from
suppression, and schools with and without Ideb share the same distribution
(`q12_tnr_ideb_ausente.csv`). TDI and TNR cover the same 925 DF schools, all
matched to the 2025 census (100%), including 336 private ones.

Open: the 0–3 population is resolved from the PDAD-A microdata (139.116 children in
the DF; 27,1% in creche, ±2,5 p.p.). What remains is per-RA precision (14–184 people
per RA, 6–36 p.p. half-width): only census-tract aggregates with a tract → RA key, or
a PDAD-A release carrying strata and primary sampling units, would settle it. Until
then per-RA figures enter as clusters, never as a rate per RA. The birth date
(`E02_1`) is filled for 49,6% of rows, so the 31/03 convention cannot replace the
interview age. Two method errors were corrected on 2026-10-23: the "36,2% of creche
enrolment is 4+" reading (age in the census year is not age on 31/03) and the library
figure (three distinct INEP items — biblioteca, sala de leitura and the union of both
— over a universe restricted to schools offering fundamental/médio). No population by
RA from Censo 2022 ingested (IBGE API only reaches the DF as one municipality).
Analyses still use `CO_RA` as an attribute and produce no map, so geo libraries stay
out of `requirements.txt` for now.
