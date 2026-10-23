# 2026-10-22 — 04. INEP ingerida e Ideb nacional

Objetivo: responder se o DF está mesmo entre os melhores do país. Até aqui o
relatório só podia dizer que a pergunta era interna. Scripts:
`07_ingest_inep.py`, `08_profile_inep.py`, `q7` de `06_analysis.py`.

## 1. Ingestão manual, declarada (`07_ingest_inep.py`)

O download automático não funciona neste ambiente (registro 01). O script não
tenta esconder: ele **espera** o arquivo em `data/raw/inep/inbox/`, recebido do
navegador.

Catálogo embutido: 8 arquivos, com URL, prioridade e o que cada um acrescenta.
`--check` imprime a lista do que falta e onde baixar; `--de DIR` permite apontar
outro diretório de entrada.

Tratamento de artefato de navegador, todos observados na prática:

- `arquivo (1).zip` → nome normalizado, sem o sufixo de duplicata;
- `.crdownload`, `.part`, `.tmp` → ignorados (download em curso);
- `arquivo.zip:Zone.Identifier` → ignorado (fluxo alternativo do Windows);
- arquivo fora do catálogo → **recusado**, com o motivo impresso.

Cada ingestão: calcula sha256, move para `data/raw/inep/<data>_<nome>` e
registra URL, data, bytes, hash e nota de procedência no `MANIFEST.md`. O
tamanho conhecido no catálogo serve para a listagem de `--check`, não como
validação — quem decide é o hash. Reingestão com o mesmo hash não move nem
registra de novo; hash diferente cria uma versão `_v2` preservando a primeira.

Nesta sessão entraram:

| Arquivo | Bytes | O que acrescenta |
|---|---|---|
| `divulgacao_regioes_ufs_ideb_2025.zip` | 757.970 | Ideb por UF e região, 2005–2025 |
| `nota_informativa_ideb_2025.pdf` | 551.360 | metodologia, comparabilidade e critérios de não-cálculo |

`MANIFEST.md`: 133 → 135 linhas. Os dois `:Zone.Identifier` ficaram na inbox,
como esperado (são só metadado do Windows).

## 2. Perfil genérico, depois leitor específico (`08_profile_inep.py`)

O primeiro passo não presume nada: lista os membros do zip, abre cada planilha,
lê o cabeçalho, imprime colunas e só recorta o DF quando reconhece uma coluna de
UF. Resultado no zip de UF: 4 membros (`.xlsx`, `.ods`, `.md5`, diretório), 3
abas, 131 colunas — e **"UF identificada: NÃO"**.

Esse "não" é o ponto técnico: a planilha é formatada, não tabular. Cinco linhas
de título, cabeçalho em três faixas, códigos de variável só na linha 10. O
`read_excel` direto devolve a linha de título como nome de coluna, e o detector
de UF não tem onde se apoiar. Em vez de adivinhar, o script disse que não sabia.

Daí `processar_ideb_uf()`, um leitor específico:

1. encontra a linha de códigos pela primeira célula que começa com
   `VL_OBSERVADO_` (linha 10, índice 9);
2. corpo a partir da linha seguinte;
3. **filtra por lista branca** de 27 UFs + 5 regiões — é isso que descarta as
   linhas de "Fonte:" e as sete notas de rodapé, que ocupam a mesma coluna;
4. derrete `VL_OBSERVADO_2005..2025` (Ideb observado) e `VL_PROJECAO_2007..2021`
   (meta), com o ano no sufixo do código;
5. separa o rótulo de rede do marcador de nota: `Total (3)(4)` →
   `rede_base = Total`, `marcadores_nota = 3)(4`;
6. extrai o zip para `mkdtemp()` e apaga o diretório ao final.

Saída: `data/interim/inep/ideb_uf_tidy.parquet`, 6.688 linhas, colunas `etapa`,
`local`, `rede`, `ano`, `indicador`, `valor`, `rede_base`, `marcadores_nota`.

**Decisão contrária à regra de recorte:** aqui ficam as 27 UFs, não só o DF. A
tabela inteira tem 152 linhas, e sem as outras 26 não existe comparação. É
exceção documentada em `SCHEMA.md`; a regra DF-only continua valendo para
microdado.

## 3. Cuidados de leitura que o arquivo exigiu

- **Marcador de nota não é do ano.** `(4)` em `Total (4)` fala do SAEB 2011
  (calculado sem as escolas federais). O DF carrega esse rótulo em 2025 e o valor
  de 2025 não é afetado. Ler o marcador como se fosse ressalva do ano corrente
  inutilizaria a série.
- **26 UFs, não 27, em AI/Estadual.** Roraima não tem resultado de rede estadual
  em 2025. Ausência não é zero e não foi preenchida.
- **A aba de ensino médio não publica linha `Pública`** em nenhuma UF (só Total,
  Privada e Estadual). A comparação pública no médio é, portanto, a rede
  estadual — e no DF ela é praticamente toda a rede pública (4 escolas estaduais
  não vinculadas, 11 federais, nenhuma municipal).
