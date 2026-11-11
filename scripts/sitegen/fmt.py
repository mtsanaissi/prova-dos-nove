"""Formatação de números e rótulos de etapa.

Entrada: valores numéricos e códigos de etapa.
Saída: texto formatado em pt-BR (milhar com ponto, decimal com vírgula).
Idempotente: sim — funções puras."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .contract import IDEB_YEARS, STAGE_SLUG


def fmt_int(value) -> str:
    return f"{int(value):,}".replace(",", ".")


def fmt_dec(value) -> str:
    return f"{float(value):.1f}".replace(".", ",")


def fmt_pct(value) -> str:
    """Número com um decimal e arredondamento half-up sobre a string decimal.

    Só para os agregados da home (percentuais e percentis): `fmt_dec` usa o float
    binário e imprimiria 8,95 como "8,9" e 4,05 como "4,0", contra o que
    `README.md` e `REPORT.md` publicam. O símbolo de unidade não entra aqui — ele
    fica no texto em volta —, então 8,95 vira "9,0" e 0,3499 vira "0,3". As
    páginas de escola continuam com `fmt_dec`, cujos valores já têm no máximo um
    decimal.
    """
    quantized = Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f"{quantized:.1f}".replace(".", ",")


def fmt_years(years) -> str:
    years = [str(a) for a in years]
    if not years:
        return ""
    if years == IDEB_YEARS:
        return "2005–2025, de dois em dois anos"
    if len(years) == 1:
        return years[0]
    if len(years) == 2 and int(years[1]) - int(years[0]) == 1:
        return f"{years[0]}–{years[1]}"
    return ", ".join(years)


def stage_slug(stage: str) -> str:
    return STAGE_SLUG.get(stage, stage.lower())


def stage_title(label: str) -> str:
    return label[:1].upper() + label[1:]


def student_word(n: int | None) -> str:
    return "aluno" if n == 1 else "alunos"
