# Plano — correções da FASE-1 (página por escola)

**Data:** 2026-11-09
**Revisão:** 2026-11-09 — fecha as diferenças da comparação com a versão anterior: L-63 para a ausência de linha em 2024, `--parcial` (não `--force`) como aceite do export incompleto, `n_referencia` só quando o `n` é contagem de alunos, escopo real do gate no CI e recusa de família ODbL já no export.
**Contrato:** [docs/FASE-1.md](../FASE-1.md)
**Build:** [scripts/12_build_site.py](../../scripts/12_build_site.py)
**Export do insumo:** [scripts/06_analysis.py](../../scripts/06_analysis.py)
**Insumo versionado:** [data/public/](../../data/public/)

## 1. Motivação e origem

A FASE-1 define uma página estática por escola, em português comum, gerada por Python a partir de `data/public/`, com a série da própria escola e a procedência de cada número. O contrato está em [docs/FASE-1.md](../FASE-1.md), o build em [scripts/12_build_site.py](../../scripts/12_build_site.py) e o recorte público em [scripts/06_analysis.py](../../scripts/06_analysis.py) (`--public`). O site tem 1.291 páginas, índice alfabético por Região Administrativa, `como-ler.html`, `creditos.html` e `dados/<CO_ENTIDADE>.json` com a procedência de cada número.

A revisão da implementação em 2026-11-09 encontrou casos em que a página publica uma causa que a fonte não distingue, uma taxa sem denominador ou uma licença inferida; além disso, o gate dos seis critérios do §8 não roda na publicação. Este plano fecha esses casos antes de a fase ser declarada concluída. Ele não altera o desenho do produto, o universo de escolas, o limiar D4 = 30, a regra de não-ranking, a proibição de média/mediana de rede, nem a decisão de não publicar a meta do Ideb (L-56).

## 2. Estado atual e o que a revisão encontrou

O build e o export atuais passam no `--check` sobre o `data/public` versionado: 1.291 páginas, 28,8 MB, seis critérios ok; o export reproduz os quatro arquivos byte a byte. Os problemas abaixo são de casos de borda e de processo.

### 2.1 Dados que sustentam o plano

| Fato | Valor | Onde |
|---|---:|---|
| Censo 2024 | 1.360 linhas | `data/interim/inep/censo_escola_df.parquet` |
| Censo 2025 | 1.291 linhas | idem |
| Cadastro 2025 | 1.291 escolas | `data/interim/seedf/escolas__relatorio_escolas_2025.parquet` |
| Escolas de 2025 sem linha no Censo 2024 | 53 | `escolas.parquet` × Censo 2024 |
| Escolas de 2025 com linha 2024 e células vazias | 3: `53013662`, `53015665`, `53019415` | idem |
| `oferta_* = 0` com matrícula 2024 > 0 | 36 school-years: 12 AI, 9 AF, 7 EM, 8 CRE | `escolas.parquet` |
| Exemplo | `53014618` (EC 803 DO RECANTO DAS EMAS), `oferta_fund_ai=0`, `mat_fund_ai_2024=493` | idem |
| `oferta_* = 0` com matrícula 2025 > 0 | 0 | idem |
| Unidades com TDI `valor`/`zero` e n < 30 | 67 em 61 escolas | `q16_faixas_n.csv`, §6 do contrato |
| Unidades ofertadas com n < 30 (build) | 80 (67 com TDI + 13 sem linha de TDI) | `--check` |
| Universo de infraestrutura | 927 escolas de EF/EM | `infraestrutura.parquet` |
| Escolas com creche (`INF_CRE=1`) | 475 | `escolas.parquet` |
| RAs no índice | 35 | `indice.json` |
| Tamanho dos parquets públicos | 60K / 40K / 13K / 3.7K | `ls -lh data/public/` |

### 2.2 Os seis achados

