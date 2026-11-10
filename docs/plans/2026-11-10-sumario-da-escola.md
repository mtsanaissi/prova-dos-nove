# Plan — table of contents (TOC) on each FASE-1 school page

**Date:** 2026-11-10
**Contract:** [docs/FASE-1.md](../FASE-1.md)
**Depends on:** [plan 0 — refatorar-build-site](2026-11-10-refatorar-build-site.md) and [plan 1 — sumario-por-ra](2026-11-10-sumario-por-ra.md); both must be merged first
**Input:** [data/public/](../../data/public/) (unchanged)
**Worklog:** `docs/worklogs/2026-11-10-03-sumario-da-escola.md` (new; Portuguese)
**Criterion:** adds criterion **8** to FASE-1 §8; `--check` goes from eight to nine items.

Anchors are **symbols and modules** (post plan 0). Identifiers are English; HTML ids, CSS classes,
CLI flags and the site copy stay Portuguese (plan 0, D4).

## 1. Motivation and origin

Each school has a static page `site/<CO_ENTIDADE>.html` (1,291 pages) with eight or nine blocks
stacked in a column up to 56 rem wide. The page is long: on a phone, reaching the infrastructure or
daycare block means scrolling through the Ideb, flow, distortion and non-response blocks, which have
one card per stage. There is no TOC to jump between blocks.

The request is a TOC **inside the page**, near the top, in native HTML, with no framework, no new
dependency and no Jinja2, with a check in `--check` that sweeps **all** 1,291 pages. The entry page
(`index.html`) and its RA jump belong to
[sumario-por-ra](2026-11-10-sumario-por-ra.md), which runs first and is not changed here
(`render_index_page` and the RA `<select>` stay as they are). That plan left this item out on
purpose; this document is its design.

Constraints inherited from [AGENTS.md](../../AGENTS.md) and the contract:

- the TOC is labels only: no number, count, ranking or new data (the contract forbids ranking and
  ordering by indicator, §2);
- `data/public/` does not change and `site/` stays out of git;
- the build stays idempotent with no manual step;
- every script opens with a docstring naming input, output and idempotence; comments and docs in
  Portuguese.

## 2. Current state and what the plan measures

### 2.1 Structure of the school page

`SchoolPage.render` (`sitegen/school_page.py`) assembles, inside `<main>`, in this order:

1. `<p class="trilha">` ("Todas as escolas" link), `<h1>` and `<p class="subtitulo">` (which, after
   plan 1, shows the RA display label);
2. when the school offers an assessed stage and has neither Ideb nor a rate, a page-wide
   `<p class="ausencia">` with `PHRASE_NO_INDICATOR`;
3. nine `<section class="bloco" id="…">`, each rendered by one `_block_*` method (plan 0, step 6),
   with an `<h2>` from `_section_heading`:

| # | id | `<h2>` label | method | exists when |
|---|---|---|---|---|
| 1 | `identificacao` | Identificação | `_block_identification` | always |
| 2 | `oferta` | Oferta por etapa | `_block_offering` | always |
| 3 | `matricula` | Matrícula por etapa | `_block_enrollment` | always |
| 4 | `ideb` | Ideb por etapa | `_block_ideb` | always |
| 5 | `fluxo` | Fluxo escolar | `_block_flow` | always |
| 6 | `tdi` | Distorção idade-série | `_block_age_grade_distortion` | always |
| 7 | `tnr` | Taxa de não-resposta | `_block_non_response` | always |
| 8 | `infraestrutura` | Infraestrutura | `_block_infrastructure` | always |
| 9 | `creche` | Creche da escola | `_block_daycare` | only when `oferta_inf_cre == 1` |

4. the page footer (`p.rodape-pagina`) and the closing `</main>`.

`layout.document` wraps the body with `<header class="topo">` and `<footer class="rodape">`. School
pages have no `<script>`; only `index.html` does.

### 2.2 Measured facts

Measured on the pre-plan-0 build (2026-11-10) and `data/public/escolas.parquet`; step 0 re-measures
every row on the post-plan-1 build. The 475 count of `oferta_inf_cre == 1` was re-verified against
the parquet while writing this plan.

