"""Utilidades compartilhadas pelos scripts do projeto.

Entrada: nenhuma (módulo importado).
Saída: funções de download, hash, detecção de formato e escrita do MANIFEST.
Idempotente: sim — nenhuma função aqui altera `data/raw/` sem checar o hash.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
MANIFEST = RAW / "MANIFEST.md"
CKAN = "https://data.se.df.gov.br/api/3/action"
DOWNLOAD_DATE = "2026-10-22"


# Nomes de Região Administrativa: cada fonte escreve de um jeito. A chave é a
# forma já normalizada (maiúscula, sem acento, espaço simples) e o valor é a
# forma canônica do projeto, a mesma do cadastro da SEEDF.
TROCAS_RA = {
    "SOL NASCENTE E POR DO SOL": "SOL NASCENTE / POR DO SOL",
    "SUDOESTE E OCTOGONAL": "SUDOESTE / OCTOGONAL",
    "SUDOESTE/OCTOGONAL": "SUDOESTE / OCTOGONAL",
    "SCIA/ESTRUTURAL": "SCIA",
    "AREA RURAL DO DF": "AREA RURAL",
    "DF AREA RURAL": "AREA RURAL",
    "DISTRITO FEDERAL (AREA RURAL)": "AREA RURAL",
}


def norm_ra(texto: str) -> str:
    """Normaliza nome de RA para a forma canônica usada nos cruzamentos.

    Maiúscula, sem acento, espaço simples, sem numeral romano de prefixo
    (`I - PLANO PILOTO` → `PLANO PILOTO`). As diferenças de grafia entre SEEDF,
    PDAD-A e GDF são resolvidas por `TROCAS_RA`; a tabela está em SCHEMA.md.
    """
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().upper()
    t = re.sub(r"^[IVXL]+\s*-\s*", "", t.strip())
    t = re.sub(r"\s+", " ", t).strip()
    return TROCAS_RA.get(t, t)


def get_json(url: str) -> dict:
    """GET simples com User-Agent, devolve o JSON decodificado."""
    req = urllib.request.Request(url, headers={"User-Agent": "prova-dos-nove/0.1"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, force: bool = False) -> tuple[Path, int]:
    """Baixa `url` para `dest`.

    Idempotente: se `dest` já existe, não baixa de novo (`force=True` rebaixa).
    A escrita é atômica (`dest.part` → `dest`), então a existência do destino
    implica download completo. Não há revalidação contra o servidor.
    Retorna (caminho, bytes).
    """
    if dest.exists() and not force:
        return dest, dest.stat().st_size
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "prova-dos-nove/0.1"})
    with urllib.request.urlopen(req, timeout=300) as resp, open(tmp, "wb") as fh:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    tmp.replace(dest)
    return dest, dest.stat().st_size


def detect_encoding(path: Path, probe: int = 1 << 22) -> str:
    """Descobre o encoding lendo bytes, sem assumir.

    Tenta utf-8 (com e sem BOM) e cai para latin-1, que nunca falha.
    """
    head = path.open("rb").read(probe)
    if head.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    try:
        head.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"


def detect_separator(path: Path, encoding: str) -> str:
    """Conta candidatos na primeira linha e devolve o separador mais frequente."""
    first = path.open("r", encoding=encoding, errors="replace").readline()
    counts = {",": first.count(","), ";": first.count(";"), "\t": first.count("\t")}
    sep = max(counts, key=counts.get)
    if counts[sep] == 0:
        return ","
    return sep



def append_manifest(rows: list[dict]) -> None:
    """Acrescenta linhas à tabela do MANIFEST.md, idempotente por sha256.

    `rows` trazem: arquivo, fonte, url, baixado_em, bytes, sha256, notas.
    Se o mesmo arquivo já está registrado com o mesmo hash, nada é escrito.
    """
    text = MANIFEST.read_text(encoding="utf-8")
    existing = set(re.findall(r"\| `([^`]+)` \|", text))
    new_lines = []
    for r in rows:
        name = r["arquivo"]
        if name in existing:
            continue
        new_lines.append(
            "| `{arquivo}` | {fonte} | {url} | {baixado_em} | {bytes} | `{sha256}` | {notas} |".format(
                arquivo=name, fonte=r["fonte"], url=r["url"], baixado_em=r["baixado_em"],
                bytes=r["bytes"], sha256=r["sha256"], notas=r.get("notas", ""),
            )
        )
    if not new_lines:
        return
    lines = text.splitlines()
    # A linha nova entra imediatamente depois da última linha da tabela. Inserir
    # "antes de ## Regras" punha a linha depois de ## Correções — foi assim que
    # as duas linhas do Censo caíram dentro daquela seção (ver MANIFEST.md,
    # Correções, 2026-11-06).
    ultima_tabela = None
    for i, line in enumerate(lines):
        if line.startswith("| `"):
            ultima_tabela = i
    if ultima_tabela is None:
        raise RuntimeError("MANIFEST.md sem tabela de arquivos (nenhuma linha '| `')")
    insert_at = ultima_tabela + 1
    lines[insert_at:insert_at] = new_lines
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