1. **2024: escola ausente vs célula vazia.** O bloco 3 (e o bloco 9, creche) usa uma única frase, "matrícula não declarada no Censo de 2024", para dois casos: 53 escolas de 2025 sem linha no Censo 2024 e 3 escolas com linha e células vazias. Para as 53, "não declarada" nomeia uma causa que a fonte não estabelece; a escola pode simplesmente não existir em 2024. O `check_estados` usa `53020529` (uma das 53) como referência da frase, então o caso de célula vazia (as 3) não é testado.
2. **2025: matrícula ausente publica taxa com `n=1`.** Em fluxo/TDI/TNR, a supressão só roda quando `n is not None`; com `n` ausente, o código passa `n or 1` a `rate_span` e publica a taxa; o JSON grava `"n": 1`. No Ideb, `n_exibir` vira 1. O `--check` pula `n is None`, então não vê. Reproduzido em uma cópia de `data/public` com `53000854.mat_fund_ai_2025 = NA`: a página publica `fluxo-ai-aprovacao-2025` com `n=1` e "n = - alunos".
3. **Creche: 2025 rotulado como 2024.** O bloco 9 usa um único `faltam` para os dois anos e sempre anexa a frase de 2024. Com `53000781.mat_inf_cre_2025 = NA`, a página mostra `2025 -` e "matrícula não declarada no Censo de 2024". O bloco 3 já usa uma frase de 2025 ("matrícula não declarada no Censo de 2025"), que não está no §3.1.
4. **Gate dos seis critérios fora da publicação.** O workflow [.github/workflows/pages.yml](../../.github/workflows/pages.yml) roda o build e envia o `site/`, mas não roda `--check`. Uma regressão em D4, estados, ranking ou licenças publica.
5. **Licença inferida.** `pagina_creditos` mapeia qualquer fonte `SEEDF...` para CC BY e qualquer `INEP...` para "público, sem licença declarada" por prefixo; a página diz "Licença como declarada no catálogo de cada fonte; nenhuma foi inferida". O inventário `data/interim/seedf_datasets.csv` tem 12 conjuntos CC BY e 5 ODbL; os dois conjuntos SEEDF usados (cadastro e infraestrutura) são CC BY, então a saída atual está correta, mas o `check_licencas` só procura "odbl"/"odc" no rótulo da fonte e não verifica o catálogo.
6. **Export público antes do check de etapas.** `06_analysis.py --public` chama `export_public` antes de checar `q0_execucao.csv`/`puladas`; com `--parcial`, uma execução incompleta grava `data/public` e retorna 0. O guard de sha256 do §5.1 só protege um destino já existente.

Achados menores: o `n` do Ideb histórico é a matrícula de 2025 em todas as linhas (sancionado pelo §5.2, mas ambíguo no JSON); o `calculo` da identificação cita `NO_ENTIDADE`, mas o campo de 2025 é `Nome da escola`; o §5.1 do contrato traz tamanhos antigos (240/800/25/15 KB) e o §6 precisa explicar que 67 e 80 são recortes diferentes.

## 3. Decisões tomadas

As decisões abaixo são do mantenedor, em 2026-11-09. Elas valem para a implementação e para a atualização do contrato.

### D1 — 2024: flag de presença no Censo + frase própria

Adicionar `censo_2024_presente` (booleano) a `escolas.parquet`, calculado pela presença do `CO_ENTIDADE` no Censo 2024. No bloco 3/9: flag `False` → `ausente` com "a escola não consta do Censo de 2024"; flag `True` e valor vazio → "matrícula não declarada no Censo de 2024"; `0` → `zero`; `> 0` → `valor`.

**Por quê:** as 53 escolas sem linha e as 3 com célula vazia são casos distintos; a frase atual nomeia uma causa que a fonte não estabelece para as 53. A flag é um fato do Censo 2024, não uma inferência da oferta.

A frase nova precisa de id próprio. A L-28 diz, literalmente, "as 76 escolas do Censo 2024 com a célula de matrícula vazia" (`docs/LIMITES.md:46`), universo do arquivo de 2024 que contém apenas 3 das 1.291 escolas de 2025 — citá-la para "a escola não consta" seria atribuição falsa, e o §3.1 exige que cada frase termine no id que a sustenta. Entra **L-63**: 1.360 linhas em 2024 contra 1.291 em 2025, 53 escolas de 2025 sem linha e 3 com linha e quatro células vazias. A frase de célula vazia continua citando L-28.

**Alternativas rejeitadas:** manter uma frase para os dois casos e só trocar o alvo do `check_estados` (mantém 53 páginas com causa não demonstrada e deixa o caso de célula vazia sem teste); citar L-28 para a ausência de linha (a L-28 é sobre célula vazia); usar `oferta_*` para marcar `nao_aplicavel` (os 36 school-years com `oferta=0` e matrícula 2024 positiva seriam apagados); ler `data/interim` no build (o §5.3 do contrato proíbe).

### D2 — 2025: suprimir taxa e usar frase de 2025

Quando `mat_*_2025` for ausente: mostrar a matrícula `-` com "matrícula não declarada no Censo de 2025", **não** publicar fluxo/TDI/TNR, e manter o Ideb (se existir) com `n: null`, nunca 1. Corrigir `n or 1` para passar `n`; com `--limiar-n 0`, `n=0` é gravado como 0. A linha do `n` passa a ser `n = -`, sem "alunos": `palavra_aluno(None)` devolve "alunos" e a página diria "n = - alunos em 2025".

**Por quê:** D4 é conservador; um denominador desconhecido não pode ser tratado como ≥ 30. O `n=1` é falso e o `--check` não vê o caso.