| Fact | Value | Where |
|---|---:|---|
| School pages (`[0-9]{8}.html`) | 1,291 | `site/`; same glob as `_clean_output` |
| Schools with `oferta_inf_cre == 1` | 475 | `escolas.parquet` (`Int64`, no null) |
| Pages with `id="creche"` | 475 | `site/*.html` |
| Pages with the 8-id sequence (no daycare) | 816 | `site/*.html` |
| Pages with the 9-id sequence (with daycare) | 475 | `site/*.html` |
| Pages with a duplicate id | 0 | `site/*.html` |
| Existing `<nav>` on school pages | 0 | `site/*.html` |
| `<h2>` per page = sections per page | yes, in all | `site/*.html` |

Block ids are part of the visible contract (they can become public anchors) and are **not**
renamed. `ideb`, `tnr` and `infraestrutura` also exist in `como-ler.html`, on a different page, so
they do not collide.

### 2.3 What already exists and is reused

From the code at HEAD:

- `SchoolPage._section_heading(title)` → `<h2>…</h2>`.
- `static/style.css`: variables `--papel-forte`, `--linha`, `--destaque`, `--tinta-suave`; `.trilha`,
  `.bloco`; the `@media (max-width: 38rem)` and `@media print` blocks.
- `_clean_output` and `build_site` write `site/<code>.html`; nothing changes there.
- `check_states`, `check_provenance`, `check_threshold`: the pattern of sweeping the 1,291 pages and
  raising `BuildError`. None is affected by a `<nav>` without `data-numero`/`data-estado`.

From plan 0: the nine `_block_*` methods and the `render` that calls them; the `Check`/`CHECKS`
registry; gate-by-bytes method and `/tmp/opencode` throwaway-tool convention.

From plan 1: `checks/common.py::require_equal_lists`; the print rule that already hides `.sumario`
(this plan appends `.sumario-escola` to the same group); the strip-and-compare baseline technique;
the criterion numbering.

## 3. Decisions

### D1 — one closed `<details>` inside a `<nav>`, no JavaScript

**Decision.** A single element, right after the subtitle:

```html
<nav class="sumario-escola" aria-label="Seções desta página"><details><summary>Nesta página</summary><ul><li><a href="#identificacao">Identificação</a></li>…</ul></details></nav>
```

`<details>` has no `open` attribute. The list is a `<ul>` (not `<ol>`) so readers see no numbering.
`<summary>` is a fixed interface label ("Nesta página").

**Why.** One line, closed, at any width; it is native: keyboard (Enter/Space), screen reader and the
open/closed state come from the browser, and anchor navigation works without a line of JavaScript.
`<nav>` with `aria-label` gives the landmark; `<ul>` gives list semantics and the screen reader
announces the item count.

**Rejected.**

- *A visible list of links under the title.* With eight or nine links it pushes "Identificação" off
  the first screen at 360 px.
- *A sticky sidebar on desktop.* `main` is a single centered 56 rem column; a sidebar needs a grid
  container around `main`, another mobile layout and one more overflow test. A layout rewrite for a
  page that does not ask for it.
- *Horizontal chips.* Hidden horizontal scroll, no list semantics.
- *A jump `<select>`.* It is what plan 1 uses for 35 RAs, but it needs JavaScript to jump; the
  requirement here is to work without JS.
- *A JavaScript TOC generated from the `<h2>`s.* Nothing without JS, and labels could diverge from
  ids without the build noticing.
- *Jinja2 or a framework.* FASE-1 §5.3 says `jinja2` does not enter the CI requirements; a nine-line
  TOC does not justify a template engine.

### D2 — one source for ids, labels, order and the daycare condition

**Decision.** `school_page.py` holds a module constant, in contract order:

```python
SCHOOL_SECTIONS = (
    ("identificacao", "Identificação", None),
    ("oferta", "Oferta por etapa", None),
    ("matricula", "Matrícula por etapa", None),
    ("ideb", "Ideb por etapa", None),
    ("fluxo", "Fluxo escolar", None),
    ("tdi", "Distorção idade-série", None),
    ("tnr", "Taxa de não-resposta", None),
    ("infraestrutura", "Infraestrutura", None),
    ("creche", "Creche da escola", "oferta_inf_cre"),
)
```

