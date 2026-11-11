# 2026-11-10 — sumário da página da escola (FASE-1, critério 8)

## O que entrou

- `scripts/sitegen/school_page.py`: `SCHOOL_SECTIONS` (âncora, rótulo e coluna de
  condição, na ordem do contrato), `_has_section`, `_open_section` (a `<section>`
  e o `<h2>` saem do mesmo lugar), `_renderers` (âncora → método `_block_*`, sem
  `getattr` sobre string portuguesa) e `toc()`. `render` percorre a tupla, chama
  o renderizador de cada seção existente e falha se as chaves não casarem com
  `SCHOOL_SECTIONS`. Os nove `_block_*` abrem com `_open_section`, e não mudam
  mais nada: as seções saem byte a byte como antes.
- O sumário é um `<nav class="sumario-escola" aria-label="Seções desta página">`
  com `<details>` fechado, `<summary>Nesta página</summary>` e um
  `<ul role="list">` (sem numeração), logo depois do `<p class="subtitulo">` e
  antes do aviso da página. Só rótulos: nada de número, `data-numero`,
  `class="num"` ou entrada em `dados/<CO_ENTIDADE>.json`. O `role="list"` existe
  porque `list-style: none` tira a semântica de lista no Safari/VoiceOver.
- `scripts/sitegen/static/style.css`: `.sumario-escola` (uma linha fechada,
  borda/fundo/raio do bloco), `summary` com foco visível, lista em
  `columns: 3 12rem` com `break-inside: avoid`, alvo de toque de `0.3rem` e
  `scroll-margin-top` nos `.bloco`; `.sumario-escola` entra no grupo
  `display: none` da impressão.
- `scripts/sitegen/checks/school_toc.py`: `CONTRACT_SECTIONS` (cópia congelada do
  §2.2), `_verify_school_toc` e `check_school_toc`. Confere posição do `<nav>`,
  `<details>` fechado, contagem de `<li>`/links/itens, âncoras e rótulos do
  sumário contra as seções e contra o contrato, `href` casando com um único `id`,
  a regra da creche pela coluna do insumo, texto visível sem dígito e ausência de
  marcação de número, o `aria-label` do `<nav>` e o `<ul role="list">`. Antes da
  varredura, roda seis mutações no HTML de `53000781`/`53000854` que precisam
  falhar (e falha se a mutação não alterar o texto).
- `scripts/sitegen/checks/__init__.py`: `Check("sumario_escola",
  "--check-sumario-escola", …)` logo depois de `estados`; `--check` passa a ter
  nove itens.
- `scripts/12_build_site.py`: linha de uso de `--check-sumario-escola` na
  docstring.
- `docs/FASE-1.md`: §2.2 (markup, ids, creche, rótulos apenas, sem JS, impressão,
  âncoras públicas), §5.2, §5.3, §7 e §8 (critério 8). O comentário do workflow
  do Pages cita o critério 8; o `run` não mudou.

## Decisões

- Um `<details>` fechado dentro de um `<nav>`: abre com teclado e clique, sem
  JavaScript, e ocupa uma linha em qualquer largura. Lista visível empurraria
  "Identificação" para fora da primeira tela a 360 px; barra lateral exigiria
  refazer o layout de `main`; `<select>` de salto precisaria de JavaScript.
- Uma fonte para ids, rótulos, ordem e condição da creche: o sumário não pode
  divergir do `<h2>` nem oferecer link para seção que a escola não tem.
- O check usa uma cópia congelada do contrato, não `SCHOOL_SECTIONS`: renomear um
  id que é âncora pública precisa quebrar o `--check` e aparecer no diff, junto
  de `docs/FASE-1.md`.
- Critério próprio (8), depois de `estados`: consistência de âncora não é
  procedência, ranking, limiar nem estado. `--check` continua sendo o gate, sem
  job novo.
- Sumário antes do aviso de "nenhum indicador" (`Q2` do plano): uma linha fechada
  e a regra "antes da primeira seção" valem nos dois casos.

## Verificação

```text
site: 1,291 páginas de escola, 29.8 MB em site
[ok] procedencia: 1,291 páginas com procedência completa
[ok] ranking: 1,291 entradas alfabéticas, sem número no índice
[ok] sumario: 35 RAs no salto, casando com as seções e com o rótulo
[ok] limiar: 80 unidades escola × etapa com n < 30 suprimidas ...
[ok] estados: símbolos, frases de 2024 e presença no Censo conferidos
[ok] sumario_escola: 1,291 páginas: sumário = seções, na ordem e com o mesmo rótulo; 475 com creche (oferta_inf_cre = 1), 816 sem
[ok] reprodutibilidade: segundo build produz os mesmos bytes
[ok] licencas: 6 fontes com licença declarada nos créditos
[ok] casos_limite: 53 sem linha/3 com célula vazia em 2024, ...
```

- `--check` com nove `[ok]`; `--check-sumario-escola` sozinho também passa. As
  seis mutações do autoteste (remover o link da creche, acrescentá-lo sem
  oferta, trocar a ordem, encurtar um rótulo, abrir o `<details>` e retirar o
  `role="list"` do `<ul>`) falham como devem; uma contagem de páginas diferente
  de `len(escolas)` também.
- `grep`: `href="#creche"` aparece 1 vez em `53000781`, 0 em `53000854` e
  `53000226`, e em 475 páginas no total; `<nav class="sumario-escola"` aparece
  exatamente 1 vez em cada uma das 1.291; nenhuma página de escola tem
  `<script>`.
- Contagem de páginas e bytes contra o golden do plano 1
  (`/tmp/opencode/golden_p1/site`): removendo o `<nav class="sumario-escola">…</nav>`
  das 1.291 páginas novas, todas ficam byte a byte iguais. `index.html`,
  `como-ler.html`, `creditos.html`, `indice.json` e os 1.291 `dados/*.json`
  idênticos; `estilo.css` é o único outro arquivo que muda.
- Navegador (Chromium headless, `http://127.0.0.1:8765`): a 360 px e 1280 px, com
  o `<details>` fechado e aberto, `scrollWidth == clientWidth` (360 e 1.265) nas
  páginas `53000781` (nove links) e `53000226` (oito); `main` continua com 896 px
  a 1280 px e a lista fica em uma coluna a 360 px e em três a 1280 px.
- Sem JavaScript: `summary` recebe foco e abre com Enter; clicar em
  "Infraestrutura" grava `#infraestrutura` e rola até a seção (topo 12 px); as
  páginas de escola continuam sem `<script>`.
- Impressão: a regra `@media print` publicada esconde `.sumario-escola` junto de
  `.topo`, `footer.rodape`, `.trilha` e `.sumario`.
- `compileall` e `git diff --check` limpos. `data/public` não mudou:
  `git diff --stat -- data/public` vazio; `site/` continua fora do git.

## Pendências

- Conferir o `<details>` no Firefox e no Safari (a verificação rodou no Chromium
  headless).
- Reavaliar `columns: 3 12rem` perto de 768 px; se ficar estranho, cair para uma
  coluna não muda nenhum critério.
- Se um dia entrar uma seção nova, atualizar `SCHOOL_SECTIONS`,
  `CONTRACT_SECTIONS` e `docs/FASE-1.md` §2.2 no mesmo commit — a duplicação é o
  gate, não um esquecimento.
