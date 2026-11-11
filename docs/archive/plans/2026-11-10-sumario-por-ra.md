# Plan — jump to an Administrative Region (RA) on the FASE-1 index

**Date:** 2026-11-10
**Contract:** [docs/FASE-1.md](../../FASE-1.md)
**Depends on:** [plan 0 — refatorar-build-site](2026-11-10-refatorar-build-site.md) (package `scripts/sitegen/`, English names, check registry, `SchoolPage._block_*`)
**Input:** [data/public/](../../../data/public/) (unchanged)
**Worklog:** `docs/worklogs/2026-11-10-02-sumario-por-ra.md` (new; Portuguese)
**Criterion:** adds criterion **7** to FASE-1 §8; `--check` goes from seven to eight items.

Anchors in this plan are **symbols and modules**, not line numbers; the monolith they used to point
into no longer exists after plan 0.

## 1. Motivation and origin

The entry page (`site/index.html`) is defined in [`docs/FASE-1.md`](../../FASE-1.md) §2.1: search by
name, no server, and a list of the 1,291 schools grouped by the 35 Administrative Regions in
alphabetical order, publishing no number. The list is long; on a phone, reaching a distant RA means
scrolling through many screens. There is no direct jump to the RA sections.

This plan adds that jump: a `<select id="ir-ra">` with the 35 RAs, `#ra-<slug>` anchors on the
existing sections, display labels in title case, and synchronization with the name search. The index
stays number-free. The table of contents of the school page (the nine blocks of
`SchoolPage.render`) is a separate item, planned in
[sumario-da-escola](2026-11-10-sumario-da-escola.md), which runs after this one and reuses parts of
it (§4.4).

## 2. Current state and what the plan measures

### 2.1 Facts behind the plan

Measured when the plan was first written (2026-11-10); step 0 re-measures every row before editing.

| Fact | Value | Where |
|---|---:|---|
| RAs in the index | 35 (re-verified: the 35 raw values equal the keys of Appendix A) | `data/public/escolas.parquet`, column `ra` |
| Schools in the index | 1,291 | idem |
| RA sections in the index | 35 | `site/index.html` |
| School names containing "CEI" | 140, in several RAs; "cei" does not isolate Ceilândia | `site/index.html` |
| Number guard of the index | catches `class="num"`, `data-numero` and "N escolas"; does not catch "Ceilândia (142)" | `check_no_ranking` |
| Site size | 34 MB, 2,587 files | `site/` (outside git) |

The index has no `id` on the RA sections: the search script hides `#lista section[data-ra]` but
there is no jump target. The school page shows the RA in upper case in the subtitle and in the
identification card because it uses the raw registry value.

### 2.2 What already exists (post plan 0)

- `loader.load_data` reads `escolas.parquet`; `ra` stays the registry string.
- `index_page.render_index_page` groups by `ra`, sorts schools by `(name, code)` and emits
  `<section class="ra" data-ra="…">` with an upper-case `<h2>`.
- `static/search.js` reads `indice.json`, filters `#lista li[data-nome]` and hides sections without a
  visible item. Its identifiers are Portuguese (plan 0 left them to this plan, §5 step 4).
- `SchoolPage.render` (subtitle) and `SchoolPage._block_identification` (the "Região Administrativa"
  row) print `e["ra"]`.
- `layout.document` builds the shared `<head>`, top bar and footer.
- `static/style.css` has the `.busca` rules and the `@media print` block.
- `checks/ranking.py::check_no_ranking` is the ranking and index-number guard; `checks/__init__.py`
  holds the `CHECKS` registry.

## 3. Decisions

### D1 — `<select id="ir-ra">` jump, not a list of links

**Decision.** The entry page gets one compact control:

```html
<div class="sumario" id="sumario">
  <label for="ir-ra">Ir para uma Região Administrativa</label>
  <select id="ir-ra" autocomplete="off">
    <option value="">Selecione…</option>
    <option value="#ra-<slug>">Rótulo da RA</option>
    <!-- one option per RA, in the same order as the sections -->
  </select>
</div>
```