The tuple is `(anchor id, label, condition column or None)`. `SchoolPage` gets
`_has_section(anchor)` (condition `None`, or `self.e[column] == 1`), `_open_section(anchor)` (emits
`<section class="bloco" id="…">` + `_section_heading(label)`) and `_renderers()` (a dict from anchor
to the bound `_block_*` method). `render` walks `SCHOOL_SECTIONS` and calls
`renderers[anchor]()` when `_has_section(anchor)`; `toc()` walks the same tuple and the same
predicate. `render` raises `BuildError` if the renderer keys differ from the tuple's ids. No string
`getattr`: the Portuguese anchor ids never become part of an identifier.

**Why.** If the TOC kept its own label list, a label changed only in the `<h2>` (or only in the
link) would go unnoticed; if the daycare condition were repeated, the link could appear without the
section. With one source the build cannot produce the mismatch by construction, and the check (D3)
confirms it in the HTML.

**Rejected.** Deducing the TOC by re-reading the rendered `<section>`s (fragile, couples generation
to regex); parallel lists in `render` and the TOC (the cause of the mismatch to be avoided);
`getattr(self, f"_block_{id}")` (builds identifiers from Portuguese strings).

### D3 — `check_school_toc` reads the generated HTML and compares it with a frozen copy of the contract

**Decision.** The check does **not** reuse `SCHOOL_SECTIONS` as truth. `checks/school_toc.py` holds
its own literal copy (`CONTRACT_SECTIONS`: the nine ids, the nine labels and the "only with daycare"
flag) and compares, page by page, over all 1,291:

1. the TOC parsed from the generated HTML;
2. the `<section>`/`<h2>` parsed from the same HTML;
3. the expected list, computed from the frozen copy and the `oferta_inf_cre` of the insumo
   (`data["por_co"][code]`), never from the HTML.

The module must not import anything from `school_page.py`.

**Why.** If the check read `SCHOOL_SECTIONS`, a coordinated rename of an id in the constant would
pass, and the requirement is precisely that ids are possible anchors and cannot be renamed silently.
With a frozen copy, a rename breaks `--check`; whoever renames on purpose edits both places and
`docs/FASE-1.md`, and the change shows in the diff. Nine lines of deliberate duplication.

**Rejected.** Comparing only the TOC against the HTML sections (catches internal mismatch but not a
rename, nor the daycare rule, which comes from the data); sampling 10 pages (the contract, §8,
already says there is no sample).

### D4 — own function, key and criterion; `--check` has nine items

**Decision.** Function `check_school_toc`, registry key `sumario_escola`, flag
`--check-sumario-escola`, **criterion 8** in `docs/FASE-1.md` §8, one `Check` entry placed **after
`estados`**. The `--check` order becomes: `procedencia, ranking, sumario, limiar, estados,
sumario_escola, reprodutibilidade, licencas, casos_limite`. `main` is not edited.

**Why.** Anchor consistency is not provenance, ranking, threshold or state; putting it into an
existing check would make that criterion's name lie. `--check` is already the workflow gate, so no
new job. The key `sumario_escola` is distinct from plan 1's `sumario`.

**Rejected.** Embedding in `check_states` or `check_no_ranking`; a separate CI step.

### D5 — labels only; the TOC is not a data block

**Decision.** The TOC has no `data-numero`, `class="num"`, `data-estado` or n, and does not enter
`dados/<CO_ENTIDADE>.json`. No new row in the §2 table of `docs/FASE-1.md`; the contract describes it
in its own subsection (§2.2, step 8). Visible text is "Nesta página" plus the labels, with no digit.

**Why.** The §2 table lists blocks with source, year, computation, n and limits; the TOC publishes
none of that. Labels need no provenance, and no new `L-xx` id is required (no new caveat).

### D6 — position: after the subtitle, before the page notice and block 1

