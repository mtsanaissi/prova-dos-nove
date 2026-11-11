# DESENVOLVIMENTO.md

Guia técnico: ambiente, pipeline, organização do código, build, verificação e
publicação. As **regras** do projeto estão em `AGENTS.md`; o **contrato** da
página em `docs/FASE-1.md`; o dicionário de dados em `SCHEMA.md`; os limites,
com id e evidência, em `docs/LIMITES.md`. Este arquivo não repete os três —
diz como mexer no código sem quebrá-los.

Os números citados aqui são medições, não constantes: os do build vêm da
execução de 2026-11-11 sobre `data/public` (sha256 em `procedencia.json`), e os
de fonte vêm do arquivo nomeado ao lado. Quando um deles mudar, quem muda é o
build, não este texto.

## 1. Ambiente

Python 3.12.3, ambiente com `uv`, dependências pinadas em `requirements.txt`:

```sh
uv venv .venv
uv pip install -r requirements.txt
```

| pacote | por quê |
|---|---|
| `pandas` | toda a leitura e o recorte; parquet como formato intermediário |
| `pyarrow` | motor do parquet |
| `numpy` | importado direto por `10_ingest_pdad.py` (variância da PDAD) |
| `openpyxl` | `.xlsx` da INEP |
| `pypdf` | dicionários e notas técnicas em PDF |

`geopandas` e `shapely` **não entram** enquanto não houver análise espacial
validada (L-46): a malha das RAs é usada só como validação por atributo.

Todos os comandos deste documento usam `.venv/bin/python`. Nada de dependência
nova para o site: o build só precisa de `pandas` e `pyarrow`, e o CI instala
apenas o `requirements.txt`.

## 2. Fluxo de dados

Quatro camadas, com regras de git diferentes:

| camada | conteúdo | git |
|---|---|---|
| `data/raw/` | original como veio da fonte, imutável; `MANIFEST.md` com URL, data, bytes e sha256 | fora, **exceto** `MANIFEST.md` |
| `data/interim/` | parquet normalizado, respostas das perguntas (`q*.csv`), artefatos de conferência | fora |
| `data/public/` | recorte mínimo que o build lê, agregado por escola e por etapa | **dentro** (exceção declarada) |
| `site/` | HTML, CSS, `indice.json` e os JSON de procedência | fora — o Pages publica o artefato |

A ordem de execução é a numeração dos scripts, e ela tem dois pontos de
entrada: rede e download manual.

```text
rede:    01 → 02 → 05 → 09
manual:  07 → 08              (arquivo baixado no navegador em data/raw/inep/inbox/)
offline: 11 → 10 → 03 → 04 → 06 → 12
```

| script | entra | sai | rede |
|---|---|---|---|
| `01_inventory_seedf.py` | API CKAN da SEEDF | `data/interim/seedf_datasets.csv` | sim |
| `02_download_seedf.py` | inventário | `data/raw/seedf/`, `MANIFEST.md` | sim (pula o que já existe) |
| `03_profile_seedf.py` | `data/raw/seedf/` | parquet + perfil de colunas | não |
| `04_crosswalk.py` | parquet | taxa de casamento entre chaves | não |
| `05_external_sources.py` | PDAD, INEP, malha | `data/raw/pdad`, `data/raw/inep`, `data/raw/malha` | sim (pula o baixado) |
| `07_ingest_inep.py` | `data/raw/inep/inbox/` | `data/raw/inep/` + `MANIFEST.md`, conferindo sha256 | não |
| `08_profile_inep.py` | `data/raw/inep/` | parquet normalizado | não |
| `09_download_malha.py` | ArcGIS do IDE/DF | malha das 37 RAs | sim |
| `10_ingest_pdad.py` | microdados da PDAD-A | agregados por RA | não |
| `11_ingest_censo.py` | microdados do Censo (recorte DF em streaming) | `censo_escola_df.parquet` | não |
| `06_analysis.py` | parquet de 11, agregados de 10, perfil de 03 | `q*.csv`, `q0_execucao.csv`; com `--public`, `data/public/` | não |
| `12_build_site.py` | `data/public/` | `site/` | não |

