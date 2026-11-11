"""Gráfico da distorção idade-série por rede, em SVG inline.

Entrada: modelo de `loader.load_data` (os agregados da home).
Saída: o SVG do gráfico, com uma tabela equivalente dentro de `<details>`.
Idempotente: sim — render puro, coordenadas formatadas com uma casa fixa."""

from __future__ import annotations

import math

from .contract import CHART_CEILING_STEP, STAGES
from .fmt import fmt_int, fmt_pct

# Geometria fixa: tudo em unidades do viewBox, nada medido no navegador.
WIDTH = 640
LEFT = 168
RIGHT = 612
LABEL_X = 86
TOP = 18
GROUP_HEIGHT = 74
ROW_HEIGHT = 26
BAR_HEIGHT = 14
AXIS_Y = TOP + 3 * GROUP_HEIGHT
HEIGHT = AXIS_Y + 28

NETWORKS = (("estadual", "Estadual"), ("privada", "Privada"))


def number_id(stage: str, network: str, metric: str) -> str:
    return f"tdi-{stage.lower()}-{network}-{metric}"


def chart_ceiling(values: dict) -> int:
    """Maior p90 arredondado para cima em múltiplo de `CHART_CEILING_STEP`."""
    maior = max(
        values[number_id(stage, network, "p90")]["valor"]
        for stage, _, _ in STAGES
        for network, _ in NETWORKS
    )
    return int(math.ceil(maior / CHART_CEILING_STEP)) * CHART_CEILING_STEP


def _span(identifier: str, text: str, tag: str = "tspan") -> str:
    return (
        f'<{tag} class="valor" data-numero="{identifier}" data-estado="valor">'
        f"{text}</{tag}>"
    )


def _table_row(values: dict, stage: str, label: str, network: str, network_label: str) -> str:
    cells = "".join(
        f"<td>{_span(number_id(stage, network, metric), fmt_pct(values[number_id(stage, network, metric)]['valor']), 'span')}</td>"
        for metric in ("p10", "mediana", "p90")
    )
    unidades = values[number_id(stage, network, "n")]
    return (
        f"<tr><td>{label}</td><td>{network_label}</td>{cells}"
        f"<td>{_span(unidades['id'], fmt_int(unidades['valor']), 'span')}</td></tr>"
    )


def render_tdi_chart(data: dict) -> str:
    """SVG com mediana e faixa central de 80% por etapa e rede, e a tabela."""
    values = data["agregados"]
    ceiling = chart_ceiling(values)
    scale = (RIGHT - LEFT) / ceiling

    def x(value: float) -> float:
        return LEFT + float(value) * scale

    parts = [
        f'<svg class="grafico-rede" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        'aria-label="Distorção idade-série em 2025 por etapa e rede: barra da faixa '
        'central de 80% das escolas, traço na mediana; os números estão na tabela '
        'logo abaixo." xmlns="http://www.w3.org/2000/svg">'
    ]

    # Grade de 5 em 5 e rótulo de 10 em 10, antes das barras.
    for tick in range(0, ceiling + 1, CHART_CEILING_STEP // 2):
        parts.append(
            f'<line class="grade" x1="{x(tick):.1f}" y1="{TOP - 6}" '
            f'x2="{x(tick):.1f}" y2="{AXIS_Y}"/>'
        )
        if tick % CHART_CEILING_STEP == 0:
            parts.append(
                f'<text class="eixo" x="{x(tick):.1f}" y="{AXIS_Y + 16}" '
                f'text-anchor="middle">{fmt_int(tick)}</text>'
            )
    parts.append(
        f'<text class="eixo-titulo" x="0" y="{AXIS_Y + 16}" '
        'text-anchor="start">Em % dos alunos</text>'
    )

    for index, (stage, label, _) in enumerate(STAGES):
        top = TOP + index * GROUP_HEIGHT
        parts.append(
            f'<text class="rotulo-grupo" x="0" y="{top + 4}">{label[:1].upper() + label[1:]}</text>'
        )
        for row, (network, network_label) in enumerate(NETWORKS):
            row_top = top + 14 + row * ROW_HEIGHT
            center = row_top + BAR_HEIGHT / 2 + 4
            p10 = values[number_id(stage, network, "p10")]["valor"]
            mediana = values[number_id(stage, network, "mediana")]["valor"]
            p90 = values[number_id(stage, network, "p90")]["valor"]
            start, end = x(p10), x(p90)
            parts.append(
                f'<text class="rotulo-rede" x="{LABEL_X}" y="{center:.1f}" '
                f'text-anchor="end">{network_label}</text>'
            )
            parts.append(
                f'<rect class="faixa faixa-{network}" x="{start:.1f}" y="{row_top}" '
                f'width="{end - start:.1f}" height="{BAR_HEIGHT}" rx="3"/>'
            )
            parts.append(
                f'<line class="mediana" x1="{x(mediana):.1f}" y1="{row_top - 2}" '
                f'x2="{x(mediana):.1f}" y2="{row_top + BAR_HEIGHT + 2}"/>'
            )
            parts.append(
                f'<text class="valor-ponta" x="{start - 5:.1f}" y="{center:.1f}" '
                f'text-anchor="end">{_span(number_id(stage, network, "p10"), fmt_pct(p10))}</text>'
            )
            parts.append(
                f'<text class="valor-ponta" x="{end + 5:.1f}" y="{center:.1f}" '
                f'text-anchor="start">{_span(number_id(stage, network, "p90"), fmt_pct(p90))}</text>'
            )
    parts.append("</svg>")

    rows = "".join(
        _table_row(values, stage, label, network, network_label)
        for stage, label, _ in STAGES
        for network, network_label in NETWORKS
    )
    parts.append(
        '<details class="tabela-dados"><summary>Os números do gráfico, em tabela</summary>'
        '<table class="tabela"><thead><tr><th>Etapa</th><th>Rede</th><th>p10 (%)</th>'
        "<th>Mediana (%)</th><th>p90 (%)</th><th>Unidades escola × etapa</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        '<p class="fonte">Unidade é a escola × etapa com taxa publicada em 2025, '
        "incluindo as de turma pequena (L-67). A barra vai do p10 ao p90.</p>"
        "</details>"
    )
    return "".join(parts)
