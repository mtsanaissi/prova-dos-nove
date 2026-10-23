# Prova dos Nove

Public-interest project: make Brazilian public education data legible. Product is
one page per school, in plain Portuguese, where every number traces back to
source, year and computation. Audience: educators, journalists, general public.
Solo maintainer, no institutional access, open data only. Starts in DF; designed
for Brazil.

This file is durable: it holds rules and conventions, not status. Current phase,
numbers and gaps live in `README.md` (§Estado), `REPORT.md` and `docs/worklogs/`.

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
mesh is validated: provenance, CRS, and name/code agreement with SEEDF and PDAD,
and only when an analysis actually uses geometry.

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
