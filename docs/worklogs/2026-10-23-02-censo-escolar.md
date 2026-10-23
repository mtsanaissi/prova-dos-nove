# 2026-10-23 — 02. Censo Escolar: ponderação, creche e conferência

Objetivo: ingerir o microdado do Censo Escolar da Educação Básica com recorte do
DF e responder três perguntas medidas — (a) as taxas por escola ponderadas pela
matrícula, (b) o lado da oferta da creche e o resíduo de 11,6 mil crianças, (c) a
conferência valor a valor da série de matrículas da SEEDF. Scripts: `11_ingest_censo.py`
(novo), `07_ingest_inep.py` (catálogo), `06_analysis.py` (q13–q15).

## 1. O que entrou

Dois arquivos, pelo caminho manual de sempre (`07_ingest_inep.py` com
`--baixado-em 2026-10-23`, que é o único acréscimo ao script): catálogo →
`--check` → ingestão, sem passo novo.

| Arquivo | Bytes | sha256 (início) |
|---|---|---|
| `2026-10-23_microdados_censo_escolar_2024.zip` | 33.829.396 | `ae29d81d…` |
| `2026-10-23_microdados_censo_escolar_2025_.zip` | 537.217.189 | `ad2c3891…` |

O sublinhado final do segundo é do nome que veio do servidor e foi preservado: o
manifesto registra o arquivo que entrou, não o que se gostaria que tivesse entrado.
`data/raw` não foi aberto nem reescrito — os zips são lidos em memória.

## 2. A premissa estava errada: desde 2024 não há linha de aluno

A tarefa partia de "o microdado de matrícula é por estudante, ainda que
desidentificado". **Não é.** O manual do usuário de 2024 diz que as bases passaram
a ser "dimensionadas ao nível de escolas", e o cabeçalho confirma: não há
`DT_NASCIMENTO`, não há idade simples, não há linha de aluno. O que há é matrícula
por etapa, turno, tempo integral, sexo, cor/raça e faixa etária, por escola.

Isso não é obstáculo, é notícia boa para a regra 2 do projeto: não existe base por
aluno a vazar, e nenhum parquet intermediário de pessoa precisou ser evitado — a
fonte já vem agregada. Também delimita o que se pode perguntar: **idade exata só
existe na série da SEEDF**, que republica o Censo. Do lado da INEP, só faixa
etária.

## 3. Leitura (`11_ingest_censo.py`)

- Zip aberto em memória, CSV em streaming, filtro `CO_UF == '53'`, nada do
  nacional materializado. As duas tabelas têm `CO_UF`, então o recorte não
  precisou passar pelo conjunto de `CO_ENTIDADE` do cadastro (regra 5 não se
  aplicou).
- **Encoding não é o do cabeçalho.** A primeira tentativa em `utf-8` passou na
  linha de cabeçalho (ASCII puro) e quebrou no corpo, no primeiro nome acentuado.
  O leitor agora tenta `utf-8` no arquivo inteiro e recomeça em `latin-1` quando
  um byte falha; a falha é imediata, então a tentativa errada custa pouco. Os dois
  arquivos são `latin-1`, `;`.
- **Colunas mudam de ano para ano, de novo.** 2024 tem `QT_MAT_MED_CT`;
  2025 não tem (o médio integrado virou `QT_MAT_MED_IFTP_CT`, que é outro
  recorte, não um rename). 2025 não tem `TP_SITUACAO_FUNCIONAMENTO` na tabela de
  matrícula (está na de escola) e tem duas colunas novas de faixa etária em 31/03.
  As colunas pedidas são declaradas por ano e a ausência entra como ausência; se
  uma coluna esperada sumir, o script para em vez de adivinhar.
- Linhas lidas: **215.545 nacionais e 1.360 do DF (0,63%) em 2024; 178.766 e 1.291
  (0,72%) em 2025.** Saída: 2.651 linhas (uma por escola × ano), 137.688 B.

## 4. Validação

| Checagem | Resultado |
|---|---|
| Creche 2024 (`QT_MAT_INF_CRE`) | 40.851, igual à âncora |
| Creche 2025 | 42.582 |
| Escolas com matrícula | 1.284 (2024) e 1.291 (2025) — o mesmo conjunto da SEEDF e do cadastro |
| Faixas etárias somam `QT_MAT_BAS` | 1.284 de 1.284 e 1.291 de 1.291 |
| Chave `CO_ENTIDADE` | 0 duplicatas nas duas edições |
| Unidades com creche em 2025 | 475, o mesmo conjunto do cadastro, escola por escola |
| Idade em 31/03 | só na edição de 2025 (`*_REF_31_03`); em 2024 não existe |
| `DT_NASCIMENTO` | não existe em nenhuma das duas edições |
| Idempotência | duas execuções, bytes idênticos |

O script interrompe acima de 0,5% de desvio nas âncoras: se o recorte não
reproduzir o que o projeto já publica, o problema é a leitura.

## 5. As três respostas

**(a) Ponderação.** Com o peso de matrícula de 2025 (925 de 925 escolas com taxa
têm peso), a mediana da escola típica e a média do aluno típico divergem **pouco**
— 1,0 p.p. ou menos na estadual e na privada, com três exceções (abandono e
reprovação no médio estadual, +1,6 e +1,5 p.p.; distorção no médio da rede
federal, −3,0) — e nunca invertem a ordem das redes:

