# data/public/

Exceção declarada à regra "`data/` nunca entra no git" (`AGENTS.md`,
Convenções). Aqui entra **apenas** o recorte mínimo que o build do site lê:
agregado por escola e por etapa, sem arquivo bruto, sem microdado e sem linha
que identifique uma pessoa. Tudo nesta pasta é gerado por script, versionado e
descrito em `SCHEMA.md`.

Gerado por:

```sh
.venv/bin/python scripts/06_analysis.py --public data/public
```

| arquivo | grão | o que traz |
|---|---|---|
| `escolas.parquet` | escola (1.291) | identificação, rede, RA, `censo_2024_presente`, 8 sinalizadores de oferta e matrícula por etapa em 2024 e 2025 |
| `indicadores.parquet` | escola × etapa × indicador × ano | Ideb observado (2005–2025), TDI, TNR, aprovação, reprovação e abandono (2025), com `estado` copiado da fonte |
| `infraestrutura.parquet` | escola × item (8 itens) | presença declarada dos itens de infraestrutura, no universo das 927 escolas que oferecem ensino fundamental ou médio |
| `procedencia.json` | família de indicador | fonte, arquivo, anos, cálculo, limites, `licenca`, `licenca_url` e o sha256 dos três parquets; topo com `execucao.etapas_puladas` |

Tamanhos medidos em 2026-11-09: 61 KB, 40 KB, 13 KB e 4.7 KB.

`censo_2024_presente` é `True` quando a escola de 2025 tem linha no Censo 2024
e `False` quando não tem. As 53 escolas sem linha e as 3 com linha e células
vazias recebem frases diferentes na página (L-63 e L-28).

A licença vem por família: os conjuntos da SEEDF usam `licenca_titulo` e
`licenca_url` do inventário do CKAN; a INEP fica com "público, sem licença
declarada no portal", sem URL. O export falha antes de gravar se uma família
SEEDF resolver para um conjunto ODbL (L-62).

O build **não** lê `data/interim/` nem `data/raw/`; ele confere o sha256
registrado em `procedencia.json` e falha se o insumo não bater. Se o destino já
existir com conteúdo diferente, o export falha e só sobrescreve com `--force`,
para que a mudança apareça no diff. Uma execução com etapa pulada não grava sem
`--parcial`; com `--parcial`, a lista vai para `execucao.etapas_puladas`.
