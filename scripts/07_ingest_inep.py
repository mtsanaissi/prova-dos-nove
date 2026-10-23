"""Ingestão dos arquivos da INEP baixados manualmente pelo navegador.

Entrada: arquivos depositados em `data/raw/inep/inbox/` (o navegador roda na
         máquina do mantenedor e grava em `~/Downloads`; o download por
         `urllib`/`curl` deste ambiente é bloqueado pela INEP).
Saída:   arquivos movidos para `data/raw/inep/<data>_<nome>`, com sha256, e
         linhas novas em `data/raw/MANIFEST.md`.
Idempotente: sim — arquivo já ingerido com o mesmo hash não é movido nem
registrado de novo; hash diferente gera segunda versão, preservando a primeira.

Uso:
    .venv/bin/python scripts/07_ingest_inep.py --check   # o que falta e onde baixar
    .venv/bin/python scripts/07_ingest_inep.py           # ingere o que estiver no inbox
    .venv/bin/python scripts/07_ingest_inep.py --de ~/Downloads

Nada é inferido sobre o conteúdo: esta etapa só registra procedência e hash. A
leitura, o recorte do DF e a conversão para parquet ficam em 08_profile_inep.py.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

import pandas as pd

from _common import DOWNLOAD_DATE, RAW, append_manifest, sha256

INEP = RAW / "inep"
INBOX = INEP / "inbox"
BASE = "https://download.inep.gov.br/"

# Catálogo do que interessa ao projeto, em ordem de prioridade. `acrescenta`
# diz o que o arquivo traz que os arquivos da SEEDF já baixados não trazem.
CATALOGO = [
    {
        "arquivo": "divulgacao_regioes_ufs_ideb_2025.zip",
        "url": BASE + "ideb/resultados/divulgacao_regioes_ufs_ideb_2025.zip",
        "fonte": "INEP/Ideb",
        "bytes_conhecidos": 757_760,
        "prioridade": 1,
        "acrescenta": "Ideb por UF e região: única forma de situar o DF no país",
    },
    {
        "arquivo": "nota_informativa_ideb_2025.pdf",
        "url": BASE + "ideb/resultados/nota_informativa_ideb_2025.pdf",
        "fonte": "INEP/Ideb",
        "bytes_conhecidos": 551_360,
        "prioridade": 1,
        "acrescenta": "metodologia e escala do Ideb 2025: condição para comparar com 2023",
    },
    {
        "arquivo": "divulgacao_brasil_ideb_2025.zip",
        "url": BASE + "ideb/resultados/divulgacao_brasil_ideb_2025.zip",
        "fonte": "INEP/Ideb",
        "bytes_conhecidos": 85_519,
        "prioridade": 2,
        "acrescenta": "Ideb do Brasil: a planilha de UF e regiões não traz a linha Brasil",
    },
    {
        "arquivo": "divulgacao_anos_iniciais_escolas_2025.zip",
        "url": BASE + "ideb/resultados/divulgacao_anos_iniciais_escolas_2025.zip",
        "fonte": "INEP/Ideb",
        "bytes_conhecidos": 112_185_922,
        "prioridade": 2,
        "acrescenta": "Ideb por escola nos anos iniciais (municipal, estadual e federal; a rede privada não é publicada)",
    },
    {
        "arquivo": "divulgacao_anos_finais_escolas_2025.zip",
        "url": BASE + "ideb/resultados/divulgacao_anos_finais_escolas_2025.zip",
        "fonte": "INEP/Ideb",
        "bytes_conhecidos": 80_112_586,
        "prioridade": 2,
        "acrescenta": "idem para os anos finais (a rede privada também não é publicada)",
    },
    {
        "arquivo": "divulgacao_ensino_medio_escolas_2025.zip",
        "url": BASE + "ideb/resultados/divulgacao_ensino_medio_escolas_2025.zip",
        "fonte": "INEP/Ideb",
        "bytes_conhecidos": 18_989_748,
        "prioridade": 2,
        "acrescenta": "idem para o ensino médio; lista escolas privadas, sem valor de Ideb depois de 2017",
    },
    {
        "arquivo": "divulgacao_ufs_Ensino_Medio_integrado_ideb_2025.xlsx",
        "url": BASE + "ideb/resultados/divulgacao_ufs_Ensino_Medio_integrado_ideb_2025.xlsx",
        "fonte": "INEP/Ideb",
        "bytes_conhecidos": 31_398,
        "prioridade": 2,
        "acrescenta": "ensino médio com o integrado à EPT por UF (rede estadual): testa o último lugar do DF no médio regular",
    },
    {
        "arquivo": "tx_rend_escolas_2025.zip",
        "url": BASE + "informacoes_estatisticas/indicadores_educacionais/2025/tx_rend_escolas_2025.zip",
        "fonte": "INEP/Taxas de Rendimento",
        "bytes_conhecidos": 66_870_247,
        "prioridade": 3,
        "acrescenta": "aprovação, reprovação e abandono por escola em todas as redes (a SEEDF só publica a rede estadual)",
    },
    {
        "arquivo": "TDI_2025_ESCOLAS.zip",
        "url": BASE + "informacoes_estatisticas/indicadores_educacionais/2025/TDI_2025_ESCOLAS.zip",
        "fonte": "INEP/Distorção idade-série",
        "bytes_conhecidos": 34_465_795,
        "prioridade": 3,
        "acrescenta": "distorção idade-série por escola em todas as redes",
    },
    {
        "arquivo": "tnr_escolas_2025.zip",
        "url": BASE + "informacoes_estatisticas/indicadores_educacionais/2025/tnr_escolas_2025.zip",
        "fonte": "INEP/Taxa de não-resposta",
        "bytes_conhecidos": 30_600_051,
        "prioridade": 3,
        "acrescenta": (
            "percentual de alunos sem informação de rendimento/movimento por escola, "
            "todas as redes; não separa não participação de resultado suprimido"
        ),
    },
]

POR_ARQUIVO = {c["arquivo"].lower(): c for c in CATALOGO}

IGNORAR = re.compile(r"(:zone\.identifier|\.crdownload|\.part|\.tmp)$", re.I)


def nome_normalizado(nome: str) -> str:
    """Remove sufixo de download repetido do navegador: 'arquivo (1).zip'."""
    caminho = Path(nome)
    base = re.sub(r"\s*\(\d+\)$", "", caminho.stem)
    return (base + caminho.suffix).lower()


def contem_em(dir_origem: Path) -> list[Path]:
    if not dir_origem.exists():
        return []
    arquivos = []
    for p in sorted(dir_origem.iterdir()):
        if not p.is_file() or IGNORAR.search(p.name):
            continue
        arquivos.append(p)
    return arquivos


def relatar_catalogo(ingeridos: set[str]) -> None:
    """Mostra o que falta, com URL e prioridade, para o download manual."""
    print("\nCatálogo (o que falta baixar no navegador):")
    linhas = []
    for c in CATALOGO:
        ok = c["arquivo"].lower() in ingeridos
        bytes_ = c["bytes_conhecidos"]
        tamanho = "?" if not bytes_ else (f"{bytes_ / 1e6:.1f} MB" if bytes_ >= 1e6 else f"{bytes_ / 1e3:.0f} KB")
        linhas.append(
            {
                "prio": c["prioridade"],
                "arquivo": c["arquivo"],
                "tamanho": tamanho,
                "situacao": "ok" if ok else "FALTA",
                "url": "" if ok else c["url"],
            }
        )
    print(pd.DataFrame(linhas).to_string(index=False))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--de", type=Path, default=INBOX, help="diretório onde os arquivos foram deixados")
    ap.add_argument("--check", action="store_true", help="só relatar, não mover nada")
    args = ap.parse_args()

    INEP.mkdir(parents=True, exist_ok=True)
    ingeridos = {
        p.name.split("_", 1)[1].lower()
        for p in INEP.iterdir()
        if p.is_file() and p.suffix.lower() in {".zip", ".pdf", ".xlsx"}
    }

    if args.check:
        relatar_catalogo(ingeridos)
        return 0

    origem = args.de.expanduser()
    if not origem.exists():
        print(f"diretório de origem não existe: {origem}", file=sys.stderr)
        relatar_catalogo(ingeridos)
        return 1

    novas, duplicadas, desconhecidas = [], [], []
    for p in contem_em(origem):
        canonico = nome_normalizado(p.name)
        meta = POR_ARQUIVO.get(canonico)
        if meta is None:
            desconhecidas.append(p.name)
            continue
        destino = INEP / f"{DOWNLOAD_DATE}_{meta['arquivo']}"
        h = sha256(p)
        if destino.exists():
            if sha256(destino) == h:
                duplicadas.append((p.name, "mesmo hash: já ingerido"))
                continue
            destino = INEP / f"{DOWNLOAD_DATE}_{Path(meta['arquivo']).stem}_v2{Path(meta['arquivo']).suffix}"
            if destino.exists() and sha256(destino) == h:
                duplicadas.append((p.name, "mesmo hash: já ingerido (v2)"))
                continue
        shutil.move(str(p), destino)
        novas.append(
            {
                "arquivo": destino.name,
                "fonte": meta["fonte"],
                "url": meta["url"],
                "baixado_em": DOWNLOAD_DATE,
                "bytes": destino.stat().st_size,
                "sha256": sha256(destino),
                "notas": f"download manual pelo navegador; {meta['acrescenta']}",
            }
        )
        ingeridos.add(meta["arquivo"].lower())

    if novas:
        append_manifest(novas)
        print(f"{len(novas)} arquivo(s) ingerido(s) e registrado(s) no MANIFEST:")
        for n in novas:
            print(f"  {n['bytes'] / 1e6:8.2f} MB  {n['arquivo']}")

    for nome, motivo in duplicadas:
        print(f"já ingerido, nada a fazer: {nome} ({motivo})")

    if desconhecidas:
        print("\nFora do catálogo — não movidos. Diga o que são antes de entrar:", file=sys.stderr)
        for n in desconhecidas:
            print(f"  {n}", file=sys.stderr)

    relatar_catalogo(ingeridos)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