**Alternativas rejeitadas:** publicar a taxa com `n` desconhecido (contraria D4); suprimir sem linha de motivo (o leitor precisa da razão; o §3.1 é o lugar); reutilizar a frase de 2024 (ano errado).

### D3 — Gate: `--check` no workflow do Pages

Substituir o passo de build do [.github/workflows/pages.yml](../../.github/workflows/pages.yml) por `python scripts/12_build_site.py --public data/public --out site --data-build 2026-11-06 --check`; o `--check` já constrói `site/`, e o upload usa essa saída.

**Por quê:** o §8 define os seis critérios como saída da fase; sem o gate, uma regressão publica.

**Escopo real do gate:** o CI cobre os critérios 1–4, 6 e a metade de build do critério 5 (idempotência). A outra metade — `06` sem etapa pulada — não roda no CI, porque `data/interim/` está fora do git (`.gitignore:4`); ela continua etapa local. O §8 do contrato passa a dizer isso, em vez de sugerir que os seis critérios rodam na publicação.

**Alternativas rejeitadas:** job de CI separado (pode ser follow-up se o workflow crescer); manter manual (não é gate); publicar `data/interim` para o CI rodar o `06` (quebra a regra de que `data/` não entra no git).

### D4 — Licença por família em `procedencia.json`

Ler a licença do inventário da SEEDF (`data/interim/seedf_datasets.csv`) e das notas da fonte INEP; gravar `licenca` e `licenca_url` por família em `procedencia.json`; `pagina_creditos` e `check_licencas` consomem esses campos. Para a SEEDF, o valor vem do catálogo (`licenca_titulo` e `licenca_url` do conjunto); para a INEP, "público, sem licença declarada no portal", que é o que o `README.md` §Licença já registra para a fonte — uma ausência declarada, não uma licença inventada. `check_licencas` falha se uma fonte publicada não tiver licença ou se a licença for ODbL. O export também falha, antes de gravar, quando uma família mapeada resolve para um conjunto ODbL — o gate da L-62 fica no ponto da causa, não só depois do insumo commitado.

**Por quê:** a página afirma que nenhuma licença foi inferida; o código infere por prefixo. Os dois conjuntos SEEDF usados são CC BY hoje, mas o inventário tem 5 conjuntos ODbL; um rótulo limpo de uma fonte ODbL futura passaria pelo check atual.

**Alternativas rejeitadas:** mapa fixo em `12_build_site.py` (duplica a fonte da verdade e deriva); manter a heurística e documentar (não é baseada em evidência; risco de licença errada); verificar ODbL só no `check_licencas` (o insumo já commitado teria de ser refeito).

### D5 — `06 --public` só exporta com execução completa, ou com `--parcial`

Mover a checagem de `puladas` para antes de `export_public`. Sem `--parcial`, etapa pulada faz o `06` sair 1 **sem gravar**. Com `--parcial` — que já significa "aceito o resultado incompleto" — o export roda, imprime as etapas puladas e grava `execucao.etapas_puladas` em `procedencia.json`; o build avisa quando a lista não está vazia. `--force` continua significando só "sobrescrever destino com sha diferente", que este plano usa para regenerar `data/public`.

**Por quê:** o export atual pode gravar um insumo parcial e o build aceita o hash; o diff é o único guard. Amarrar o aceite ao `--force` reintroduziria o problema: ele é usado na regeneração de rotina (inclusive na Etapa 1 deste plano) e o aceite de etapa pulada viraria silencioso.

**Alternativas rejeitadas:** usar `--force` para aceitar etapa pulada (dois consentimentos no mesmo flag, e o de rotina é o perigoso); mover o export para depois do check e nunca exportar com `--parcial` (impede um export deliberado de depuração); manter como está (risco de insumo parcial).

### D6 — `n_referencia` no JSON, só quando o `n` é contagem de alunos

Adicionar `n_referencia` ao número **quando o `n` for contagem de alunos e o ano da matrícula usada como `n` diferir do ano do número**. Hoje isso ocorre só no Ideb: as linhas de 2005–2023 levam `"n_referencia": "2025"`, a de 2025 não leva. Matrícula, creche, oferta e infraestrutura têm `n = 1` (a escola, §2), não uma contagem de alunos, e não recebem o campo. Manter `n` e permitir `n: null`.

**Por quê:** o `n` do Ideb histórico é a matrícula de 2025 em todas as linhas; a página diz "em 2025", mas o JSON de `ideb-ai-2005` traz `"n": 247` e um consumidor pode ler como denominador de 2005. Carimbar `n_referencia` no `n = 1` de escola afirmaria um ano de matrícula para um número que não é matrícula.

