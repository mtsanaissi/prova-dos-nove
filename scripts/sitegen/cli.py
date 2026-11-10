"""CLI do build: argumentos e execução das verificações.

Entrada: `sys.argv` (ou a lista passada a `main`).
Saída: o site em `--out` e uma linha por verificação; código 1 em erro.
Idempotente: sim — depende só de `--data-build`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .build import build_site
from .checks import CHECKS, CheckContext
from .contract import DEFAULT_DATA_BUILD, DEFAULT_N_THRESHOLD
from .errors import BuildError


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build estático da página por escola (FASE-1).")
    ap.add_argument("--public", type=Path, default=Path("data/public"), help="diretório do insumo público")
    ap.add_argument("--out", type=Path, default=Path("site"), help="diretório de saída")
    ap.add_argument("--data-build", default=DEFAULT_DATA_BUILD, help="único carimbo de tempo do build")
    ap.add_argument(
        "--limiar-n", type=int, default=DEFAULT_N_THRESHOLD,
        dest="n_threshold", metavar="LIMIAR_N", help="limiar de n pequeno (D4)",
    )
    ap.add_argument("--check", action="store_true", help="roda os critérios do §8 e os casos de limite")
    for check in CHECKS:
        if check.flag:
            ap.add_argument(check.flag, action="store_true", help=check.help)
    args = ap.parse_args(argv)
    if args.n_threshold < 0:
        ap.error("--limiar-n não pode ser negativo")

    try:
        result = build_site(args.public, args.out, args.data_build, args.n_threshold)
    except (BuildError, FileNotFoundError, ValueError) as exc:
        print(f"ERRO: {exc}")
        return 1

    if args.check:
        selected = [check.key for check in CHECKS]
    else:
        selected = [
            check.key for check in CHECKS
            if check.flag and getattr(args, check.flag[2:].replace("-", "_"))
        ]

    context = CheckContext(
        public=args.public,
        out=args.out,
        data=result["dados"],
        data_build=args.data_build,
        threshold=args.n_threshold,
    )
    by_key = {check.key: check for check in CHECKS}
    for key in selected:
        try:
            detail = by_key[key].run(context)
        except BuildError as exc:
            print(f"[falhou] {key}: {exc}")
            return 1
        print(f"[ok] {key}: {detail}")
    return 0