`_common.py` concentra o que todos compartilham: `sha256`, `download`,
`get_json`, `append_manifest`, `detect_encoding`, `detect_separator`,
`norm_ra`. Detecção de formato é medida, nunca presumida — CSV da SEEDF muda de
separador e de encoding entre anos.

Todo script é idempotente e abre com docstring dizendo entrada, saída e o que
acontece na reexecução. Script novo segue a numeração por ordem de execução.

## 3. Onde mora o código do site

`scripts/12_build_site.py` é **só a CLI** (docstring e `from sitegen.cli import
main`). O build é o pacote irmão `scripts/sitegen/`, importável porque
`python scripts/12_build_site.py` põe `scripts/` no `sys.path`.

| módulo | responsabilidade |
|---|---|
| `contract.py` | constantes do contrato: etapas, anos do Ideb, frases fixas, limites por família, `DEFAULT_DATA_BUILD`, `DEFAULT_N_THRESHOLD`, `MAX_SITE_BYTES` |
| `loader.py` | confere sha256 e monta o modelo em memória de `data/public/` |
| `fmt.py` | formatação pt-BR (milhar com ponto, decimal com vírgula), rótulo e slug de etapa |
| `assets.py` + `static/` | CSS e JS de busca em arquivos de verdade, lidos uma vez: o CSS sai como `site/estilo.css`, o JS do índice é embutido no HTML |
| `layout.py` | o documento HTML comum (cabeçalho com a navegação, rodapé, carimbo) |
| `region.py` | rótulo de exibição e slug de RA (tabela escrita à mão, L-64) |
| `home_page.py` | a home: quatro cartões, motivação, resumo de método e o coletor de procedência (`HomeNumbers`), espelho do `SchoolPage._add` |
| `home_chart.py` | o gráfico de distorção por rede em SVG inline, com a tabela equivalente em `<details>` |
| `schools_page.py` | `escolas.html`: busca, salto por RA e lista por RA |
| `methodology_page.py` | `metodologia.html`: fontes, tratamento, limites e como conferir |
| `info_pages.py` | `como-ler.html` e `creditos.html` |
| `school_page.py` | a página da escola: `SchoolPage.render` e os nove `_block_*`, na ordem do §2 do contrato |
| `build.py` | limpeza da saída, escrita de tudo e o limite de tamanho |
| `checks/` | um módulo por critério, `CheckContext`/`Check` e a tupla `CHECKS` |
| `cli.py` | argumentos, montagem das flags `--check-*` e execução no primeiro erro |

Regra de idioma: identificadores em inglês (classes, funções, constantes,
parâmetros); **strings não**. Colunas do parquet, chaves de `procedencia.json` e
dos JSON publicados, `id`/`class` do HTML, frases do site, flags da CLI e chaves
dos checks continuam em português — é o vocabulário de dados, e renomear isso
quebraria insumo e site de uma vez.

Novo critério de verificação = um módulo em `checks/` com `check_<nome>(ctx)`
mais uma entrada em `CHECKS`. A CLI monta `--check-<nome>` sozinha; a ordem
documentada é a da tupla. Critério que muda o contrato entra também no §8 de
`docs/FASE-1.md` e no comentário do workflow.

## 4. O que o código não pode quebrar

Quatro estados, três símbolos na tela (§3 do contrato). `ausente` **nunca** é
deduzido de `NaN`; `nao_aplicavel` **nunca** é deduzido de indicador ausente — a
oferta vem do vetor da SEEDF; `zero` é `0`.

- Todo número visível tem `data-numero` e entrada em `dados/<CO_ENTIDADE>.json`
  com `fonte`, `arquivo`, `ano`, `calculo`, `id`, `n` e `limites` não vazios. A
  conferência é o critério 1, em todas as páginas.