**Alternativas rejeitadas:** adicionar a todos os números (afirma um ano de matrícula para o `n = 1` de escola); deixar como está (ambíguo para consumidor); trocar `n` pela coorte do ano (o contrato adota a proxy de 2025; a coorte histórica não está no insumo público).

### D7 — O bloco 3 não usa `oferta_*`

A matrícula do bloco 3 vem do Censo, como está no campo; a flag `censo_2024_presente` só escolhe a frase, nunca converte valor positivo em `nao_aplicavel`. A oferta de 2025 (bloco 2) não descreve 2024.

**Por quê:** 36 school-years com `oferta=0` e matrícula 2024 positiva; o exemplo `53014618` tem 493 alunos em AI em 2024 e `oferta_fund_ai=0` em 2025. Usar a oferta apagaria dado real.

**Alternativas rejeitadas:** derivar `nao_aplicavel` da oferta (apaga os 36); usar `q16` no build (o build não lê `data/interim`).

### D8 — Sem dependência nova; teste no `--check`

Estender o `--check` com um caso de limite que copia `data/public` para um diretório temporário, altera os parquets, recalcula o sha256, chama `carregar_dados` e renderiza **só as escolas afetadas** (três ou quatro `PaginaEscola.render()`), não o site inteiro. Usar `tempfile` e o padrão de `check_reprodutibilidade`, sem pytest/jinja2. O caso `--limiar-n 0` (n=0 gravado como 0) também roda aqui, com uma renderização a limiar 0, sem um segundo build completo.

**Por quê:** o §5.3 do contrato fixa `pandas`/`pyarrow` e o build por f-string; o `--check` é a suíte. Passar pelo parquet e pelo `carregar_dados` cobre a coluna nova e o guard de sha256; reconstruir 1.291 páginas só repetiria `check_reprodutibilidade`.

**Alternativas rejeitadas:** pytest (dependência nova); fixture permanente em `data/public` (polui o insumo); clonar o modelo em memória e pular o loader (não cobre a leitura da coluna nem o sha).

## 4. Arquivos, interfaces e código existente

### 4.1 Contrato e documentação

| Arquivo | Papel | Mudança |
|---|---|---|
| [docs/FASE-1.md](../FASE-1.md) | contrato da fase | §2 blocos 3/9; §3.1 três frases (as duas de matrícula e a de infraestrutura que já existe no código) + L-63; §5.1 coluna, licenças (`licenca`, `licenca_url`) e tamanhos; §5.2 `n_referencia`/`n: null`; §6 67/80; §7 `--check` e escopo do CI; §8 critérios 1/4/5/6 |
| [SCHEMA.md](../../SCHEMA.md) | dicionário de dados | `censo_2024_presente`, `licenca`, `licenca_url`, `n_referencia`; vocabulário de estados/frases |
| [data/public/README.md](../../data/public/README.md) | descrição do insumo | coluna nova; licença por família; tamanhos 60/40/13/3.7 KB |
| [docs/LIMITES.md](../LIMITES.md) | limites | **L-63** nova (ausência de linha no Censo 2024); citar L-28 (célula vazia), L-43 e L-62 |
| [README.md](../../README.md) | estado do projeto | atualizar a descrição do insumo se necessário |
| [REPORT.md](../../REPORT.md) | números publicados | sem número novo; não muda |

### 4.2 Export (`06_analysis.py`)

Funções e estruturas existentes: `S` (`data/interim/seedf`), `INTERIM`, `norm_ra`, `sha256`; `ETAPAS_PUBLICAS`, `INFRA_ITENS`, `ANOS_IDEB`, `REDE_SITE`, `REGISTROS_PUBLICOS`, `ExportError`, `_escolas_publicas`, `_indicadores_publicos`, `_infraestrutura_publica`, `_grava_parquets`, `export_public`, `main` com `--public`, `--force`, `--parcial`; `q0_execucao.csv`.

Mudanças:

- `_escolas_publicas`: ler o Censo 2024 como já lê o 2025; `e["censo_2024_presente"] = e["co_entidade"].isin(censo_2024.index)`; manter as quatro `mat_*_2024` NA para os dois casos; incluir a coluna em `colunas`; falhar se uma escola com `False` tiver matrícula 2024 não nula.
- `REGISTROS_PUBLICOS`: adicionar `licenca` e `licenca_url` às 9 famílias. Para as famílias SEEDF (identificação, oferta, infraestrutura), resolver pelo inventário `data/interim/seedf_datasets.csv` (`licenca_titulo`, `licenca_url`) e falhar com mensagem que cite L-62 se o conjunto resolvido for ODbL; para INEP, "público, sem licença declarada no portal" e `licenca_url` nulo.
- `export_public`: manter a gravação atômica e o guard de sha256; `procedencia.json` inclui `licenca`/`licenca_url` por registro e `execucao.etapas_puladas` (lista de nomes de etapa, sem tempos).
- `main`: mover o bloco `if args.public` para depois de `puladas`; sem `--parcial`, etapa pulada imprime a mensagem e retorna 1 sem chamar `export_public`; com `--parcial`, imprime as etapas puladas e exporta, gravando a lista em `procedencia.json`. `--force` continua só com o papel de sobrescrever destino divergente.

