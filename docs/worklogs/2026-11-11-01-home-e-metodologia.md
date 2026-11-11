# 2026-11-11-01 — home com números de destaque, lista em `escolas.html` e página de metodologia

Plano: [`docs/plans/2026-11-11-home-e-metodologia.md`](../plans/2026-11-11-home-e-metodologia.md).
Contrato: [`docs/FASE-1.md`](../FASE-1.md) §2.1, §2.3, §2.4, §5.1, §5.2 e §8 (critério 9).

## 1. O que entrou

1. **Home em `site/index.html`**: chamada, quatro cartões, gráfico de distorção
   idade-série por rede, motivação em três parágrafos e resumo de método.
2. **Lista de escolas em `site/escolas.html`**: o antigo índice, sem mudança de
   comportamento, marcação, `id="ir-ra"`, bloco `noscript` ou `indice.json`.
3. **`site/metodologia.html`**: oito seções (fontes, entrada do dado, chaves,
   estados, o que a página da escola mostra, a comparação entre redes, como
   conferir, limites e reprodução).
4. **Duas tabelas de contexto em `data/public/`**: `ideb_uf.parquet` (24 linhas)
   e `agregados.parquet` (40 linhas), com a emenda correspondente no
   `AGENTS.md` e a lista fechada declarada em `data/public/README.md`.
5. **Critério 9 (`--check-home`)** e escopo do critério 2.

## 2. Decisões tomadas e por quê

