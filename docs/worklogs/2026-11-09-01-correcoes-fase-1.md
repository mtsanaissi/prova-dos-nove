# 2026-11-09 — correções da FASE-1 (casos de borda, licença e gate)

## O que entrou

- `scripts/06_analysis.py --public data/public`: `escolas.parquet` ganhou
  `censo_2024_presente` (presença do `CO_ENTIDADE` no Censo 2024). O export
  falha se uma escola com `False` tiver matrícula de 2024 não nula.
- `procedencia.json`: `licenca` e `licenca_url` por família. As famílias SEEDF
  resolvem no inventário `data/interim/seedf_datasets.csv` (`licenca_titulo` e
  `licenca_url` do conjunto); as INEP usam "público, sem licença declarada no
  portal", com URL nula. O export recusa conjunto ODbL antes de gravar (L-62).
- `procedencia.json`: `execucao.etapas_puladas`. Sem `--parcial`, etapa pulada
  faz o `06` sair 1 **sem** gravar; com `--parcial`, exporta e registra a lista.
  `--force` continua só como "sobrescrever destino com sha diferente".
- `scripts/12_build_site.py`: três frases de matrícula (2024 sem linha, 2024
  célula vazia e 2025), `n` pode ser `null`, `n_referencia` só em Ideb de ano
  diferente de 2025, créditos por licença do insumo, checagens de 2024 em todas
  as 1.291 páginas e o novo `check_casos_limite` (`--check-casos`).
- `.github/workflows/pages.yml`: o passo de publicação usa `--check` antes do
  upload. O CI cobre os critérios 1–4 e 6, a idempotência do 5 e os casos de
  limite; a metade do critério 5 que roda o `06` continua local, porque
  `data/interim/` está fora do git.
- `docs/FASE-1.md`, `SCHEMA.md`, `data/public/README.md`, `README.md` e
  `docs/LIMITES.md` (L-63) descrevem o que entrou.

## Números do insumo

- Censo 2024: 1.360 linhas; Censo 2025: 1.291; cadastro de 2025: 1.291.
- 53 escolas de 2025 sem linha no Censo 2024 (`censo_2024_presente = False`) e
  3 com linha e as quatro células de matrícula vazias (`53013662`, `53015665`,
  `53019415`).
- 36 school-years com `oferta_* = 0` e matrícula de 2024 positiva; o exemplo
  `53014618` mantém 493 em AI/2024.
- Build: 1.291 páginas, 21.720 linhas de indicador e 7.416 de infraestrutura;
  80 unidades escola × etapa com n < 30 (67 com TDI valor/zero).
- `data/public`: `escolas.parquet` 61 KB, `indicadores.parquet` 40 KB,
  `infraestrutura.parquet` 13 KB e `procedencia.json` 4.7 KB. O plano previa
  3.7 KB para o `procedencia.json`; as licenças por família e
  `execucao.etapas_puladas` acrescentaram ~1 KB.

## Verificação

```sh
.venv/bin/python scripts/06_analysis.py --public data/public
.venv/bin/python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check
.venv/bin/python scripts/12_build_site.py --public data/public --out site \
  --data-build 2026-11-06 --check-casos
```

Resultado: `06` sem etapa pulada; `procedencia`, `ranking`, `limiar` (80/67),
`estados` (53 sem linha e 3 com célula vazia), `reprodutibilidade`,
`licencas` (6 fontes) e `casos_limite` ok. O caso de limite cobre também a
creche com célula vazia em 2024 (`53001419`). Dois builds produziram os mesmos
2.587 arquivos. Um `procedencia.json` de teste com ODbL fez o `--check` sair 1
em `[falhou] licencas`; um teste controlado de `main` confirmou que etapa
pulada sem `--parcial` não chama o export e com `--parcial` grava
`etapas_puladas = ["qb"]`. O `53020529.html` cita L-63; o `53013662.html` cita
L-28; o `53014618.html` mostra 493 em 2024.

## Pendências

- L-63 fica aberto: a flag registra a ausência de linha, mas a fonte não diz se
  a escola não existia, mudou de código ou ficou fora da coleta.