- `n` é a matrícula da etapa de 2025. `n` inteiro abaixo do limiar (30, D4)
  suprime a taxa; `n` `null` suprime a taxa e mostra a matrícula `-`.
  `n_referencia` existe exatamente quando o `n` é contagem de alunos de outro
  ano — hoje, Ideb de 2005–2023 → `"2025"`.
- Nenhuma média, mediana, faixa p10–p90 ou contagem de rede na página da escola
  nem em `escolas.html` (D3), e nenhuma ordenação por indicador: a página não
  vira ranking por clique. A home é a única exceção declarada (contrato §2.3),
  tem legenda própria e check próprio (critério 9).
- Nenhum número publicado cita família ODbL da SEEDF; o export recusa antes de
  gravar e o build recusa na lista de licenças (L-62).
- Determinismo: iteração em ordem fixa, JSON com `sort_keys=True`, nenhum
  `datetime.now()`. O único carimbo de tempo é `--data-build`, e é ele que
  aparece no rodapé.

Ressalva nova em número publicado entra em `docs/LIMITES.md` com id `L-xx` e
passa a ser citada na página. Id não se reutiliza.

## 5. Build e verificação

```sh
# construir
.venv/bin/python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06

# rodar todas as verificações (sai != 0 no primeiro erro)
.venv/bin/python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check
```

Saída de referência (2026-11-11): 1.291 páginas de escola, 2.590 arquivos,
29,9 MB, e dez `[ok]`. A tabela está na ordem de execução (a de `CHECKS`); a
coluna `#` é o número do critério no §8 do contrato.

| # | chave | flag | o que cobre |
|---|---|---|---|
| 1 | `procedencia` | `--check-procedencia` | todo número visível tem registro completo |
| 2 | `ranking` | — | `escolas.html` e páginas de escola sem p10/p90/mediana e sem número |
| 7 | `sumario` | `--check-sumario` | 35 RAs no salto de `escolas.html`, na mesma ordem das seções |
| 3 | `limiar` | `--check-limiar` | unidade com `n < limiar` não publica taxa |
| 4 | `estados` | `--check-estados` | `-`, `—`, `0` e as frases fixas |
| 8 | `sumario_escola` | `--check-sumario-escola` | sumário = seções, ordem e rótulo; creche só com oferta |
| 9 | `home` | `--check-home` | procedência, somas, quatro cartões, legenda da home e nenhum id morto no agregado |
| 5 | `reprodutibilidade` | — | segundo build com os mesmos bytes |
| 6 | `licencas` | `--check-licencas` | fonte de cada família nos créditos, sem ODbL |
| — | `casos_limite` | `--check-casos` | 2024 sem linha/célula vazia, 2025 e creche ausentes, 493 em 2024, limiar 0 |

Cada check lê o site já construído pela mesma execução (`CheckContext` leva
insumo, saída, modelo, carimbo e limiar). Nenhum tem amostra: os critérios 1, 3,
4 e 8 varrem as 1.291 páginas, o 2 varre `escolas.html` e as páginas de escola, o
9 varre a home e o `dados/home.json`, o 6 varre todo o `site/dados`.

**Um check que não falha quando o defeito é injetado não é um check.** Ao mexer
num deles, injete a falha de propósito (ex.: `"limites": []` numa entrada,
`p90` no texto de `como-ler`, `-` virando `00`) e confirme o `[falhou]`; depois
reverta. Os worklogs registram as mutações já feitas e qual classe de erro cada
uma cobre.

O que o CI **não** cobre: a metade do critério 5 que roda o `06`. `data/interim/`
está fora do git e o CI não tem as etapas, então "`06` sai 0 sem etapa pulada" é
verificação local.

## 6. Servir as páginas localmente

