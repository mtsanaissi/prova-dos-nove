"""Download dos recursos prioritários da SEEDF para `data/raw/seedf/`.

Entrada: `data/interim/seedf_resources.csv` (gerado por 01_inventory_seedf.py).
Saída:   arquivos em `data/raw/seedf/` com prefixo de data, e linhas novas em
         `data/raw/MANIFEST.md` (URL, data, bytes, sha256).
Idempotente: sim — arquivo já presente com mesmo tamanho declarado não é
baixado de novo; MANIFEST não duplica registros.

Recortes deliberados, para não baixar 5,4 GB de duplicatas em JSON/XML/GeoJSON:
- só CSV (mais o XLSX de matrículas 2025, que não tem CSV);
- turmas e docentes: apenas os três anos mais recentes;
- `serie-historica-numero-de-matriculas-por-modalidade` não entra: só existe em
  JSON/XML e o grão é agregado, já coberto por `quantidade-de-matriculas`.
"""

from __future__ import annotations

import sys

import pandas as pd

from _common import DOWNLOAD_DATE, INTERIM, RAW, append_manifest, download, sha256

# anos a manter por conjunto (None = todos os CSV do conjunto)
ANOS_LIMITE = {
    "turmas-de-todas-as-modalidades-de-ensino-abrangendo-todas-as-redes-de-ensino-do-df": {2023, 2024, 2025},
    "total-de-docentes-abrangendo-todas-as-redes-de-ensino-do-df": {2023, 2024, 2025},
}

INCLUIR = [
    "relacao-de-unidades-escolares-abrangendo-todas-as-redes-de-ensino-do-distrito-federal",
    "quantidade-de-matriculas-das-modalidades-de-ensino-abrangendo-todas-as-redes-de-ensino-do-df",
    "dados-de-infraestrutura-abrangendo-todas-as-redes-de-ensino-df",
    "indicadores-educacionais-de-distorcao-idade-serie-abrangendo-todas-as-redes-de-ensino-do-df",
    "indice-de-desenvolvimento-da-educacao-basica-ideb-2019-2021-e-2023",
    "resultados-do-saeb-e-ideb-nas-unidades-de-ensino-da-rede-publica-do-distrito-federal",
    "situacao-do-aluno-serie-historica",
    "unidades-de-ensino-oferta-educacao-infantil-do-distrito-federal",
    "unidades-de-ensino-com-oferta-de-ensino-fundamental-na-rede-publica-de-ensino-do-distrito-federal",
    "unidades-de-ensino-com-oferta-de-ensino-medio-na-rede-publica-de-ensino-do-distrito-federal",
    "2023_educa_escola_infraestrutura_tecnologia_alunos_turno_salas",
    "turmas-de-todas-as-modalidades-de-ensino-abrangendo-todas-as-redes-de-ensino-do-df",
    "total-de-docentes-abrangendo-todas-as-redes-de-ensino-do-df",
]

DEST = RAW / "seedf"


def ano_do_arquivo(nome: str) -> int | None:
    import re

    achados = re.findall(r"(?:19|20)\d{2}", nome)
    return int(achados[-1]) if achados else None


def main() -> None:
    rr = pd.read_csv(INTERIM / "seedf_resources.csv", dtype=str, keep_default_na=False)
    rr = rr[rr.dataset.isin(INCLUIR)]
    rr = rr[rr.formato.isin(["CSV", "XLSX"])]

    rows, baixados = [], []
    for _, r in rr.iterrows():
        limite = ANOS_LIMITE.get(r.dataset)
        ano = ano_do_arquivo(r.arquivo)
        if limite and ano not in limite:
            continue
        destino = DEST / f"{DOWNLOAD_DATE}_{r.arquivo}"
        try:
            _, nbytes = download(r.url, destino)
        except Exception as exc:  # noqa: BLE001 - registrar e seguir
            print(f"FALHOU {r.arquivo}: {exc}", file=sys.stderr)
            continue
        h = sha256(destino)
        rows.append(
            {
                "arquivo": destino.name,
                "fonte": "SEEDF",
                "url": r.url,
                "baixado_em": DOWNLOAD_DATE,
                "bytes": nbytes,
                "sha256": h,
                "notas": r.dataset[:60],
            }
        )
        baixados.append((destino.name, nbytes))

    append_manifest(rows)
    total = sum(b for _, b in baixados)
    print(f"{len(baixados)} arquivos, {total / 1e6:.1f} MB")
    for nome, b in sorted(baixados):
        print(f"  {b / 1e6:8.2f} MB  {nome}")


if __name__ == "__main__":
    main()
