"""Rótulos e âncoras das Regiões Administrativas.

Entrada: o valor bruto de `ra` no insumo.
Saída: rótulo de exibição, id de âncora e chave de ordenação.
Idempotente: sim — funções puras sobre a tabela do Apêndice A do plano.

O valor bruto é o do cadastro SEEDF e não muda; o rótulo é só de exibição.
Uma RA nova sem entrada aqui interrompe o build em vez de vazar o valor bruto.
"""

from __future__ import annotations

import re
import unicodedata

from .errors import BuildError

REGION_LABELS = {
    "AGUA QUENTE": "Água Quente",
    "AGUAS CLARAS": "Águas Claras",
    "ARAPOANGA": "Arapoanga",
    "ARNIQUEIRA": "Arniqueira",
    "BRAZLANDIA": "Brazlândia",
    "CANDANGOLANDIA": "Candangolândia",
    "CEILANDIA": "Ceilândia",
    "CRUZEIRO": "Cruzeiro",
    "FERCAL": "Fercal",
    "GAMA": "Gama",
    "GUARA": "Guará",
    "ITAPOA": "Itapoã",
    "JARDIM BOTANICO": "Jardim Botânico",
    "LAGO NORTE": "Lago Norte",
    "LAGO SUL": "Lago Sul",
    "NUCLEO BANDEIRANTE": "Núcleo Bandeirante",
    "PARANOA": "Paranoá",
    "PARK WAY": "Park Way",
    "PLANALTINA": "Planaltina",
    "PLANO PILOTO": "Plano Piloto",
    "RECANTO DAS EMAS": "Recanto das Emas",
    "RIACHO FUNDO": "Riacho Fundo",
    "RIACHO FUNDO II": "Riacho Fundo II",
    "SAMAMBAIA": "Samambaia",
    "SANTA MARIA": "Santa Maria",
    "SAO SEBASTIAO": "São Sebastião",
    "SCIA": "SCIA",
    "SIA": "SIA",
    "SOBRADINHO": "Sobradinho",
    "SOBRADINHO II": "Sobradinho II",
    "SOL NASCENTE / POR DO SOL": "Sol Nascente/Pôr do Sol",
    "SUDOESTE / OCTOGONAL": "Sudoeste/Octogonal",
    "TAGUATINGA": "Taguatinga",
    "VARJAO": "Varjão",
    "VICENTE PIRES": "Vicente Pires",
}


def _strip_accents(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def region_anchor_id(region: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", _strip_accents(region).lower()).strip("-")
    if not base:
        raise BuildError(f"RA sem âncora: {region!r}")
    return f"ra-{base}"


def region_label(region: str) -> str:
    try:
        return REGION_LABELS[region]
    except KeyError:
        raise BuildError(f"RA sem rótulo de exibição: {region!r}") from None


def region_sort_key(region: str) -> tuple[str, str]:
    return (_strip_accents(region_label(region)).lower(), region)