**Why.** One line at any width, good on phones, and it avoids a block of 35 links that, with
`columns: 14rem`, falls to one column and becomes 35 lines at 360 px. The native `<select>` has form
semantics, keyboard and screen-reader support; the `<label>` gives the accessible name. No layout
rewrite.

**Rejected.** A `<nav>` of 35 links in columns (35 lines on a phone, pushes the list down); a
`<details>` with 35 links (more taps, still a long list); horizontal chips (hidden scroll, no list
semantics); a sticky sidebar (layout rewrite, out of scope).

### D2 — display labels in title case; data stays at the source

**Decision.** The index and the school page display labels such as "Águas Claras", "Ceilândia", "Sol
Nascente/Por do Sol" and "Sudoeste/Octogonal". The raw registry value (`AGUAS CLARAS`, `CEILANDIA`,
`SOL NASCENTE / POR DO SOL`) stays in `data-ra`, in `indice.json` and in `data/public`. The anchor is
derived from the raw value (`#ra-aguas-claras`, `#ra-ceilandia`).

**Why.** Upper case is an artifact of the registry, not a design choice; 35 options and 35 headings
in capitals look like a database export. An explicit 35-entry map is reviewable and does not touch
the data contract. `REGION_LABELS` without an entry for a new RA makes the build fail, which forces a
label review instead of leaking a raw value.

**Rejected.** Showing the raw value (readable, inelegant); writing the label into `escolas.parquet`
(changes the insumo, its sha256 and the contract); `str.title()` (yields "De", "Do" and adds no
accents); `text-transform: capitalize` (adds no accents, yields "Aguas Claras").

### D3 — no count per RA

**Decision.** The select lists names, not numbers. No "Ceilândia (142)", no "35 RAs".

**Why.** [`docs/FASE-1.md`](../../FASE-1.md) §2.1 forbids numbers on the index; a count per RA is a
statistic and would need a source block, a computation and limit ids like any other number. The
current guard (`check_no_ranking`) catches `class="num"`, `data-numero` and "N escolas"; a bare
number would slip through. This plan does not widen the guard because it publishes no number; if a
count is requested later it needs its own contract and a precise check.

**Rejected.** Publishing the count now (violates §2.1); publishing it with an improvised provenance
block (new scope and contract); trusting `check_no_ranking` to block any number (it does not).

### D4 — no "back to index" link at the end of each RA

**Decision.** Sections get no return link. The jump uses `location.hash`; the browser records a
history entry and Back returns to the previous position. The select stays at the top.

**Why.** 35 return links add 35 tab stops and 35 repeated lines; browser history already solves the
return. If an explicit return is needed later, prefer a single "back to top" or a floating button.

**Rejected.** 35 "Voltar ao índice" links (noise, tab stops); a floating button now (more UI and JS);
a sticky sidebar (layout rewrite).

### D5 — its own check, registered in `CHECKS`; criterion 7

**Decision.** Jump consistency gets its own function `check_region_toc(site)` in
`sitegen/checks/region_toc.py`, one registry entry
`Check("sumario", "--check-sumario", "critério 7: salto por RA e seções na mesma ordem", …)` placed
**after `ranking`**, and criterion 7 in [`docs/FASE-1.md`](../../FASE-1.md) §8. `check_no_ranking` keeps
only the "no number" rule. `main` is not edited: plan 0's registry generates the flag and the
`--check` list.

**Why.** Anchor consistency is not ranking. Putting it into `check_no_ranking` would make the
criterion's name lie and mix two invariants. A function of its own measures options, ids, order,
labels and duplicates, and fails before the Pages upload because the workflow already runs `--check`.

**Rejected.** Extending `check_no_ranking` (wrong name and criterion); manual `grep` (not a gate); a
separate CI job (`--check` already is the gate).

### D6 — select hidden without JavaScript, on the index only

**Decision.** `layout.document` gains an optional `head_extra=""` parameter, inserted right after the
stylesheet `<link>` with no newline when empty. Only `render_index_page` passes
`<noscript><style>.sumario { display: none; }</style></noscript>`. The body notice says search and
jump need JavaScript and the RA list below stays complete. The select is not shown without JS.

