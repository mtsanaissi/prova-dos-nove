"""Critério 3: unidade escola × etapa com n < limiar não publica taxa.

Entrada: HTML do site, modelo do insumo e limiar.
Saída: o texto do `[ok]` ou `BuildError`.
Idempotente: sim — só lê."""

from __future__ import annotations

import re

from ..errors import BuildError
from ..contract import STAGES, PHRASE_ENROLLMENT_2025, PHRASE_SMALL_N
from ..fmt import student_word
from ..loader import get_indicator
from .common import read_page


def check_threshold(site: Path, data: dict, threshold: int) -> str:
    units = 0
    with_tdi = 0
    without_enrollment = 0
    for school in data["escolas"]:
        markup = read_page(site, school["co"])
        for stage, _, offering in STAGES:
            if not school[offering]:
                continue
            n = school.get(f"mat_{stage}_2025")
            if n is not None and n >= threshold:
                continue
            if n is None:
                without_enrollment += 1
            else:
                units += 1
                if get_indicator(data, school["co"], stage, "tdi")["estado"] in ("valor", "zero"):
                    with_tdi += 1
            word = student_word(n)
            note = f"{n} {word} {PHRASE_SMALL_N}"
            for block in ("fluxo", "tdi", "tnr"):
                found_block = re.search(
                    rf'<article class="etapa" data-bloco="{block}" data-etapa="{stage}"[^>]*>(.*?)</article>',
                    markup,
                    re.S,
                )
                if not found_block:
                    raise BuildError(f"{school['co']}/{stage}/{block}: falta o cartão da etapa")
                snippet = found_block.group(1)
                if n is None:
                    if 'data-situacao="suprimido"' not in found_block.group(0) and 'data-situacao="ausente"' not in found_block.group(0):
                        raise BuildError(f"{school['co']}/{stage}/{block}: n ausente não foi suprimido")
                    if PHRASE_ENROLLMENT_2025 not in re.sub(r"<[^>]+>", "", snippet):
                        raise BuildError(f"{school['co']}/{stage}/{block}: falta a frase de 2025")
                else:
                    if 'data-situacao="suprimido"' not in found_block.group(0):
                        raise BuildError(f"{school['co']}/{stage}/{block}: n < {threshold} não foi suprimido")
                    if note not in re.sub(r"<[^>]+>", "", snippet):
                        raise BuildError(f"{school['co']}/{stage}/{block}: falta a nota de amostra pequena")
                if re.search(rf'data-numero="{block}-[^"]+"', snippet):
                    raise BuildError(f"{school['co']}/{stage}/{block}: publica taxa sem denominador")

    target = "53001419"
    markup = read_page(site, target)
    if 15 < threshold:
        if "15 alunos nesta etapa — o indicador não é publicado quando a turma é pequena" not in re.sub(
            r"<[^>]+>", "", markup
        ):
            raise BuildError(f"{target}: falta a nota de 15 alunos")
        if "0,0%" in markup:
            raise BuildError(f"{target}: TDI 0,0% aparece como taxa mesmo com 15 alunos")
    return (
        f"{units:,} unidades escola × etapa com n < {threshold} suprimidas "
        f"({with_tdi:,} delas com TDI valor/zero, a matriz do q16); "
        f"{without_enrollment:,} sem matrícula de 2025 também suprimidas"
    )
