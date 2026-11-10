"""Critério 4: valor, zero, ausente e não aplicável não se confundem.

Entrada: HTML do site e modelo do insumo.
Saída: o texto do `[ok]` ou `BuildError`.
Idempotente: sim — só lê."""

from __future__ import annotations

from pathlib import Path

import html
import re

from ..errors import BuildError
from ..contract import PHRASE_IDEB_PUBLIC, PHRASE_IDEB_PRIVATE, PHRASE_STAGE_NOT_OFFERED, PHRASE_CENSUS_2024_NO_ROW, PHRASE_ENROLLMENT_2024, PHRASE_NO_INDICATOR
from .common import read_page


def check_states(site: Path, data: dict, threshold: int) -> str:
    phrases = {
        "53000862": [PHRASE_IDEB_PUBLIC],
        "53000781": [PHRASE_IDEB_PRIVATE],
        "53000226": [PHRASE_STAGE_NOT_OFFERED],
        "53020529": [PHRASE_CENSUS_2024_NO_ROW, PHRASE_NO_INDICATOR],
        "53013662": [PHRASE_ENROLLMENT_2024],
        "53000331": [PHRASE_NO_INDICATOR],
    }
    if 15 < threshold:
        phrases["53001419"] = [
            "15 alunos nesta etapa — o indicador não é publicado quando a turma é pequena"
        ]
    for code, entries in phrases.items():
        markup = read_page(site, code)
        visible_text = re.sub(r"<[^>]+>", "", markup)
        for phrase in entries:
            if phrase not in visible_text:
                raise BuildError(f"{code}: frase ausente ou com redação diferente: {phrase!r}")

    for school in data["escolas"]:
        markup = read_page(site, school["co"])
        if "NaN" in markup:
            raise BuildError(f"{school['co']}: NaN na página")
        visible_text = re.sub(r"<[^>]+>", "", markup)
        if not school["censo_2024_presente"]:
            if PHRASE_CENSUS_2024_NO_ROW not in visible_text:
                raise BuildError(f"{school['co']}: sem linha em 2024 e sem a frase de L-63")
            if PHRASE_ENROLLMENT_2024 in visible_text:
                raise BuildError(f"{school['co']}: sem linha em 2024 com a frase de célula vazia")
        elif any(school.get(f"mat_{stage}_2024") is None for stage in ("CRE", "AI", "AF", "EM")):
            if PHRASE_ENROLLMENT_2024 not in visible_text:
                raise BuildError(f"{school['co']}: célula vazia em 2024 sem a frase de L-28")
            if PHRASE_CENSUS_2024_NO_ROW in visible_text:
                raise BuildError(f"{school['co']}: linha em 2024 com a frase de escola ausente")
        elif (
            PHRASE_ENROLLMENT_2024 in visible_text
            or PHRASE_CENSUS_2024_NO_ROW in visible_text
        ):
            raise BuildError(f"{school['co']}: frase de 2024 sem ausência de 2024")
        for state, snippet in re.findall(
            r'data-estado="(ausente|nao_aplicavel|zero|valor)"[^>]*>([^<]*)<', markup
        ):
            text = html.unescape(snippet).strip()
            if state == "ausente" and text and not text.startswith("-"):
                raise BuildError(f"{school['co']}: estado ausente sem hífen: {text!r}")
            if state == "nao_aplicavel" and text and not text.startswith("—"):
                raise BuildError(f"{school['co']}: estado nao_aplicavel sem travessão: {text!r}")
            if state == "zero" and text and not text.startswith("0"):
                raise BuildError(f"{school['co']}: estado zero sem 0: {text!r}")
    return "símbolos, frases de 2024 e presença no Censo conferidos"
