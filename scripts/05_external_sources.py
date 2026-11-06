"""Fontes externas: PDAD-A 2024 (IPEDF), INEP e malha territorial.

Entrada: `https://pdad.ipe.df.gov.br/api/upts_reports/` (PDFs por RA),
         páginas do INEP (Censo Escolar) e portais territoriais do GDF. Com
         `--offline`, só `data/raw/pdad/` e as notas do `MANIFEST`.
Saída:   `data/raw/pdad/*.pdf` + linhas no MANIFEST
         `data/interim/pdad_populacao.csv` (população por faixa etária, por RA)
         `data/interim/fontes_externas_status.csv` (o que abriu e o que não;
         não é gravado em `--offline`)
Idempotente: sim — PDF já baixado não é baixado de novo.

`--offline` reconstrói `pdad_populacao.csv` a partir dos PDFs já baixados e das
notas "relatório por RA: <nome>" do MANIFEST, sem tocar a API. É o que permite
rodar `06` e `10` em cópia limpa sem rede (V1).

Achado central: a PDAD-A 2024 publica faixas "até 4 anos", "5 a 9 anos", ... —
não existe faixa 0–3. Qualquer conta de creche usa, portanto, 0–4 anos, que
inclui crianças de 4 anos e superestima a demanda por creche.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

from _common import DOWNLOAD_DATE, INTERIM, MANIFEST, RAW, append_manifest, download, sha256

PDAD = "https://pdad.ipe.df.gov.br"
DEST = RAW / "pdad"
STATUS = INTERIM / "fontes_externas_status.csv"

SUFIXOS_ACEITOS = {".pdf", ".zip", ".xlsx", ".csv", ".ods"}


def sufixo_da_url(url: str, padrao: str = ".pdf") -> str:
    """Extensão real do arquivo, lida da URL.

    A PDAD serve PDFs por RA, mas também os microdados em `.zip` e o dicionário
    em `.xlsx`. Fixar `.pdf` no nome local já custou três arquivos com extensão
    errada (corrigido em 2026-10-23, ver `MANIFEST.md` → Correções).
    """
    sufixo = Path(url.split("?")[0]).suffix.lower()
    return sufixo if sufixo in SUFIXOS_ACEITOS else padrao


def eh_pdf(caminho: Path) -> bool:
    """Confere pelos bytes: extensão não decide o formato."""
    return caminho.open("rb").read(4) == b"%PDF"


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


def tabela_populacao(linhas: list[dict]) -> pd.DataFrame:
    """DataFrame de população por RA, com as duas colunas de procedência."""
    pop = pd.DataFrame(linhas)
    pop["fonte"] = "PDAD-A 2024, tabela 'População por faixa etária e sexo'"
    pop["faixa"] = "até 4 anos (não existe 0–3 na PDAD-A)"
    return pop


def populacao_offline() -> pd.DataFrame:
    """Reconstrói a tabela de população sem rede, do MANIFEST e de `data/raw/pdad`.

    A ponte entre arquivo e RA é a nota do MANIFEST ("relatório por RA: <nome>"),
    escrita por este script no download. Se um arquivo registrado não existe no
    disco, para — não completa a tabela com ausência silenciosa.
    """
    linhas = []
    for linha in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not linha.startswith("| `") or "IPEDF/PDAD-A 2024" not in linha:
            continue
        campos = [c.strip() for c in linha.strip().strip("|").split(" | ")]
        if len(campos) != 7 or not campos[6].startswith("relatório por RA:"):
            continue
        arquivo = DEST / campos[0].strip("`")
        if not arquivo.exists():
            raise SystemExit(f"--offline: {arquivo} está no MANIFEST e não no disco")
        nome = campos[6].split(":", 1)[1].strip()
        vals = ler_pdf(arquivo) if eh_pdf(arquivo) else {"pop_0_4": None, "pop_total": None}
        linhas.append({"ra_pdad": nome, "ra": norm(nome), **vals})
    if not linhas:
        raise SystemExit("--offline: nenhum relatório da PDAD-A no MANIFEST")
    return tabela_populacao(linhas)


def main(argv: list[str] | None = None) -> int:
    import json
    import urllib.request

    import argparse

    ap = argparse.ArgumentParser(description="Fontes externas: PDAD-A, INEP e malha.")
    ap.add_argument(
        "--offline",
        action="store_true",
        help="não acessa a rede: reconstrói pdad_populacao.csv do que está em data/raw",
    )
    args = ap.parse_args(argv)

    if args.offline:
        INTERIM.mkdir(parents=True, exist_ok=True)
        pop = populacao_offline()
        pop.to_csv(INTERIM / "pdad_populacao.csv", index=False)
        print(pop.to_string(index=False))
        print(f"\n--offline: {len(pop)} RA(s) em data/interim/pdad_populacao.csv; status da rede não foi tocado")
        return 0

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
        base = f"{DOWNLOAD_DATE}_pdad_a_2024_{re.sub(r'[^a-z0-9]+', '_', norm(nome).lower()).strip('_')}"
        arquivo = DEST / f"{base}{sufixo_da_url(url)}"
        legado = DEST / f"{base}.pdf"
        # arquivo já baixado em 2026-10-22 com extensão errada: reaproveita em vez
        # de baixar de novo (raw é imutável; o nome errado está em MANIFEST.md →
        # Correções)
        if not arquivo.exists() and legado.exists():
            arquivo = legado
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
        if eh_pdf(caminho):
            try:
                vals = ler_pdf(caminho)
            except Exception as exc:  # noqa: BLE001
                vals = {"pop_0_4": None, "pop_total": None}
                print(f"  falhou leitura {nome}: {exc}")
        else:
            vals = {"pop_0_4": None, "pop_total": None}
            print(f"  {caminho.name}: não é PDF (microdados/dicionário) — lido em 10_ingest_pdad.py")
        linhas.append({"ra_pdad": nome, "ra": norm(nome), **vals})
        print(f"  {nome[:40]:42} 0-4 anos: {vals['pop_0_4']}")

    append_manifest(registros)
    pop = tabela_populacao(linhas)
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