**Why.** A `<select>` without JavaScript is inert; leaving it visible suggests it works. The full
list below is the no-JS path required by §2.1; the select is progressive enhancement. Putting the
`<noscript>` in the shared `<head>` (as the first draft of this plan did) would change the head of
all 1,291 school pages for an element that exists only on the index.

**Rejected.** Leaving an inert visible select (confusing); 35 duplicate links inside `<noscript>`
(the complete HTML is already below); requiring JavaScript for the whole page (against §2.1);
`<noscript>` in every page's head (byte churn for nothing).

### D7 — no framework, no new dependency

**Decision.** Implementation stays Python f-strings plus the CSS and JS files. No Jinja2, Astro,
Eleventy, Hugo, Next.js, Bootstrap or Tailwind.

**Why.** The change is a `<select>`, a 35-label map, some JavaScript and one check. FASE-1 §5.3 fixes
`pandas`/`pyarrow` and f-string HTML, and says `jinja2` does not enter the CI requirements. The
summary is generated from data, not from Markdown headings, so a framework's "embedded TOC" would not
solve this part. Plan 0 records when Jinja2 would be worth revisiting.

**Rejected.** Jinja2 (a pip dependency, not a runtime, but a contract change that this jump does not
need); Astro/Eleventy/Hugo (Node/Go in CI and a JSON export); Next.js (excessive for static pages); a
CSS framework (generic look, no gain for one select).

### D8 — school-page TOC out of scope

**Decision.** Do not change the school page beyond the RA label. The nine-block TOC is plan 2.

**Why.** The index needs a 35-destination jump; the school page needs a nine-block summary, with its
own check over 1,291 pages. Mixing the two raises risk and scope.

## 4. Files, interfaces and existing code

### 4.1 Files

| File | Role | Change |
|---|---|---|
| `scripts/sitegen/region.py` | new | `REGION_LABELS`, `_strip_accents`, `region_anchor_id`, `region_label`, `region_sort_key` |
| `scripts/sitegen/index_page.py` | index | select, `region_ids`, anchors, `data-ra`, label in `<h2>`, `head_extra` |
| `scripts/sitegen/school_page.py` | school page | `region_label` in the subtitle (`render`) and the ficha (`_block_identification`) |
| `scripts/sitegen/layout.py` | shared head | `document(..., head_extra="")` |
| `scripts/sitegen/static/search.js` | index JS | jump listener, sync with the filter, English identifiers |
| `scripts/sitegen/static/style.css` | CSS | `.sumario`, `.ra` scroll margin, print |
| `scripts/sitegen/checks/region_toc.py` | new | `check_region_toc` |
| `scripts/sitegen/checks/common.py` | helpers | `require_equal_lists` (reused by plan 2) |
| `scripts/sitegen/checks/__init__.py` | registry | one entry |
| `docs/FASE-1.md` | contract | §2.1, §2 block 1, §5.2, §7, §8 (criterion 7) |
| `.github/workflows/pages.yml` | publishing | **comment only** (line about covered criteria); the command does not change |
| `docs/worklogs/2026-11-10-02-sumario-por-ra.md` | worklog | new |
| `data/public/`, `README.md`, `SCHEMA.md`, `requirements.txt` | — | unchanged |

### 4.2 Interfaces

```text
REGION_LABELS: dict[str, str]                 # raw registry value -> display label
_strip_accents(text: str) -> str              # NFKD -> ASCII; shared by slug and ordering
region_anchor_id(region: str) -> str          # "ra-<slug>"; BuildError if the slug is empty
region_label(region: str) -> str              # label; BuildError if the region is not in the map
region_sort_key(region: str) -> tuple[str, str]   # (label without accents/case, raw value)
check_region_toc(site: Path) -> str           # options, ids, order, labels, duplicates
require_equal_lists(where, name_a, a, name_b, b) -> None   # BuildError at the first difference
layout.document(title, body, data_build, threshold, head_extra="") -> str
--check-sumario                               # runs only criterion 7
```

