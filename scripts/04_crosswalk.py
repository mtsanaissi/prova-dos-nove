"""Crosswalk de chaves entre os arquivos da SEEDF.

Entrada: parquets de `data/interim/seedf/`.
Saída:   `data/interim/crosswalk.csv` (taxa de casamento por par de arquivos)
         `data/interim/ra_por_fonte.csv` (nomes de RA como cada fonte escreve)
Idempotente: sim — só leitura e reescrita das saídas.

A chave usada é `CO_ENTIDADE` (Censo Escolar), que a SEEDF carrega em todas as
séries. A taxa é medida, nunca estimada; órfãos são listados, não completados.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from _common import INTERIM

SEEDF = INTERIM / "seedf"
ENTIDADE = ("CO_ENTIDADE", "cod_inep", "Cód_Inep", "Código INEP", "Cód. Inep")
RA = ("NO_RA", "Nome RA", "NO_DRE")


def carregar(prefixo: str) -> pd.DataFrame | None:
    arquivos = sorted(SEEDF.glob(f"{prefixo}_*.parquet"))
    if not arquivos:
        return None
    frames = []
    for a in arquivos:
        df = pd.read_parquet(a)
        col = next((c for c in ENTIDADE if c in df), None)
        if col is None:
            continue
        ano_col = next(
            (c for c in ("NU_ANO_CENSO", "Ano do Censo", "Ano", "ano") if c in df), None
        )
        achado = re.findall(r"\d{4}", a.name)
        # os arquivos de unidades por oferta não têm ano no nome; o metadado do
        # recurso no CKAN declara 2023 para os três.
        # série por linha: o arquivo do IDEB guarda vários anos
        ano = (
            df[ano_col].astype(str).str.strip()
            if ano_col
            else pd.Series([achado[0] if achado else "2023"] * len(df), index=df.index)
        )
        col_ra = next((c for c in RA if c in df), None)
        frames.append(
            pd.DataFrame(
                {
                    "ano": ano,
                    "codigo": df[col].astype(str).str.strip(),
                    "ra": df[col_ra].astype(str).str.strip() if col_ra else None,
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    fontes = {
        "escolas": carregar("escolas"),
        "matriculas": carregar("matriculas"),
        "infraestrutura": carregar("infraestrutura"),
        "situacao": carregar("situacao"),
        "tecnologia": carregar("tecnologia"),
        "ideb_serie": carregar("ideb_serie"),
        "unidades_ei": carregar("unidades_ei"),
        "unidades_oferta": carregar("unidades_oferta"),
    }

    linhas = []
    for ano in sorted({a for f in fontes.values() if f is not None for a in f.ano.unique()}):
        for alvo in ("matriculas", "infraestrutura", "situacao", "tecnologia", "unidades_ei"):
            base, outro = fontes["escolas"], fontes[alvo]
            if base is None or outro is None:
                continue
            b = set(base.loc[base.ano == ano, "codigo"]) - {"", "nan"}
            o = set(outro.loc[outro.ano == ano, "codigo"]) - {"", "nan"}
            if not b or not o:
                continue
            comuns = b & o
            linhas.append(
                {
                    "ano": ano,
                    "de": "escolas",
                    "para": alvo,
                    "n_de": len(b),
                    "n_para": len(o),
                    "casados": len(comuns),
                    "taxa_de_para_pct": round(100 * len(comuns) / len(b), 1),
                    "taxa_para_de_pct": round(100 * len(comuns) / len(o), 1),
                    "orfaos_em_de": len(b - o),
                    "orfaos_em_para": len(o - b),
                }
            )

    # toda a série do IDEB contra o cadastro do mesmo ano (não só o ano corrente)
    if fontes["ideb_serie"] is not None and fontes["escolas"] is not None:
        ideb = fontes["ideb_serie"]
        for ano, sub in ideb.groupby("ano"):
            b = set(fontes["escolas"].loc[fontes["escolas"].ano == ano, "codigo"]) - {"", "nan"}
            o = set(sub.codigo) - {"", "nan"}
            if not b or not o:
                continue
            linhas.append(
                {
                    "ano": ano,
                    "de": "escolas",
                    "para": "ideb_serie",
                    "n_de": len(b),
                    "n_para": len(o),
                    "casados": len(b & o),
                    "taxa_de_para_pct": round(100 * len(b & o) / len(b), 1),
                    "taxa_para_de_pct": round(100 * len(b & o) / len(o), 1),
                    "orfaos_em_de": len(b - o),
                    "orfaos_em_para": len(o - b),
                }
            )

    cw = pd.DataFrame(linhas).sort_values(["para", "ano"])
    cw.to_csv(INTERIM / "crosswalk.csv", index=False)
    print(cw.to_string(index=False))

    ras = []
    for nome, f in fontes.items():
        if f is None or f.ra is None:
            continue
        for ano, sub in f.groupby("ano"):
            valores = sorted({v for v in sub.ra.dropna().unique() if v not in ("", "nan", "None")})
            ras.append({"fonte": nome, "ano": ano, "n_ra": len(valores), "ras": "|".join(valores)})
    pd.DataFrame(ras).to_csv(INTERIM / "ra_por_fonte.csv", index=False)


if __name__ == "__main__":
    main()
