"""Critério 1: todo número publicado tem procedência.

Entrada: HTML e JSON do site e o modelo do insumo.
Saída: o texto do `[ok]` ou `BuildError`.
Idempotente: sim — só lê."""

from __future__ import annotations

from ..errors import BuildError
from ..contract import STATES, STUDENT_COUNT_FAMILIES, SLUG_BY_STAGE_LABEL
from .common import read_page, read_school_json, number_ids


def check_provenance(site: Path, data: dict, data_build: str) -> str:
    for school in data["escolas"]:
        markup = read_page(site, school["co"])
        record = read_school_json(site, school["co"])
        if record.get("escola") != school["co"]:
            raise BuildError(f"{school['co']}: JSON de procedência com escola diferente")
        if record.get("gerado_em") != data_build:
            raise BuildError(f"{school['co']}: JSON de procedência com gerado_em diferente")
        numbers = record.get("numeros")
        if not isinstance(numbers, list) or not numbers:
            raise BuildError(f"{school['co']}: JSON de procedência sem números")
        by_id = {}
        for number in numbers:
            identifier = number.get("id")
            if not identifier or identifier in by_id:
                raise BuildError(f"{school['co']}: número sem id ou id duplicado")
            by_id[identifier] = number
        for identifier in number_ids(markup):
            if identifier not in by_id:
                raise BuildError(f"{school['co']}: número {identifier} sem procedência")
            number = by_id[identifier]
            for field in ("fonte", "arquivo", "ano", "calculo", "estado"):
                if not number.get(field):
                    raise BuildError(f"{school['co']}: {identifier} sem {field}")
            n = number.get("n")
            if not (n is None or isinstance(n, int)):
                raise BuildError(f"{school['co']}: {identifier} sem n inteiro ou null")
            if n is None:
                if number.get("bloco") not in STUDENT_COUNT_FAMILIES:
                    raise BuildError(
                        f"{school['co']}: {identifier} com n null fora de família de alunos"
                    )
                # Ideb com valor e denominador ausente continua sendo valor; as
                # taxas (fluxo, TDI, TNR) são suprimidas e ficam ausentes.
                if number["bloco"] == "ideb":
                    states_when_n_null = ("valor", "zero", "ausente")
                else:
                    states_when_n_null = ("ausente", "nao_aplicavel")
                if number["estado"] not in states_when_n_null:
                    raise BuildError(
                        f"{school['co']}: {identifier} com n null e estado {number['estado']}"
                    )
                slug = SLUG_BY_STAGE_LABEL.get(number.get("etapa"))
                if slug is None or (
                    f'data-numero="matricula-{slug}-2025" data-estado="ausente"' not in markup
                ):
                    raise BuildError(
                        f"{school['co']}: {identifier} com n null sem matrícula ausente na página"
                    )
            if not number.get("limites"):
                raise BuildError(f"{school['co']}: {identifier} sem limites")
            if number["estado"] not in STATES:
                raise BuildError(f"{school['co']}: {identifier} com estado fora do contrato")
            if number["estado"] in ("valor", "zero") and number.get("valor") is None:
                raise BuildError(f"{school['co']}: {identifier} com estado {number['estado']} e valor nulo")
            if number["estado"] in ("ausente", "nao_aplicavel") and number.get("valor") is not None:
                raise BuildError(f"{school['co']}: {identifier} com estado {number['estado']} e valor")
            if not str(number["arquivo"]).startswith("data/public/"):
                raise BuildError(f"{school['co']}: {identifier} aponta para fora de data/public")
            requires_reference = (
                number.get("bloco") in STUDENT_COUNT_FAMILIES
                and str(number.get("ano")) != "2025"
                and n is not None
            )
            if requires_reference and number.get("n_referencia") != "2025":
                raise BuildError(
                    f"{school['co']}: {identifier} sem n_referencia = '2025' para ano != 2025"
                )
            if not requires_reference and "n_referencia" in number:
                raise BuildError(
                    f"{school['co']}: {identifier} com n_referencia onde não há outro ano de n"
                )
    return f"{len(data['escolas']):,} páginas com procedência completa"
