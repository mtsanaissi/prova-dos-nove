# 2026-11-07 — build do site da FASE-1

## O que entrou

- `scripts/06_analysis.py --public data/public`: exporta `escolas.parquet`,
  `indicadores.parquet`, `infraestrutura.parquet` e `procedencia.json` a partir
  de `data/interim/`, com guarda de sha256 e `--force`.
- `scripts/12_build_site.py`: gera `site/` a partir **só** de `data/public/`.
  Inclui `index.html` (busca por `indice.json` + lista por RA, sem número),
  `indice.json`, `estilo.css`, `creditos.html`, `como-ler.html`, uma página por
  escola e `dados/<CO_ENTIDADE>.json`.
- `.github/workflows/pages.yml`: publicação no GitHub Pages por Actions.
- `data/public/README.md` e `SCHEMA.md` descrevem o insumo publicado.

## Decisões de implementação

- O insumo de infraestrutura tem o universo das **927** escolas de EF/EM; nas
  demais o bloco é `nao_aplicavel` (L-25). Isso faz a distribuição do parquet
  bater com a tabela do contrato (39,4% com biblioteca etc.).
- `rede` no insumo é a categoria do site (federal, estadual, privada conveniada,
  privada não conveniada) e `rede_cadastro` guarda o `Nome Rede` original.
- O build não usa `datetime.now()`; `--data-build` tem o padrão `2026-11-06`,
  que é o carimbo do contrato. O workflow não passa a flag, então o Pages publica
  com esse carimbo até que o build receba outro.
- Cada número visível carrega `data-numero`; o JSON da escola é montado a partir
  do mesmo objeto que renderiza o HTML, e o `--check` confere a correspondência.

## Verificação

```sh
.venv/bin/python scripts/06_analysis.py --public data/public
.venv/bin/python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check
```

Resultado: `procedencia`, `ranking`, `limiar` (80 unidades com n < 30; 67 com
TDI valor/zero), `estados`, `reprodutibilidade` e `licencas` ok. O `06` rodou
sem etapa pulada. O segundo build produz os mesmos bytes.
