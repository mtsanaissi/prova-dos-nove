"""Ingestão dos microdados da PDAD-A 2024 (IPEDF): leitura, validação e agregados.

Entrada: `data/raw/pdad/2026-10-22_pdad_a_2024_base_de_morador.pdf`,
         `..._base_de_domicilios.pdf` e `..._dicionario_de_dados.pdf`. A extensão
         está errada (o 05 nomeava tudo `.pdf`): os dois primeiros são ZIP com
         `moradores.csv` e `domicilios.csv`; o terceiro é XLSX. O conteúdo é
         detectado pelos primeiros bytes, nunca pela extensão.
Saída:   `data/interim/pdad/`: população por idade e por faixa, frequência
         escolar, fluxo RA de moradia → RA de estudo, entorno goiano, e as
         conferências (`pdad_conferencia.csv`, `pdad_metodo.csv`).
         Nenhuma linha individual e nenhum identificador é gravado: o grão de
         tudo que sai daqui é Região Administrativa (ou município goiano).
Idempotente: sim — reescreve as saídas a partir do raw; não acessa a rede e não
         escreve em `data/raw/`.

Uso:
    .venv/bin/python scripts/10_ingest_pdad.py --check   # o que existe e se lê
    .venv/bin/python scripts/10_ingest_pdad.py           # reescreve os agregados

Decisões que o dado impõe (ver SCHEMA.md):
- `peso_mor` e `peso_dom` são pesos de expansão. A variância é aproximada
  (Kish para proporções, com reposição para totais): o arquivo não traz estrato
  nem unidade primária, então o intervalo é um limite inferior de largura.
- Sentinela não é valor: `88888` = não sabe, `99999` = não se aplica. Nunca
  entram em soma, média ou contagem.
- `idade_calculada` é a idade na entrevista. O critério de matrícula é 31/03,
  então a idade em 31/03/2024 é calculada de `E02_1` em memória e a data de
  nascimento é descartada antes de qualquer escrita.
- Renda domiciliar não é usada nesta versão: `renda_domiciliar_pc_r` é 99999
  (não se aplica) em 78,7% dos domicílios, e a cobertura varia de 6,7% a 33,9%
  por RA — não é ausência aleatória, e média sobre ela seria um número falso.
"""

from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from _common import INTERIM, RAW, norm_ra

PDAD = RAW / "pdad"
DEST = INTERIM / "pdad"

# Códigos de localidade da PDAD: 5301–5336 são as 35 RAs + Área Rural do DF;
# 5241–5252 são os 12 municípios goianos da área de influência. Os nomes vêm do
# anexo_1 do dicionário — não são digitados aqui.
DF_PREFIXO = 53
GO_PREFIXO = 52

SENTINELAS = {88888: "não sabe", 99999: "não se aplica"}
DATA_REFERENCIA = pd.Timestamp("2024-03-31")

FAIXAS = [
    (0, 3, "0-3"),
    (4, 5, "4-5"),
    (6, 10, "6-10"),
    (11, 14, "11-14"),
    (15, 17, "15-17"),
    (18, 24, "18-24"),
    (25, 120, "25+"),
]

COLUNAS_DESCARTADAS = [
    # identificadores diretos e de vínculo
    "morador_id", "A01nficha", "index", "E04_1_1", "E08_1",
    # geografia mais fina que a RA (setor/distrito identifica em RA pequena)
    "setor_distrito",
    # data de nascimento: usada em memória para a idade em 31/03
    "E02_1", "E02_2", "E02_3",
]


# ---------------------------------------------------------------- leitura bruta
def localizar(prefixo: str) -> Path:
    """Acha o arquivo da PDAD por prefixo, aceitando extensão trocada."""
    achados = sorted(PDAD.glob(f"*{prefixo}*"))
    if not achados:
        raise FileNotFoundError(f"sem arquivo em {PDAD} para *{prefixo}*")
    return achados[0]