- **Não existe linha "Brasil"** nesta planilha. O DF é comparado às 27 UFs, não à
  média nacional; a linha Brasil vive em outro zip, ainda não baixado.

## 4. `q7` — posição do DF entre as UFs

Saídas: `data/interim/q7_ideb_uf.csv` (etapa × ano × rede, com `df`, `posicao`,
`n_ufs`, `mediana_ufs`, `melhor`, `melhor_valor`) e `q7_matriculas_por_rede.csv`
(composição da matrícula por rede, 2024).

Ideb 2025:

| Etapa | Rede | DF | Posição | Mediana das UFs |
|---|---|---|---|---|
| Anos iniciais | Total | 6,4 | 8º de 27 | 6,1 |
| Anos iniciais | Pública | 6,0 | 13º de 27 | 6,0 |
| Anos iniciais | Estadual | 6,0 | 16º de 26 | 6,15 |
| Anos iniciais | Privada | 7,4 | 4º de 27 | 7,0 |
| Anos finais | Total | 5,1 | 11º de 27 | 5,1 |
| Anos finais | Pública | 4,7 | 16º de 27 | 4,8 |
| Anos finais | Estadual | 4,6 | 21º de 27 | 4,8 |
| Anos finais | Privada | 6,2 | 10º de 27 | 6,2 |
| Ensino médio | Total | 4,1 | 22º de 27 | 4,4 |
| Ensino médio | Estadual | 3,6 | **27º de 27** | 4,2 |
| Ensino médio | Privada | 5,7 | 9º de 27 | 5,7 |

Movimento 2023 → 2025: Total 4º→8º (AI), 8º→11º (AF), 10º→22º (EM); Estadual
11º→16º (AI), 16º→21º (AF), 18º→27º (EM). O Ideb do DF quase não se moveu (6,4 →
6,4 em AI Total); a mediana das UFs subiu (5,8 → 6,1). É piora relativa.

Por que o "Total" engana: a rede privada não conveniada tem 26,9% da matrícula de
fundamental e 24,3% da de médio em 2024 (`relatorio_matriculas_2024.csv`), e essa
privada é a 4ª do país em anos iniciais. A linha que sustenta a reputação do DF é
a que mistura redes e só olha os anos iniciais.

## 5. O que a nota informativa mudou no relatório

`nota_informativa_ideb_2025.pdf` (8 páginas, lido manualmente, não convertido):

- metodologia **inalterada desde 2007**; 2023 e 2025 são comparáveis às edições
  anteriores. A ressalva provisória que estava no relatório foi removida e
  substituída pela ressalva verdadeira;
- 2023 e 2025 **não têm metas** — por isso `VL_PROJECAO` termina em 2021 e não há
  coluna de meta para 2023/2025;
- esta é a **última divulgação na formulação original**: a próxima edição quebra a
  série, e isso está escrito no relatório;
- critérios de não-cálculo, com nome e portaria (nº 435/2025): (H) menos de 10
  estudantes presentes no SAEB; (I) participantes abaixo de 80% dos matriculados.
  É o que permite dizer, com fonte, que escola sem Ideb é ausência com causa
  declarada — nunca zero.

## 6. Verificação

- `06_analysis.py` e `08_profile_inep.py` rodam com exit 0; `07` reexecutado não
  ingere nada (dedup por sha256).
- `q7_ideb_uf.csv` e `q7_matriculas_por_rede.csv` reproduzem cada número do
  `REPORT.md` §2.4 e do veredito.
- `ideb_uf_tidy.parquet`: 6.688 linhas, 3 etapas, 32 locais, anos 2005–2025.
- Nenhum diretório temporário sobrou (`/tmp/inep_*` vazio após a execução).
- Duas armadilhas verificadas por inspeção do dado, não por suposição: os 26/27
  de AI/Estadual e a ausência da linha `Pública` no médio.

## 7. Pendências

- `divulgacao_brasil_ideb_2025.zip` — linha Brasil: permite DF × média nacional,
  que hoje não é calculável.
- `divulgacao_anos_iniciais_escolas_2025.zip`,
  `divulgacao_anos_finais_escolas_2025.zip`,
  `divulgacao_ensino_medio_escolas_2025.zip` (~112 MB cada) — Ideb por escola de
  todas as redes: fecha o que `REPORT.md` §5 ainda chama de invisível.
- `tx_rend_escolas_2025.zip`, `TDI_2025_ESCOLAS.zip`, `tnr_escolas_2025.zip` —
  fluxo, distorção e taxa de não-resposta por escola.
- Join escola a escola com `CO_ENTIDADE` só depois de medir a taxa de casamento,
  como todos os outros. A INEP nem sempre usa esse nome (`CO_ESCOLA` aparece em
  indicadores por escola).
