# 2026-11-09 — validação pré-publicação da FASE-1

## O que entrou

- `scripts/12_build_site.py`: `n_referencia` passou a existir só quando há
  contagem de alunos. O Ideb histórico com `n` presente continua levando
  `"n_referencia": "2025"`; quando o `n` é `null` (matrícula de 2025 ausente),
  o campo não aparece. `check_procedencia` exige o campo exatamente nessa
  condição e `check_casos_limite` cobre os dois lados: AI histórico com n null
  sem o campo e AF histórico com n = 138 com `"2025"`.
- `docs/FASE-1.md` §2: o campo do cadastro de 2025 passou de `NO_ENTIDADE` para
  `Nome da escola`.
- `docs/FASE-1.md` §8: a menção a uma amostra determinística de 10 páginas foi
  substituída pelo escopo real do `--check`: todas as 1.291 páginas nos
  critérios 1, 3 e 4, todo o HTML/índice no critério 2, todo o `site/dados` no
  critério 6 e um segundo build no critério 5; os sete perfis ficam na
  conferência manual e os casos de limite em `check_casos_limite`.
- `docs/FASE-1.md` §5.2 e §8 e `SCHEMA.md`: explicitam que `n_referencia` não
  aparece quando `n` é `null`.

Nenhuma mudança em `data/public`: o `06` completo foi executado e os quatro
arquivos permaneceram byte a byte iguais (nenhum diff em `data/public`).

## Verificação executada

```sh
.venv/bin/python scripts/06_analysis.py --public data/public
.venv/bin/python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check
.venv/bin/python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-casos
.venv/bin/python -m py_compile scripts/06_analysis.py scripts/12_build_site.py
```

- `06`: as 16 etapas `executado`, nenhuma `pulado`; `q0_execucao.csv` sem
  `pulado`; saída `1.291 escolas, 21.720 linhas de indicador e 7.416 de
  infraestrutura`.
- `--check`: todos os sete critérios `[ok]` — 1.291 páginas de procedência,
  índice sem número, 80 unidades com n < 30 (67 com TDI valor/zero), 0 sem
  matrícula de 2025, estados/frases de 2024, reprodutibilidade, 6 fontes com
  licença e casos de limite.
- `--check-casos`: `[ok]`, incluindo o Ideb histórico com `n` null sem
  `n_referencia` e o AF histórico com `n = 138` com `"2025"`.
- `git diff --check` limpo; `site/` continua ignorado e fora do git.

## Conferência do site servido

O site foi servido em `http://127.0.0.1:8123/prova-dos-nove/`, reproduzindo o
subpath do GitHub Pages, a partir de uma cópia do `site/` gerado.

- Índice: 1.291 escolas, 35 seções de RA, 0 números; busca sem acento/caixa
  (`ceilandia` e `ÁGUAS CLARAS`) encontra; `zzzz` mostra “Nenhuma escola
  encontrada.”; limpar restaura 1.291/35. Sem JS, a lista completa continua e
  aparece o aviso; com `indice.json` bloqueado, o status de fallback aparece e o
  campo é desabilitado.
- Tipos MIME: HTML `text/html`, `indice.json` `application/json`, CSS
  `text/css`, `dados/53000854.json` `application/json`, todos 200.
- `como-ler.html`: nove âncoras (`estados`, `ideb`, `ideb-privada`, `tnr`, `n`,
  `denominador`, `censo`, `infraestrutura`, `limites`), texto de estados,
  limiar 30, L-28/L-63 e link de L-63 para `#censo` funcionando.
- `creditos.html`: sete fontes (cinco INEP e duas SEEDF), licenças e URL do
  catálogo da SEEDF, nenhuma ODbL, MIT/CC BY 4.0/Marcelo Anaissi, build
  `2026-11-06` e limiar 30.
- Perfis a–g e casos de borda `53020529`, `53000331`, `53013662`, `53014618`:
  valores conferidos no HTML (Ideb, matrícula, TDI, TNR, fluxo, infraestrutura
  e creche), sem `NaN`/`undefined`/`None`; `53001419` não publica `0,0%` nem
  `100,0%`; `53014618` mantém 493 em AI/2024.
- Layout: sem overflow horizontal a 360, 768 e 1280 px; na impressão, topo,
  rodapé e trilha ficam ocultos e os blocos não têm sombra.
- Links locais e âncoras: `pages=1294 errors=0` (1.291 escolas + índice +
  `como-ler` + `creditos`).
- JSON: 30.912 números; 4.410 com `n_referencia`, todos em Ideb histórico com
  `n` presente; 0 com `n_referencia` e `n` null; o único `n = 1` em família de
  alunos é a matrícula real de 1 aluno da `53013719`, não o antigo `n or 1`.
- Fixture temporário com `53000854.mat_fund_ai_2025 = NA`: página com `n = -`,
  frase de 2025, sem `fluxo/tdi/tnr` de AI; Ideb AI com `n: null` e sem
  `n_referencia`; Ideb AF histórico com `n: 138` e `"2025"`.
- Teste negativo de licença: uma cópia temporária de `data/public` com uma fonte
  SEEDF marcada como ODbL fez `--check-licencas` sair 1 com
  `[falhou] licencas: registro 'identificacao' publicado sob licença ODbL`.
- Teste negativo do export: `_licencas_seedf` com um inventário temporário
  ODbL levantou `ExportError` antes de qualquer gravação, citando L-62.
- O único 404 no servidor local é `/favicon.ico`, pedido automático do
  navegador; não há asset gerado apontando para ele.

## Pendências

- Ativar GitHub Pages em **Settings → Pages → Source: GitHub Actions** e
  publicar o commit; o deploy anterior falhou com 404 porque o Pages não estava
  habilitado. Isto é ação do mantenedor, não do código.
- Rodar o workflow real depois do push e conferir o `deploy` no ambiente
  `github-pages`.
- O caminho de `06 --parcial` com etapa forçada a pular não foi reexecutado
  nesta sessão; o worklog anterior registra o teste controlado. O código foi
  revisado e a ordem `puladas` → `export_public` está correta.
- O `06 --public` completo com inventário ODbL não foi reexecutado; a função de
  causa, `_licencas_seedf`, foi exercitada diretamente e recusou o conjunto.
- O visual do caso `n = null` foi conferido em fixture temporário, não em página
  do insumo versionado: o insumo atual tem 0 matrículas de 2025 ausentes.
