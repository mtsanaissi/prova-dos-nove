# 2026-11-10 — salto por Região Administrativa no índice (FASE-1, critério 7)

## O que entrou

- `scripts/sitegen/region.py`: `REGION_LABELS` (35 entradas do Apêndice A do
  plano), `_strip_accents`, `region_anchor_id` (`ra-<slug>` a partir do valor
  bruto), `region_label` (rótulo de exibição; RA fora do mapa interrompe o build)
  e `region_sort_key` (rótulo sem acento e sem caixa, valor bruto como desempate).
- `index_page.render_index_page`: `<select id="ir-ra">` com o rótulo
  `for="ir-ra"`, uma opção por RA em ordem de rótulo e a opção vazia
  "Selecione…"; cada seção ganhou `id="ra-<slug>"` e o `<h2>` passou a mostrar o
  rótulo. Colisão de âncora entre duas RAs interrompe o build. Nenhuma contagem,
  nenhum link de volta.
- `layout.document`: parâmetro opcional `head_extra=""`, inserido na mesma linha
  do `<link rel="stylesheet">` — vazio, os bytes das outras páginas não mudam.
  Só o índice passa o `<noscript><style>.sumario { display: none; }</style></noscript>`.
- `school_page`: o subtítulo e a linha "Região Administrativa" da ficha mostram o
  rótulo; o insumo, `indice.json` e a procedência continuam com o valor bruto.
- `static/search.js`: o salto (`change` registrado antes do `fetch`, então
  funciona mesmo se `indice.json` falhar), a sincronia com o filtro (opção
  escondida e desabilitada quando a RA não tem escola visível; `<select>`
  desabilitado quando não há resultado) e os identificadores traduzidos para
  inglês. Strings, ids e `data-*` do HTML não mudaram.
- `static/style.css`: o `<select>` herda tipografia, borda, fundo, raio e foco do
  campo de busca; `.ra` ganhou `scroll-margin-top: .5rem`; impressão esconde
  `.sumario`.
- `checks/region_toc.py` (`check_region_toc`) e `require_equal_lists` em
  `checks/common.py`: confere seletor, rótulo, opções, âncoras, ordem, rótulos e
  duplicatas. Registro em `CHECKS` logo depois de `ranking`, com a flag
  `--check-sumario`; o `main` não foi tocado.
- `docs/FASE-1.md`: §2.1 (três formas de chegar, rótulo de exibição, fallback sem
  JavaScript), bloco 1 do §2, árvore do §5.2, escopo do gate no §7 e critério 7 no
  §8. O comentário do workflow do Pages cita o critério 7; o comando não mudou.

## Decisões

- `<select>` de salto em vez de 35 links: uma linha em qualquer largura e
  semântica de formulário; a lista completa continua abaixo.
- Rótulo de exibição em caixa de título e com acentos; `data-ra`, `indice.json` e
  `data/public` guardam o valor bruto, e o slug deriva dele. `SCIA` e `SIA`
  ficam em caixa alta por serem siglas.
- Nenhuma contagem por RA: o índice não publica número (§2.1) e o guarda atual não
  pegaria um número solto como "Ceilândia (142)".
- Nenhum "voltar ao índice" por seção: o histórico do navegador já resolve, e 35
  links custariam 35 paradas de tabulação.
- Critério próprio em vez de estender `check_no_ranking`: consistência de âncora
  não é ranking, e o nome do critério 2 continua verdadeiro.
- Sem JavaScript o `<select>` fica escondido, porque um controle inerte sugere
  que funciona; a lista completa é o caminho sem JS.
- Sem framework e sem dependência nova: f-string para o HTML, CSS e JS em
  arquivos.

## Verificação

```text
site: 1,291 páginas de escola, 29.1 MB em site
[ok] procedencia: 1,291 páginas com procedência completa
[ok] ranking: 1,291 entradas alfabéticas, sem número no índice
[ok] sumario: 35 RAs no salto, casando com as seções e com o rótulo
[ok] limiar: 80 unidades escola × etapa com n < 30 suprimidas ...
[ok] estados: símbolos, frases de 2024 e presença no Censo conferidos
[ok] reprodutibilidade: segundo build produz os mesmos bytes
[ok] licencas: 6 fontes com licença declarada nos créditos
[ok] casos_limite: 53 sem linha/3 com célula vazia em 2024, ...
```

