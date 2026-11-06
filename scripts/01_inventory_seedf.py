"""Inventário dos conjuntos de dados da SEEDF no portal CKAN.

Entrada: API `https://data.se.df.gov.br/api/3/action/package_list` e
         `package_show?id=<nome>`.
Saída:   `data/interim/seedf_datasets.csv`  (um conjunto por linha)
         `data/interim/seedf_resources.csv` (um recurso por linha)
Idempotente: sim — apenas leitura da API e reescrita das duas saídas.
"""

from __future__ import annotations

import re

import pandas as pd

from _common import CKAN, INTERIM, get_json

YEAR = re.compile(r"(?:19|20)\d{2}")


def anos_do_recurso(nome: str, titulo: str) -> str:
    """Anos extraídos do nome do arquivo/recurso. É inferência, não metadado."""
    texto = f"{nome} {titulo}"
    anos = sorted({m.group(0) for m in YEAR.finditer(texto)})
    return ";".join(anos)


def main() -> None:
    INTERIM.mkdir(parents=True, exist_ok=True)
    nomes = get_json(f"{CKAN}/package_list")["result"]

    datasets, resources = [], []
    for nome in nomes:
        d = get_json(f"{CKAN}/package_show?id={nome}")["result"]
        rs = d.get("resources", [])
        formatos = sorted({r.get("format") for r in rs if r.get("format")})
        tem_dicionario = any(
            "dicion" in (r.get("name") or "").lower() for r in rs
        )
        anos = sorted(
            {a for r in rs for a in anos_do_recurso(r.get("name", ""), r.get("title") or "").split(";") if a}
        )
        datasets.append(
            {
                "dataset": d["name"],
                "titulo": d.get("title", ""),
                "descricao": (d.get("notes") or "").strip().replace("\n", " "),
                "modificado_em": (d.get("metadata_modified") or "")[:10],
                "n_recursos": len(rs),
                "formatos": ",".join(formatos),
                "bytes_total": sum(int(r.get("size") or 0) for r in rs),
                "anos_no_nome": ";".join(anos),
                "tem_dicionario": "sim" if tem_dicionario else "nao",
                # licença declarada no package_show: entra como está, sem inferir.
                "licenca_id": d.get("license_id") or "",
                "licenca_titulo": d.get("license_title") or "",
                "licenca_url": d.get("license_url") or "",
            }
        )
        for r in rs:
            resources.append(
                {
                    "dataset": d["name"],
                    "recurso": r.get("name", ""),
                    "formato": r.get("format"),
                    "bytes": int(r.get("size") or 0),
                    "url": r.get("url"),
                    "arquivo": (r.get("url") or "").split("/download/")[-1],
                    "anos_no_nome": anos_do_recurso(r.get("name", ""), r.get("title") or ""),
                    "modificado_em": (r.get("last_modified") or r.get("created") or "")[:10],
                    # a licença é do conjunto, repetida no recurso para o join ser direto
                    "licenca_id": d.get("license_id") or "",
                    "licenca_titulo": d.get("license_title") or "",
                    "licenca_url": d.get("license_url") or "",
                }
            )

    ds = pd.DataFrame(datasets).sort_values("dataset")
    rr = pd.DataFrame(resources).sort_values(["dataset", "formato", "arquivo"])
    ds.to_csv(INTERIM / "seedf_datasets.csv", index=False)
    rr.to_csv(INTERIM / "seedf_resources.csv", index=False)

    print(f"{len(ds)} conjuntos, {len(rr)} recursos")
    print(f"{ds['bytes_total'].sum() / 1e6:.1f} MB declarados no total")
    with pd.option_context("display.width", 250, "display.max_colwidth", 60):
        print(
            ds[["dataset", "n_recursos", "formatos", "bytes_total", "anos_no_nome", "tem_dicionario"]]
            .assign(bytes_total=lambda x: (x.bytes_total / 1e6).round(1))
            .to_string(index=False)
        )


if __name__ == "__main__":
    main()