Index HTML:

```html
<div class="sumario" id="sumario">
  <label for="ir-ra">Ir para uma Região Administrativa</label>
  <select id="ir-ra" autocomplete="off">
    <option value="">Selecione…</option>
    <option value="#ra-<slug>">Label</option>
  </select>
</div>

<section class="ra" id="ra-<slug>" data-ra="<raw value>">
  <h2>Label</h2>
  <ul>...</ul>
</section>
```

The section `id` is `ra-<slug>`; the option `value` is `#ra-<slug>`; `data-ra` keeps the raw value.
`indice.json` keeps the raw `ra`; `dados/<CO_ENTIDADE>.json` does not change schema.
`require_equal_lists` reports the position and both values at the first divergence.

### 4.3 Insertion points

- `sitegen/region.py` (new): `import re`, `import unicodedata`, `from .errors import BuildError`.
- `sitegen/index_page.py::render_index_page`: after the body `<noscript>`, before `<div id="lista">`.
- `sitegen/school_page.py`: the subtitle in `SchoolPage.render` and the ficha row in
  `_block_identification`.
- `sitegen/layout.py::document`: `<link rel="stylesheet" href="estilo.css">{head_extra}` on the same
  line, so an empty value produces identical bytes.
- `sitegen/static/style.css`: extend the `.busca label`/`.busca input`/`.busca input:focus` rules to
  `.sumario`; the `@media print` block.
- `sitegen/checks/__init__.py`: entry after `ranking` in `CHECKS`.

### 4.4 What the next plan reuses

[sumario-da-escola](2026-11-10-sumario-da-escola.md) depends on: `require_equal_lists`; the registry
entry pattern; the `@media print` hide group (it appends `.sumario-escola` to it); the baseline method
(strip-and-compare, step 8); and the criterion numbering (it becomes criterion 8, `--check` nine
items). It does **not** depend on `region.py` or on the `head_extra` parameter.

## 5. Execution plan

Commit in order; gate G of plan 0 does **not** apply as is (the index and the school pages change
on purpose); the diff scope of §6, criterion 13, replaces it.

### Step 0 — Baseline and re-measurement

- [ ] Plan 0 is complete (its definition of done holds). `git status --short` clean.
- [ ] Golden = the plan-0 golden in `/tmp/opencode/golden/site` (rebuild it from the plan-0 final
  commit if missing; its hashes must equal `golden/site.sha`).
- [ ] Re-measure the rows of §2.1 (RA count, school count, "CEI" count, `index.html` guards).
- [ ] Confirm every raw RA of the insumo is a key of Appendix A and the reverse (35 = 35).

### Step 1 — Labels and helpers (`region.py`)

- [ ] `REGION_LABELS` with the 35 entries of Appendix A (keys are raw values of
  `escolas.parquet`; values are display labels).
- [ ] `_strip_accents(text)`:
  `unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")`.
- [ ] `region_anchor_id(region)`: `_strip_accents(region).lower()`, replace `[^a-z0-9]+` with `-`,
  trim hyphens, prefix `ra-`; if the base is empty, `BuildError` naming the region.
- [ ] `region_label(region)`: `REGION_LABELS[region]`; if missing,
  `BuildError(f"RA sem rótulo de exibição: {region!r}")`.
- [ ] `region_sort_key(region)`: `(_strip_accents(region_label(region)).lower(), region)`.
- [ ] Do not read `data/interim/`, do not alter `data/public`, do not use locale.

### Step 2 — Select, order and anchors in `render_index_page`

- [ ] `order = sorted(by_region, key=region_sort_key)`.
- [ ] `region_ids` with collision guard **by value**: `seen: dict[str, str]`; for each `region` in
  `order` compute `anchor`; if `anchor in seen`, `BuildError` citing `seen[anchor]`, `region` and
  `anchor`; else `seen[anchor] = region` and `region_ids[region] = anchor`.
- [ ] Insert `<div class="sumario" id="sumario">` with the `<label for="ir-ra">` and
  `<select id="ir-ra" autocomplete="off">` after the body `<noscript>` and before `<div id="lista">`.
