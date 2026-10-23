"""Fontes externas: PDAD-A 2024 (IPEDF), INEP e malha territorial.

Entrada: `https://pdad.ipe.df.gov.br/api/upts_reports/` (PDFs por RA),
         páginas do INEP (Censo Escolar) e portais territoriais do GDF.
Saída:   `data/raw/pdad/*.pdf` + linhas no MANIFEST
         `data/interim/pdad_populacao.csv` (população por faixa etária, por RA)
         `data/interim/fontes_externas_status.csv` (o que abriu e o que não)
Idempotente: sim — PDF já baixado não é baixado de novo.

Achado central: a PDAD-A 2024 publica faixas "até 4 anos", "5 a 9 anos", ... —
não existe faixa 0–3. Qualquer conta de creche usa, portanto, 0–4 anos, que
inclui crianças de 4 anos e superestima a demanda por creche.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

from _common import DOWNLOAD_DATE, INTERIM, RAW, append_manifest, download, sha256

PDAD = "https://pdad.ipe.df.gov.br"
DEST = RAW / "pdad"
STATUS = INTERIM / "fontes_externas_status.csv"


def norm(texto: str) -> str:
    """Maiúsculas sem acento e sem numeral romano, para casar com a SEEDF."""
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().upper()
    t = re.sub(r"^[IVXL]+\s*-\s*", "", t.strip())
    return re.sub(r"\s+", " ", t)


def numero(txt: str) -> int:
    return int(txt.replace(".", "").replace(",", ""))


def ler_pdf(caminho) -> dict:
    """Extrai população total e 'até 4 anos' da tabela de faixa etária."""
    from pypdf import PdfReader

    texto = "\n".join((p.extract_text() or "") for p in PdfReader(caminho).pages)
    texto = texto.replace("\n", "")
    m4 = re.search(r"até\s*4\s*anos\s+([\d.]+)\s+[\d,]+\s+([\d.]+)\s+[\d,]+", texto)
    tot = re.search(r"Total\s+([\d.]+)\s+[\d,]+\s+([\d.]+)\s+[\d,]+", texto)
    return {
        "pop_0_4": numero(m4.group(1)) + numero(m4.group(2)) if m4 else None,
        "pop_total": numero(tot.group(1)) + numero(tot.group(2)) if tot else None,
    }


def main() -> None:
    import json
    import urllib.request

    STATUS.parent.mkdir(parents=True, exist_ok=True)
    status = []

    # --- PDAD-A 2024 -------------------------------------------------------
    req = urllib.request.Request(f"{PDAD}/api/upts_reports/", headers={"User-Agent": "prova-dos-nove/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        dados = json.loads(r.read().decode("utf-8"))

    relatorios = {}
    for bloco in dados.get("presentations", []):
        for ra in bloco.get("ras", []):
            if ra.get("report"):
                relatorios[ra["name"]] = PDAD + ra["report"]

    linhas, registros = [], []
    for nome, url in sorted(relatorios.items()):
        arquivo = DEST / f"{DOWNLOAD_DATE}_pdad_a_2024_{re.sub(r'[^a-z0-9]+', '_', norm(nome).lower()).strip('_')}.pdf"
        caminho, nbytes = download(url, arquivo)
        registros.append(
            {
                "arquivo": caminho.name,
                "fonte": "IPEDF/PDAD-A 2024",
                "url": url,
                "baixado_em": DOWNLOAD_DATE,
                "bytes": nbytes,
                "sha256": sha256(caminho),
                "notas": f"relatório por RA: {nome}",
            }
        )
        try:
            vals = ler_pdf(caminho)
        except Exception as exc:  # noqa: BLE001
            vals = {"pop_0_4": None, "pop_total": None}
            print(f"  falhou leitura {nome}: {exc}")
        linhas.append({"ra_pdad": nome, "ra": norm(nome), **vals})
        print(f"  {nome[:40]:42} 0-4 anos: {vals['pop_0_4']}")

    append_manifest(registros)
    pop = pd.DataFrame(linhas)
    pop["fonte"] = "PDAD-A 2024, tabela 'População por faixa etária e sexo'"
    pop["faixa"] = "até 4 anos (não existe 0–3 na PDAD-A)"
    pop.to_csv(INTERIM / "pdad_populacao.csv", index=False)
    status.append(
        {
            "fonte": "IPEDF/PDAD-A 2024",
            "recurso": "PDFs por RA",
            "resultado": "ok",
            "detalhe": f"{len(pop)} relatórios; faixa etária mais fina é 'até 4 anos'",
        }
    )

    # --- INEP -------------------------------------------------------------
    urls_inep = [
        "https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_2024.zip",
        "https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_2025_.zip",
    ]
    for u in urls_inep:
        try:
            req = urllib.request.Request(u, method="HEAD", headers={"User-Agent": "prova-dos-nove/0.1"})
            with urllib.request.urlopen(req, timeout=30) as r:
                tamanho = r.headers.get("Content-Length")
            status.append(
                {
                    "fonte": "INEP Censo Escolar",
                    "recurso": u.rsplit("/", 1)[-1],
                    "resultado": "ok",
                    "detalhe": f"Content-Length={tamanho}; não baixado (SEEDF cobre o DF)",
                }
            )
        except Exception as exc:  # noqa: BLE001
            status.append(
                {
                    "fonte": "INEP Censo Escolar",
                    "recurso": u.rsplit("/", 1)[-1],
                    "resultado": "inacessivel",
                    "detalhe": f"{type(exc).__name__}: {exc}",
                }
            )

    # --- malha territorial -------------------------------------------------
    for u in [
        "https://www.dados.df.gov.br/api/3/action/package_list",
        "https://www.geoportal.segov.df.gov.br/arcgis/rest/services?f=json",
        "https://www.sisdia.df.gov.br/",
    ]:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "prova-dos-nove/0.1"})
            with urllib.request.urlopen(req, timeout=20) as r:
                corpo = r.read(400).decode("utf-8", "replace").strip()
            status.append(
                {
                    "fonte": "malha RA",
                    "recurso": u,
                    "resultado": "respondeu sem catálogo CKAN/ArcGIS",
                    "detalhe": corpo[:120].replace("\n", " "),
                }
            )
        except Exception as exc:  # noqa: BLE001
            status.append(
                {"fonte": "malha RA", "recurso": u, "resultado": "inacessivel", "detalhe": str(exc)[:120]}
            )

    pd.DataFrame(status).to_csv(STATUS, index=False)
    print(pd.DataFrame(status).to_string(index=False))


if __name__ == "__main__":
    main()
