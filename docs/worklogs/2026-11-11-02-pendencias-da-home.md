# 2026-11-11-02 — as duas pendências da home: fronteira do agregado e gatilhos de L-67

Antecessor: [`docs/plans/2026-11-11-home-e-metodologia.md`](../plans/2026-11-11-home-e-metodologia.md)
e [`2026-11-11-01-home-e-metodologia.md`](2026-11-11-01-home-e-metodologia.md). O
plano desta sessão foi entregue como revisão do §10 daquele plano e não virou
arquivo em `docs/plans/`; as decisões ficam registradas aqui.
Contrato: [`docs/FASE-1.md`](../FASE-1.md) §2.3 e §8 (critério 9).

## 1. O que entrou

1. `data/public/README.md`: parágrafo que separa lista de **arquivos** de lista de
   **linhas** e põe a fronteira no `calculo` da família.
2. `scripts/sitegen/checks/home.py`: asserção de id morto (`agregados.parquet`
   menos o que a home publica), uma linha no docstring e o `[ok]` citando as duas
   contagens.
3. `docs/LIMITES.md`: L-67 ganha os dois gatilhos de reabertura; o item continua
   **aberto**.
4. `docs/FASE-1.md`: §2.3 ganha as cinco peças que mudam juntas se o limiar for
   aplicado ao agregado; §8, critério 9, passa a exigir que todo id do agregado
   seja publicado.
5. `DESENVOLVIMENTO.md`: §5 (linha do critério 9) e §9 (id novo no agregado).
6. Este worklog.

A entrega anterior estava na árvore sem commit; entrou antes, em `dfa9b0c`, para
separar as duas mudanças no histórico.

## 2. Decisão 1 — a lista fechada é de arquivos, não de linhas

**A decisão.** Um id novo dentro de `agregados.parquet` não exige emenda do
`AGENTS.md`; uma tabela nova exige. A razão é o que a lista protege: arquivo novo
traz fonte, licença, `sha256` e entrada no `MANIFEST.md` — decisão de fonte, não
de formato. Id novo não muda nenhum dos dois; muda só uma conta, e a conta já tem
casa declarada, que é o `calculo` da família.

**A fronteira.** É o `calculo`. Se o texto que descreve a família já descreve a
conta do id novo, é linha. Se não descreve, é família nova em `procedencia.json`,
isto é, decisão de fonte, cálculo, limites e licença.