- [ ] First option `<option value="">Selecione…</option>`; then one option per region in `order` with
  `value="#{region_ids[region]}"` and `html.escape(region_label(region))` as text.
- [ ] Sections in `order`:
  `<section class="ra" id="{region_ids[region]}" data-ra="{html.escape(region)}">`; the `<h2>` uses
  `html.escape(region_label(region))`.
- [ ] No count, no `<span class="num">`, no `data-numero`, no per-section return link.
- [ ] Pass `head_extra` (D6) to `document`; add the `head_extra` parameter in `layout.document`
  (empty default, no added newline).

### Step 3 — RA label on the school page

- [ ] In `SchoolPage.render`, replace the subtitle's `e["ra"]` with `region_label(e["ra"])`.
- [ ] In `SchoolPage._block_identification`, replace the "Região Administrativa" row's `e["ra"]` the
  same way.
- [ ] `data/public`, `indice.json` and the provenance JSON keep the raw value; this is display only.

### Step 4 — JavaScript: jump, sync, and English identifiers (`static/search.js`)

- [ ] Translate the existing identifiers while the file is open (strings, element ids, `data-*`
  names and messages unchanged): `campo→searchField`, `itens→items`, `secoes→sections`,
  `normaliza→normalize`, `texto→text`, `indice→searchIndex`, `resposta→response`, `erro→error`,
  `porCodigo→byCode`, `termo→term`, `encontrou→found`, `dados→entry`, `nome→name`, `mostrar→show`,
  `secao→section`.
- [ ] Before the `fetch`, declare `const jumpSelect = document.getElementById('ir-ra');` and
  `const jumpOptions = Array.from(jumpSelect.querySelectorAll('option[value^="#ra-"]'));`.
- [ ] Register the `change` listener **before** the `fetch`, so the jump works even if `indice.json`
  fails. In it: read `jumpSelect.value`; if empty, return; get the section with
  `document.getElementById(target.slice(1))`; if the section does not exist or is `hidden`, reset the
  select to the placeholder and return; if `location.hash === target`, call
  `section.scrollIntoView()`; otherwise set `location.hash = target`; reset the select to the
  placeholder.
- [ ] In the search `input` handler, after the section loop, walk `jumpOptions`:
  `const section = document.getElementById(option.value.slice(1));`
  `const visible = Boolean(section && !section.hidden);`
  `option.hidden = !visible; option.disabled = !visible;` and, if the selected option became
  invisible, reset to the placeholder.
- [ ] After the loop, `jumpSelect.disabled = sections.every((section) => section.hidden);`.
- [ ] If `indice.json` fails, the `catch` keeps disabling only the search field; the select stays
  enabled and the jump keeps working.
- [ ] The body `<noscript>` in `render_index_page` says search and jump need JavaScript and the RA
  list below stays complete.

### Step 5 — CSS and print (`static/style.css`)

- [ ] Extend `.busca label`, `.busca input`, `.busca input:focus` to `.sumario label`,
  `.sumario select`, `.sumario select:focus` so the select shares the search field's typography,
  border, background, radius and focus.
- [ ] `.sumario { margin: 1rem 0 1.2rem; }`, and `scroll-margin-top: .5rem` on `.ra`.
- [ ] In `@media print`, hide `.sumario` along with `.topo`, `footer.rodape` and `.trilha`.
- [ ] No card and no columns for the select; it is one line.

### Step 6 — `check_region_toc` and registry

- [ ] `checks/common.py::require_equal_lists(where, name_a, a, name_b, b)`.
- [ ] `checks/region_toc.py::check_region_toc(site)` reads `site/index.html`; requires `id="ir-ra"`
  and `for="ir-ra"`; collects
  `options = re.findall(r'<option value="#(ra-[^"]+)">([^<]+)</option>', index)` and
  `sections = re.findall(r'<section class="ra" id="(ra-[^"]+)" data-ra="[^"]*"><h2>([^<]+)</h2>', index)`.