- **A comparação entre redes é publicada, e é a única do site.** Sem o valor
  nacional e a posição, a motivação ("o DF é 27º de 27 na rede estadual do
  ensino médio") seria uma frase sem fonte visível. O número entra por um parquet
  versionado, não por texto digitado.
- **D3 ganhou escopo em vez de exceção.** `checks/ranking.py` continua com a
  mesma lista de termos, aplicada a `escolas.html` e às 1.291 páginas de escola.
  A home nomeia `p10`/`p90` porque precisa (legenda e tabela do gráfico), e isso
  está no contrato (§2.3) e no docstring do check.
- **A distribuição usa todos os valores publicados, sem limiar de n** (decisão do
  mantenedor, 2026-11-11). Assim a mediana da home é a mesma de `README.md` e
  `REPORT.md` (9,0 / 17,1 / 20,7 e 1,2 / 3,2 / 4,5) e nenhum parâmetro de build
  entra no export. A diferença em relação à página da escola é declarada em
  **L-67**, na legenda e no `calculo` de cada registro `tdi-*`.
- **"Privada" = conveniada + não conveniada** (decisão do mantenedor,
  2026-11-11), dito no `calculo` e na legenda (L-36, L-37). A rede federal fica
  fora (L-32).
- **O cartão da ausência de Ideb é decomposto por estado do dado**, nunca por
  causa: 499 com Ideb (499 públicas e 0 privadas), 80 públicas com linha e sem
  nota, 11 públicas sem linha, 31 privadas com linha e sem nota e 306 privadas
  sem linha. A regra de participação (L-30) aparece como explicação possível de
  parte dos casos; L-08 e L-09 sustentam o resto.
- **Um decimal com arredondamento half-up sobre a string decimal** (`fmt_pct`,
  `Decimal` + `ROUND_HALF_UP`), e não `fmt_dec`: 8,95 precisa sair 9,0 e 4,05
  precisa sair 4,1, como nos documentos. `fmt_dec` continua intocado nas páginas
  de escola, cujos valores têm no máximo um decimal.
- **O `fmt_pct` não carrega o símbolo `%`**: o símbolo fica no texto em volta
  (o cartão da creche, o cabeçalho da tabela do gráfico, o eixo do SVG). Assim o
  texto do `data-numero` é o número, e o check compara número com número.
- **A posição "27º de 27" é derivada do parquet, não digitada.** O check confere
  a invariante `posicao == n_ufs` para a linha EM/Estadual 2025, e falha se a
  frase aparecer sem essa condição. A mutação de §9 do plano ("posicao 26 no
  export com a copy dizendo 27º de 27") foi reproduzida passando ao check o site
  construído e um modelo com `posicao = 26`: o check falha no confronto
  texto × parquet. Com a copy derivada, não existe o caso de texto velho.

## 3. Medições (2026-11-11, `data/public`)

| o que | valor | como |
|---|---|---|
| escolas / RAs | 1.291 / 35 | `escolas.parquet` |
| unidades com creche | 475 (estadual 7) | `oferta_inf_cre == 1` |
| matrícula em creche 2025 | 42.582 (estadual 149 = 0,3499%) | `mat_inf_cre_2025` |
| universo do Ideb | 927 | oferta de AI, AF ou EM |
| com Ideb 2025 | 499 | qualquer etapa ofertada com `valor` |
| pública sem Ideb | 91 (80 com linha, 11 sem) | idem |
| privada sem Ideb | 337 (31 com linha, 306 sem) | idem |
| distorção 2025, n | 386 / 311 / 195 / 200 / 101 / 150 | estados `valor` e `zero` |
| medição do CSV do `q8` | sha256 `0d5cbb07…e7e0` antes e depois | `sha256sum` |

Os três parquets que já existiam tiveram **conteúdo** idêntico (medido com
`hash_pandas_object` sobre as linhas ordenadas pela chave) e, nesta execução,
bytes idênticos também: o `git diff` de `data/public` só mostra o
`procedencia.json`. O insumo publicado cresceu 11.683 B (5.653 + 6.030).

## 4. Verificação executada

- `python scripts/06_analysis.py --public data/public --force`: sai 0,
  `q0_execucao.csv` sem etapa pulada, e grava 1.291 escolas, 21.720 linhas de
  indicador, 7.416 de infraestrutura, 24 de Ideb por UF e 40 agregados.
- `python scripts/12_build_site.py --public data/public --out site
  --data-build 2026-11-06 --check`: dez `[ok]`, incluindo `home`, e 2.590
  arquivos / 29,9 MB.
- `python -m compileall -q scripts`: limpo.
- Servidor local no mesmo subpath de produção: `200` para `/prova-dos-nove/`,
  `escolas.html`, `metodologia.html`, `dados/home.json`, `indice.json`,
  `estilo.css`, `como-ler.html`, `creditos.html` e uma página de escola.
- Nenhum caminho raiz-absoluto em nenhum HTML do site; `index.html` sem
  `id="ir-ra"` e `escolas.html` com as 35 seções e as 1.291 escolas.

Mutações injetadas (todas revertidas), com o `[falhou]` esperado:

| mutação | check que falhou |
|---|---|
| `"limites": []` num registro de `home.json` | `home` |
| `data-numero` sem registro | `home` |
| legenda do gráfico removida | `home` |
| L-67 retirado dos `limites` de um `tdi-*` | `home` |
| "turma pequena" retirado do `calculo` de um `tdi-*` | `home` |
| `posicao = 26` no modelo com a copy em 27º | `home` |
| `▲` num cartão | `home` |
| link para `53000854.html` na home | `home` |
| soma da ausência errada no export | `home` |
| `p90` no texto de `como-ler.html` | **nenhum** (fora do escopo, como planejado) |
| `p90` numa página de escola | `ranking` |
| `p90` em `escolas.html` | `ranking` |
| `<noscript><style>.sumario` removido de `escolas.html` | `sumario` |

O `casos_limite` foi conferido com a lista de cópia atualizada (os dois parquets
novos); sem eles, o `load_data` da cópia temporária falha antes de qualquer
asserção, que é o efeito esperado da mutação "tirar um parquet da lista".

## 5. O que ficou fora, de propósito

- Busca na home (ela linka `escolas.html`, que já tem busca).
- Qualquer indicador que não esteja em `data/public/` (o déficit de creche da
  PDAD, 27,1%, continua fora).
- Mudança na página da escola além do link "Todas as escolas" (agora
  `escolas.html`) e do cabeçalho compartilhado.
- Redesenho do site, favicon, roteador de cliente ou página 404.

## 6. Pendências abertas

- **L-66**: o denominador da posição ("de 27") varia entre etapas e anos (em
  2023 a rede estadual dos anos iniciais tinha 26 UFs com valor). A home nomeia o
  denominador em cada cartão, mas a leitura de "27º de 27" continua sendo do
  projeto, não da INEP.
- **L-67**: se o propósito do gráfico mudar, ou se a mediana da home tiver de
  bater com a da página da escola, o export passa a precisar do limiar e os
  documentos (`README.md`, `REPORT.md`) mudam no mesmo commit.
- **Crescimento de `agregados.parquet`**: a lista fechada do `AGENTS.md` se refere
  ao arquivo, não às linhas. Ids novos dentro do arquivo não exigem nova emenda —
  o que se confirmou aqui, mas segue como pergunta aberta no plano (§10).