def tipo_real(caminho: Path) -> str:
    """Detecta zip/xlsx/pdf pelos primeiros bytes."""
    cabeca = caminho.open("rb").read(4)
    if cabeca.startswith(b"PK\x03\x04"):
        with zipfile.ZipFile(caminho) as z:
            nomes = z.namelist()
        return "xlsx" if any(n.startswith("xl/") for n in nomes) else "zip"
    if cabeca.startswith(b"%PDF"):
        return "pdf"
    raise ValueError(f"{caminho.name}: formato não reconhecido ({cabeca!r})")


def ler_csv_do_zip(caminho: Path, membro: str) -> pd.DataFrame:
    """Lê um CSV dentro do ZIP em memória, sem extrair para o disco."""
    with zipfile.ZipFile(caminho) as z:
        nomes = [n for n in z.namelist() if n.endswith(membro)]
        if not nomes:
            raise FileNotFoundError(f"{caminho.name} não tem {membro}: {z.namelist()}")
        bruto = z.read(nomes[0])
    return pd.read_csv(
        io.BytesIO(bruto), sep=";", decimal=",", encoding="utf-8-sig", dtype=str, low_memory=False
    )


def ler_anexos(caminho: Path) -> tuple[dict[int, str], set[int]]:
    """Lê do dicionário (XLSX) os nomes de localidade e o domínio de `H04_4`."""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(caminho.read_bytes()), read_only=True, data_only=True)
    localidades: dict[int, str] = {}
    for linha in wb["anexo_1"].iter_rows(values_only=True):
        cod, nome = linha[1], linha[2]
        if cod is None or nome is None or str(cod).lower() == "valor":
            continue
        localidades[int(cod)] = str(nome).strip()

    dominio_h44: set[int] = set()
    for linha in wb["anexo_10"].iter_rows(values_only=True):
        cod = linha[1]
        if cod is None or str(cod).lower() == "valor":
            continue
        dominio_h44.add(int(cod))
    return localidades, dominio_h44


# ---------------------------------------------------------------- preparação
def numero(serie: pd.Series) -> pd.Series:
    """Texto em número, preservando nulo. Sentinela fica de fora (vira nulo)."""
    v = pd.to_numeric(serie.astype(str).str.replace(",", ".", regex=False), errors="coerce")
    return v.mask(v.isin(list(SENTINELAS)))


def idade_em(df: pd.DataFrame, referencia: pd.Timestamp) -> pd.Series:
    """Idade em `referencia`, a partir de `E02_1`; nulo quando a data não parseia.

    `E02_1` vem em ISO (`1988-10-17`), em ISO parcial ou como sentinela.
    """
    datas = pd.to_datetime(df["E02_1"], errors="coerce", format="mixed")
    anos = referencia.year - datas.dt.year
    ref_md = referencia.month * 100 + referencia.day
    nasc_md = datas.dt.month * 100 + datas.dt.day
    antes = ref_md < nasc_md
    return (anos - antes.astype("Int64")).astype("Float64")


def faixa_de(idades: pd.Series) -> pd.Series:
    """Faixa fechada de idade (`0-3`, `4-5`, ...) para a tabela de frequência."""
    rotulo = pd.Series(pd.NA, index=idades.index, dtype="string")
    for lo, hi, nome in FAIXAS:
        rotulo = rotulo.mask(idades.between(lo, hi), nome)
    return rotulo


def efetivo_kish(pesos: pd.Series) -> float:
    """n efetivo de Kish: (Σw)² / Σw². Base do intervalo de proporções."""
    if len(pesos) == 0:
        return float("nan")
    return float(pesos.sum() ** 2 / (pesos**2).sum())


def ic_proporcao(p: pd.Series, pesos: pd.Series) -> pd.Series:
    """Meio-intervalo de 95% para proporção, aproximado por n efetivo de Kish.

    Não incorpora estratificação nem conglomeração (o arquivo não as traz):
    é um limite inferior da largura real do intervalo.
    """
    n_ef = efetivo_kish(pesos)
    return 1.96 * np.sqrt(p * (1 - p) / n_ef)


def ic_total(pesos: pd.Series) -> float:
    """Erro-padrão aproximado de um total expandido, com reposição."""
    if len(pesos) < 2:
        return float("nan")
    desvios = pesos - pesos.mean()
    return float(np.sqrt(len(pesos) / (len(pesos) - 1) * (desvios**2).sum()))