**Decision.** The TOC goes immediately after `<p class="subtitulo">` and before the "no indicator"
notice (when present) and `#identificacao`.

**Why.** "Near the top, after h1/subtitle and before the first section", as requested, closed on one
line. See Q2 on the notice.

### D7 — print and responsiveness

**Decision.** `@media print` hides `.sumario-escola` with the other navigation parts. The list uses
`columns: 3 12rem` (three columns on desktop, one at 360 px) with `break-inside: avoid` on items;
links get vertical `padding` for the touch target; blocks get a small `scroll-margin-top`. No fixed
width and no `scroll-behavior: smooth`.

**Why.** The printed page is content only; a clickable TOC does not serve on paper. Column width and
`columns` inherit from the 56 rem `main` and do not alter it.

## 4. Files, interfaces and existing code

### 4.1 Files

| File | Role | Change |
|---|---|---|
| `scripts/sitegen/school_page.py` | school page | `SCHOOL_SECTIONS`, `_has_section`, `_open_section`, `_renderers`, `toc()`; `render` loop; `_block_*` open with `_open_section` |
| `scripts/sitegen/static/style.css` | CSS | `.sumario-escola` rules, `.bloco` scroll margin, print group |
| `scripts/sitegen/checks/school_toc.py` | new | `CONTRACT_SECTIONS`, `_verify_school_toc`, `check_school_toc` |
| `scripts/sitegen/checks/__init__.py` | registry | one `Check` entry |
| `scripts/12_build_site.py` | CLI | docstring usage line only |
| `docs/FASE-1.md` | contract | §2.2 (new), §5.2, §5.3, §7 (gate scope), §8 (criterion 8) |
| `docs/worklogs/2026-11-10-03-sumario-da-escola.md` | worklog | new |
| `.github/workflows/pages.yml` | publishing | **comment only** (add 8 to the covered criteria); the `run` does not change |
| `data/public/`, `README.md`, `SCHEMA.md`, `REPORT.md`, `requirements.txt` | — | unchanged: no field, published number or dependency |
| `site/` | output | generated; stays out of git |

### 4.2 New interfaces

```text
school_page.SCHOOL_SECTIONS: tuple[tuple[str, str, str | None], ...]
SchoolPage._has_section(anchor) -> bool          # None condition, or self.e[column] == 1
SchoolPage._open_section(anchor) -> str          # '<section class="bloco" id="…"><h2>label</h2>'
SchoolPage._renderers() -> dict[str, Callable[[], str]]   # anchor -> bound _block_* method
SchoolPage.toc() -> str                          # the <nav>; only sections that exist
checks/school_toc.py:
  CONTRACT_SECTIONS: tuple[tuple[str, str, bool], ...]    # frozen copy: (id, label, only_with_daycare)
  _verify_school_toc(code, markup, daycare_offered) -> None   # raises BuildError
  check_school_toc(site, data) -> str
Check("sumario_escola", "--check-sumario-escola", "critério 8: sumário da página da escola", …)
--check-sumario-escola                           # runs only criterion 8
```

`_open_section` produces exactly the bytes that today come out of
`'<section class="bloco" id="…">'` followed by `_section_heading("…")`, so no section changes a byte
(verified in step 7).

### 4.3 Insertion points

- `school_page.py`: `SCHOOL_SECTIONS` above the class; `_has_section`, `_open_section`, `_renderers`
  and `toc` next to `_section_heading`; in `render`, `self.toc()` right after the
  `<p class="subtitulo">` and before the page notice; the nine explicit `_block_*` calls become the
  loop of D2, and the `if e["oferta_inf_cre"] == 1` guard becomes `_has_section("creche")`.
- `static/style.css`: `.sumario-escola` rules after `.trilha`; `.bloco` scroll margin; `.sumario-escola`
  appended to the `@media print` hide group that plan 1 already extended with `.sumario`.
- `checks/school_toc.py` and the `CHECKS` entry after `estados`.
- Not touched: `render_index_page`, the index JavaScript, `check_no_ranking`, `region.py`,
  `layout.document`.

## 5. Execution plan

