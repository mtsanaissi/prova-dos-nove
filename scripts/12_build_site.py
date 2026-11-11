"""Build do site estático da Prova dos Nove (fase 1 de `docs/FASE-1.md`).

Entrada: `data/public/` (`escolas.parquet`, `indicadores.parquet`,
         `infraestrutura.parquet` e `procedencia.json`), gerado por
         `06_analysis.py --public data/public`.
Saída:   `site/index.html`, `site/indice.json`, `site/estilo.css`,
         `site/creditos.html`, `site/como-ler.html`, uma página por escola
         (`site/<CO_ENTIDADE>.html`) e a procedência de cada número
         (`site/dados/<CO_ENTIDADE>.json`).
Idempotente: sim — o build não chama `datetime.now()`, itera em ordem fixa e
usa `--data-build` como único carimbo de tempo.

Regras de leitura: `estado` vem do parquet e nunca é deduzido de `NaN` quando a
fonte o registra; `0` é zero; `—` é não aplicável. O build lê apenas
`data/public/` e confere o sha256 registrado em `procedencia.json`.

O build vive em `scripts/sitegen/`; este arquivo é a CLI.

Uso:
    python scripts/12_build_site.py --public data/public --out site \
        --data-build 2026-11-06 --limiar-n 30
    python scripts/12_build_site.py --public data/public --out site --check
    python scripts/12_build_site.py --public data/public --out site --check-sumario-escola
    python scripts/12_build_site.py --public data/public --out site --check-casos
"""

from __future__ import annotations

from sitegen.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