def rotulo_escola(codigo: pd.Series) -> pd.Series:
    """H04_1 em rótulo; sentinela vira categoria explícita, não some."""
    mapa = {"1": "pública", "2": "particular"}
    return codigo.map(mapa).fillna(
        codigo.map({str(k): v for k, v in SENTINELAS.items()}).fillna("não informado")
    )


def destino_escolar(df: pd.DataFrame, localidades: dict[int, str]) -> pd.Series:
    """Onde a criança estuda, em relação à RA/município de moradia.

    Códigos de `H04_4`: 0 = na própria RA; 40 = no próprio município; 1–36 =
    RA (5300 + código); 41–52 = município goiano (5200 + código). O respondente
    às vezes informa o código do próprio município em vez de 40 — por isso os
    dois caminhos são comparados com o código de moradia.
    """
    propria_ra = (df["localidade"] // 1) % 100  # 5309 -> 9
    h = df["_h44"]
    em_df = df["A01uf"] == str(DF_PREFIXO)
    saida = pd.Series("não informado", index=df.index, dtype="object")
    saida = saida.mask(h.isin(list(SENTINELAS)), "não informado")
    saida = saida.mask(h.between(1, 36), "outra RA do DF")
    saida = saida.mask(h.between(41, 52), "Goiás")
    saida = saida.mask(h == 40, "no próprio município")
    if em_df.any():
        saida = saida.mask(em_df & (h == 0), "própria RA")
        # quem é do DF e informa o código da própria RA
        saida = saida.mask(em_df & (h == propria_ra), "própria RA")
        saida = saida.mask(em_df & (h == 40), "outra RA do DF")  # "no município" = DF
        saida = saida.mask(em_df & h.between(41, 52), "Goiás")
    fora = ~em_df
    if fora.any():
        saida = saida.mask(fora & (h == propria_ra), "próprio município")
        saida = saida.mask(fora & (h == 40), "próprio município")
        saida = saida.mask(fora & (h == 0), "não informado")
        saida = saida.mask(fora & h.between(1, 36), "DF")
        saida = saida.mask(fora & h.between(41, 52), "outro município de GO")
    return saida


# ---------------------------------------------------------------- validação
def conferir_dominios(df: pd.DataFrame, localidades: dict[int, str], dominio_h44: set[int]) -> list[dict]:
    """Falha se aparecer localidade ou código de destino fora do dicionário."""
    fora_loc = sorted(set(df["localidade"].unique()) - set(localidades))
    if fora_loc:
        raise ValueError(f"localidade fora do anexo_1: {fora_loc}")
    h = set(df["_h44"].dropna().astype(int).unique())
    conhecidos = dominio_h44 | set(SENTINELAS) | {0, 40}
    fora_h = sorted(c for c in h if c not in conhecidos and not (1 <= c <= 36) and not (41 <= c <= 52))
    if fora_h:
        raise ValueError(f"código de H04_4 fora do domínio: {fora_h}")
    return [{"checagem": "dominio_localidade", "resultado": "ok", "detalhe": f"{len(localidades)} localidades"}]


def conferir_populacao(pop: pd.DataFrame, localidades: dict[int, str]) -> tuple[pd.DataFrame, list[dict]]:
    """Compara o total expandido do microdado com a tabela dos PDFs.

    `pdad_populacao.csv` (feito pelo 05) traz uma linha por localidade da PDAD,
    inclusive a do DF inteiro. A checagem por RA usa só as 35 RAs; o total do DF
    é comparado com o documento "Distrito Federal". Divergência acima de 5% em
    qualquer RA, ou de 1% no total, interrompe a execução.
    """
    pdf = pd.read_csv(INTERIM / "pdad_populacao.csv")
    pdf["ra"] = pdf["ra_pdad"].map(norm_ra)
    pdf = pdf.dropna(subset=["pop_total"])

    total_doc = pdf[pdf["ra"] == "DISTRITO FEDERAL"]["pop_total"].sum()
    # só as RAs do DF entram na checagem por unidade; os 12 municípios goianos da
    # área de influência ficam fora (conferidos à parte, no bloco do entorno)
    nomes_df = {norm_ra(n) for c, n in localidades.items() if c // 100 == DF_PREFIXO}
    pdf_ra = pdf[pdf["ra"].isin(nomes_df - {"AREA RURAL"})]
    pdf_ra = pdf_ra.groupby("ra", as_index=False)["pop_total"].sum()

    micro = pop[pop["ra"].isin(nomes_df - {"AREA RURAL"})]
    micro = micro.groupby("ra", as_index=False)["pop_est"].sum()
    tab = pdf_ra.merge(micro, on="ra", how="outer")
    tab["desvio_pct"] = (100 * (tab["pop_est"] - tab["pop_total"]) / tab["pop_total"]).round(2)
    if tab["pop_est"].isna().any():
        faltando = tab[tab["pop_est"].isna()]["ra"].tolist()
        raise ValueError(f"RA na tabela dos PDFs sem par no microdado: {faltando}")
    ruins = tab[tab["desvio_pct"].abs() > 5]
    if not ruins.empty:
        raise ValueError(
            "microdado e tabela dos PDFs divergem acima de 5% em: "
            + ", ".join(f"{r.ra} ({r.desvio_pct:+.1f}%)" for r in ruins.itertuples())
        )

    micro_df = pop[pop["ra"] == "AREA RURAL"]["pop_est"].sum()
    total_micro = pop["pop_est"].sum()
    desvio = 100 * (total_micro - total_doc) / total_doc if total_doc else float("nan")
    if abs(desvio) > 1:
        raise ValueError(f"total da população diverge {desvio:+.2f}% do documento do DF")
    checks = [
        {
            "checagem": "populacao_por_ra_microdado_x_pdf",
            "resultado": "ok",
            "detalhe": f"{len(tab)} RAs; desvio máximo {tab['desvio_pct'].abs().max():.2f}%",
        },
        {
            "checagem": "populacao_total_df_microdado_x_pdf",
            "resultado": "ok",
            "detalhe": f"microdado {total_micro:,.0f} (Área Rural {micro_df:,.0f}) × PDF {total_doc:,.0f}: {desvio:+.2f}%",
        },
    ]
    return tab, checks


# ---------------------------------------------------------------- agregados
def arred(x: float, casas: int = 0):
    """Arredonda preservando ausente como ausente (NaN não vira inteiro)."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    return round(x, casas)


def agregar(  # noqa: PLR0913
    df: pd.DataFrame, grupo: list[str], pesos: str = "peso_mor"
) -> pd.DataFrame:
    """n, total expandido, erro-padrão e intervalo do total por grupo."""
    linhas = []
    for chave, sub in df.groupby(grupo, dropna=False):
        chave = chave if isinstance(chave, tuple) else (chave,)
        pesos_sub = sub[pesos]
        se = ic_total(pesos_sub)
        total = pesos_sub.sum()
        linhas.append(
            {
                **dict(zip(grupo, chave)),
                "n": len(sub),
                "pop_est": arred(total),
                "se": arred(se),
                "ic95_inf": arred(total - 1.96 * se) if se == se else None,
                "ic95_sup": arred(total + 1.96 * se) if se == se else None,
            }
        )
    return pd.DataFrame(linhas)


def tabela_populacao(moradores: pd.DataFrame, localidades: dict[int, str]) -> pd.DataFrame:
    """População por RA: idade simples (0–17), faixas fechadas e o corte 31/03.

    Três escopos, para não misturar convenções de idade numa mesma coluna:
    `idade_simples` e `faixa` usam a idade na entrevista (`idade_calculada`);
    `faixa_31_03` usa a idade em 31/03/2024, que só existe para a subamostra com
    data de nascimento preenchida.
    """
    d = moradores.copy()
    d["ra"] = d["localidade"].map(lambda c: norm_ra(localidades[int(c)]))
    d["idade_entrevista"] = d["_idade"]
    d["idade_31_03"] = d["_idade_31_03"]
    d["elegivel_creche_31_03"] = d["idade_31_03"].between(0, 3).fillna(False).astype(bool)

    simples = d[d["idade_entrevista"].between(0, 17)]
    t1 = agregar(simples, ["ra", "idade_entrevista"]).rename(columns={"idade_entrevista": "idade"})
    t1["escopo"] = "idade_simples"
    t1["idade"] = t1["idade"].astype("Int64")
    t1["faixa"] = pd.Series(pd.NA, index=t1.index, dtype="string")

    faixas = d.assign(faixa=faixa_de(d["idade_entrevista"])).dropna(subset=["faixa"])
    t2 = agregar(faixas, ["ra", "faixa"])
    t2["escopo"] = "faixa"
    t2["idade"] = pd.Series(pd.NA, index=t2.index, dtype="Int64")

    creche = d[d["elegivel_creche_31_03"]]
    t3 = agregar(creche, ["ra"])
    t3["escopo"] = "faixa_31_03"
    t3["idade"] = pd.Series(pd.NA, index=t3.index, dtype="Int64")
    t3["faixa"] = "0-3"

    colunas = ["escopo", "ra", "idade", "faixa", "n", "pop_est", "se", "ic95_inf", "ic95_sup"]
    return pd.concat([t1, t2, t3], ignore_index=True)[colunas]


def _linha_frequencia(ra: str, faixa: str, sub: pd.DataFrame) -> dict:
    total = sub["peso_mor"].sum()
    freq = sub[sub["frequenta"] == "sim"]
    p = freq["peso_mor"].sum() / total if total else np.nan
    linha = {
        "ra": ra, "faixa": faixa, "n": len(sub), "pop_est": arred(total),
        "freq_n": len(freq["peso_mor"]), "freq_est": arred(freq["peso_mor"].sum()),
        "freq_pct": arred(100 * p, 1) if p == p else None,
        "freq_ic95_pp": arred(100 * float(ic_proporcao(pd.Series([p]), sub["peso_mor"]).iloc[0]), 1) if p == p else None,
    }
    for tipo in ["pública", "particular", "não sabe", "não informado"]:
        fatia = freq[freq["escola"] == tipo]["peso_mor"].sum()
        linha[f"escola_{tipo.replace(' ', '_')}_pct"] = (
            arred(100 * fatia / freq["peso_mor"].sum(), 1) if len(freq) else None
        )
    return linha


def tabela_frequencia(moradores: pd.DataFrame, localidades: dict[int, str]) -> pd.DataFrame:
    """Frequência a creche/escola por RA, faixa etária e tipo de escola.

    A linha com `ra = "DF"` é o agregado do Distrito Federal: existe para que o
    número do relatório tenha arquivo atrás dele, e não para ser somado às RAs.
    """
    d = moradores.copy()
    d["ra"] = d["localidade"].map(lambda c: norm_ra(localidades[int(c)]))
    d["faixa"] = faixa_de(d["_idade"])
    d = d.dropna(subset=["faixa"])
    d["frequenta"] = d["_h02"].map({1: "sim", 2: "não"})
    d["frequenta"] = d["frequenta"].fillna("não informado")
    d["escola"] = rotulo_escola(d["H04_1"])

    linhas = [_linha_frequencia(ra, faixa, sub) for (ra, faixa), sub in d.groupby(["ra", "faixa"])]
    if len(moradores):
        linhas += [_linha_frequencia("DF", faixa, sub) for faixa, sub in d.groupby("faixa")]
    return pd.DataFrame(linhas)


def tabela_fluxo(moradores: pd.DataFrame, localidades: dict[int, str]) -> pd.DataFrame:
    """Para onde vão os alunos de 6 a 17 anos, por RA de moradia e rede."""
    d = moradores.copy()
    d["ra_moradia"] = d["localidade"].map(lambda c: norm_ra(localidades[int(c)]))
    d["_h44"] = numero(d["H04_4"])
    d["localidade"] = d["localidade"].astype(int)
    d["destino"] = destino_escolar(d, localidades)
    d["escola"] = rotulo_escola(d["H04_1"])
    d = d[(d["_h02"] == 1) & d["_idade"].between(6, 17)]
    return agregar(d, ["ra_moradia", "destino", "escola"])


def tabela_entorno(moradores: pd.DataFrame, localidades: dict[int, str]) -> pd.DataFrame:
    """Moradores de 6 a 17 anos dos municípios goianos e quanto estudam no DF."""
    d = moradores[moradores["A01uf"] == str(GO_PREFIXO)].copy()
    d["_h44"] = numero(d["H04_4"])
    d["municipio"] = d["localidade"].map(lambda c: localidades[int(c)])
    d["destino"] = destino_escolar(d, localidades)
    d["escola"] = rotulo_escola(d["H04_1"])
    d = d[(d["_h02"] == 1) & d["_idade"].between(6, 17)]
    return agregar(d, ["municipio", "destino", "escola"])


# ---------------------------------------------------------------- principal
def main(check: bool = False) -> None:
    arquivos = {
        "moradores": localizar("base_de_morador"),
        "domicilios": localizar("base_de_domicilios"),
        "dicionario": localizar("dicionario_de_dados"),
    }
    for chave, caminho in arquivos.items():
        print(f"  {chave:11} {caminho.name:55} {tipo_real(caminho):6} {caminho.stat().st_size:>10} B")

    localidades, dominio_h44 = ler_anexos(arquivos["dicionario"])
    moradores = ler_csv_do_zip(arquivos["moradores"], "moradores.csv")
    domicilios = ler_csv_do_zip(arquivos["domicilios"], "domicilios.csv")
    print(f"  moradores   {moradores.shape[0]} linhas × {moradores.shape[1]} colunas")
    print(f"  domicílios  {domicilios.shape[0]} linhas × {domicilios.shape[1]} colunas")
    if check:
        print("\n  --check: leitura ok; nada foi gravado.")
        return

    metodo = []
    moradores["localidade"] = moradores["localidade"].astype(int)
    moradores["_h02"] = numero(moradores["H02"])
    moradores["_h44"] = numero(moradores["H04_4"])
    moradores["_idade"] = numero(moradores["idade_calculada"])
    moradores["_idade_31_03"] = idade_em(moradores, DATA_REFERENCIA)
    moradores["peso_mor"] = numero(moradores["peso_mor"])

    if moradores["peso_mor"].isna().any():
        raise ValueError("peso_mor nulo: a expansão não fecha")
    metodo += conferir_dominios(moradores, localidades, dominio_h44)

    com_data = moradores["E02_1"] != "99999"
    if com_data.any():
        parse_disponivel = moradores.loc[com_data, "_idade_31_03"].notna().mean()
    else:
        parse_disponivel = 0.0
    if parse_disponivel < 0.99:
        raise ValueError(
            f"E02_1 só parseia em {100*parse_disponivel:.1f}% das linhas com data preenchida"
        )
    metodo.append(
        {"checagem": "data_nascimento_disponivel", "resultado": "ok",
         "detalhe": "E02_1 preenchida em %.1f%% das linhas; parse em %.2f%% das preenchidas"
                   % (100 * com_data.mean(), 100 * parse_disponivel)}
    )
    metodo.append(
        {"checagem": "idade_31_03_subamostra", "resultado": "ok",
         "detalhe": "idade em 31/03/2024 só existe para a subamostra com data de nascimento "
                    "(%d de %d moradores)" % (int(moradores["_idade_31_03"].notna().sum()), len(moradores))}
    )

    df_uf = moradores[moradores["A01uf"] == str(DF_PREFIXO)].copy()
    df_uf["ra"] = df_uf["localidade"].map(lambda c: norm_ra(localidades[int(c)]))
    pop_ra = agregar(df_uf, ["ra"])
    conferencia, checks = conferir_populacao(pop_ra, localidades)
    metodo += checks

    df = moradores.loc[:, ~moradores.columns.isin(COLUNAS_DESCARTADAS)].copy()
    moradores = df  # a partir daqui o frame não tem data de nascimento nem identificador

    DEST.mkdir(parents=True, exist_ok=True)
    populacao = tabela_populacao(df_uf, localidades)
    frequencia = tabela_frequencia(df_uf, localidades)
    fluxo = tabela_fluxo(df_uf, localidades)
    entorno = tabela_entorno(moradores, localidades)

    populacao.to_parquet(DEST / "pdad_populacao.parquet", index=False)
    frequencia.to_parquet(DEST / "pdad_frequencia.parquet", index=False)
    fluxo.to_parquet(DEST / "pdad_fluxo_escolar.parquet", index=False)
    entorno.to_parquet(DEST / "pdad_entorno.parquet", index=False)
    conferencia.to_csv(DEST / "pdad_conferencia.csv", index=False)

    idade_df = populacao[populacao["escopo"] == "faixa"]
    idade_31 = populacao[populacao["escopo"] == "faixa_31_03"]
    df_total = df_uf["peso_mor"].sum()
    metodo.append({"checagem": "total_expandido_df", "resultado": "ok",
                   "detalhe": f"{df_total:,.0f} moradores no DF (soma de peso_mor)"})
    metodo.append({"checagem": "creche_0_3_convencao", "resultado": "ok",
                   "detalhe": "0-3 na entrevista: %d; 0-3 em 31/03/2024: %d"
                   % (idade_df[idade_df.faixa == "0-3"]["pop_est"].sum(),
                      idade_31["pop_est"].sum())})
    cobertura_03 = idade_31["pop_est"].sum() / idade_df[idade_df.faixa == "0-3"]["pop_est"].sum()
    metodo.append({"checagem": "cobertura_data_nascimento_0_3", "resultado": "atenção",
                   "detalhe": "só %.1f%% da população de 0-3 tem data de nascimento: a idade em "
                              "31/03 não substitui a idade na entrevista como denominador" % (100 * cobertura_03)})
    pd.DataFrame(metodo).to_csv(DEST / "pdad_metodo.csv", index=False)

    # ---- relatório de tela
    print("\n== população (soma de peso_mor)")
    print(
        idade_df.pivot_table(index="faixa", values=["n", "pop_est"], aggfunc="sum")
        .reindex([f for _, _, f in FAIXAS])
        .to_string()
    )
    print(f"  DF total: {df_total:,.0f}")
    print(f"  0-3 na entrevista: {idade_df[idade_df.faixa == '0-3'].pop_est.sum():,.0f}"
          f"  |  0-3 em 31/03/2024 (subamostra): {idade_31['pop_est'].sum():,.0f}")

    print("\n== PDAD × tabela dos PDFs (pop_total)")
    print(conferencia.sort_values("desvio_pct").head(6).to_string(index=False))
    print(f"  desvio máximo: {conferencia['desvio_pct'].abs().max():.2f}%")

    print("\n== frequência escolar, DF")
    resumo = frequencia.groupby("faixa").apply(
        lambda g: pd.Series({
            "pop_est": g.pop_est.sum(),
            "freq_pct": round(100 * g.freq_est.sum() / g.pop_est.sum(), 1),
        }),
        include_groups=False,
    )
    print(resumo.to_string())
    creche = frequencia[frequencia.faixa == "0-3"]
    for tipo in ["pública", "particular", "não sabe"]:
        col = f"escola_{tipo.replace(' ', '_')}_pct"
        if col in creche:
            print(f"  0-3 que frequenta, na rede {tipo:11}: {100*(creche['freq_est']*creche[col]/100).sum()/creche['freq_est'].sum():.1f}%")

    print("\n== fluxo escolar, DF, 6 a 17 anos (share do total que frequenta)")
    df_fluxo = fluxo[fluxo.escola.isin(["pública", "particular", "não informado"])]
    tot = df_fluxo.groupby("destino")["pop_est"].sum()
    print((100 * tot / tot.sum()).sort_values(ascending=False).round(1).to_string())

    print("\n== entorno goiano, 6 a 17 anos")
    go = entorno.groupby("municipio").apply(
        lambda g: pd.Series({
            "pop_est": g.pop_est.sum(),
            "estuda_no_DF_pct": round(100 * g[g.destino == "DF"].pop_est.sum() / g.pop_est.sum(), 1),
        }),
        include_groups=False,
    ).sort_values("estuda_no_DF_pct", ascending=False)
    print(go.to_string())
    print(f"  total que estuda no DF: {entorno[entorno.destino == 'DF'].pop_est.sum():,.0f}")

    print("\n== conferências")
    print(pd.DataFrame(metodo).to_string(index=False))
    print(f"\nsaídas em {DEST}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="só lê e descreve, sem gravar")
    main(**vars(ap.parse_args()))