### Step 0 — Baseline and re-measurement

- [ ] Plans 0 and 1 are merged; `git status --short` clean; `git status --porcelain data/public`
  empty.
- [ ] Build the baseline from the current HEAD **outside** `site/`:
  `.venv/bin/python scripts/12_build_site.py --public data/public --out /tmp/opencode/golden_p1/site --data-build 2026-11-06`
  and record its `sha256` list (`/tmp/opencode/golden_p1/site.sha`). `site/` may be stale and is not a
  reference.
- [ ] Re-measure §2.2 on that build. Confirm `oferta_inf_cre` for the three profile schools: `53000781`
  has the daycare block; `53000854` and `53000226` do not.

### Step 1 — Sections from one source

- [ ] Add `SCHOOL_SECTIONS` (D2), with a Portuguese comment: the ids are public anchors and are not
  renamed.
- [ ] Add `_has_section`, `_open_section`, `_renderers` to `SchoolPage`.
- [ ] Make each of the nine `_block_*` methods start with `self._open_section("<id>")` (replacing the
  heading code plan 0 left in them). Drop nothing else from the block bodies.
- [ ] Replace the nine explicit calls and the daycare guard in `render` with the loop of D2 and the
  `BuildError` on renderer/section mismatch.
- [ ] Gate: the site is byte-identical to `golden_p1` (nothing visible has changed yet).

### Step 2 — The TOC

- [ ] `SchoolPage.toc()` builds the `<nav>` of D1 with one `<li><a href="#id">label</a></li>` for
  each section where `_has_section` is true, labels through `html.escape`.
- [ ] In `render`, concatenate `self.toc()` immediately after `<p class="subtitulo">` and before the
  page notice.
- [ ] No `data-numero`, `class="num"` or `data-estado` inside the `<nav>`; nothing goes to
  `self.numbers`.

### Step 3 — CSS and print

- [ ] Rules in `static/style.css` after `.trilha`:
  - `.sumario-escola { margin: 0 0 1rem; }`;
  - `.sumario-escola details`: `1px solid var(--linha)` border, `var(--papel-forte)` background, 8 px
    radius;
  - `.sumario-escola summary`: `cursor: pointer; padding: .55rem .8rem; font-weight: 600; font-size:
    .9rem;` and `:focus-visible` with `outline: 2px solid var(--destaque); outline-offset: 1px`;
  - `.sumario-escola ul`: `list-style: none; margin: 0; padding: 0 .8rem .6rem; columns: 3 12rem;
    column-gap: 1rem;`;
  - `.sumario-escola li { break-inside: avoid; }`;
  - `.sumario-escola a { display: inline-block; padding: .3rem 0; }`;
  - `.bloco { scroll-margin-top: .75rem; }`.
- [ ] Append `.sumario-escola` to the `display: none` group of `@media print`.
- [ ] Do not touch `main`, the width of `.bloco` or the breakpoints.

### Step 4 — The check (`checks/school_toc.py`)

- [ ] `CONTRACT_SECTIONS`: a literal tuple of the nine `(id, label, only_with_daycare)` (frozen copy
  of `docs/FASE-1.md` §2.2; Portuguese comment explaining that it exists so a rename breaks
  `--check`). It imports nothing from `school_page.py`.
- [ ] `_verify_school_toc(code, markup, daycare_offered)` raises `BuildError` (with `code` in the
  message) when:
  - there is not exactly one `<nav class="sumario-escola"`, or it does not come after the `<h1>` and
    the `.subtitulo` and before the first `<section class="bloco"`;
  - the `<details>` has `open`, or `<summary>` is missing;
  - `<li>`, `<a href="#…">` and parsed `<li><a href="#id">label</a></li>` items are not equal in
    number (no loose item, no link outside an `<li>`);
  - the TOC ids, in order, differ from the ids of the parsed sections
    (`<section class="bloco" id="…"><h2>…</h2>`), or either differs from the expected list, which
    comes from `CONTRACT_SECTIONS` filtered by `oferta_inf_cre == 1` (data, not HTML); use
    `require_equal_lists` for these comparisons;
  - a TOC label, after `html.unescape`, differs from the `<h2>` of the section with the same id, or
    from the contract label;
  - any `href="#x"` does not match exactly one `id="x"` in the document;
  - the daycare rule is broken, with its own messages: a `#creche` link or `id="creche"` present with
    `oferta_inf_cre != 1`, or absent with `== 1`;
  - the visible `<nav>` text (without tags) is not "Nesta página" followed only by the labels, or
    has a digit, `data-numero` or `class="num"`.
