# 2026-11-10 — refatoração do build do site (pacote `sitegen`, código em inglês)

## O que entrou

- `scripts/12_build_site.py` virou a CLI fina (32 linhas): docstring, `from
  sitegen.cli import main` e o guard de entrada. O comando do CI, do README e da
  FASE-1 não mudou.
- `scripts/sitegen/`: pacote do build, sem dependência nova.
  - `contract.py` (constantes de etapa, frases, anos e limites), `errors.py`
    (`BuildError`), `loader.py` (sha256 e modelo de `data/public/`), `fmt.py`
    (formatação pt-BR e rótulos de etapa).
  - `assets.py` + `static/style.css` + `static/search.js`: CSS e JS agora são
    arquivos de verdade; `CSS` e `JS_INDEX` são lidos uma vez.
  - `layout.py` (`document`), `index_page.py` (índice e busca),
    `info_pages.py` (`como-ler`, `creditos`), `school_page.py` (`SchoolPage`) e
    `build.py` (limpeza, escrita e limite de tamanho).
  - `school_page.SchoolPage.render` foi dividido em nove métodos `_block_*`
    (identificação, oferta, matrícula, Ideb, fluxo, distorção, não-resposta,
    infraestrutura, creche), na mesma ordem.
  - `checks/`: `common.py` (leitores), um módulo por critério e `__init__.py`
    com `CheckContext`, `Check` e a tupla ordenada `CHECKS`; `cli.py` monta as
    flags `--check-*` e a lista do `--check` a partir do registro.
- Identificadores Python renomeados para inglês (classes, funções, constantes,
  parâmetros, locais e atributos). Strings não foram tocadas: colunas do
  parquet, chaves de `procedencia.json` e dos JSON publicados, ids e classes do
  HTML, frases do site, flags da CLI e chaves dos checks continuam em português.
- `README.md`, `docs/FASE-1.md` e a docstring da CLI descrevem o novo layout;
  `check_casos_limite` na FASE-1 virou `check_edge_cases`.

`data/public` e os bytes de `site/` não mudaram: o build no HEAD e o build
depois da refatoração produzem os mesmos 2.587 arquivos, com os mesmos sha256.

## Decisões

- Pacote irmão `scripts/sitegen/` em vez de renomear a CLI: `python
  scripts/12_build_site.py` põe `scripts/` no `sys.path` e o pacote importa sem
  mudança de CI; o nome `sitegen` não colide com o `site/` ignorado.
- Renomear primeiro, mover depois: a renomeação foi verificada por AST no
  arquivo único e cada movimento seguinte foi comparado símbolo a símbolo com o
  arquivo renomeado. Depois disso, as etapas de split são movimentos puros.
- Regra "tokens, não strings": o vocabulário de dados (`co_entidade`, `estado`,
  `valor`, `por_co`, `numeros`…) permanece em português. O resíduo interno fica
  para o plano Q3 (modelo tipado).
- Checks por registro: cada novo critério é um módulo mais uma entrada em
  `CHECKS`, não quatro edições na `main`.
- CSS/JS em `static/` extraídos com `ast.literal_eval`, sem redigitar; o CSS
  publicado mantém a quebra de linha inicial e o `estilo.css` continua idêntico.
- Sem Jinja2, Astro ou framework: o problema era a função de 265 linhas e a
  mistura de responsabilidades, não a f-string.

## Verificação

Portão G a cada commit: `compileall`, build com `--check`, sha256 de cada
arquivo de `site/`, `--help` e `git diff -- data/public` vazio. Saída do último:

```text
[ok] compileall
build rc=0 stderr=''
[ok] stdout
[ok] hashes do site
[ok] --help
[ok] data/public intocado
```

- `stdout` inclui a linha `site: 1,291 páginas de escola, 29.1 MB em OUT` e os
  sete `[ok]` (procedencia, ranking, limiar, estados, reprodutibilidade,
  licencas, casos_limite), iguais ao golden do HEAD.
- `site.sha` do golden e do build final: 2.587 arquivos, mesmos hashes.
- `move_check.py` (comparação de AST) encontrou cada símbolo do arquivo
  renomeado exatamente uma vez no pacote, com o mesmo corpo; só ficaram de fora
  os nomes deliberadamente alterados (`CSS`, `render_index_page`, `main`,
  `SchoolPage.render`) e os nove `_block_*` novos.
- Testes de mutação em árvore limpa, cada um revertido depois:

| mutação | comando | resultado |
|---|---|---|
| `_add` grava `"limites": []` | `--check-procedencia` | `[falhou] procedencia` |
| `p90` no texto de `como-ler` | `--check` | `[falhou] ranking` |
| `rate_span`, ramo `ausente`, texto `"-"` → `"00"` | `--check-estados` | não exercitada |
| texto `"-"` da matrícula ausente → `"00"` | `--check-estados` | `[falhou] estados` |

  A terceira mutação do plano não é exercitada por este insumo: não existe
  linha de taxa com `estado = ausente` e `n ≥ 30` (todos os casos sem taxa são
  `nao_aplicavel`), então o ramo não aparece em página nenhuma. A quarta cobre a
  mesma classe de erro (`data-estado="ausente"` sem hífen) num ramo que o
  insumo exercita.
- `python -m compileall -q scripts` sem saída; `requirements.txt` e
  `.github/workflows/pages.yml` não foram tocados; `site/` continua fora do git.

## Pendências

- Q3 — modelo tipado: trocar os dicionários com chave em português
  (`escola["co"]`, `dados["por_co"]`, `{"valor", "estado"}`) por dataclasses com
  atributos em inglês, traduzindo o vocabulário de dados uma vez no
  `loader.py`. É a metade que falta de "código em inglês" e toca todo acesso,
  por isso fica num plano próprio, depois dos planos 1 e 2.
- Q1/Q2 continuam em aberto: idioma de `docs/plans/` (exceção declarada no
  `AGENTS.md`) e guarda das ferramentas descartáveis de migração.
- `school_page.py` tem 520 linhas; acima das ~500 do critério de pronto por 20
  linhas, mas sem mistura de responsabilidades (só a classe e seus métodos).