### 4.3 Build (`12_build_site.py`)

Funções e estruturas existentes: `carregar_dados`, `PaginaEscola` (`_add`, `mat_span`, `rate_span`, `ideb_cell`, `ausencia`, `pequena`, `render`), `pagina_index`, `pagina_como_ler`, `pagina_creditos`, `construir_site`, `check_procedencia`, `check_sem_ranking`, `check_limiar`, `check_estados`, `check_reprodutibilidade`, `check_licencas`, `main`; constantes `FRASE_*`, `ETAPAS`, `MAT_COLS`, `OFERTAS`, `INFRA_ITENS`, `ANOS_IDEB`, `REDE_SITE`, `ESTADOS`.

Mudanças:

- `carregar_dados`: validar a coluna `censo_2024_presente`; guardar no modelo da escola; falhar se `False` vier com matrícula 2024 não nula; avisar (sem falhar) quando `execucao.etapas_puladas` não estiver vazia.
- `PaginaEscola.mat_span`: receber a família (`matricula`/`creche`), o ano e a flag; escolher a frase/estado:
  - 2024 e `censo_2024_presente=False` → `ausente`, texto `-`, motivo "a escola não consta do Censo de 2024";
  - 2024 e `True` com valor ausente → `ausente`, texto `-`, motivo "matrícula não declarada no Censo de 2024";
  - 2025 e valor ausente → `ausente`, texto `-`, motivo "matrícula não declarada no Censo de 2025";
  - 0 → `zero`, texto `0`; > 0 → `valor`, texto formatado.
  O `mat_cache` continua; o motivo é renderizado uma vez por bloco, com `ausencia`.
- Bloco 3 e bloco 9: usar o mesmo helper; remover o `faltam` da creche e as frases duplicadas; o bloco 9 mantém a família `creche` para citar L-27.
- Fluxo/TDI/TNR: se `n is None`, montar o artigo como `suprimido`/`ausente` com a matrícula `-` e a frase de 2025, sem `rate_span` e sem `data-numero` de taxa; `rate_span(..., n, ...)` sem `n or 1`.
- Ideb: `ideb_cell(etapa, ano, n)` recebe `n` (pode ser `None`); `_add` grava `"n": null`; a linha do `n` usa `mat_span` e vira `n = -` (sem "alunos"), sem inventar 1.
- `_add`: aceitar `n: int | None`; adicionar `n_referencia` só quando o `n` for contagem de alunos e o ano da matrícula usada como `n` diferir do `ano` do número (hoje, Ideb 2005–2023 → `"2025"`; Ideb 2025, matrícula, creche, oferta e infraestrutura não levam o campo).
- `pagina_creditos`: remover `licenca(fonte)` por prefixo; agrupar as famílias por `fonte` e usar o `licenca` do grupo (o export falha na Etapa 1 se duas famílias da mesma fonte divergirem); a tabela mostra a licença exata e, quando houver, `licenca_url`.
- `check_procedencia`: exigir `n_referencia` exatamente quando o `n` é contagem de alunos e o ano da matrícula difere do `ano`; aceitar `n` inteiro ou `null`; se `null`, exigir que o `n` seja contagem de alunos, que o estado seja `ausente`/`nao_aplicavel` e que a página mostre a matrícula ausente; manter `fonte`, `arquivo`, `ano`, `calculo`, `limites`.
- `check_estados`: usar `53013662` para a frase de célula vazia de 2024 e `53020529` para a frase de escola ausente; **varrer as 1.291 páginas**: flag `False` exige a frase sem linha e proíbe a de célula vazia, e célula vazia com flag `True` exige a frase de célula vazia; acrescentar as frases de 2025 e da creche via `check_casos_limite`.
- `check_limiar`: tratar `n is None` como unidade que exige supressão; o caso `--limiar-n 0` (n=0 gravado como 0) roda em `check_casos_limite`, sem um segundo build completo.
- `check_licencas`: ler `licenca`/`licenca_url` de `procedencia.json`; falhar se faltar licença; falhar se uma fonte publicada for ODbL; conferir a tabela de `creditos.html`.
- `check_casos_limite` (novo): copiar `data/public` para um temporário, alterar os parquets, recalcular o sha256, chamar `carregar_dados` e renderizar **só as escolas afetadas**; afirmar:
  - 2024 sem linha → "a escola não consta do Censo de 2024";
  - 2024 com célula vazia → "matrícula não declarada no Censo de 2024";
  - 2025 ausente → sem taxa de fluxo/TDI/TNR, matrícula `-` com a frase de 2025, Ideb com `n: null` e, nas linhas de ano ≠ 2025, `n_referencia: "2025"`;
  - creche 2025 ausente → "Censo de 2025";
  - `53014618` → 493 em AI 2024 continua visível, sem virar `nao_aplicavel`;
  - renderização a `limiar 0` → `n=0` gravado como 0, não 1.
