# Plan — split `12_build_site.py` into a package and move code identifiers to English

**Date:** 2026-11-10
**Contract:** [docs/FASE-1.md](../FASE-1.md) (§5.3, build interface)
**Build:** [scripts/12_build_site.py](../../scripts/12_build_site.py)
**Worklog:** `docs/worklogs/2026-11-10-01-refatorar-build-site.md` (new; Portuguese, like the other worklogs)
**Order:** plan 0 of 3. [sumario-por-ra](2026-11-10-sumario-por-ra.md) runs after this one and
[sumario-da-escola](2026-11-10-sumario-da-escola.md) after that; both are written against the
module layout and the English names defined here.

This plan is in English at the maintainer's request. `AGENTS.md` §Conventions says docs are in
Portuguese; see Q1. User-facing strings of the site, CLI vocabulary, comments and docstrings stay
in Portuguese everywhere.

## 1. Motivation and origin

`scripts/12_build_site.py` has 1,862 lines and five responsibilities in one file: data loading
(`carregar_dados`), page rendering (`PaginaEscola`, 265 lines in one `render`), inline CSS (181
lines) and JS, the acceptance checks (about 450 lines) and the CLI. Every pending change touches the
same regions: the CSS string, `@media print`, `documento()`, `main` and the `--check` list. Each
new check costs four edits in `main` (option, list, `elif`, dispatch dict). Two plans already queue
up on top of this file and cite each other's line numbers.

Two constraints from `AGENTS.md` shape the plan:

- *Code is in English: identifiers, filenames, functions, modules.* The script uses Portuguese
  identifiers (`PaginaEscola`, `check_estados`, `carregar_dados`, and every local).
- *Every script runs from scratch, opens with a docstring naming input, output and idempotence.*
  Library modules under `scripts/` follow the `scripts/_common.py` precedent.

The split is cheap and safe here because the build is deterministic: the contract (§5.3) forbids
`datetime.now()` and fixes iteration order, and `check_reproducibility` already compares two builds.
"No behavior change" is therefore a byte comparison of `site/`, not a judgment call.

## 2. Current state (HEAD `05fc4dc`; use symbols, not line numbers, after the first commit)

| Responsibility | Symbols | Lines |
|---|---|---:|
| Contract constants | `ETAPAS` … `SLUG_POR_ETAPA_LABEL`, `*_PADRAO`, `TAMANHO_MAXIMO_SITE` | 37–105 |
| Error type | `BuildError` | 107–110 |
| Loading and validation | `_sha256`, `_int_ou_none`, `_registros_por_familia`, `carregar_dados`, `indicador`, `tem_*` | 115–319 |
| Formatting | `fmt_int`, `fmt_dec`, `fmt_anos`, `slug_etapa`, `titulo_etapa`, `palavra_aluno` | 322–353 |
| School page | `PaginaEscola` (`render` alone is 543–807) | 355–807 |
| CSS | `CSS` (no backslashes, one literal) | 814–994 |
| Shared layout | `documento` | 997–1019 |
| Index page + its JS | `pagina_index` (JS literal 1056–1096) | 1022–1097 |
| Static prose pages | `pagina_como_ler`, `pagina_creditos` | 1100–1262 |
| Build | `_limpar_saida`, `_tamanho`, `construir_site` | 1269–1342 |
| Checks | `_html`, `_json_escola`, `_ids_numeros`, `_hashes_site`, 7 `check_*` | 1345–1797 |
| CLI | `main` | 1800–1862 |

Facts that constrain the design:

- `12_build_site.py` is not importable (a module name cannot start with a digit); it must stay a
  thin CLI. Python puts `scripts/` first on `sys.path` when run as `python scripts/12_build_site.py`,
  so a sibling package imports without any CI change (as `_common` does for the other scripts).
- `.github/workflows/pages.yml` has no `paths:` filter and calls `python scripts/12_build_site.py …`;
  README, FASE-1 and worklogs cite the same command. The CLI surface must not move.
- `.gitignore` ignores `site/`, so no package may be called `site`.
- Only `docs/FASE-1.md:402` (`check_casos_limite`) names a code symbol in a normative doc; worklogs
  and older plans are historical and are not rewritten.

## 3. Decisions

### D1 — package `scripts/sitegen/`; `12_build_site.py` stays as a thin CLI

**Decision.** A sibling package `scripts/sitegen/`. `12_build_site.py` keeps its name (run-order
numbering, CI, docs), its docstring and `main`, and imports from `sitegen`.