- `--check` com oito `[ok]`; `--check-sumario` sozinho também passa. Mutações na
  cópia do índice (âncora repetida, opções fora de ordem, rótulo fora do mapa,
  seletor ausente, seções ausentes) fazem o check falhar com a posição e os dois
  valores.
- `index.html`: 1 `<select id="ir-ra">`, 35 opções `value="#ra-…"`, 35 seções
  `id="ra-…"`, ordem idêntica; nenhum `[0-9]+ escolas?`; rótulos com acento e
  `data-ra` bruto presentes.
- Navegador (Playwright, `http://127.0.0.1:8765`): saltar para Ceilândia grava
  `#ra-ceilandia`, rola até a seção (topo 8 px) e devolve o select ao
  placeholder; repetir a escolha rola de novo; Back volta ao topo. Opção
  desabilitada não navega. Buscar "CEF 01 DO PLANALTO" deixa só Plano Piloto na
  lista e no select; limpar restaura as 35; "zzzz" desabilita o select e mostra
  "Nenhuma escola encontrada.".
- Com `indice.json` abortado: a busca desabilita, o select continua habilitado e o
  salto para `#ra-gama` funciona.
- JavaScript desligado: `.sumario` com `display: none`, aviso do corpo visível e
  1.291 escolas na lista. Impressão: `.sumario` escondido.
- 360, 768 e 1280 px: sem rolagem horizontal; o select ocupa 325, 544 e 544 px,
  a mesma largura do campo de busca, em uma linha.
- Build duas vezes: 2.587 arquivos com os mesmos sha256.
- Escopo do diff contra o golden do plano 0: mudam `index.html`, `estilo.css` e
  1.279 páginas de escola; as 12 de SCIA e SIA ficam idênticas porque o rótulo é
  igual ao valor bruto. `como-ler.html`, `creditos.html`, `indice.json` e os
  1.291 `dados/*.json` byte a byte iguais. Em cada página alterada, substituir o
  rótulo pelo valor bruto no subtítulo e na ficha reproduz o golden.
- `compileall` e `git diff --check` limpos. `data/public` não mudou: `git diff --
  data/public` vazio; `site/` continua fora do git.

## Correções da revisão (2026-11-10)

- `region.py`: o rótulo de `SOL NASCENTE / POR DO SOL` passa a "Sol Nascente/Pôr
  do Sol". A revisão pegou a falta do circunflexo; a forma oficial é "Pôr do Sol"
  (SEGOV-DF, RA XXXII; CLDF; G1). A âncora não muda, porque deriva do valor bruto.
- `checks/region_toc.py` passou a conferir o que a revisão apontou como sem
  guarda: o `<noscript><style>.sumario { display: none; }</style></noscript>` no
  `<head>` do índice (critério 6) e, por seção, que `id` e rótulo derivem do
  `data-ra` bruto (`region_anchor_id`, `region_label`). Antes o check comparava só
  a lista de opções com a lista de seções.
- `docs/LIMITES.md` ganhou **L-64**: o rótulo é tabela escrita à mão, não campo
  da fonte, e o `calculo` do bloco de identificação em `procedencia.json` segue
  "cópia dos campos" porque regenerá-lo mudaria `data/public` — que o escopo
  desta tarefa congela. `docs/FASE-1.md` §2.1 e o bloco 1 citam L-64.

## Pendências

- Reavaliar se o desktop pede uma visão das 35 RAs além do select (um
  `<details>` ou lista visível entram sem mudar as âncoras).
- Confirmar a forma oficial de `SCIA`, `SIA`, "Riacho Fundo II" e "Sobradinho II"
  antes de publicar; hoje seguem o Apêndice A. "Pôr do Sol" foi conferido e
  corrigido na revisão (L-64).
- Conferir o salto no Firefox e no Safari. A revisão rodou só no Chromium
  (headless no Linux), onde a seta num `<select>` fechado abre o popup nativo e
  não dispara `change`; no Chrome/Windows a seta muda o valor e dispara `change`,
  e o salto devolve o select ao placeholder a cada escolha. Se o teclado ficar
  preso na primeira RA, a alternativa é navegar no `blur`/confirm, não no
  `change`.
- Reavaliar `<nav>`/`<form>` em volta do select se uma auditoria de
  acessibilidade pedir um landmark.
