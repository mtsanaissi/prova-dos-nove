"""Recorte do DF dos microdados do Censo Escolar da Educação Básica (INEP).

Entrada: `data/raw/inep/2026-10-23_microdados_censo_escolar_2024.zip` e
         `..._microdados_censo_escolar_2025_.zip`, abertos em memória
         (`zipfile`) e lidos em streaming; `data/raw` não é extraído.
Saída:   `data/interim/inep/censo_escola_df.parquet` (uma linha por escola × ano,
         com a matrícula por etapa) e `data/interim/inep/censo_metodo.csv` (as
         checagens desta leitura). O log imprime linhas nacionais × DF e o
         tamanho do que foi gravado.
Idempotente: sim — reescreve o parquet a partir do raw; não acessa a rede.

Por que a leitura é assim
-------------------------
Desde a edição de 2024 a INEP publica os microdados **por estabelecimento**:
o manual do usuário diz que as bases foram "dimensionadas ao nível de escolas"
e trazem matrícula por etapa, turno, tempo integral, sexo, cor/raça e faixa
etária. Não há linha de aluno, nem `DT_NASCIMENTO`, nem idade simples — então
nada de pessoa pode sair daqui, e a idade simples continua vindo da série da
SEEDF, que republica o Censo (ver `SCHEMA.md`).

Os dois anos têm arquivos e nomes de coluna diferentes: 2024 vem em
`microdados_ed_basica_2024.csv` (426 colunas, separador `;`, latin-1); 2025 vem
em `dados/Tabela_Matricula_2025_V2.csv` (263 colunas, `;`, latin-1) e não tem
`QT_MAT_MED_CT` — o médio integrado virou `QT_MAT_MED_IFTP_CT`, que não é o
mesmo recorte. Por isso as colunas pedidas são declaradas por ano e a ausência
é registrada, não preenchida.
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import pandas as pd

from _common import INTERIM, RAW

INEP = RAW / "inep"
DEST = INTERIM / "inep"

# TP_DEPENDENCIA -> rótulo. É o mesmo vocabulário que a TDI e a TNR usam
# (`NO_DEPENDENCIA`), para os joins de 06_analysis.py não precisarem de tradução.
REDE = {"1": "Federal", "2": "Estadual", "3": "Municipal", "4": "Privada"}

IDENT = [
    "CO_ENTIDADE",
    "NO_ENTIDADE",
    "CO_UF",
    "SG_UF",
    "CO_MUNICIPIO",
    "TP_DEPENDENCIA",
    "TP_CATEGORIA_ESCOLA_PRIVADA",
]

# Matrícula por etapa e por faixa etária: as colunas que 2024 e 2025 têm em
# comum. `QT_MAT_BAS` é o total da educação básica e não é a soma de EI+EF+EM
# (inclui EJA, técnico concomitante/subsequente e FIC; ver o dicionário).
MATRICULA = [
    "QT_MAT_BAS",
    "QT_MAT_INF",
    "QT_MAT_INF_CRE",
    "QT_MAT_INF_PRE",
    "QT_MAT_FUND",
    "QT_MAT_FUND_AI",
    "QT_MAT_FUND_AF",
    "QT_MAT_MED",
    "QT_MAT_MED_PROP",
    "QT_MAT_MED_NM",
    "QT_MAT_PROF_TEC_CONC",
    "QT_MAT_PROF_TEC_SUBS",
    "QT_MAT_PROF_FIC_CONC",
    "QT_MAT_EJA",
    "QT_MAT_ESP",
    "QT_MAT_BAS_0_3",
    "QT_MAT_BAS_4_5",
    "QT_MAT_BAS_6_10",
    "QT_MAT_BAS_11_14",
    "QT_MAT_BAS_15_17",
    "QT_MAT_BAS_18_MAIS",
]

POR_ANO = {
    2024: {
        "fragmento": "microdados_ed_basica_2024",
        "colunas": IDENT + ["TP_SITUACAO_FUNCIONAMENTO"] + MATRICULA + ["QT_MAT_MED_CT"],
        # colunas que existem em 2025 e não existem aqui
        "ausentes_no_arquivo": [
            "QT_MAT_BAS_0_3_REF_31_03",
            "QT_MAT_BAS_4_5_REF_31_03",
        ],
    },
    2025: {
        "fragmento": "Tabela_Matricula_2025",
        # a Tabela de Matrícula de 2025 não tem situação de funcionamento: ela
        # está na Tabela de Escola, que não é lida aqui (infraestrutura e
        # situação já vêm dos arquivos da SEEDF).
        "colunas": IDENT + MATRICULA
        + ["QT_MAT_BAS_0_3_REF_31_03", "QT_MAT_BAS_4_5_REF_31_03"],
        "ausentes_no_arquivo": ["TP_SITUACAO_FUNCIONAMENTO", "QT_MAT_MED_CT"],
    },
}

# colunas do parquet, na ordem; o que não existe no arquivo do ano entra como
# ausente (NA) — nunca como zero.
COLUNAS_SAIDA = (
    IDENT
    + ["TP_SITUACAO_FUNCIONAMENTO"]
    + MATRICULA
    + ["QT_MAT_MED_CT", "QT_MAT_BAS_0_3_REF_31_03", "QT_MAT_BAS_4_5_REF_31_03"]
)

# O que o manual e os arquivos não trazem. Registrado, não inferido.
NAO_EXISTE = [
    ("linha de aluno", "a partir de 2024 a publicação é por estabelecimento"),
    ("DT_NASCIMENTO", "não há data de nascimento em nenhuma das duas bases"),
    ("idade simples", "só faixa etária (0-3, 4-5, 6-10, 11-14, 15-17, 18+)"),
]

# Âncoras já publicadas no projeto. Se a leitura não as reproduzir, o problema é
# a leitura — o script para em vez de seguir com um número torto.
ANCORAS = {
    2024: {"QT_MAT_INF_CRE": 40_851, "escolas_com_matricula": 1_284},
    2025: {"QT_MAT_INF_CRE": 42_582, "escolas_com_matricula": 1_291},
}
TOLERANCIA = 0.0  # âncora conhecida tem de fechar exata (L-06)


def localizar(ano: int) -> Path:
    """Acha o zip do ano em `data/raw/inep`, sem adivinhar o nome."""
    achados = sorted(INEP.glob(f"*microdados_censo_escolar_{ano}*.zip"))
    if len(achados) != 1:
        raise FileNotFoundError(
            f"esperava 1 zip do Censo {ano} em {INEP}, achei {len(achados)}: "
            + ", ".join(p.name for p in achados)
        )
    return achados[0]


def membro_unico(zf: zipfile.ZipFile, fragmento: str) -> str:
    """O CSV cujo nome contém `fragmento`; erro se houver zero ou mais de um."""
    achados = [
        n
        for n in zf.namelist()
        if n.lower().endswith(".csv") and fragmento.lower() in Path(n).name.lower()
    ]
    if len(achados) != 1:
        raise RuntimeError(
            f"esperava 1 CSV com '{fragmento}' no zip, achei {len(achados)}: "
            + ", ".join(achados)
        )
    return achados[0]


def separador_do_cabecalho(zf: zipfile.ZipFile, membro: str) -> str:
    """Descobre o separador contando candidatos nos primeiros bytes (só ASCII)."""
    with zf.open(membro) as fh:
        head = fh.read(1 << 16)
    primeiro = head.split(b"\n", 1)[0].decode("latin-1")
    contagem = {";": primeiro.count(";"), ",": primeiro.count(","), "\t": primeiro.count("\t")}
    sep = max(contagem, key=contagem.get)
    if contagem[sep] == 0:
        raise RuntimeError(f"cabeçalho sem separador reconhecível em {membro}")
    return sep


def ler_ano(ano: int) -> tuple[pd.DataFrame, dict]:
    """Lê o zip do ano em streaming e devolve (recorte do DF, métricas).

    O encoding não é assumido: a primeira passagem tenta utf-8 e, se o arquivo
    tiver qualquer byte fora de utf-8 (os dois têm: latin-1 nos nomes), a
    leitura recomeça em latin-1. A falha é imediata, então a tentativa errada
    custa pouco.
    """
    caminho = localizar(ano)
    config = POR_ANO[ano]
    with zipfile.ZipFile(caminho) as zf:
        membro = membro_unico(zf, config["fragmento"])
        sep = separador_do_cabecalho(zf, membro)

        for enc in ("utf-8-sig", "latin-1"):
            try:
                linhas_df, nacionais, cabecalho = _varrer(zf, membro, enc, sep, config)
                break
            except UnicodeDecodeError:
                continue
        else:  # pragma: no cover - latin-1 decodifica qualquer byte
            raise RuntimeError(f"{ano}: não foi possível decodificar {membro}")

    df = pd.DataFrame(linhas_df, columns=config["colunas"])
    df.insert(0, "ano", ano)
    for c in COLUNAS_SAIDA:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[["ano"] + COLUNAS_SAIDA]

    # a chave tem de ser única: se não for, o recorte está errado
    duplicadas = df["CO_ENTIDADE"].duplicated().sum()
    if duplicadas:
        raise RuntimeError(f"{ano}: {duplicadas} CO_ENTIDADE repetidos no recorte do DF")

    df["CO_ENTIDADE"] = df["CO_ENTIDADE"].str.strip()
    df["rede"] = df["TP_DEPENDENCIA"].map(REDE)
    if df["rede"].isna().any():
        raise RuntimeError(f"{ano}: TP_DEPENDENCIA fora do dicionário")

    for c in df.columns:
        if c.startswith("QT_"):
            # vazio é ausente (escola sem matrícula declarada), não zero
            df[c] = pd.to_numeric(df[c], errors="coerce")

    metricas = {
        "ano": ano,
        "arquivo": caminho.name,
        "membro": membro,
        "encoding": enc,
        "separador": sep,
        "colunas_no_arquivo": len(cabecalho),
        "linhas_nacionais": nacionais,
        "linhas_df": len(df),
        "pct_df_do_nacional": round(100 * len(df) / nacionais, 2),
        "escolas_df": int(df["CO_ENTIDADE"].nunique()),
        "colunas_ausentes": "|".join(config["ausentes_no_arquivo"]),
    }
    return df, metricas


def _varrer(
    zf: zipfile.ZipFile, membro: str, enc: str, sep: str, config: dict
) -> tuple[list[dict], int, list[str]]:
    """Uma passagem pelo CSV, guardando só as linhas do DF."""
    with zf.open(membro) as fh:
        texto = io.TextIOWrapper(fh, encoding=enc, newline="")
        leitor = csv.reader(texto, delimiter=sep)
        cabecalho = next(leitor)
        faltando = [c for c in config["colunas"] if c not in cabecalho]
        if faltando:
            raise RuntimeError(
                f"colunas pedidas que não existem no arquivo: {faltando}. "
                "O esquema mudou; confira o dicionário antes de seguir."
            )
        posicao = {c: i for i, c in enumerate(cabecalho)}
        colunas_lidas = [posicao[c] for c in config["colunas"]]
        i_uf = posicao["CO_UF"]

        linhas: list[dict] = []
        nacionais = 0
        for bruto in leitor:
            nacionais += 1
            if bruto[i_uf] != "53":
                continue
            linhas.append({c: bruto[i] for c, i in zip(config["colunas"], colunas_lidas)})
    return linhas, nacionais, cabecalho


def checar(df: pd.DataFrame, ano: int) -> list[dict]:
    """Checagens de conteúdo, sem interromper: devolve todas as linhas."""
    linhas = []
    for coluna, esperado in ANCORAS[ano].items():
        if coluna == "escolas_com_matricula":
            # 2024 tem 1.360 linhas de escola no DF, mas 76 delas com a célula de
            # matrícula vazia (escola sem aluno declarado). A âncora é o número de
            # escolas com matrícula, que é o universo da série da SEEDF.
            valor = int(df["QT_MAT_BAS"].notna().sum())
        else:
            valor = float(df[coluna].sum())
        desvio = abs(valor - esperado) / esperado if esperado else 0.0
        linhas.append(
            {
                "checagem": f"ancora_{ano}_{coluna}",
                "valor": valor,
                "esperado": esperado,
                "desvio_pct": round(100 * desvio, 3),
                "resultado": "ok" if desvio <= TOLERANCIA else "FALHOU",
            }
        )

    # as faixas etárias têm de particionar QT_MAT_BAS, escola por escola (entre
    # as que declaram matrícula: a célula vazia é ausência, não zero)
    faixas = [
        "QT_MAT_BAS_0_3",
        "QT_MAT_BAS_4_5",
        "QT_MAT_BAS_6_10",
        "QT_MAT_BAS_11_14",
        "QT_MAT_BAS_15_17",
        "QT_MAT_BAS_18_MAIS",
    ]
    com_matricula = df[df["QT_MAT_BAS"].notna()]
    soma = com_matricula[faixas].sum(axis=1, skipna=True)
    iguais = int((soma == com_matricula["QT_MAT_BAS"]).sum())
    linhas.append(
        {
            "checagem": f"faixas_etarias_somam_bas_{ano}",
            "valor": iguais,
            "esperado": len(com_matricula),
            "desvio_pct": round(100 * (len(com_matricula) - iguais) / len(com_matricula), 2),
            "resultado": "ok" if iguais == len(com_matricula) else "divergente",
        }
    )

    sem_matricula = int(df["QT_MAT_BAS"].isna().sum())
    linhas.append(
        {
            "checagem": f"escolas_sem_matricula_declarada_{ano}",
            "valor": sem_matricula,
            "esperado": "",
            "desvio_pct": "",
            "resultado": "ausente (célula vazia), não zero",
        }
    )

    # o que a publicação não tem
    for nome, motivo in NAO_EXISTE:
        linhas.append(
            {
                "checagem": f"nao_existe_{nome.replace(' ', '_')}_{ano}",
                "valor": "",
                "esperado": "",
                "desvio_pct": "",
                "resultado": motivo,
            }
        )
    return linhas


def validar(linhas: list[dict], ano: int) -> None:
    """Levanta RuntimeError se alguma âncora falhou.

    A mensagem não culpa a leitura antes de conferir o arquivo: o primeiro
    suspeito é o zíper ter mudado no servidor (L-05, L-06).
    """
    falhas = [l for l in linhas if l["resultado"] == "FALHOU"]
    if not falhas:
        return
    pior = max(falhas, key=lambda l: float(l["desvio_pct"] or 0))
    raise RuntimeError(
        f"{ano}: {pior['checagem']} = {pior['valor']:,.0f}, esperado "
        f"{pior['esperado']:,} (desvio {pior['desvio_pct']:.3f}%). Antes de culpar "
        "a leitura, confira o sha256 do zip contra o MANIFEST: se o arquivo mudou "
        "no servidor, a leitura pode estar certa."
    )


def conferir(df: pd.DataFrame, ano: int) -> list[dict]:
    """checar + validar. É o que o --autoteste usa para provar que o script para."""
    linhas = checar(df, ano)
    validar(linhas, ano)
    return linhas


def autoteste(argv: list[str]) -> int:
    """Prova que uma âncora perturbada faz o script parar, e que a intacta passa.

    Entrada: `data/interim/inep/censo_escola_df.parquet` já gravado.
    Saída:   código 0 se o negativo passou (RuntimeError na âncora perturbada) e
             o positivo também; 1 se a perturbação passou batida.
    Idempotente: sim — só lê.
    """
    arq = DEST / "censo_escola_df.parquet"
    if not arq.exists():
        raise SystemExit("--autoteste: falta o parquet; rode o script uma vez")
    df = pd.read_parquet(arq)
    df = df[df["ano"] == 2025].copy()
    conferir(df, 2025)
    print("ok: dataframe intacto passa nas âncoras")
    for coluna in ANCORAS[2025]:
        if coluna == "escolas_com_matricula":
            continue
        perturbado = df.copy()
        perturbado[coluna] = pd.to_numeric(perturbado[coluna]).astype(float)
        perturbado.iloc[0, perturbado.columns.get_loc(coluna)] += 1
        try:
            conferir(perturbado, 2025)
        except RuntimeError as exc:
            print(f"ok: {coluna} + 1 → RuntimeError — {str(exc)[:110]}")
            return 0
    print("FALHA: nenhuma âncora perturbada levantou RuntimeError")
    return 1


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Recorte do DF dos microdados do Censo Escolar.")
    ap.add_argument(
        "--autoteste",
        action="store_true",
        help="prova que uma âncora perturbada faz o script parar (não grava nada)",
    )
    args = ap.parse_args(argv)
    if args.autoteste:
        return autoteste(argv)

    DEST.mkdir(parents=True, exist_ok=True)
    partes, metricas = [], []
    for ano in sorted(POR_ANO):
        df, m = ler_ano(ano)
        partes.append(df)
        linhas_ano = checar(df, ano)
        metricas.extend(linhas_ano)
        # grava antes de validar: se a âncora falhar, a linha "FALHOU" já está no
        # CSV, em vez de se perder com a exceção (era o defeito de L-06)
        pd.DataFrame(metricas).to_csv(DEST / "censo_metodo.csv", index=False)
        validar(linhas_ano, ano)
        print(
            f"{ano}: {m['linhas_nacionais']:,} linhas nacionais, {m['linhas_df']:,} do DF "
            f"({m['pct_df_do_nacional']}%) | {m['colunas_no_arquivo']} colunas, "
            f"{m['encoding']}, sep '{m['separador']}'"
        )

    censo = pd.concat(partes, ignore_index=True)
    destino = DEST / "censo_escola_df.parquet"
    censo.to_parquet(destino, index=False)

    tamanho = destino.stat().st_size
    metodo = pd.DataFrame(metricas)
    metodo = pd.concat(
        [
            metodo,
            pd.DataFrame(
                [
                    {
                        "checagem": "saida_censo_escola_df",
                        "valor": len(censo),
                        "esperado": len(censo),
                        "desvio_pct": 0,
                        "resultado": f"{tamanho:,} B em {destino.name}",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    metodo.to_csv(DEST / "censo_metodo.csv", index=False)

    print(f"\ngravado: {destino.relative_to(INTERIM.parent)}  {len(censo):,} linhas, {tamanho:,} B")
    print("  (nenhuma linha de aluno: uma linha por escola × ano)")
    print("\nchecagens:")
    print(metodo.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
