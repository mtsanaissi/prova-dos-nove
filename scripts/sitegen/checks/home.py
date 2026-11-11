"""Critério 9: números, procedência e legenda da home.

Entrada: HTML da home, `dados/home.json` e o modelo do insumo.
Saída: o texto do `[ok]` ou `BuildError`.
Idempotente: sim — só lê.

O check confere o que o critério promete: todo `data-numero` da home tem registro
completo em `dados/home.json`, o texto renderizado bate com o parquet pelo mesmo
formatador da página, as somas da ausência fecham, há quatro cartões, a legenda
do gráfico é a do contrato e diz o que precisa dizer, e a home não publica
truque de ranking nem link para escola. Nenhum id de `agregados.parquet` fica sem
publicação: o arquivo é auditado pelo que a home mostra.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from ..contract import PHRASE_HOME_NETWORK_COMPARISON, STATES
from ..errors import BuildError
from ..home_page import fmt_aggregate, fmt_ideb_uf, ideb_uf_id
from .common import number_ids

CARD_COUNT = 4

DELTA_GLYPHS = ("▲", "▼", "↑", "↓")


def _aggregate(data: dict, identifier: str) -> float:
    try:
        return data["agregados"][identifier]["valor"]
    except KeyError:
        raise BuildError(f"agregados.parquet sem o id {identifier!r}") from None


def _expected_text(data: dict, identifier: str) -> tuple[str, object]:
    """Texto e valor que o parquet determina para um id da home."""
    if identifier in data["agregados"]:
        row = data["agregados"][identifier]
        if row["estado"] != "valor":
            raise BuildError(f"agregado {identifier} com estado {row['estado']!r}")
        return fmt_aggregate(row), row["valor"]
    for (stage, year, network), entry in data["ideb_uf"].items():
        for field in ("df", "brasil", "posicao", "n_ufs"):
            if ideb_uf_id(stage, year, network, field) != identifier:
                continue
            if field in ("df", "brasil") and entry[f"{field}_estado"] != "valor":
                raise BuildError(
                    f"{identifier}: Ideb ausente renderizado como número"
                )
            return fmt_ideb_uf(field, entry), entry[field]
    raise BuildError(f"{identifier}: id sem origem no insumo")


def _home_records(site: Path) -> tuple[dict, list[dict]]:
    path = site / "dados" / "home.json"
    if not path.is_file():
        raise BuildError(f"falta {path}")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("pagina") != "home":
        raise BuildError("dados/home.json sem pagina = 'home'")
    if not record.get("gerado_em"):
        raise BuildError("dados/home.json sem gerado_em")
    numbers = record.get("numeros")
    if not isinstance(numbers, list) or not numbers:
        raise BuildError("dados/home.json sem a lista 'numeros'")
    return record, numbers


def _check_records(numbers: list[dict]) -> dict[str, dict]:
    by_id: dict[str, dict] = {}
    for number in numbers:
        identifier = number.get("id")
        if not identifier:
            raise BuildError("dados/home.json com número sem id")
        if identifier in by_id:
            raise BuildError(f"dados/home.json com id duplicado: {identifier}")
        for field in ("id", "fonte", "arquivo", "ano", "calculo", "estado"):
            if not number.get(field):
                raise BuildError(f"{identifier}: registro sem {field}")
        if not str(number["arquivo"]).startswith("data/public/"):
            raise BuildError(f"{identifier}: arquivo fora de data/public")
        n = number.get("n")
        if not (n is None or isinstance(n, int)):
            raise BuildError(f"{identifier}: n não é inteiro nem null")
        if not number.get("limites"):
            raise BuildError(f"{identifier}: registro sem limites")
        if number["estado"] not in STATES:
            raise BuildError(f"{identifier}: estado fora do contrato")
        if number["estado"] == "valor" and number.get("valor") is None:
            raise BuildError(f"{identifier}: estado valor com valor nulo")
        if number["estado"] == "ausente" and number.get("valor") is not None:
            raise BuildError(f"{identifier}: estado ausente com valor")
        by_id[identifier] = number
    return by_id


def _check_arithmetic(data: dict) -> None:
    universo = _aggregate(data, "ideb-universo")
    if _aggregate(data, "ideb-com-valor") + _aggregate(data, "ideb-sem-valor") != universo:
        raise BuildError("ausência: com valor + sem valor não fecha o universo")
    publica_sem = _aggregate(data, "ideb-publica-linha-sem-valor") + _aggregate(
        data, "ideb-publica-sem-linha"
    )
    privada_sem = _aggregate(data, "ideb-privada-linha-sem-valor") + _aggregate(
        data, "ideb-privada-sem-linha"
    )
    if publica_sem + privada_sem != _aggregate(data, "ideb-sem-valor"):
        raise BuildError("ausência: pública sem valor + privada sem valor não fecha")
    publica_total = _aggregate(data, "ideb-publica-com-valor") + publica_sem
    privada_total = _aggregate(data, "ideb-privada-com-valor") + privada_sem
    if publica_total + privada_total != universo:
        raise BuildError("ausência: pública + privada não fecha o universo")
    if _aggregate(data, "escolas-total") != len(data["escolas"]):
        raise BuildError("escolas-total não é a contagem do cadastro")
    if _aggregate(data, "ras-total") != len({escola["ra"] for escola in data["escolas"]}):
        raise BuildError("ras-total não é o número de RAs distintas do cadastro")
    total = _aggregate(data, "creche-mat-total")
    estadual = _aggregate(data, "creche-mat-estadual")
    if total <= 0 or estadual > total:
        raise BuildError("creche: matrícula estadual não cabe no total")
    if abs(round(100 * estadual / total, 4) - _aggregate(data, "creche-mat-estadual-pct")) > 1e-9:
        raise BuildError("creche: a porcentagem não é estadual ÷ total")
    if _aggregate(data, "creche-unidades-estadual") > _aggregate(data, "creche-unidades-total"):
        raise BuildError("creche: unidades estaduais passam do total")


def check_home(site: Path, data: dict) -> str:
    markup = (site / "index.html").read_text(encoding="utf-8")
    _, numbers = _home_records(site)
    by_id = _check_records(numbers)

    identifiers = number_ids(markup)
    if not identifiers:
        raise BuildError("index.html não publica número nenhum")
    for identifier in identifiers:
        if identifier not in by_id:
            raise BuildError(f"index.html: número {identifier} sem procedência em home.json")
    listed = set(identifiers)
    for identifier in by_id:
        if identifier not in listed:
            raise BuildError(f"home.json: {identifier} não aparece no HTML")

    orphans = sorted(set(data["agregados"]) - set(by_id))
    if orphans:
        raise BuildError(
            "agregados.parquet com id que a home não publica: " + ", ".join(orphans)
        )

    for identifier in sorted(listed):
        found = re.search(
            rf'data-numero="{re.escape(identifier)}"[^>]*>([^<]*)<', markup
        )
        if not found:
            raise BuildError(f"index.html: {identifier} sem texto legível")
        rendered = html.unescape(found.group(1)).strip()
        expected, value = _expected_text(data, identifier)
        if rendered != expected:
            raise BuildError(
                f"index.html: {identifier} mostra {rendered!r} e o parquet diz {expected!r}"
            )
        if by_id[identifier]["valor"] != value:
            raise BuildError(f"home.json: {identifier} com valor diferente do parquet")

    _check_arithmetic(data)

    cards = re.findall(r'data-cartao="([^"]+)"', markup)
    if len(cards) != CARD_COUNT:
        raise BuildError(f"index.html com {len(cards)} cartões, esperado {CARD_COUNT}")
    if len(set(cards)) != CARD_COUNT:
        raise BuildError("index.html repete o mesmo cartão")

    if html.escape(PHRASE_HOME_NETWORK_COMPARISON) not in markup:
        raise BuildError("index.html sem a legenda de comparação de redes do contrato")
    legend = re.search(r'<p class="legenda-rede">(.*?)</p>', markup, re.S)
    if not legend:
        raise BuildError('index.html sem o parágrafo class="legenda-rede"')
    legend_text = html.unescape(legend.group(1))
    for limit in ("L-65", "L-67", "L-36", "L-37", "L-32"):
        if limit not in legend_text:
            raise BuildError(f"legenda de rede sem {limit}")
    for identifier, number in by_id.items():
        if not identifier.startswith("tdi-"):
            continue
        for limit in ("L-65", "L-67"):
            if limit not in number["limites"]:
                raise BuildError(f"{identifier}: limites sem {limit}")
        if "turma pequena" not in number["calculo"]:
            raise BuildError(f"{identifier}: calculo sem a ressalva da turma pequena")

    for glyph in DELTA_GLYPHS:
        if glyph in markup:
            raise BuildError(f"index.html com seta de variação {glyph!r}: isso é juízo")
    if re.search(r'href="\d{8}\.html"', markup):
        raise BuildError("index.html linka uma página de escola")
    if 'href="metodologia.html"' not in markup:
        raise BuildError("index.html sem link para metodologia.html")

    for (stage, year, network), entry in data["ideb_uf"].items():
        if entry["df_estado"] != "ausente":
            continue
        identifier = ideb_uf_id(stage, year, network, "df")
        if identifier in listed:
            raise BuildError(f"index.html renderiza {identifier}, que é ausente no Ideb")

    visible = re.sub(r"<[^>]+>", "", markup)
    if "27º de 27" in visible:
        entry = data["ideb_uf"][("EM", "2025", "Estadual")]
        if entry["posicao"] != entry["n_ufs"]:
            raise BuildError(
                "a home diz '27º de 27' e a linha do EM/Estadual 2025 não é o último lugar"
            )

    return (
        f"{len(by_id)} números com procedência ({len(data['agregados'])} ids de "
        f"agregado), {CARD_COUNT} cartões, somas da ausência fechadas e legenda de "
        "rede conferida"
    )