- `main`: adicionar `casos_limite` à lista do `--check` e um `--check-casos`; atualizar a docstring.
- `check_reprodutibilidade`: reutilizar o padrão de temporário; não muda.

### 4.4 Workflow

[.github/workflows/pages.yml](../../.github/workflows/pages.yml): substituir o passo `python scripts/12_build_site.py --public data/public --out site` por `... --data-build 2026-11-06 --check`; o upload continua depois. O `--check` constrói `site/` e roda os critérios 1–4 e 6, a idempotência do 5 e o `casos_limite`; a metade do critério 5 que roda o `06` é local, porque `data/interim/` não está no repositório. O passo leva comentário dizendo isso.

### 4.5 Interfaces novas

```text
escolas.parquet
  + censo_2024_presente: bool   # True se CO_ENTIDADE existe no Censo 2024

procedencia.json
  registros[].licenca: str       # "CC BY (Creative Commons Atribuição)" | "público, sem licença declarada no portal"
  registros[].licenca_url: str | null  # catálogo da SEEDF; null quando a fonte não declara licença
  execucao.etapas_puladas: list[str]   # vazio numa execução completa; preenchido só com --parcial

dados/<CO_ENTIDADE>.json
  numeros[].n: int | null        # null quando a matrícula que serve de denominador não existe
  numeros[].n_referencia: str    # opcional; só quando n é contagem de alunos de outro ano; Ideb 2005–2023 = "2025"
```

Frases (cada uma cita o id que a sustenta):

```text
FRASE_CENSO_2024_SEM_LINHA = "a escola não consta do Censo de 2024"      # L-63
FRASE_MATRICULA_2024       = "matrícula não declarada no Censo de 2024"  # L-28
FRASE_MATRICULA_2025       = "matrícula não declarada no Censo de 2025"  # L-28
```

## 5. Plano de execução

### Etapa 0 — Contrato e esquema

- [ ] Atualizar [docs/FASE-1.md](../FASE-1.md) §2 (blocos 3/9), §3.1 (duas frases novas, a frase de infraestrutura que já existe no código e L-63 na frase de ausência de linha), §5.1 (`censo_2024_presente`, `licenca`, `licenca_url`, tamanhos 60/40/13/3.7 KB), §5.2 (`n_referencia` condicional, `n: null`), §6 (67/80), §7 (`--check` e o escopo real do CI), §8 (critérios 1/4/5/6).
- [ ] Atualizar [SCHEMA.md](../../SCHEMA.md) com a coluna, as licenças (`licenca`, `licenca_url`), o `n_referencia`, o vocabulário e os tamanhos.
- [ ] Atualizar [data/public/README.md](../../data/public/README.md).
- [ ] Em [docs/LIMITES.md](../LIMITES.md), criar **L-63** (ausência de linha no Censo 2024, com evidência e status) e citar L-28 para a célula vazia, L-43 e L-62.
- [ ] Corrigir o `calculo` da identificação em `REGISTROS_PUBLICOS` para `Nome da escola` (o campo de 2025; `NO_ENTIDADE` era o de 2024).

### Etapa 1 — Export

- [ ] `_escolas_publicas`: `censo_2024_presente` a partir do índice do Censo 2024; incluir na lista de colunas; falhar se `False` vier com matrícula 2024 não nula.
- [ ] `REGISTROS_PUBLICOS`: `licenca` e `licenca_url` por família; SEEDF pelo inventário, INEP pela nota do `README.md` §Licença; falhar antes de gravar se uma família SEEDF resolver para conjunto ODbL (L-62).
- [ ] `main`: mover o export para depois de `puladas`; sem `--parcial`, etapa pulada sai 1 sem gravar; com `--parcial`, exporta e grava `execucao.etapas_puladas` em `procedencia.json`.
- [ ] Regenerar `data/public` e conferir o diff (coluna nova, licenças, `execucao`, sha256).
- [ ] Conferir os 53 `False`, os 3 `True` com células vazias, os 36 valores positivos de 2024 e o `53014618` com 493.

### Etapa 2 — Build

