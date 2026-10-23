"""Perfil dos arquivos da SEEDF e conversão para parquet.

Entrada: arquivos em `data/raw/seedf/`.
Saída:   `data/interim/seedf/<familia>_<ano>.parquet`
         `data/interim/profile_files.csv`    (um arquivo por linha)
         `data/interim/profile_columns.csv`  (uma coluna por linha)
Idempotente: sim — reescreve as saídas a partir dos brutos.

Nada é convertido para número aqui: tudo entra como texto para não colapsar
zero, ausente e "não aplicável". A conversão acontece na análise.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

import pandas as pd

from _common import INTERIM, RAW, detect_encoding, detect_separator

SEEDF = RAW / "seedf"
OUT = INTERIM / "seedf"

# marcadores que aparecem na linha de nomes de variável
VAR_TOKENS = {
    "NU_ANO_CENSO", "CO_ENTIDADE", "CO_REDE", "SG_UF", "Cód_Inep", "cod_inep",
    "Ano", "CO_MUNICIPIO", "Rede", "NO_ENTIDADE",
}


def sem_prefixo(nome: str) -> str:
    """Remove o prefixo de data de download (`2026-10-22_`)."""
    return re.sub(r"^\d{4}-\d{2}-\d{2}_", "", nome)


def familia(nome: str) -> str:
    n = sem_prefixo(nome).lower()
    if "dicionario" in n:
        return "dicionario"
    if "infraestrutura_tecnologia" in n:
        return "tecnologia"
    if "situacao" in n:
        return "situacao"
    if "docente" in n:
        return "docentes"
    if "turma" in n:
        return "turmas"
    if "matricula" in n:
        return "matriculas"
    if "relatorio_escolas" in n:
        return "escolas"
    if "relatorio_matriculas" in n:
        return "matriculas"
    if "relatorio_infraestrutura" in n:
        return "infraestrutura"
    if "relatorio_distorcao" in n:
        return "distorcao"
    if "relatorio_situacao" in n:
        return "situacao"
    if "relatorio_docentes" in n:
        return "docentes"
    if "educa_dados_turma" in n:
        return "turmas"
    if n.startswith("ideb_"):
        return "ideb_serie"
    if n.startswith("planilha_ideb"):
        return "ideb_planilha"
    if n.startswith("lista_unidades"):
        return "unidades_ei"
    if "unidades-ef" in n or "unidades-em" in n:
        return "unidades_oferta"
    return "outros"


def ano_do_arquivo(nome: str) -> str:
    anos = re.findall(r"(?:19|20)\d{2}", sem_prefixo(nome))
    return anos[-1] if anos else "unico"


def header_row(path: Path, enc: str, sep: str) -> int:
    """Descobre se há linha de título acima do cabeçalho."""
    txt = path.open("r", encoding=enc, errors="replace").read(1 << 16)
    rows = list(csv.reader(io.StringIO(txt), delimiter=sep))[:2]
    if not rows:
        return 0
    primeira = [c.strip() for c in rows[0] if c.strip()]
    if not primeira:
        return 1
    if VAR_TOKENS & set(primeira):
        return 0
    return 1


def limpar_colunas(cols: list[str]) -> list[str]:
    vistos: dict[str, int] = {}
    saida = []
    for i, c in enumerate(cols):
        nome = str(c).strip() or f"col_{i}"
        if nome in vistos:
            vistos[nome] += 1
            nome = f"{nome}_{vistos[nome]}"
        else:
            vistos[nome] = 0
        saida.append(nome)
    return saida


def carregar(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".xlsx":
        df = pd.read_excel(path, dtype=str, keep_default_na=False, na_values=[""])
        df.columns = limpar_colunas(list(df.columns))
        return df
    enc = detect_encoding(path)
    sep = detect_separator(path, enc)
    h = header_row(path, enc, sep)
    df = pd.read_csv(
        path, dtype=str, encoding=enc, sep=sep, header=h,
        keep_default_na=False, na_values=[""], engine="python",
        on_bad_lines="warn",
    )
    df.columns = limpar_colunas(list(df.columns))
    return df


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    perfis, colunas = [], []

    for path in sorted(list(SEEDF.glob("*.csv")) + list(SEEDF.glob("*.xlsx"))):
        fam = familia(path.name)
        ano = ano_do_arquivo(path.name)
        try:
            df = carregar(path)
        except Exception as exc:  # noqa: BLE001
            print(f"ERRO ao ler {path.name}: {exc}")
            perfis.append({"arquivo": path.name, "familia": fam, "ano": ano, "erro": str(exc)[:200]})
            continue

        # nome único: família + nome original (vários arquivos da mesma família/ano
        # existem, ex. unidades-ef-anos-iniciais e unidades-em, ambos 2023)
        base = re.sub(r"[^a-z0-9]+", "_", sem_prefixo(path.stem).lower()).strip("_")
        destino = OUT / f"{fam}__{base}.parquet"
        df.to_parquet(destino, index=False)

        entidade_col = next(
            (
                c
                for c in ("CO_ENTIDADE", "cod_inep", "Cód_Inep", "Código INEP", "Cód. Inep")
                if c in df
            ),
            None,
        )
        n_ent = df[entidade_col].nunique() if entidade_col else None
        dups = (
            int(df[entidade_col].duplicated().sum()) if entidade_col else None
        )
        anos = sorted(df["NU_ANO_CENSO"].dropna().unique()) if "NU_ANO_CENSO" in df else []
        perfis.append(
            {
                "arquivo": path.name,
                "familia": fam,
                "ano_no_nome": ano,
                "linhas": len(df),
                "colunas": df.shape[1],
                "ano_no_dado": ";".join(map(str, anos)),
                "coluna_entidade": entidade_col or "",
                "entidades_distintas": n_ent if n_ent is not None else "",
                "linhas_por_entidade_duplicadas": dups if dups is not None else "",
                "cols_100_nulas": int((df.isna().mean() == 1).sum()),
                "parquet": destino.name,
            }
        )
        for c in df.columns:
            s = df[c]
            colunas.append(
                {
                    "arquivo": path.name,
                    "coluna": c,
                    "pct_nulo": round(float(s.isna().mean()) * 100, 2),
                    "n_distintos": int(s.nunique()),
                    "exemplo": (s.dropna().iloc[0] if s.notna().any() else ""),
                }
            )
        print(f"{path.name[:55]:57} {len(df):>7} linhas × {df.shape[1]:>3} col  {fam}")

    pd.DataFrame(perfis).to_csv(INTERIM / "profile_files.csv", index=False)
    pd.DataFrame(colunas).to_csv(INTERIM / "profile_columns.csv", index=False)
    print(f"\nperfil gravado: {len(perfis)} arquivos, {len(colunas)} colunas")


if __name__ == "__main__":
    main()