| Indicador | Etapa / rede | Mediana | Ponderada |
|---|---|---|---|
| Distorção idade-série | iniciais, estadual | 8,95% | 9,43% |
| Distorção idade-série | iniciais, privada | 1,20% | 2,22% |
| Distorção idade-série | finais, estadual | 17,10% | 18,09% |
| Aprovação | finais, estadual | 94,20% | 92,94% |
| Abandono | médio, estadual | 2,4% | 4,0% |
| Ideb | iniciais, estadual | 6,00 | 6,00 |
| Ideb | finais, estadual | 4,70 | 4,71 |
| Ideb | médio, estadual | 3,60 | 3,70 |

O maior deslocamento é o abandono no médio estadual (+1,6 p.p.): a escola grande
abandona mais que a mediana. O peso também valida a metodologia — ponderado, o
Ideb das estaduais dá 6,00 / 4,71 / 3,70 contra 6,0 / 4,6 / 3,6 publicados pela
INEP para a rede. O que a ponderação acrescenta de mais importante é a
**cobertura**: o Ideb por escola cobre 89,6% da matrícula de iniciais, 82,3% nos
finais e **64,8%** no médio.

**(b) Creche.** Oferta: 470 unidades em 2024 e 475 em 2025 (7 da rede estadual,
o resto privada); 40.851 e 42.582 matrículas, das quais **99,7% na rede privada**.
Idade exata (só a série da SEEDF tem), creche 2024 → 2025: 0 ano 17 → 24; 1 ano
2.272 → 2.577; 2 anos 7.875 → 8.926; 3 anos 15.912 → 16.432; **4 anos 14.505 →
14.488**; 5 anos 188 → 95; 6 anos 82 → 40.

O resíduo de 11,6 mil da sessão anterior **não era oferta faltando, era
convenção de idade**. O próprio Censo 2024 conta 37.595 matrículas de criança de
até 3 anos (`QT_MAT_BAS_0_3`), contra 37.654 frequentando na PDAD — 59 de
diferença, 0,16%, dentro do IC amostral. Os 26.076 são creche **× idade no ano**,
e a diferença de 11.519 é a coorte que tinha 4 anos no ano e 3 na data de
referência do Censo. A hipótese "creche não declarada" não se confirma nem se
testa: deixa de ser necessária.

A data de referência, que é o que faltava para dizer isso, foi medida: em 2025 o
dicionário publica as duas (maio: 39.293; 31/03: 42.945, +9,3% em 31/03). Em
2024 ele não declara. Nas escolas que só têm creche, a razão faixa 0–3 / creche é
91,4% em 2024, 92,7% em 2025 na referência de maio e 99,9% em 31/03 — a edição de
2024 se comporta como a de maio. É inferência, e está declarada como inferência.

**(c) Conferência.** 13 campos, 16.692 células escola × etapa, 16.480 iguais
(98,7%) e 212 divergentes. **Exatos**: creche (1.284 de 1.284), EM integrado
(1.284) e educação especial (1.284). **Divergentes**: pré-escola −109 (−0,16%),
EF iniciais −274 (−0,14%), EF finais −19, EM propedêutico+normal −17, EJA −1.381
(−5,16%), técnico concomitante −588 (−11,2%), técnico subsequente −5.755
(−27,9%), FIC +80. Total da educação básica: −8.063 (−1,28%). Contraste com o
Ideb, que deu 5.276 valores e zero divergências: a série de matrículas da SEEDF
**não é** cópia exata do Censo, e o que ela subestima é EJA e educação
profissional — onde está o aluno adulto. A causa não é determinável nas tabelas
por escola; a base por aluno que explicaria não é mais pública.

## 6. Limites

- **Sem idade exata pela INEP.** Faixa etária apenas. Idade simples continua vindo
  da série da SEEDF, que cobre o DF e não o país.
- **A data de referência de 2024 é inferência**, não declaração do dicionário.
- **Divergências de EJA e educação profissional sem causa determinada.** A
  hipótese do aluno sem `IDADE` não é testável com o arquivo publicado.
- **Sem RA no Censo.** A tabela traz `CO_DISTRITO`/`CO_SUBDISTRITO`, que não são
  Regiões Administrativas; todo recorte territorial continua vindo da SEEDF.
- **Cobertura do Ideb limita a ponderação**: no médio estadual, 64,8% da matrícula.
- **Tabelas não lidas**: `Tabela_Escola`, `Tabela_Docente`, `Tabela_Turma`,
  `Tabela_Gestor`, `Tabela_Curso_Tecnico` (2025) e o suplemento de cursos técnicos
  (2024). Infraestrutura e docentes já vêm da SEEDF com série histórica; turma e
  gestor não respondem nenhuma pergunta desta fase.
- **A URL registrada no `MANIFEST.md` é a canônica do diretório de microdados da
  INEP, não uma URL verificada**: `download.inep.gov.br` reseta a conexão deste
  ambiente, então o caminho foi reconstruído a partir do nome do arquivo e está
  anotado como tal na linha do manifesto. O que está verificado são os bytes e o
  sha256 do arquivo que entrou.

## Reprodução

```sh
.venv/bin/python scripts/07_ingest_inep.py --check          # catálogo
.venv/bin/python scripts/07_ingest_inep.py --baixado-em 2026-10-23
.venv/bin/python scripts/11_ingest_censo.py                  # recorte do DF
.venv/bin/python scripts/06_analysis.py                      # q13, q14, q15
```

O `11` é offline, lê só `data/raw/inep/` e reescreve
`data/interim/inep/censo_escola_df.parquet` e `censo_metodo.csv`. O `06` passou a
emitir `q13_ponderacao_df.csv`, `q14_creche_{oferta,idade,referencia,fecho}.csv` e
`q15_conferencia_censo.csv`.
