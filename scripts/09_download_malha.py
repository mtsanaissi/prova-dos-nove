"""Baixa e valida a malha das Regiões Administrativas do DF (GDF/IDE).

Entrada: serviço ArcGIS público do IDE/DF,
         `https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/LIMITES/FeatureServer/1`
         (camada "Regiões Administrativas", 37 feições).
Saída:   `data/raw/malha/2026-10-22_regioes_administrativas_df.geojson` e linha
         nova em `data/raw/MANIFEST.md`;
         `data/interim/malha_ra_validacao.csv` (nome, código e área por RA, e se
         a RA aparece no cadastro da SEEDF de 2025 e na PDAD-A 2024).
Idempotente: sim — GeoJSON já baixado não é baixado de novo; a validação é
reescrita a partir do arquivo local.

Esta etapa **não** usa geometria: só atributos (`ra_nome`, `ra_codigo`,
`ra_cira`, `ra_areakm2`). É a validação que o projeto exige antes de qualquer
biblioteca geoespacial entrar em `requirements.txt`: procedência, CRS e
concordância de nome/código com as fontes de educação. Nenhum mapa é produzido.
"""

from __future__ import annotations

import json
import re
import unicodedata

import pandas as pd

from _common import DOWNLOAD_DATE, INTERIM, RAW, append_manifest, download, sha256

MALHA = RAW / "malha"
DEST = MALHA / f"{DOWNLOAD_DATE}_regioes_administrativas_df.geojson"
EXTRATO = INTERIM / "malha_ra_validacao.csv"
SERVICO = (
    "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/LIMITES/FeatureServer/1"
)
URL = (
    SERVICO
    + "/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
)
S = INTERIM / "seedf"


def norm_ra(txt: str) -> str:
    """Maiúsculas sem acento, com os mesmos apelidos usados em 06_analysis.py."""
    t = unicodedata.normalize("NFKD", str(txt)).encode("ascii", "ignore").decode().upper()
    t = re.sub(r"\s+", " ", t).strip()
    trocas = {
        "SOL NASCENTE E POR DO SOL": "SOL NASCENTE / POR DO SOL",
        "SUDOESTE/OCTOGONAL": "SUDOESTE / OCTOGONAL",
        "SCIA/ESTRUTURAL": "SCIA",
    }
    return trocas.get(t, t)


def main() -> None:
    MALHA.mkdir(parents=True, exist_ok=True)
    caminho, nbytes = download(URL, DEST)
    geojson = json.loads(caminho.read_text(encoding="utf-8"))
    feicoes = geojson["features"]
    print(f"malha: {len(feicoes)} feições, {nbytes / 1e6:.2f} MB → {caminho.name}")

    append_manifest(
        [
            {
                "arquivo": caminho.name,
                "fonte": "GDF/IDE — Geoserviços",
                "url": URL,
                "baixado_em": DOWNLOAD_DATE,
                "bytes": nbytes,
                "sha256": sha256(caminho),
                "notas": (
                    "malha das Regiões Administrativas do DF, serviço ArcGIS "
                    f"{SERVICO} (EPSG:31983 no serviço; GeoJSON em EPSG:4326); "
                    "download automático (fonte aberta, sem bloqueio)"
                ),
            }
        ]
    )

    malha = pd.DataFrame(
        [{**f["properties"], "geometry_type": f["geometry"]["type"]} for f in feicoes]
    )
    malha["ra_norm"] = malha["ra_nome"].map(norm_ra)

    # Cadastro da SEEDF de 2025: uma linha por escola, com NO_RA.
    escolas = pd.read_parquet(S / "escolas__relatorio_escolas_2025.parquet")
    nomes_seedf = (
        escolas.assign(ra_norm=escolas["Nome RA"].map(norm_ra))
        .groupby("ra_norm")["Nome RA"]
        .agg(lambda s: sorted(set(s))[0])
    )
    # PDAD-A 2024: uma linha por RA (35).
    pdad = pd.read_csv(INTERIM / "pdad_populacao.csv")
    nomes_pdad = pdad.assign(ra_norm=pdad["ra"].map(norm_ra)).set_index("ra_norm")["ra_pdad"]

    malha["no_cadastro_seedf_2025"] = malha["ra_norm"].isin(nomes_seedf.index)
    malha["nome_seedf_2025"] = malha["ra_norm"].map(nomes_seedf)
    malha["na_pdad_2024"] = malha["ra_norm"].isin(nomes_pdad.index)
    malha["nome_pdad_2024"] = malha["ra_norm"].map(nomes_pdad)

    saida = malha[
        ["ra_nome", "ra_codigo", "ra_cira", "ra_areakm2", "geometry_type",
         "no_cadastro_seedf_2025", "nome_seedf_2025", "na_pdad_2024", "nome_pdad_2024"]
    ].rename(columns={"ra_nome": "ra_malha", "ra_areakm2": "area_km2"})
    saida = saida.sort_values("ra_cira")
    saida.to_csv(EXTRATO, index=False)

    print(f"\nmalha × cadastro SEEDF 2025: {int(saida['no_cadastro_seedf_2025'].sum())} de {len(saida)} RAs")
    print(f"malha × PDAD-A 2024:        {int(saida['na_pdad_2024'].sum())} de {len(saida)} RAs")
    so_malha = saida[~saida["no_cadastro_seedf_2025"] | ~saida["na_pdad_2024"]]
    if len(so_malha):
        print("\nRA na malha sem par nas fontes de educação:")
        print(so_malha[["ra_malha", "ra_codigo", "no_cadastro_seedf_2025", "na_pdad_2024"]].to_string(index=False))
    # A PDAD-A traz também 12 municípios goianos e 6 documentos que não são RA;
    # por isso a checagem reversa usa a interseção das duas fontes (as RAs do DF).
    faltam = sorted(set(nomes_seedf.index) & set(nomes_pdad.index) - set(malha["ra_norm"]))
    print(f"RA nas duas fontes e ausente da malha: {faltam or 'nenhuma'}")
    print(f"\nvalidação gravada em {EXTRATO.relative_to(INTERIM.parent)}")


if __name__ == "__main__":
    main()