O site é HTML estático com caminhos relativos, publicado em
`https://mtsanaissi.github.io/prova-dos-nove/`. Para que o teste valha, sirva no
**mesmo subpath**: `/` esconde um link absoluto que quebraria em produção.

```sh
cd /home/mitissa/code/prova-dos-nove
work=/tmp/opencode/pdn-serve-live
mkdir -p "$work"
ln -sfn "$PWD/site" "$work/prova-dos-nove"
.venv/bin/python -m http.server 8000 --bind 127.0.0.1 --directory "$work"
```

Roda em primeiro plano: os acessos aparecem no terminal e `CTRL+C` encerra. O
`/prova-dos-nove/` é um symlink para `site/`, então reconstruir o site e recarregar
já mostra o resultado — nada de cópia para ficar velha. Abra
`http://127.0.0.1:8000/prova-dos-nove/`.

Conferências rápidas:

```sh
# nenhum caminho raiz-absoluto (quebraria no subpath do Pages)
grep -R --include='*.html' -e 'href="/' -e 'src="/' site || echo ok

# status e tipo de conteúdo
for u in /prova-dos-nove/ /prova-dos-nove/escolas.html \
         /prova-dos-nove/metodologia.html /prova-dos-nove/como-ler.html \
         /prova-dos-nove/creditos.html /prova-dos-nove/indice.json \
         /prova-dos-nove/estilo.css /prova-dos-nove/dados/home.json \
         /prova-dos-nove/dados/53000854.json /prova-dos-nove/53000854.html; do
  printf '%s %s\n' "$(curl -s -o /dev/null -w '%{http_code} %{content_type}' "http://127.0.0.1:8000$u")" "$u"
done
```

O que só o navegador mostra: a home a 360 px e em tela larga, o gráfico legível
sem cor, o `<details>` da tabela do gráfico, a busca de `escolas.html` sem acento
e sem caixa (`ceilandia`, `ÁGUAS CLARAS`), o `<select>` de salto por RA, a lista
completa sem JavaScript, as nove âncoras de `como-ler.html`, o `<details>` do
sumário de cada escola e os sete perfis-piloto — mais as duas páginas sem
indicador e os casos de borda (2024 sem linha, célula vazia, `n < 30`, 493 de
2024). Os códigos e o que cada um prova estão no §4 de `docs/FASE-1.md`.

Um 404 em `/favicon.ico` é esperado: o site não gera ícone. Não há `404.html`
nem rota de cliente — código de escola errado cai no 404 padrão do GitHub.

## 7. Publicação

`.github/workflows/pages.yml`, em cada push para `main` (e via
`workflow_dispatch`):

1. `pip install -r requirements.txt` e
   `python scripts/12_build_site.py --public data/public --out site --data-build 2026-11-06 --check`;
2. upload de `site/` como artefato do Pages;
3. `deploy-pages` no environment `github-pages`.

O `--check` é o portão: critério que regride barra o upload. `site/` nunca entra
no git; o Pages publica o artefato.

Antes do primeiro deploy, o mantenedor precisa ativar **Settings → Pages →
Source: GitHub Actions**. Sem isso o job `build` passa e o `deploy` falha com
`404 … Ensure GitHub Pages has been enabled` — que é o estado atual do
repositório.

Depois do deploy verde: abrir a URL raiz e um link direto
(`/prova-dos-nove/53000854.html`) para confirmar que o artefato caiu na raiz do
subpath.

Dois pontos conhecidos do workflow: `--data-build` está fixo em `2026-11-06`, de
propósito (é o carimbo do dado, não o da execução) — se `data/public` mudar, o
valor precisa ser atualizado à mão, no workflow e no README; e as actions
(`checkout@v4`, `setup-python@v5`, `upload-pages-artifact@v3`) ainda são de
Node 20 e emitem aviso de depreciação, sem falhar.

## 8. Armadilhas já pagas