- [ ] Fails if a list is empty, the lengths differ, a slug repeats, the slug order differs, the
  `html.unescape`d label order differs, or a label is not in `REGION_LABELS.values()` (use
  `require_equal_lists` for the comparisons).
- [ ] Returns `f"{len(options)} RAs no salto, casando com as seções e com o rótulo"`.
- [ ] Registry: `Check("sumario", "--check-sumario", "critério 7: salto por RA e seções na mesma ordem", …)`
  after `ranking`. `main` is not edited.
- [ ] `check_no_ranking` keeps being criterion 2; do not move the number guard.

### Step 7 — Contract and worklog

- [ ] `docs/FASE-1.md` §2.1: add the RA jump (`<select id="ir-ra">`, 35 options, order by label,
  `#ra-<slug>`, no count, select hidden without JS, full list as fallback); update "two forms" to
  search + jump + list and "the JavaScript only filters" to "filters and jumps"; record that the label
  is display-only and `data-ra`, `indice.json` and `data/public` keep the raw value, the slug coming
  from the raw value.
- [ ] §2 block 1: the RA in the ficha is a display label, not a field copy.
- [ ] §5.2: `index.html` = "busca por nome + salto por RA + lista por RA, sem número".
- [ ] §7 and §8: update the criterion count and add **criterion 7** (one option per `#ra-<slug>`,
  same order and label, no duplicate slug; command `--check-sumario`); "Escopo real do gate" becomes
  criteria 1–4, 6 and 7.
- [ ] `.github/workflows/pages.yml`: update the comment that lists covered criteria (add 7); do not
  change the `run`.
- [ ] Create `docs/worklogs/2026-11-10-02-sumario-por-ra.md` (*O que entrou*, decisions: select,
  labels, no count, no back link; *Verificação*; the explicit sentence that `data/public` did not
  change).
- [ ] Do not change `README.md`, `SCHEMA.md` or `requirements.txt`.

### Step 8 — Verification

- [ ] Run the §7 commands; confirm eight `[ok]` lines.
- [ ] Run the strip-and-compare of criterion 13.
- [ ] Check the select at 360, 768 and 1280 px (no horizontal overflow), the jump, Back, and search
  with a unique name; JavaScript off; print.
- [ ] `git diff -- data/public` empty; `site/` out of git.

## 6. Acceptance criteria

1. **Select and anchors.** `site/index.html` has one `<select id="ir-ra">` with exactly 35 RA options,
   one per `#ra-<slug>`, in the same order as the 35 sections; no duplicate slug.
2. **Labels.** Options and section `<h2>` use the Appendix A labels, with accents and title case;
   `SCIA` and `SIA` stay upper case.
3. **Source preserved.** `data-ra`, `indice.json` and `data/public/escolas.parquet` keep the raw
   value; no file in `data/public` changes.
4. **Jump.** Choosing an RA moves to its section, updates the URL hash and returns the select to the
   placeholder; choosing the same RA again scrolls to the section; choosing a hidden option does not
   navigate.
5. **Search.** Typing a name filters the list and leaves in the select only RAs with a visible
   school; clearing restores all 35; with no result the select is disabled and the status says
   "Nenhuma escola encontrada".
6. **No JavaScript.** The index `<head>` carries the `<noscript>` rule that hides the select; the
   full list of 1,291 schools stays readable; the body notice shows.
7. **No number.** No per-RA count enters the index; `check_no_ranking` still passes.
8. **Gate.** `--check` passes eight items including `sumario`; `--check-sumario` passes alone; a
   second build produces the same bytes.
9. **Responsive and print.** At 360 px the select takes one line with no overflow; at 1280 px it
   aligns with the search field; in print it is hidden.
10. **School page.** The subtitle and the ficha show the label ("Plano Piloto") while the insumo and
    `indice.json` keep `PLANO PILOTO`.
11. **No new dependency.** `requirements.txt` unchanged; Python + f-strings + CSS/JS files; no
    Jinja2 or framework.
12. **Documentation.** `docs/FASE-1.md` describes the select, the labels, the no-JS fallback and
    criterion 7; the worklog records the verification.