**Why.** Same pattern as `_common.py`; no CI, README or FASE-1 command changes. `sitegen` cannot
collide with the ignored `site/`.

**Rejected.** `scripts/build/` (ambiguous with build artifacts); a top-level `src/` (new project
layout for one script); renaming the CLI (breaks CI, docs and the worklogs' commands). Do not run
the build with `-I` or `-P`: both drop `scripts/` from `sys.path`.

### D2 — no behavior change; the gate is a byte-identical `site/`

**Decision.** Every step passes gate G (§7): same `--check` output lines, same sha256 for every file
in `site/`, same `--help`, `data/public` untouched. The only exceptions are the deliberate edits
named per step (the registry in `main`, `render` → `_block_*`, the assets); each is covered by the
same byte gate.

**Why.** It converts "did the refactor break anything" into a diff that is empty or not.

**Rejected.** Reviewing by reading (does not scale to 1,862 lines); sampling pages (the contract, §8,
already forbids a 10-page sample).

### D3 — rename first, then split

**Decision.** Step 1 renames identifiers inside the single file; steps 2–6 then move code that is
already in English. New code (registry, `_block_*` methods, new modules) is authored in English from
the start.

**Why.** The rename is mechanical and easiest to verify in one file; the moves afterwards are pure
moves, which `git diff --color-moved` shows cleanly. Doing it the other way would touch ~25 files
with a second pass.

**Rejected.** Rename after the split (second churn across every module, plus the plans would have to
be written twice); rename and split in one commit (cannot attribute a failing gate).

### D4 — rename scope: Python identifiers only; strings are never renamed

**Decision.** The rename covers every Python identifier (modules, classes, functions, methods,
constants, parameters, keyword arguments, locals, attributes). It does **not** touch:

- **String literals of any kind**, including dict keys. In particular the data vocabulary stays
  Portuguese: parquet columns (`co_entidade`, `nome`, `ra`, `rede`, `oferta_*`, `mat_*`, `etapa`,
  `indicador`, `ano`, `estado`, `valor`, `item`), `procedencia.json` keys, the JSON keys written to
  `dados/*.json` and `indice.json`, the four states (`valor`, `zero`, `ausente`, `nao_aplicavel`),
  `data-situacao` values, and the loader's internal model keys (`escola["co"]`, `dados["por_co"]`,
  `dados["escolas"]`, `{"valor": …, "estado": …}`).
- **Output vocabulary**: HTML ids and anchors (`identificacao`, `ra-<slug>`), CSS class names
  (`.bloco`, `.ausencia`), `data-*` attributes, the Portuguese site copy and `PHRASE_*` values.
- **The CLI surface**: flags (`--limiar-n`, `--check-procedencia`, …), the printed `[ok] <key>`
  labels and the check keys (`procedencia`, `estados`, …). New flags and keys in later plans follow
  this surface (`--check-sumario`, `--check-sumario-escola`).
- **Comments and docstrings** (Portuguese by `AGENTS.md`), except that mentions of renamed
  *definitions* are updated by hand (§5, step 1).
- **JavaScript identifiers** inside the index script: they are emitted into `index.html`, which must
  stay byte-identical here. They are translated in plan 1, step 4, when that file is rewritten.
- Language-neutral single-letter names (`e`, `p`, `r`, `n`, `a`, `b`, `k`, `x`) and the INEP acronyms
  that name indicators (`tdi`, `tnr`, `ideb`).

**Why.** A string is data, and data names are the project's contract (`SCHEMA.md`, `FASE-1.md`). A
rename that crosses a string is not mechanical and changes bytes, parquet schemas (`06_analysis.py`,
`data/public` sha256) or public anchors. Keeping one rule — "tokens, not strings" — is what makes the
rename checkable by an AST comparison.

**Residue, stated honestly.** After this plan, internal dict keys such as `"por_co"` and `"co"`
remain Portuguese. Closing that needs a typed model (dataclasses with English attributes and one
translation at the `loader.py` boundary), which touches every access site and belongs in its own plan
(Q3).

