"""Registro ordenado das verificações do build.

Entrada: o contexto do build (insumo, saída, modelo e limiar).
Saída: `CHECKS`, a tupla ordenada que a CLI percorre.
Idempotente: sim — metadados apenas.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .edge_cases import check_edge_cases
from .licenses import check_licenses
from .provenance import check_provenance
from .ranking import check_no_ranking
from .region_toc import check_region_toc
from .reproducibility import check_reproducibility
from .school_toc import check_school_toc
from .states import check_states
from .threshold import check_threshold


@dataclass(frozen=True)
class CheckContext:
    public: Path
    out: Path
    data: dict
    data_build: str
    threshold: int


@dataclass(frozen=True)
class Check:
    key: str
    flag: str | None
    help: str
    run: Callable[[CheckContext], str]


CHECKS = (
    Check(
        "procedencia",
        "--check-procedencia",
        "critério 1: procedência de todo número",
        lambda ctx: check_provenance(ctx.out, ctx.data, ctx.data_build),
    ),
    Check(
        "ranking",
        None,
        "critério 2: nenhum ranking no índice",
        lambda ctx: check_no_ranking(ctx.out),
    ),
    Check(
        "sumario",
        "--check-sumario",
        "critério 7: salto por RA e seções na mesma ordem",
        lambda ctx: check_region_toc(ctx.out),
    ),
    Check(
        "limiar",
        "--check-limiar",
        "critério 3: n < limiar não publica taxa",
        lambda ctx: check_threshold(ctx.out, ctx.data, ctx.threshold),
    ),
    Check(
        "estados",
        "--check-estados",
        "critério 4: valor, zero, ausente e não aplicável",
        lambda ctx: check_states(ctx.out, ctx.data, ctx.threshold),
    ),
    Check(
        "sumario_escola",
        "--check-sumario-escola",
        "critério 8: sumário da página da escola",
        lambda ctx: check_school_toc(ctx.out, ctx.data),
    ),
    Check(
        "reprodutibilidade",
        None,
        "critério 5: segundo build com os mesmos bytes",
        lambda ctx: check_reproducibility(ctx.public, ctx.out, ctx.data_build, ctx.threshold),
    ),
    Check(
        "licencas",
        "--check-licencas",
        "critério 6: licenças e fontes",
        lambda ctx: check_licenses(ctx.out, ctx.data),
    ),
    Check(
        "casos_limite",
        "--check-casos",
        "casos de limite: 2024, 2025, creche, 493 e limiar 0",
        lambda ctx: check_edge_cases(ctx.public, ctx.data_build),
    ),
)