- [ ] `check_school_toc(site, data)`:
  - count `site.glob("[0-9]" * 8 + ".html")` (the glob of `_clean_output`) and fail if it differs from
    `len(data["escolas"])`, so the sweep is provably complete;
  - call `_verify_school_toc` for **every** school;
  - before the sweep, an in-memory self-test on the HTML of `53000781` (with daycare) and `53000854`
    (without): each mutation below must raise `BuildError`, and each `str.replace` must actually
    change the text (otherwise the test is empty and the check fails):
    1. remove the `<li>` of `#creche` from `53000781`;
    2. add a `#creche` `<li>` to `53000854`;
    3. swap the first two `<li>` of `53000781`;
    4. change "Oferta por etapa" to "Oferta" only in the TOC;
    5. add `open` to the `<details>`;
  - return, with computed (not hand-written) numbers, something like `"1,291 páginas: sumário =
    seções, na ordem e com o mesmo rótulo; 475 com creche (oferta_inf_cre = 1), 816 sem"`, in the
    `:,` format the other checks use.

### Step 5 — Registry and CLI

- [ ] Add `Check("sumario_escola", "--check-sumario-escola", "critério 8: sumário da página da escola",
  lambda ctx: check_school_toc(ctx.out, ctx.data))` after `estados` in `CHECKS`.
- [ ] Add the usage line to the docstring of `scripts/12_build_site.py`.
- [ ] `check_edge_cases` does not change.

### Step 6 — Local verification (no file edits)

- [ ] Run the §7 commands; confirm nine `[ok]` lines.
- [ ] Strip-and-compare against `golden_p1`: in all 1,291 new pages remove the
  `<nav class="sumario-escola">…</nav>` and require bytes identical to the baseline page;
  `index.html`, `como-ler.html`, `creditos.html`, `indice.json`, every `dados/*.json` and `data/public`
  identical; `estilo.css` is the only other file that changes.
- [ ] Browser checks of §7 (360 px, 1280 px, print, no JS).

### Step 7 — Contract and worklog

- [ ] `docs/FASE-1.md`:
  - **§2.2 "O sumário da página da escola"** (after §2.1): the markup; the nine ids and labels in
    order; daycare only with `oferta_inf_cre == 1`; label = `<h2>`; labels only (no number, count or
    ranking; not a data block, no provenance, n or limit ids); closed by default, no JavaScript,
    hidden in print; ids are public anchors and are not renamed; the order is the fixed order of §2,
    not sortable by indicator;
  - **§5.2**: the comment of `<CO_ENTIDADE>.html` mentions the section TOC (§2.2);
  - **§5.3**: the `--check` block and the text describing what it runs;
  - **§7 "Escopo real do gate"**: criteria 1–4, 6, 7 and 8;
  - **§8**: the opening paragraph says `--check` sweeps the 1,291 pages in criteria 1, 3, 4 and 8; new
    **criterion 8. Sumário da página da escola** with the `--check-sumario-escola` command in the same
    style as the others.
- [ ] `.github/workflows/pages.yml`: update the comment on covered criteria (add 8); do not change the
  `run`.
- [ ] Create `docs/worklogs/2026-11-10-03-sumario-da-escola.md` in the existing format (*O que
  entrou*, *Decisões*, *Verificação*, *Pendências*), recording: the choice and rejected alternatives;
  the pasted `[ok] sumario_escola` line and the whole `--check`; the 360 px, 1280 px, print and no-JS
  results; the baseline comparison; and the explicit sentence that `data/public` did not change (with
  `git diff --stat -- data/public` empty).