- [ ] `carregar_dados`: validar/guardar `censo_2024_presente`; falhar se `False` vier com matrícula 2024 não nula; avisar quando `execucao.etapas_puladas` não estiver vazio.
- [ ] `mat_span` com família/ano/flag e as três frases; bloco 3 e bloco 9 usam o helper.
- [ ] Fluxo/TDI/TNR: `n is None` suprime; remover `n or 1`; linha do `n` vira `n = -`.
- [ ] Ideb: `n` pode ser `None`; `n_referencia` só nas linhas de ano ≠ 2025; sem `n=1`.
- [ ] `pagina_creditos` e `check_licencas` baseados em `procedencia.json` (`licenca`/`licenca_url`).
- [ ] `check_procedencia`, `check_limiar`, `check_estados` atualizados.
- [ ] `check_casos_limite` e `--check-casos`.

### Etapa 3 — Workflow

- [ ] Trocar o passo de build por `--check` no [.github/workflows/pages.yml](../../.github/workflows/pages.yml), com comentário sobre o escopo (critérios 1–4, 6, idempotência do 5; o `06` do critério 5 é local).
- [ ] Atualizar o §7 do contrato e o §8 (critério 5 dividido entre CI e execução local).

### Etapa 4 — Verificação e documentação

- [ ] Rodar `06` completo e `--check` completo.
- [ ] Inspecionar 53/3/36, os 7 perfis, as 2 páginas vazias, o índice (1.291, 35 RAs), os tamanhos e o L-63 no `53020529.html`.
- [ ] Conferir a reprodutibilidade (dois builds, mesmos bytes) e o `06` sem `pulado`.
- [ ] Exercitar o export pelo caminho novo: etapa pulada sem `--parcial` sai 1 sem gravar; com `--parcial` grava e registra `execucao.etapas_puladas`; `--force` só sobrescreve destino divergente.
- [ ] Registrar o worklog em `docs/worklogs/2026-11-09-...md`.
- [ ] Commitar `data/public` regenerado; `site/` continua fora do git.

## 6. Critérios de aceitação

1. **2024.** As 53 escolas sem linha no Censo 2024 mostram `-` e "a escola não consta do Censo de 2024"; as 3 com linha e células vazias mostram `-` e "matrícula não declarada no Censo de 2024". `53020529` é o exemplo da primeira; `53013662` (ou `53015665`/`53019415`) da segunda.
2. **2025.** Em uma cópia com `53000854.mat_fund_ai_2025 = NA`, a página não publica fluxo/TDI/TNR de AI; mostra a matrícula `-` com "matrícula não declarada no Censo de 2025" e a linha `n = -` (sem "alunos"); o Ideb de 2025, se existir, tem `n: null`; as linhas de Ideb de ano ≠ 2025 levam `n_referencia: "2025"`; nenhum `n` vira 1.
3. **Creche.** Em uma cópia com `53000781.mat_inf_cre_2025 = NA`, o bloco 9 mostra `2025 -` e "matrícula não declarada no Censo de 2025"; 2024 ausente continua "Censo de 2024".
4. **36 school-years.** `53014618` mostra 493 em AI 2024, mesmo com `oferta_fund_ai=0`; nenhum dos 36 vira `nao_aplicavel`; o build não usa `oferta_*` no bloco 3.
5. **Limiar.** Nenhuma unidade com n < 30 publica TDI/TNR/aprovação/reprovação/abandono; `n is None` também é suprimido; na renderização a `limiar 0`, `n=0` é registrado como 0.
6. **Licença.** `creditos.html` mostra a licença de cada fonte a partir de `procedencia.json` (`licenca` e, quando houver, `licenca_url`); o export falha antes de gravar quando uma família SEEDF resolve para conjunto ODbL; `check_licencas` falha se faltar licença ou se uma fonte publicada for ODbL; nenhum número cita a série ODbL.
7. **Export.** `06 --public` com uma etapa pulada: sem `--parcial`, sai 1 e não grava; com `--parcial`, grava e registra `execucao.etapas_puladas`; `--force` só sobrescreve destino divergente; `06` completo sem `pulado`.
8. **Gate.** O workflow roda `--check`; um erro semeado em um critério executável (1–4, 6) faz o passo sair 1 antes do upload; o contrato diz que o `06` do critério 5 é local.
9. **Reprodutibilidade.** Dois builds com o mesmo `--data-build` produzem os mesmos bytes; o `06` completo não pula etapa.
10. **Documentação.** O contrato, `SCHEMA.md` e `data/public/README.md` descrevem a coluna, as licenças, o `n_referencia` condicional, as frases (com L-63) e os tamanhos 60/40/13/3.7 KB; o §6 explica 67/80; o `calculo` da identificação diz `Nome da escola`.

## 7. Verificação