13. **Diff scope.** Against the plan-0 golden, only `index.html`, `estilo.css` and the school pages
    change. In each school page exactly two occurrences differ (the subtitle and the "Região
    Administrativa" row, raw value → label); a strip-and-compare over all 1,291 pages (replace the
    label by the raw value at those two spots, compare bytes) passes. `como-ler.html`,
    `creditos.html`, `indice.json`, every `dados/*.json` and `data/public` are byte-identical.
    Because `head_extra` is empty elsewhere, no other page's `<head>` changes.

## 7. Verification

```sh
# build + criteria 1–4, 6, 7, idempotence of 5 and edge cases
.venv/bin/python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check

# criterion 7 only
.venv/bin/python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-sumario

# syntax and diff
.venv/bin/python -m compileall -q scripts
git diff --check
git diff -- data/public
```

Manual checks:

- `grep -c 'id="ir-ra"' site/index.html` → 1.
- `grep -o 'value="#ra-[^"]*"' site/index.html | wc -l` → 35.
- `grep -o 'id="ra-[^"]*"' site/index.html | wc -l` → 35.
- `diff <(grep -o 'value="#ra-[^"]*"' site/index.html | sed 's/value="#//;s/"//') <(grep -o 'id="ra-[^"]*"' site/index.html | sed 's/id="//;s/"//')` → empty.
- `grep -E '[0-9]+ escolas?' site/index.html` → empty.
- In the HTML: the labels `Água Quente`, `Águas Claras`, `Ceilândia`, `São Sebastião`, `Sol
  Nascente/Por do Sol`, `Sudoeste/Octogonal`; and `data-ra="AGUAS CLARAS"` etc. still present.
- Open `site/53000854.html`: subtitle and ficha show `Plano Piloto`; open `site/53000226.html` and
  `site/53000781.html` for the same labels.
- In the browser: choose "Ceilândia"; check `#ra-ceilandia`, Back, and repeating the same selection.
  Type a unique name (for example "CEF 01 DO PLANALTO"); only the matching RA stays in the select and
  the list; clear; type `zzzz`; the select is disabled.
- JavaScript off: select hidden, notice shown, full list readable. Print: select hidden.
- 360, 768 and 1280 px: no horizontal overflow.
- Build twice and compare `sha256sum` of `site/` for idempotence.

## 8. Risks and open questions

### Risks

- **`option.hidden` varies by browser.** `option.disabled` is the functional guarantee; `hidden` is
  the visual one. Test Chrome, Firefox and Safari; if `hidden` is ignored the options are gray but
  not selectable.
- **Native select styling varies by platform.** Keep the search field's border, background, radius
  and focus; do not customize the arrow.
- **History.** `location.hash` adds an entry, so Back returns to the previous position (desired), at
  the cost of a longer history after successive jumps. If it bothers, switch to `scrollIntoView` +
  `history.replaceState` and lose Back.
- **New or renamed RA.** An RA without a label makes the build fail; a rename changes the slug and
  breaks external links. Both are deliberate gates.
- **Map maintenance.** `REGION_LABELS` is a display translation; if the registry changes it must
  follow. The guard is the `BuildError` in `region_label` (no separate coverage test exists).
- **`check_region_toc` regexes.** If the option/section markup changes, they break; keep the markup
  stable or replace them with a small parser.
- **The select hides the overview.** On desktop it does not show the 35 RAs at once. If visual
  comparison is needed, a `<details>` or a visible list can be added later without changing anchors.
- **Long labels.** "Sol Nascente/Por do Sol" and "Sudoeste/Octogonal" are the longest; confirm they
  do not overflow the select at 360 px.
- **No JavaScript.** The hidden select is honest but there is no TOC without JS; the full list below
  is the fallback; if a no-JS TOC is required, `<details>` is the alternative.

### Open questions

- Does the maintainer want a visible overview of the 35 RAs on desktop besides the select? This plan
  uses only the select; a visible list can come later.