## 6. Acceptance criteria

1. **One TOC per page.** Each of the 1,291 pages `site/<CO_ENTIDADE>.html` has exactly one
   `<nav class="sumario-escola">`, after the `<h1>` and the subtitle and before `#identificacao`,
   with a closed `<details>`.
2. **Anchors and labels.** The links point, in order, to the ids of the rendered sections
   (`identificacao`, `oferta`, `matricula`, `ideb`, `fluxo`, `tdi`, `tnr`, `infraestrutura` and, when
   it exists, `creche`); each link has the same label as its section's `<h2>`; each `href="#x"`
   matches an `id="x"`.
3. **Daycare.** The `#creche` link exists if and only if `oferta_inf_cre == 1`: 475 pages with, 816
   without. `53000781` has the link; `53000854` and `53000226` do not.
4. **Labels only.** The TOC has no digit, count, ranking, `data-numero` or `class="num"`; the
   `dados/*.json` are identical to before.
5. **Ids preserved.** The nine block ids are today's; no block changes a byte.
6. **Index untouched.** `render_index_page` and `index.html` do not change (nor does the RA jump).
7. **Gate.** `--check` passes with `[ok] sumario_escola` and the eight earlier items unchanged in
   result; `--check-sumario-escola` passes alone; the message reports 1,291 pages swept, 475 with
   daycare and 816 without.
8. **The check can fail.** The five self-test mutations raise `BuildError`; a page count different
   from `len(schools)` does too.
9. **Responsive.** At 360 px and 1280 px, with the TOC open and closed, there is no horizontal
   overflow (`documentElement.scrollWidth <= clientWidth`); the 56 rem layout does not change.
10. **Print.** In `print` media the TOC is `display: none`.
11. **No JavaScript.** School pages have no `<script>`; the `<details>` opens by keyboard and click,
    and clicking a link changes the hash and goes to the section.
12. **Insumo and repository.** `git diff -- data/public` empty; `site/` stays out of git;
    `requirements.txt` unchanged; two consecutive builds produce the same bytes.
13. **Documentation.** `docs/FASE-1.md` describes the TOC (§2.2) and criterion 8; the worklog carries
    the check output and the `data/public` sentence.

## 7. Verification

```sh
# build + criteria 1–4, 6–8, idempotence of 5 and edge cases
.venv/bin/python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check

# criterion 8 only
.venv/bin/python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-sumario-escola

# syntax, diff and insumo
.venv/bin/python -m compileall -q scripts
git diff --check
git diff --stat -- data/public          # empty
git status --short                      # site/ does not appear
```

`grep` checks (the three pages are profiles a, d and e of §4 of the contract):

- `grep -c 'href="#creche"' site/53000781.html` → 1; `site/53000854.html` and `site/53000226.html` → 0;
- `grep -l 'href="#creche"' site/[0-9]*.html | wc -l` → 475;
- `grep -c '<nav class="sumario-escola"' site/[0-9]*.html` → 1 on every file (no 0 or 2);
- `grep -l '<script' site/[0-9]*.html` → empty (no JS on school pages);
- two builds, `find site -type f -exec sha256sum {} + | sort`, `diff` → empty.

Browser checks (Playwright or chrome-devtools MCP; the `playwright` package is not in the `.venv`, so
there is no test script in the repository):

- at 360 px and 1280 px, on `53000781` (nine links, the longest TOC) and `53000226` (eight links),
  with the `<details>` closed and open, measure `document.documentElement.scrollWidth <= clientWidth`;
  if a page already overflows in the baseline (a long school name, for example), compare it with
  `/tmp/opencode/golden_p1/site` and pick another so the result is attributable to the TOC;
- emulate `print` media and check `getComputedStyle(nav).display === "none"`;
- without JS: the `<details>` opens by click and by Enter/Space; clicking "Infraestrutura" changes
  `location.hash` to `#infraestrutura`;
- keyboard: Tab reaches the `<summary>`, then the links, with visible focus.

## 8. Risks and open questions

### Risks