```sh
# insumo
.venv/bin/python scripts/06_analysis.py --public data/public
# build + critérios (1–4, 6, idempotência do 5 e os casos de limite)
.venv/bin/python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check
# só os casos de limite, para depurar
.venv/bin/python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-casos
# sintaxe
python -m py_compile scripts/06_analysis.py scripts/12_build_site.py
```

Conferências manuais:

- `53020529.html` (sem linha 2024) e `53013662.html` (célula vazia 2024);
- `53014618.html` (493 em AI 2024, `oferta_fund_ai=0`);
- `53001419.html` (perfil f; 15 alunos; TDI 0,0% não vira taxa);
- `53000854`, `53000986`, `53000862`, `53000781`, `53000226`, `53001354` (perfis a–e, g);
- `53000331` (vazia);
- `site/indice.json` (1.291; ordem alfabética), as 35 seções de RA, `site/dados/*.json` (Ideb de ano ≠ 2025 com `n_referencia`, Ideb de 2025 sem o campo, matrícula/creche sem o campo);
- `site/creditos.html` (licenças e `licenca_url`), `site/como-ler.html` (frases/limiar);
- `docs/LIMITES.md` com L-63 e a frase de `53020529.html` citando L-63;
- `find site -type f -exec sha256sum {} + | sort` em dois builds, `diff` vazio;
- `06 --public` com uma etapa forçada a pular: sem `--parcial`, sai 1 sem gravar e sem tocar `data/public`; com `--parcial`, grava e `procedencia.json` traz `execucao.etapas_puladas`; `--force` não altera nenhum dos dois comportamentos.

## 8. Riscos e perguntas em aberto

- **Licença e inventário.** O `06` passa a depender de `data/interim/seedf_datasets.csv` (não versionado); se faltar, o export deve falhar com mensagem clara. O `procedencia.json` guarda a licença resolvida e a URL, então o CI do Pages não precisa do inventário.
- **L-63.** O id é novo e não pode colidir com um limite registrado fora do repositório; conferir `docs/LIMITES.md` antes da Etapa 0. A L-28 continua sendo o id da célula vazia.
- **`data/public` muda.** A coluna nova, as licenças e `execucao` alteram o `sha256`; o build falha até o insumo regenerado ser commitado. É a única dependência de sequência. Um export com `--parcial` seguido de um completo também exige `--force`, porque o `procedencia.json` difere — é o comportamento desejado.
- **`n: null` no JSON.** É mudança de esquema para consumidores; documentar no §5.2 e no `SCHEMA.md`, junto da regra de que `n_referencia` só aparece quando o `n` é contagem de alunos de outro ano.
- **Fixture do `check_casos_limite`.** Copiar os quatro arquivos e alterar cinco escolas custa ~2,5 s, mas a renderização fica restrita às escolas afetadas; um fixture mínimo de 5 escolas seria mais rápido e não passaria pelo loader nem pelo guard de sha.
- **Tempo do CI.** O `--check` constrói o site, roda os critérios e o build de reprodutibilidade; ~5 s no ambiente local. O upload usa o `site/` já construído.
- **As 53 escolas.** São escolas de 2025 sem linha em 2024; a frase nova é factual e não afirma que a escola é nova. Se o Censo 2024 tiver a escola com `CO_ENTIDADE` diferente, a flag continua sendo o critério.

## 9. Fora de escopo

- Alterar o universo de 1.291 escolas, as 35 RAs, as 927 de infraestrutura, as 475 com creche ou os 7 perfis.
- Ranking, média/mediana/distribuição de rede, comparação entre escolas, mapa (L-46), idade exata (L-03), Ideb privado pós-2017 (L-08), meta do Ideb (L-56), série ODbL (L-62).
- Novas fontes, rede, `jinja2`, pytest ou qualquer dependência fora do `requirements.txt`.
- Implementar o plano neste documento; a execução é uma etapa separada.

## 10. Definição de pronto

- `06_analysis.py --public data/public` roda sem etapa pulada e o `data/public` regenerado está commitado.
- `12_build_site.py --check` passa os critérios 1–4 e 6, a idempotência do 5 e o `casos_limite` sobre o insumo completo.
- As 53/3/36, os 7 perfis, as 2 páginas vazias e os fixtures de 2025/creche conferem; `53020529.html` cita L-63.
- O workflow do Pages roda `--check` e falha antes do upload quando um critério executável falha; o contrato registra que o `06` do critério 5 é local.
- `SCHEMA.md`, `docs/FASE-1.md`, `data/public/README.md` e `docs/LIMITES.md` (L-63) descrevem o que entrou; o worklog registra os números e a verificação.
- `data/public` versionado; `site/` fora do git; nenhuma etapa manual não documentada.
- `REPORT.md` não ganha número novo; se algum limite novo for necessário, ele está em `docs/LIMITES.md` com id e evidência.