**Rejected.** Renaming parquet columns (changes the insumo, its sha256, `06_analysis.py` and
`SCHEMA.md`); renaming CLI flags with aliases (breaks the CI command and every doc that quotes it for
no gain to a reader of the code); English CSS classes (changes every page's bytes).

### D5 — checks become a registry

**Decision.** `sitegen/checks/__init__.py` defines `CheckContext` and `Check` (frozen dataclasses)
and an ordered tuple `CHECKS`. `main` builds the `--check-*` flags and the `--check` list from it.

```python
@dataclass(frozen=True)
class CheckContext:
    public: Path; out: Path; data: dict; data_build: str; threshold: int

@dataclass(frozen=True)
class Check:
    key: str                 # printed as "[ok] <key>"; Portuguese, unchanged
    flag: str | None         # "--check-procedencia"; None = only inside --check
    help: str
    run: Callable[[CheckContext], str]
```

| key | flag | function (module) |
|---|---|---|
| `procedencia` | `--check-procedencia` | `check_provenance` (`provenance`) |
| `ranking` | — | `check_no_ranking` (`ranking`) |
| `limiar` | `--check-limiar` | `check_threshold` (`threshold`) |
| `estados` | `--check-estados` | `check_states` (`states`) |
| `reprodutibilidade` | — | `check_reproducibility` (`reproducibility`) |
| `licencas` | `--check-licencas` | `check_licenses` (`licenses`) |
| `casos_limite` | `--check-casos` | `check_edge_cases` (`edge_cases`) |

The tuple order is today's `--check` order. `help` strings are copied verbatim from the current
`add_argument` calls. Stop-at-first-failure and the `[ok]`/`[falhou]` printing stay as they are.
`--limiar-n` gets `dest="n_threshold"` **and** `metavar="LIMIAR_N"`, so `--help` stays identical (the
default metavar is derived from `dest`).

**Why.** A new check becomes one module plus one registry entry instead of four edits in `main`;
plans 1 and 2 each add one check this way.

**Rejected.** Auto-discovery by `import`-time decorators (hides the order, which is part of the
contract); keeping the dispatch dict (the status quo).

### D6 — CSS and JS become real files, with identical bytes

**Decision.** `sitegen/static/style.css` and `sitegen/static/search.js`, read once by
`sitegen/assets.py` into `CSS` and `JS_INDEX`. The files are extracted with `ast.literal_eval` from
the existing literals, not retyped.

- `CSS` today starts with a newline (the literal is `"""\n:root {…`). `assets.py` prepends `"\n"`
  with a comment, so `site/estilo.css` stays byte-identical and `style.css` starts at `:root`.
- `JS_INDEX` is the text between `<script>` and `</script>` (including the trailing newline after
  `})();`); `render_index_page` rebuilds `"\n<script>\n" + JS_INDEX + "</script>\n"`.
- The directory is `static/`, not `assets/`, to avoid an `assets/` directory next to `assets.py`.

**Why.** Editors, diffs and syntax highlighting work on real files; plans 1 and 2 edit both
substantially. The source file is `style.css`; the generated file stays `site/estilo.css` (public
name in FASE-1 §5.2).

### D7 — `SchoolPage.render` is split into one method per block (step 6)

**Decision.** `render` keeps the page header, the page-level notice and the footer, and calls nine
methods in the current order: `_block_identification`, `_block_offering`, `_block_enrollment`,
`_block_ideb`, `_block_flow`, `_block_age_grade_distortion`, `_block_non_response`,
`_block_infrastructure`, `_block_daycare`. Each returns the whole `<section>` as one string
(`"".join(parts)`). The `if e["oferta_inf_cre"] == 1` guard stays in `render` for now.

**Why.** Plan 2 needs a table of sections and plan 1 needs the identification block's RA row on its
own. This is the only step that is not a pure move; the order of `_add` calls fixes the order of
`numbers`, which is written to `dados/*.json`, and the byte gate covers that.

**Rejected.** Deduplicating the `fluxo`/`tdi`/`tnr` loops (same stage loop three times). It changes
state logic and needs its own plan and its own review; mixing it here would make a failing gate
unattributable.

### D8 — no template engine, no framework

**Decision.** HTML stays f-strings; JS stays plain; no Jinja2, Astro, Eleventy or UI framework.

**Why.** The pain is the 265-line function and the mixed responsibilities, not f-strings. Jinja2 is a
pip dependency, not a runtime, so the cost is smaller than "a second runtime", but `PaginaEscola._add`
records the provenance of each number *while rendering*; that coupling is the point of the project
and the blocks that register numbers would stay Python either way. FASE-1 §5.3 also says `jinja2`
does not enter the CI requirements. Reconsider Jinja2 for the two prose pages (`como-ler`,
`creditos`) once this split is done and editing prose still hurts; that would be a plan of its own.
Astro would add Node to CI, a JSON export contract, and would force the provenance coupling and the
regex checks to be rebuilt.

## 4. Target layout

```text
scripts/
├── 12_build_site.py              # docstring + main (about 60 lines)
└── sitegen/
    ├── __init__.py               # docstring only
    ├── errors.py                 # BuildError
    ├── contract.py               # constants (stages, phrases, years, limits)
    ├── loader.py                 # sha256, load_data, get_indicator, has_*
    ├── fmt.py                    # fmt_*, stage_slug, stage_title, student_word
    ├── school_page.py            # SchoolPage
    ├── layout.py                 # document
    ├── assets.py                 # CSS, JS_INDEX
    ├── static/
    │   ├── style.css
    │   └── search.js
    ├── index_page.py             # render_index_page
    ├── info_pages.py             # render_how_to_read_page, render_credits_page
    ├── build.py                  # _clean_output, _total_size, build_site
    └── checks/
        ├── __init__.py           # CheckContext, Check, CHECKS
        ├── common.py             # read_page, read_school_json, number_ids, site_hashes
        ├── provenance.py  ranking.py  threshold.py  states.py
        ├── reproducibility.py  edge_cases.py  licenses.py
```

Origin (HEAD line ranges): `errors` 107–110; `contract` 37–105; `loader` 115–319; `fmt` 322–353;
`school_page` 355–807; `static/style.css` 814–994; `layout` 997–1019; `index_page` 1022–1097 (JS
1057–1095 → `search.js`); `info_pages` 1100–1262; `build` 1269–1342; `checks/common` 1345–1358 and
1565–1571; `checks/*` 1360–1797; `main` 1800–1862 stays.

Dependency rules (no cycles): `errors` and `contract` import nothing from the package; `loader` and
`fmt` import those two; `school_page` imports `contract`, `loader`, `fmt`, `errors`; `layout` and
`assets` import nothing; `index_page` and `info_pages` import `layout` (and `assets` for the index);
`build` imports pages, `loader`, `assets`; `checks` import `build` and the lower modules; **`build`
never imports `checks`**.

Each new module opens with a Portuguese docstring in the `_common.py` style (Entrada / Saída /
Idempotente). `checks/*` modules keep each function body byte-for-byte; they only gain imports.

## 5. Rename specification (step 1)

The map is an input to the tool. This table was derived by reading the file at HEAD; step 1
re-derives the identifier list mechanically and any Portuguese identifier missing here is added to
the map before the run.

### 5.1 Module-level names

| Old | New |
|---|---|
| `DATA_BUILD_PADRAO`, `LIMIAR_N_PADRAO`, `TAMANHO_MAXIMO_SITE` | `DEFAULT_DATA_BUILD`, `DEFAULT_N_THRESHOLD`, `MAX_SITE_BYTES` |
| `ETAPAS`, `ETAPA_LABEL`, `ETAPA_SLUG` | `STAGES`, `STAGE_LABEL`, `STAGE_SLUG` |
| `MAT_COLS`, `MAT_LABEL` | `ENROLLMENT_COLUMNS`, `ENROLLMENT_LABEL` |
| `OFERTAS`, `INFRA_ITENS` | `OFFERINGS`, `INFRA_ITEMS` |
| `ANOS_IDEB`, `ANOS_IDEB_ETAPA` | `IDEB_YEARS`, `IDEB_YEARS_BY_STAGE` |
| `REDES`, `ESTADOS` | `NETWORKS`, `STATES` |
| `FRASE_ETAPA`, `FRASE_IDEB_PRIVADA`, `FRASE_IDEB_PUBLICA` | `PHRASE_STAGE_NOT_OFFERED`, `PHRASE_IDEB_PRIVATE`, `PHRASE_IDEB_PUBLIC` |
| `FRASE_CENSO_2024_SEM_LINHA`, `FRASE_MATRICULA_2024`, `FRASE_MATRICULA_2025` | `PHRASE_CENSUS_2024_NO_ROW`, `PHRASE_ENROLLMENT_2024`, `PHRASE_ENROLLMENT_2025` |
| `FRASE_SEM_INDICADOR`, `FRASE_INFRA_NAO_APLICAVEL`, `FRASE_N_PEQUENA` | `PHRASE_NO_INDICATOR`, `PHRASE_INFRA_NOT_APPLICABLE`, `PHRASE_SMALL_N` |
| `FAMILIAS_N_ALUNOS`, `SLUG_POR_ETAPA_LABEL` | `STUDENT_COUNT_FAMILIES`, `SLUG_BY_STAGE_LABEL` |
| `_sha256`, `_int_ou_none`, `_registros_por_familia` | `sha256`, `_int_or_none`, `_records_by_family` |
| `carregar_dados`, `indicador` | `load_data`, `get_indicator` |
| `tem_ideb_publicado`, `tem_linha_de_taxa` | `has_published_ideb`, `has_rate_row` |
| `fmt_anos`, `slug_etapa`, `titulo_etapa`, `palavra_aluno` | `fmt_years`, `stage_slug`, `stage_title`, `student_word` |
| `PaginaEscola` | `SchoolPage` |
| `documento`, `pagina_index` | `document`, `render_index_page` |
| `pagina_como_ler`, `pagina_creditos` | `render_how_to_read_page`, `render_credits_page` |
| `_limpar_saida`, `_tamanho`, `construir_site` | `_clean_output`, `_total_size`, `build_site` |
| `_html`, `_json_escola`, `_ids_numeros`, `_hashes_site` | `read_page`, `read_school_json`, `number_ids`, `site_hashes` |
| `check_procedencia`, `check_sem_ranking`, `check_limiar` | `check_provenance`, `check_no_ranking`, `check_threshold` |
| `check_estados`, `check_reprodutibilidade`, `check_casos_limite`, `check_licencas` | `check_states`, `check_reproducibility`, `check_edge_cases`, `check_licenses` |

`BuildError`, `CSS`, `main`, `fmt_int`, `fmt_dec` are already English and unchanged. `_sha256`,
`_html`, `_json_escola`, `_ids_numeros` and `_hashes_site` lose the underscore because they become
cross-module helpers.

### 5.2 `SchoolPage` members

`mat_span` → `enrollment_span`; `mat_ausencias` → `enrollment_absences`; `fonte` → `source_note`;
`ausencia` → `absence`; `pequena` → `small_n`; `_cabecalho_bloco` → `_section_heading`; `_artigo` →
`_stage_article`; attributes `por_id` → `by_id`, `mat_cache` → `enrollment_cache`, `numeros` →
`numbers`, `limiar` → `threshold`. `_add`, `rate_span`, `ideb_cell`, `render`, `self.d`, `self.e`,
`self.data_build` are unchanged (`d` and `e` are single letters; a readability rename of them is out
of scope).

### 5.3 Locals, parameters and keyword names (one flat map)

- **Domain.** `escola→school`, `escolas→schools`, `escolas_df→schools_df`, `co→code`,
  `por_co→by_code`, `ra→region`, `por_ra→by_region`, `etapa→stage`, `etapas→stages`,
  `etapa_label→stage_label`, `etapas_puladas→skipped_steps`, `oferta→offering`,
  `oferece_etapa_avaliada→offers_assessed_stage`, `ano→year`, `anos→years`, `ano_2025→year_2025`,
  `valor→value`, `estado→state`, `estados_n_null→states_when_n_null`, `familia→family`,
  `fonte→source_note`, `fontes→sources`, `por_fonte→by_source`, `licenca→license_name`,
  `licencas_por_fonte→licenses_by_source`, `licenca_por_fonte→license_by_source`,
  `declaracao→declaration`, `registro→record`, `registros→records`,
  `registro_numero→number_record`, `numero→number`, `numeros→numbers`, `id_numero→number_id`,
  `identificador→identifier`, `indicadores→indicators`, `indicadores_df→indicators_df`,
  `procedencia→provenance`, `execucao→execution`, `dados→data`, `dados_dir→data_dir`.
- **Page assembly.** `partes→parts`, `corpo→body`, `texto→text`, `texto_visivel→visible_text`,
  `trecho→snippet`, `frase→phrase`, `frases→phrases`, `rotulo→label`, `titulo→title`,
  `linhas→rows`, `celula→cell`, `simbolo→symbol`, `prefixo→prefix`, `palavra→word`,
  `ancora→anchor`, `situacao→status`, `bloco→block`, `pagina→page`, `resultado→result`,
  `html_num→number_html`.
- **Flags and predicates.** `tem_ideb→has_ideb`, `tem_taxa→has_rate`, `tem_valor→has_value`,
  `universo_infra→infra_universe`, `exige_referencia→requires_reference`,
  `n_referencia→n_reference`, `limites→limits`, `limiar→threshold`, `atual→current`,
  `anterior→previous`.
- **Loader and checks.** `nome→name`, `nomes→names`, `chave→key`, `campo→field`, `mapa→mapping`,
  `coluna→column`, `colunas_2024→columns_2024`, `preenchidas→filled`, `faltantes→missing`,
  `real→actual`, `reg→entry`, `lista→entries`, `indice→index_entries`, `caminho→path`,
  `alvo→target`, `proibidos→forbidden`, `termo→term`, `minusculo→lowercase`,
  `creditos→credits_html`, `obrigatorio→required`, `unidades→units`, `com_tdi→with_tdi`,
  `sem_matricula→without_enrollment`, `nota→note`, `achado→found_block`, `taxas→rates`,
  `mascara→mask`, `base_temporaria→temp_base`, `diferentes→differing`, `altera→alter`,
  `selecionados→selected`, `verificacoes→checks_by_key`, `detalhe→detail`.
- **Scope overrides** (keyed by the *old* function name, because the tool runs on the old file):
  `carregar_dados: indicador→indicator` (the loader shadows the function with a string today, and
  keeps doing so); `pagina_creditos: fonte→source` and `check_licencas: fonte→source` (locals; the
  global `fonte→source_note` is the method).
- **Never renamed.** Attributes of `args` (`args.limiar_n`, `args.check_procedencia`, …): their names
  derive from the flag strings; step 5 replaces them. `builtins` and names such as `license`,
  `credits`, `match`, `id` are avoided as targets (hence `license_name`, `credits_html`,
  `found_block`); `id` already exists as a parameter and stays.

The tool refuses to run if the map is not injective, if a target already exists as an identifier in
the file, or if a target is a builtin or a keyword.

## 6. Execution plan

Each step is one commit and passes gate G (§7). Commit the three plan files first so the tree is
clean.

### Step 0 — Baseline and throwaway tools

- [ ] `git status --short` shows nothing under `scripts/`, `docs/FASE-1.md`, `data/public/`.
- [ ] Build the golden at HEAD (commands in §7) and store it in `/tmp/opencode/golden/`: `check.txt`
  (the `[ok]`/`[falhou]` lines), `site.sha`, `help.txt`, `orig.py`. **If `--check` does not pass at
  HEAD, stop**: there is no baseline to preserve.
- [ ] Write three throwaway tools in `/tmp/opencode/` (not versioned; contracts in §8):
  `rename_idents.py`, `verify_rename.py`, `move_check.py`.

### Step 1 — Rename identifiers in place

- [ ] Run the AST inventory over `scripts/12_build_site.py` (every `Name`, `arg`, `keyword`,
  `Attribute`, def/class name, import alias, `except … as`). Review it against §5; add what is
  missing to `/tmp/opencode/rename_map.json`.
- [ ] Run `rename_idents.py` on the file; review its list of mapped *attribute* occurrences whose
  receiver is not `self`, `p` or `args` (guards against a map key that is also an external API
  name).
- [ ] Run `verify_rename.py orig.py scripts/12_build_site.py rename_map.json`: empty output.
- [ ] Update, by hand, comments and docstrings that mention a renamed *definition* (examples at HEAD:
  `mat_ausencias` in `mat_span`'s docstring, `carregar_dados` in `check_casos_limite`'s). `grep` the
  old def names; do nothing to prose that merely contains a Portuguese word.
- [ ] Gate G. `git diff --stat` lists only `scripts/12_build_site.py`.
- [ ] Save the renamed file as `/tmp/opencode/golden/renamed.py` (the reference for steps 2–6).

### Step 2 — Core modules

- [ ] Create `sitegen/__init__.py`, `errors.py`, `contract.py`, `fmt.py`, `loader.py` by moving the
  corresponding definitions; the script imports them from `sitegen`.
- [ ] Gate G; `move_check.py` (identity: only imports, module docstrings and the script's own
  header differ).

### Step 3 — Assets and pages

- [ ] Extract `CSS` and the index JS with `ast.literal_eval` into `static/style.css` and
  `static/search.js`; create `assets.py` (with the `"\n"` prefix for the CSS, §D6).
- [ ] Create `layout.py`, `index_page.py` (uses `JS_INDEX`), `info_pages.py`.
- [ ] Gate G. `move_check.py` allows only `render_index_page` (JS literal) and `CSS` to differ.

### Step 4 — `school_page` and `build`

- [ ] Create `school_page.py` (`SchoolPage` unchanged) and `build.py` (`_clean_output`,
  `_total_size`, `build_site`).
- [ ] Gate G; `move_check.py` as in step 3.

### Step 5 — Checks package, registry, slim `main`

- [ ] Create `checks/common.py`, the seven check modules (bodies unchanged) and
  `checks/__init__.py` with `CheckContext`, `Check`, `CHECKS` (table in D5).
- [ ] Rewrite `main`: flags and the `--check` list come from `CHECKS`; `--limiar-n` uses
  `dest="n_threshold"` and `metavar="LIMIAR_N"`; individual flags are read with
  `getattr(args, check.flag[2:].replace("-", "_"))`; the `ERRO:` and `[falhou]` paths and exit codes
  stay.
- [ ] Gate G; `move_check.py` allows `main`, `CSS`, `render_index_page` to differ.
- [ ] Mutation tests (§7), each on a clean tree and reverted afterwards.

### Step 6 — `SchoolPage.render` into `_block_*`

- [ ] Replace the nine in-line sections with the nine methods of D7, in the same order, each
  returning `"".join(parts)`; `render` appends their results.
- [ ] Gate G. The site hash is the proof; `move_check.py` now allows `SchoolPage.render` and the nine
  new methods.

### Step 7 — Docs and worklog

- [ ] `README.md`: replace the one `12_build_site.py` line of the `scripts/` tree with the thin CLI
  plus `sitegen/` and a one-line description.
- [ ] `docs/FASE-1.md`: §5.3 gets one sentence (the build lives in `scripts/sitegen/`;
  `12_build_site.py` is the CLI); line 402 `check_casos_limite` → `check_edge_cases`.
- [ ] The docstring of `12_build_site.py` mentions the package.
- [ ] `docs/worklogs/2026-11-10-01-refatorar-build-site.md` (Portuguese: *O que entrou*, *Decisões*,
  *Verificação* with the gate output pasted, *Pendências* with Q3), including the explicit sentence
  that `data/public` and `site/` bytes did not change.
- [ ] Not touched: `SCHEMA.md`, `requirements.txt`, `.github/workflows/pages.yml`, historical
  worklogs and older plans.

## 7. Verification

### Gate G (run at every step)

```sh
G=/tmp/opencode/golden; W=/tmp/opencode/work; mkdir -p "$G" "$W"

# step 0 only, from a clean HEAD
.venv/bin/python scripts/12_build_site.py --public data/public --out "$G/site" \
  --data-build 2026-11-06 --check | grep -E '^\[(ok|falhou)\]' > "$G/check.txt"
(cd "$G/site" && find . -type f -exec sha256sum {} + | sort -k2) > "$G/site.sha"
COLUMNS=100 .venv/bin/python scripts/12_build_site.py --help > "$G/help.txt"
cp scripts/12_build_site.py "$G/orig.py"

# every step
.venv/bin/python -m compileall -q scripts
rm -rf "$W/site"
.venv/bin/python scripts/12_build_site.py --public data/public --out "$W/site" \
  --data-build 2026-11-06 --check | grep -E '^\[(ok|falhou)\]' | diff - "$G/check.txt"
(cd "$W/site" && find . -type f -exec sha256sum {} + | sort -k2) | diff - "$G/site.sha"
COLUMNS=100 .venv/bin/python scripts/12_build_site.py --help | diff - "$G/help.txt"
git diff --stat -- data/public          # empty
git status --short                      # only the files of the step; site/ never appears
```

`check.txt` has seven `[ok]` lines at HEAD (procedencia, ranking, limiar, estados,
reprodutibilidade, licencas, casos_limite). All diffs must be empty.

### Mutation tests (step 5; clean tree, `git checkout -- scripts/sitegen` after each)

| Mutation | Command | Expected |
|---|---|---|
| `SchoolPage._add` writes `"limites": []` | `… --check-procedencia` | `[falhou] procedencia` |
| literal `p90` added to `como-ler` text in `info_pages.py` | `… --check` | `[falhou] ranking` |
| `rate_span`: the `"-"` of the `ausente` branch becomes `"0"` | `… --check-estados` | `[falhou] estados` |

They prove the moved checks still fail when they should, which the byte gate cannot.

## 8. Throwaway tool contracts (`/tmp/opencode/`, not versioned)

- **`rename_idents.py <map.json> <file>`** — tokenizes with `tokenize` (Python 3.12 emits NAME tokens
  inside f-string replacement fields), replaces only NAME tokens by (row, col) span so formatting,
  comments and strings are untouched; honors `scope_overrides` by function line range and skips
  attributes of `args`; enforces the injectivity, collision and builtin checks of §5.3.
- **`verify_rename.py <old.py> <new.py> <map.json>`** — independent of the tokenizer: applies the same
  map with an `ast.NodeTransformer` (`Name.id`, `arg.arg`, `keyword.arg`, `Attribute.attr`,
  `FunctionDef.name`, `ClassDef.name`, `alias`, `ExceptHandler.name`, same overrides and `args`
  exception) to the old tree and compares `ast.dump` with the new tree, docstrings blanked on both
  sides. Any difference is printed.
- **`move_check.py <renamed.py> <package-dir> [--allow name,…]`** — for every top-level `def`, class
  (method by method) and assignment of the reference file, finds it exactly once in the package and
  compares `ast.dump`; names in `--allow` may differ; imports, module docstrings and the script's
  header are ignored; unmatched or duplicated names fail.

## 9. Risks and open questions

### Risks

- **The byte gate does not exercise error branches.** The mutations of §7 cover one failure per check
  family; the `move_check.py` AST comparison covers the rest of the moved bodies.
- **Step 6 is the only non-mechanical edit to rendering.** Mitigation: it is its own commit and the
  hash of every `dados/*.json` proves the order of `_add` calls.
- **Tool bug in the rename.** Two independent mechanisms (token rewrite, AST transform) must agree;
  the attribute-receiver review catches a map key that collides with an external API.
- **Review noise.** Git does not track code moved between files; use one commit per step and
  `git diff --color-moved=dimmed-zebra`.
- **Assets read at import.** A missing `static/` file becomes a traceback instead of `ERRO:`; that is
  a development error, not a data error.
- **`sys.path` assumption.** `python scripts/12_build_site.py` works; `-I` or `-P` do not. CI does not
  use them.
- **Plans 1 and 2 cite names.** They are already written against this layout; if a name changes here,
  update them in the same commit.

### Open questions

- **Q1 — language of `docs/plans/`.** `AGENTS.md` says docs are in Portuguese. Recommendation: add one
  line to §Conventions ("`docs/plans/` are in English; worklogs and the contract stay in Portuguese")
  so the exception is declared rather than silent. Not done here: `AGENTS.md` is the maintainer's file.
- **Q2 — throwaway tools.** Kept out of the repo (they check a one-time migration). If the maintainer
  wants them versioned, they need a home (for example `scripts/dev/`) and the `AGENTS.md` script
  docstring rule applies to them.
- **Q3 — typed model.** Replace the string-keyed `escola`/`dados` dicts with dataclasses whose
  attributes are English, translating the Portuguese data vocabulary once in `loader.py`. Recommended
  as a separate plan after plan 2; it is the remaining half of "code in English".

## 10. Out of scope

- Any change to rendered HTML, `dados/*.json`, `indice.json`, `estilo.css` bytes or `data/public`.
- Deduplicating the `fluxo`/`tdi`/`tnr` stage loops; Jinja2 or any framework; new dependencies.
- Renaming parquet columns, JSON keys, CSS classes, HTML ids, CLI flags or check keys.
- Translating the JavaScript identifiers (plan 1, step 4) or renaming `self.d` / `self.e`.
- Changing `pages.yml`, README commands or the CI command.

## 11. Definition of done

- [ ] `scripts/12_build_site.py` is at most about 70 lines; no `sitegen` module exceeds about 500
  lines.
- [ ] Gate G passes at every commit; the final `site/` hashes equal the step-0 golden; the three
  mutations fail as expected.
- [ ] No Portuguese identifier remains in `scripts/12_build_site.py` or `scripts/sitegen/` except the
  residue listed in D4 (strings, `self.d`/`self.e`, single letters, INEP acronyms, JS identifiers
  until plan 1).
- [ ] `git diff -- data/public` empty; `requirements.txt` and `pages.yml` unchanged; `site/` out of
  git.
- [ ] README, FASE-1 and the worklog describe the new layout; no undocumented manual step; the build
  is still idempotent.