- **Dependency on plans 0 and 1.** This plan assumes the `_block_*` methods and the `CHECKS` registry
  (plan 0) and `require_equal_lists` and the print group (plan 1). If either landed differently,
  adjust steps 1, 4 and 5; the design does not change. `.sumario-escola` does not collide with plan
  1's `.sumario` (a `.sumario` selector does not match the class `sumario-escola`), and plan 1's
  `<noscript>` rule lives only on the index.
- **Fragile regexes.** `_verify_school_toc` parses markup the build itself emits; changing the format
  breaks the check (which is, in part, the point). If it bothers, replace them with an
  `html.parser.HTMLParser` subclass from the standard library, no new dependency.
- **Deliberate duplication** of ids and labels between `SCHOOL_SECTIONS` and `CONTRACT_SECTIONS`
  (D3): a new section requires updating the constant, the frozen copy and `docs/FASE-1.md`. That is
  the gate, not an oversight.
- **A closed `<details>` hides the links** until clicked. Accepted for the no-JS version; the sections
  remain in the normal scrollable flow.
- **Columns.** `columns: 3 12rem` needs a visual check around 768 px. If it looks odd, fall back to a
  single column (drop `columns`); no criterion depends on the columns.
- **Long labels.** "Distorção idade-série" and "Taxa de não-resposta" are the longest; at 360 px the
  layout is one column and should not overflow, but the measurement of §7 is what proves it.
- **Identifier language.** Plan 0 moved code identifiers to English; the anchor ids, CSS classes and
  copy stay Portuguese by design (plan 0, D4), so `SCHOOL_SECTIONS` mixes English names with
  Portuguese string values on purpose.

### Open questions

- **Q1 (resolved) — criterion 7 or 8?** Plan 1 took 7; this plan is **8**, as its own criterion
  rather than a sub-item of criterion 2 (D4).
- **Q2 — does the TOC go before or after the page-wide notice?** On pages such as `53020529` and
  `53000331`, the "nenhum indicador" `<p class="ausencia">` sits today between the subtitle and block
  1. This plan puts the TOC before it (one closed line, and the "before the first section" rule holds
  in both cases). Putting the notice right under the title is the alternative; only the order of the
  two concatenations in `render` and the position check change.
- **Q3 — `<summary>` label.** "Nesta página" is a fixed interface label. If the maintainer prefers
  "Seções desta página" or another text, one string in the build and in §2.2 changes.
- **Q4 — TOC in `check_edge_cases` too?** That check renders pages from a doctored insumo and does not
  look at the TOC; the TOC depends only on `oferta_inf_cre`, not on enrollment. Not included: the
  sweep over the 1,291 real pages already covers it.

## 9. Out of scope

- `render_index_page`, the RA jump, the index JavaScript and any change to `index.html` or
  `indice.json`.
- A sticky sidebar, an always-open TOC, a "back to top" button or smooth scrolling.
- A per-stage TOC inside blocks (the `<h3>` of initial years / final years / high school).
- Count, number, ranking or any new data on the page; changes to `data/public`, `procedencia.json` or
  the schema of `dados/<CO_ENTIDADE>.json`.
- Renaming block ids or reordering blocks.
- Jinja2, a framework, a new dependency, hosting changes or the workflow command.

## 10. Definition of done

- [ ] `sitegen/school_page.py` generates `<nav class="sumario-escola">` on every school page, with
  section headings and TOC both coming from `SCHOOL_SECTIONS`.
- [ ] `check_school_toc` sweeps the 1,291 pages and passes; its mutation self-test fails where it
  should; `--check` passes nine items and `--check-sumario-escola` passes alone.
- [ ] `53000781` shows the daycare link; `53000854` and `53000226` do not.
- [ ] 360 px and 1280 px without horizontal overflow; print hides the TOC; without JavaScript the page
  stays navigable.
- [ ] The baseline comparison shows only the `<nav>` and `estilo.css` changed.
- [ ] `docs/FASE-1.md` (§2.2, §5.2, §5.3, §7, §8) and the worklog describe what entered;
  `data/public` did not change; `site/` stays out of git.
- [ ] No undocumented manual step; the build is still idempotent.