- Should the select sit inside a `<nav>` or a `<form>`? This plan uses `<div>` + `<label>` +
  `<select>` because it is a form control, not a list of links. Reassess if an accessibility audit
  asks for a landmark.
- `SCIA` and `SIA` stay upper case as acronyms; "Riacho Fundo II" and "Sobradinho II" use Roman
  numerals. Confirm the official form before publishing.
- Resolved: `REGION_LABELS` lives in `sitegen/region.py`; criterion 7 is its own criterion rather
  than a sub-item of criterion 2.

## 9. Out of scope

- The nine-block TOC of the school page (plan 2).
- A count per RA, mean, median, ranking or any new number on the index.
- Changing `data/public`, `indice.json`, `procedencia.json` or the schema of
  `dados/<CO_ENTIDADE>.json`.
- Jinja2, a framework, a CSS framework or any new dependency.
- Hosting, the Pages workflow command or the site size.
- A "Voltar ao índice" per section, a sticky sidebar or a floating button.
- Search changes beyond the sync with the select.
- Visual restructuring of the index beyond the select and the labels.

## 10. Definition of done

- [ ] `sitegen` generates the select, the anchors and the labels; the school page shows the RA label.
- [ ] `--check` passes eight items including `sumario`; `--check-sumario` passes alone.
- [ ] The 35 Appendix A labels are in the HTML; `data-ra` and `indice.json` keep the raw value.
- [ ] The select jumps, returns to the placeholder, syncs with the search and is hidden without JS.
- [ ] The diff scope of criterion 13 holds; `data/public` did not change; `site/` stays out of git.
- [ ] `docs/FASE-1.md` and the worklog describe what entered; no undocumented manual step; the build
  is still idempotent.

## Appendix A — display labels for the RAs

Keys are the raw values of `data/public/escolas.parquet`; values are display only.

| Raw value in the registry | Display label |
|---|---|
| `AGUA QUENTE` | Água Quente |
| `AGUAS CLARAS` | Águas Claras |
| `ARAPOANGA` | Arapoanga |
| `ARNIQUEIRA` | Arniqueira |
| `BRAZLANDIA` | Brazlândia |
| `CANDANGOLANDIA` | Candangolândia |
| `CEILANDIA` | Ceilândia |
| `CRUZEIRO` | Cruzeiro |
| `FERCAL` | Fercal |
| `GAMA` | Gama |
| `GUARA` | Guará |
| `ITAPOA` | Itapoã |
| `JARDIM BOTANICO` | Jardim Botânico |
| `LAGO NORTE` | Lago Norte |
| `LAGO SUL` | Lago Sul |
| `NUCLEO BANDEIRANTE` | Núcleo Bandeirante |
| `PARANOA` | Paranoá |
| `PARK WAY` | Park Way |
| `PLANALTINA` | Planaltina |
| `PLANO PILOTO` | Plano Piloto |
| `RECANTO DAS EMAS` | Recanto das Emas |
| `RIACHO FUNDO` | Riacho Fundo |
| `RIACHO FUNDO II` | Riacho Fundo II |
| `SAMAMBAIA` | Samambaia |
| `SANTA MARIA` | Santa Maria |
| `SAO SEBASTIAO` | São Sebastião |
| `SCIA` | SCIA |
| `SIA` | SIA |
| `SOBRADINHO` | Sobradinho |
| `SOBRADINHO II` | Sobradinho II |
| `SOL NASCENTE / POR DO SOL` | Sol Nascente/Por do Sol |
| `SUDOESTE / OCTOGONAL` | Sudoeste/Octogonal |
| `TAGUATINGA` | Taguatinga |
| `VARJAO` | Varjão |
| `VICENTE PIRES` | Vicente Pires |

Display order: by `region_sort_key`, that is, label without accents and case, with the raw value as
tiebreaker. Examples: `AGUA QUENTE` before `AGUAS CLARAS`; `SAO SEBASTIAO` before `SCIA` and `SIA`;
`SOBRADINHO II` before `SOL NASCENTE / POR DO SOL`; `SUDOESTE / OCTOGONAL` before `TAGUATINGA`.