**Por que o gate real não é a frase do `AGENTS.md`.** A frase ("Adding a table to
this list requires amending this file") é nominal: declara a regra, não a executa.
O que roda é `REGISTROS_PUBLICOS` em `scripts/06_analysis.py` — 14 famílias, quatro
delas de agregado (`home_contagem`, `home_creche`, `home_ideb_cobertura`,
`home_tdi_rede`) — somado a `DATASET_SEEDF_POR_FAMILIA` e `FAMILIAS_INEP`.
`_registros_publicos()` resolve a licença por família e falha com "família … sem
origem de licença declarada no export" quando ela não está em nenhum dos dois
mapas. Do outro lado, `procedencia.json` é o que o build lê para fonte, limites,
licença e `sha256`; família fora de `REGISTROS_PUBLICOS` não tem nada disso. Em
resumo: a emenda do `AGENTS.md` é a declaração; `REGISTROS_PUBLICOS` mais os dois
mapas de família são a guarda.

**O que garante o outro lado.** Se o export pode crescer por linha, a home precisa
ser obrigada a publicar toda linha exportada; senão o agregado vira depósito de id
que ninguém lê. É a asserção do §3.

**O que não foi feito.** `REGISTROS_PUBLICOS`, os dois mapas de família e
`06_analysis.py` já existiam e não mudaram. A emenda do `AGENTS.md` também não foi
feita: a frase atual basta, e ampliá-la com nomes de bloco convidaria a lista a
envelhecer dentro do arquivo durável.

## 3. Decisão 2 — nenhum id morto no agregado

`check_home` compara o conjunto de ids de `agregados.parquet` com os ids que a
home publica e falha com a lista dos que sobraram. A leitura importa para a
próxima sessão: **se um dia um número for exportado e deliberadamente não
exibido, a saída correta é não exportar o id** — não afrouxar o check. O arquivo é
auditado pelo que a home mostra.

A asserção compara ids, não valores: id publicado com valor errado continua sendo
pego pela comparação texto × parquet que já existe no mesmo check. A lógica não foi
duplicada.

## 4. Decisão 3 — L-67 não fecha

**Não fecha**, e a razão é a decisão de 2026-11-11-01: a distribuição da home usa
todos os valores publicados, inclusive as unidades de turma pequena que a página
da escola suprime (D4). Enquanto o gráfico comparar redes, a diferença existe e
está declarada — na legenda e no `calculo` de cada registro `tdi-*`. O item não é
sobre o limiar em si; é sobre a diferença entre a mediana da home e a da página da
escola.

**Os dois gatilhos de reabertura**, agora escritos no próprio L-67:

- (a) o gráfico deixa de comparar redes — a pergunta "qual é o valor da rede" pede
  outra forma de gráfico;
- (b) a mediana da home passa a ter de bater com a mediana da página da escola.

**A distinção que evita deriva.** Mudar o valor de `--limiar-n` **não reabre** o
item: o texto de L-67 é relativo ao limiar de D4, não ao número que estiver na
flag. Mas mudar o valor **invalida a medição** de 0,7 e 0,2, feita com n = 30:
remedir e reescrever antes de citar. O item fecha com data quando o gráfico usar
só unidades ≥ limiar.

**A mudança acoplada** (registrada em §2.3 do contrato, não executada): se o limiar
for aplicado ao agregado, cinco peças mudam no mesmo commit — `06_analysis.py` (o
export passa a receber o limiar e `CALCULO_TDI_REDE` perde a ressalva da turma
pequena), `contract.py` (`PHRASE_HOME_NETWORK_COMPARISON`), `README.md` e
`REPORT.md` (as medianas), L-67 e `data/public/`. O critério 9 falha até as peças
se alinharem, porque confere a legenda e a ressalva da turma pequena em cada
registro `tdi-*`.

## 5. Verificação executada

Passo 0, antes de editar:

```text
[ok] home: 48 números com procedência, 4 cartões, somas da ausência fechadas e legenda de rede conferida
ids no parquet: 40 | mortos: []
```

Depois das edições:

- `.venv/bin/python -m compileall -q scripts`: limpo.
- `.venv/bin/python scripts/12_build_site.py --public data/public --out site
  --data-build 2026-11-06 --check`: dez `[ok]`, e o da home citando as duas
  contagens — "48 números com procedência (40 ids de agregado), 4 cartões, somas
  da ausência fechadas e legenda de rede conferida".
- Conferência de texto: `grep` encontra "arquivos, não de linhas" uma vez em
  `data/public/README.md`, "não reabre o item" na linha de L-67, "Se o limiar for
  aplicado ao agregado" em §2.3 e "id exportado e não usado" em §8/9.

**Mutação.** `check_home` foi chamado direto, com o modelo de `load_data` mais um
id `id-fantasma` no agregado:

```text
[falhou] home: agregados.parquet com id que a home não publica: id-fantasma
```

A variante do plano — copiar `data/public`, acrescentar uma linha ao parquet,
refazer o `sha256` e rodar o build com `--public` apontando para a cópia — **não
rodou nesta sessão**: o guarda de shell nega `cp`, inclusive dentro do workspace, e
a cópia não é possível aqui. O caminho de código exercitado é o mesmo (a asserção é
local ao check), e o carregamento dos 40 ids está coberto pela execução positiva
acima. Quem rodar em ambiente sem esse bloqueio tem o roteiro no plano da sessão.

**`data/public`.** Nenhum parquet e nenhum `procedencia.json` mudou: o `git diff`
de `data/public` mostra apenas o `README.md`, que é documentação. Nenhum byte foi
regerado, nenhum `--force` foi executado.

## 6. O que ficou fora, de propósito

- Emenda do `AGENTS.md` (a frase atual basta; listar blocos no arquivo durável
  envelhece).
- `SCHEMA.md`: nenhum campo ou grão mudou.
- Regerar `data/public/`, rodar `--force`, mexer em `06_analysis.py`,
  `contract.py`, `agregados.parquet` ou em qualquer texto de página.
- Reescrever o §10 do plano anterior: o plano é registro datado, e o fechamento
  vai aqui e nos documentos normativos.

## 7. Pendências e leituras para a próxima sessão

- **L-67 segue aberto**, agora com gatilhos escritos. Fechar só com data e com o
  gráfico usando apenas unidades ≥ limiar.
- **Id órfão:** exportar e não exibir é defeito do export, não do check.
- **Medição de 0,7/0,2** é medição com n = 30, não constante do texto: se o limiar
  mudar de valor, remedir antes de citar.
- **Medianas de §2.3:** o parágrafo cita 8,9 / 17,0 / 20,5 e 1,3 / 3,2 / 4,5 como
  os valores que `README.md` e `REPORT.md` passariam a mostrar **se** o limiar for
  aplicado. Não foram medidas nesta sessão; ao aplicar, medir e citar arquivo, ano
  e cálculo antes de publicar.