- **`download.inep.gov.br` serve cadeia TLS incompleta.** `curl`/`urllib` sem a
  CA da RNP saem 60/21. O caminho é declarado: download no navegador (ou
  `curl -sk`) → `data/raw/inep/inbox/` → `07_ingest_inep.py`, que confere o
  sha256 contra o `MANIFEST` antes de registrar. Nenhum script finge que baixou
  o que não baixou.
- **Arquivo não verificado não entra no `MANIFEST`.** Com `curl -sk`, a
  conferência de sha256 é obrigatória.
- **Microdado nacional é grande** (Censo 2025: 537 MB). O recorte é feito em
  streaming, filtrando `CO_UF=53` e `CO_MUNICIPIO=5300108`, e o resto é
  descartado — nunca materializado inteiro.
- **Parquet não é byte-determinístico.** Reprodutibilidade se mede por conteúdo:
  `hash_pandas_object` sobre as linhas ordenadas pela chave (parquet) e `sha256`
  (CSV). Comparar bytes de parquet dá falso negativo.
- **Separador e encoding do CSV da SEEDF variam por ano.** Detecte com
  `_common.detect_separator`/`detect_encoding`; não presuma.
- **A série da SEEDF não é independente do Censo** e subestima EJA e educação
  profissional (L-01, L-07). Concordância entre as duas não é confirmação.
- **Rótulo de RA é de tela.** `data/public`, `indice.json` e `data-ra` guardam o
  valor bruto do cadastro; a tabela de rótulo/slug vive em `sitegen/region.py`
  (L-64). Escola cuja RA não está na tabela tem de falhar, não cair num slug
  adivinhado.
- **`data/raw` é imutável.** Correção de fonte entra por script novo ou por
  entrada de correção no `MANIFEST`, nunca sobrescrevendo o original.

## 9. Antes de commitar

```sh
.venv/bin/python -m compileall -q scripts
.venv/bin/python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check
git status --short            # site/ não aparece; data/interim/ não aparece
git diff -- data/public       # vazio se o dado não mudou
```

- Mudou campo do insumo ou do parquet publicado: `SCHEMA.md` e o §5.1 do
  contrato.
- Id novo em `agregados.parquet`: se o `calculo` da família já descreve a conta,
  é linha; se não descreve, é família nova em `procedencia.json` (decisão de
  fonte, cálculo, limites e licença).
- Mudou a página, o bloco ou uma frase de ausência: `docs/FASE-1.md` (o texto é
  contrato, não redação).
- Descobriu limite novo: `docs/LIMITES.md` com id, evidência e status.
- Documentou a sessão: `docs/worklogs/AAAA-MM-DD-NN-tema.md`, em português, com
  o que entrou, as decisões e a verificação executada; se houve plano,
  `docs/plans/` guarda o par.
- `data/public` regenerado entra no mesmo commit, para a mudança do insumo
  aparecer no diff.

## 10. Pendências técnicas conhecidas

- **Q3 — modelo tipado.** `loader.py` ainda entrega dicionários com chave em
  português (`escola["co"]`, `dados["por_co"]`, `{"valor", "estado"}`). Trocar
  por dataclasses com atributos em inglês, traduzindo o vocabulário uma vez no
  loader, é a metade que falta da regra "código em inglês" e toca todo acesso.
- **Q1/Q2.** Idioma de `docs/plans/` — o `AGENTS.md` declara que não há regra
  (exceção registrada em 2026-11-10), resta decidir se ela fica permanente — e a
  guarda das ferramentas descartáveis de migração.
- `school_page.py` tem 520 linhas, 20 acima do alvo de ~500 do critério de
  pronto, sem mistura de responsabilidades.
- O caso `n = null` está coberto por fixture e por `--check-casos`, mas o insumo
  versionado não tem nenhuma matrícula de 2025 ausente: nenhuma página real o
  exercita hoje.
- L-61: o zip do Censo 2025 nunca foi conferido contra o servidor (só o de
  2024). L-63: a fonte não diz por que uma escola de 2025 não tem linha em 2024.
