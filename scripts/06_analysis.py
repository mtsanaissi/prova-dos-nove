"""Respostas às seis perguntas da fase 0, ao Ideb nacional (q7–q10), ao Ideb
ausente (q11–q12) e ao Censo Escolar (q13–q15).

Entrada: parquets de `data/interim/seedf/`, `data/interim/pdad_populacao.csv`,
         `data/interim/pdad/` (agregados da PDAD-A) e `data/interim/inep/`
         (incluindo `censo_escola_df.parquet`, gravado por `11_ingest_censo.py`).
Saída:   `data/interim/q1_unidades.csv` ... `q8_conferencia_seedf.csv`,
         `q9_em_integrado.csv`, `q10_fluxo_df.csv`, `q11_distorcao_df.csv`,
         `q12_*.csv`, `q13_ponderacao_df.csv`, `q14_creche_*.csv`,
         `q15_conferencia_censo.csv`, os três `q3_biblioteca*.csv` e um log com
         os números que vão para o REPORT.md. Também
         `q16_presenca_escola_etapa.csv` e `q16_faixas_n.csv` (matriz de presença
         escola × etapa) e `q0_execucao.csv` (executado|pulado por etapa). Com
         `--public DIR`, grava também o insumo versionado do site
         (`escolas.parquet`, `indicadores.parquet`, `infraestrutura.parquet`,
         `ideb_uf.parquet`, `agregados.parquet` e `procedencia.json`).
Idempotente: sim — leitura e reescrita das saídas; o insumo público só é
sobrescrito com `--force` quando o sha256 do destino difere. Com `--public`,
uma etapa pulada impede a gravação (código 1) a menos de `--parcial`; nesse
caso a lista de etapas puladas vai para `procedencia.json`.

Regra de leitura: nulo é ausente, `0` é zero. Nunca se soma nulo como zero.

`main()` executa as etapas em ordem, grava `q0_execucao.csv` e sai com código 1
se alguma pulou; `--parcial` aceita o resultado incompleto e sai com 0.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from _common import INTERIM, norm_ra, sha256

S = INTERIM / "seedf"
class Pulado(Exception):
    """Etapa que nao pode rodar por falta de insumo; o motivo vai para q0_execucao.csv."""


NOME_REDE = {
    "REDE PÚBLICA FEDERAL": "pública federal",
    "REDE PÚBLICA ESTADUAL VINCULADA À SEEDF": "pública estadual (SEEDF)",
    "REDE PÚBLICA ESTADUAL NÃO VINCULADA À SE": "pública estadual (não vinculada)",
    "REDE PARTICULAR CONVENIADA": "privada conveniada",
    "REDE PARTICULAR NÃO CONVENIADA": "privada não conveniada",
}


def carrega(prefixo: str, ano: str | None = None) -> pd.DataFrame:
    padrao = f"{prefixo}__*{ano or ''}.parquet" if ano else f"{prefixo}__*.parquet"
    arquivos = sorted(S.glob(padrao))
    if not arquivos:
        raise FileNotFoundError(f"sem parquet para {padrao}")
    return pd.concat([pd.read_parquet(a) for a in arquivos], ignore_index=True)


def num(serie: pd.Series) -> pd.Series:
    """Converte texto em número preservando nulo como nulo."""
    return pd.to_numeric(serie, errors="coerce")


# ---------------------------------------------------------------- Q1
def q1() -> None:
    e = pd.read_parquet(S / "escolas__relatorio_escolas_2025.parquet").copy()
    e["rede"] = e["Nome Rede"].map(NOME_REDE).fillna(e["Nome Rede"])
    etapas = {
        "creche": "INF_CRE",
        "pré-escola": "INF_PRE",
        "fundamental": "FUND",
        "médio": "MED",
    }
    linhas = []
    for rotulo, col in etapas.items():
        sub = e[num(e[col]) == 1]
        for rede, n in sub["rede"].value_counts().items():
            linhas.append({"etapa": rotulo, "rede": rede, "escolas": n})
    tab = pd.DataFrame(linhas)
    tab.to_csv(INTERIM / "q1_unidades.csv", index=False)
    print("== Q1 (escolas 2025, arquivo relatorio_escolas_2025.csv)")
    print(tab.pivot_table(index="etapa", columns="rede", values="escolas", fill_value=0).to_string())
    print(f"\ntotal de unidades em 2025: {len(e)}")
    print(e["rede"].value_counts().to_string())
    print("\nunidades por tipologia (top):")
    print(e["Tipologia"].value_counts().head(12).to_string())


# ---------------------------------------------------------------- Q2
def q2() -> None:
    e = pd.read_parquet(S / "escolas__relatorio_escolas_2025.parquet").copy()
    e["rede"] = e["Nome Rede"].map(NOME_REDE).fillna(e["Nome Rede"])
    cod_por_rede = dict(zip(e["CO_ENTIDADE"].astype(str), e["rede"]))
    total_por_rede = e["rede"].value_counts().to_dict()

    fontes = {
        "escolas 2025": (pd.read_parquet(S / "escolas__relatorio_escolas_2025.parquet"), "CO_ENTIDADE", "Nome Rede"),
        "matrículas 2024": (pd.read_parquet(S / "matriculas__relatorio_matriculas_2024.parquet"), "CO_ENTIDADE", "NO_REDE"),
        "infraestrutura 2025": (pd.read_parquet(S / "infraestrutura__relatorio_infraestrutura_2025.parquet"), "CO_ENTIDADE", "NO_REDE"),
        "situação 2023": (pd.read_parquet(S / "situacao__relatorio_situacao_aluno_excel_2023.parquet"), "CO_ENTIDADE", "NO_REDE"),
        "IDEB 2025 (AI)": (pd.read_parquet(S / "ideb_serie__ideb_ef_ai_2005_2025_ckan1.parquet"), "cod_inep", "rede"),
    }
    linhas = []
    for nome, (df, col, rede_col) in fontes.items():
        codigos = set(df[col].astype(str).str.strip())
        presentes = {r: len([c for c in total_por_rede if c == r]) for r in total_por_rede}
        presentes = {
            r: sum(1 for cod in cod_por_rede if cod_por_rede[cod] == r and cod in codigos)
            for r in total_por_rede
        }
        for rede, n in total_por_rede.items():
            linhas.append(
                {"arquivo": nome, "rede": rede, "escolas_2025": n, "presentes": presentes[rede],
                 "cobertura_pct": round(100 * presentes[rede] / n, 1)}
            )
    tab = pd.DataFrame(linhas)
    tab.to_csv(INTERIM / "q2_cobertura.csv", index=False)
    print("\n== Q2 cobertura de cada arquivo contra o cadastro de 2025")
    print(tab.pivot_table(index="rede", columns="arquivo", values="cobertura_pct").to_string())
    for nome, (df, col, rede_col) in fontes.items():
        if rede_col in df:
            print(f"   {nome}: redes no arquivo -> {df[rede_col].value_counts().to_dict()}")


# ---------------------------------------------------------------- Q3
def escolas_com_ef_em(ano: str) -> dict[str, bool]:
    """Códigos das escolas que ofertam fundamental ou médio no cadastro do ano.

    2014–2024 informam turmas por etapa (`ESC_*`), inclusive multietapa; 2025
    informa sinalizadores 0/1 (`FUND_AI`, `FUND_AF`, `MED`). A multietapa
    (`ESC_MULTI`, `ESC_EF_MULTI`) conta como oferta de fundamental: a escola tem
    turma de EF, mesmo que em classe multisseriada.
    """
    arquivos = [
        a for a in sorted(S.glob(f"escolas__*{ano}*.parquet"))
        if "dicionario" not in a.name
    ]
    if not arquivos:
        raise FileNotFoundError(f"sem cadastro de escolas para {ano}")
    d = pd.read_parquet(arquivos[0])
    if "FUND_AI" in d:
        colunas = ["FUND_AI", "FUND_AF", "MED"]
    else:
        colunas = ["ESC_EF_INI", "ESC_EF_FIN", "ESC_EM_TOTAL", "ESC_MULTI", "ESC_EF_MULTI"]
    colunas = [c for c in colunas if c in d]
    oferta = pd.concat([num(d[c]) for c in colunas], axis=1).fillna(0).sum(axis=1)
    return dict(zip(d["CO_ENTIDADE"].astype(str), oferta > 0))


def q3() -> None:
    bruto = pd.read_parquet(S / "infraestrutura__relatorio_infraestrutura_2025.parquet").copy()
    # só escolas em funcionamento: o arquivo traz 1471 registros, incluindo
    # paralisadas e extintas (TP_SITUACAO_FUNCIONAMENTO 2 e 3)
    i = bruto[bruto["TP_SITUACAO_FUNCIONAMENTO"] == "1"].copy()
    i["rede"] = i["NO_REDE"].map(NOME_REDE).fillna(i["NO_REDE"])
    i["ra"] = i["NO_RA"].map(norm_ra)
    print(f"   infraestrutura 2025: {len(bruto)} registros, {len(i)} em funcionamento")
    itens = {
        "laboratório de informática": "IN_LABORATORIO_INFORMATICA",
        "internet (existência)": "IN_INTERNET",
        "internet para os alunos": "IN_INTERNET_ALUNOS",
        "quadra de esportes": "IN_QUADRA_ESPORTES",
        "acessibilidade (nenhum item)": "IN_ACESSIBILIDADE_INEXISTENTE",
        "banheiro": "IN_BANHEIRO",
        "água potável": "IN_AGUA_POTAVEL",
        "esgoto inexistente": "IN_ESGOTO_INEXISTENTE",
    }
    # o mesmo item em dois universos: todas as escolas em funcionamento e só as
    # que ofertam fundamental ou médio (onde laboratório, quadra e biblioteca são
    # exigência). Sem a segunda coluna, o número mistura públicos diferentes.
    oferta = escolas_com_ef_em("2025")
    i["efem"] = i["CO_ENTIDADE"].astype(str).map(oferta).fillna(False)
    linhas = []
    for rotulo, col in itens.items():
        if col not in i:
            continue
        v = num(i[col])
        # colunas *_INEXISTENTE marcam a ausência com 1, não com 0
        negativo = col.endswith("_INEXISTENTE")
        sem = (v == 1) if negativo else (v == 0)
        v_efem = num(i.loc[i["efem"], col])
        sem_efem = (v_efem == 1) if negativo else (v_efem == 0)
        linhas.append(
            {
                "item": rotulo,
                "escolas_com_dado": int(v.notna().sum()),
                "sem_item": int(sem.sum()),
                "nao_reportado": int(v.isna().sum()),
                "pct_sem_item": round(100 * sem.sum() / v.notna().sum(), 1),
                "escolas_efem": int(v_efem.notna().sum()),
                "pct_sem_item_efem": round(100 * sem_efem.sum() / v_efem.notna().sum(), 1) if v_efem.notna().any() else None,
            }
        )
    tab = pd.DataFrame(linhas)
    tab["universo_efem"] = "escolas em funcionamento que ofertam fundamental ou médio (n=927)"
    tab.to_csv(INTERIM / "q3_infra_itens.csv", index=False)
    print("\n== Q3 infraestrutura 2025 (infraestrutura__relatorio_infraestrutura_2025)")
    print("   duas colunas de universo: todas as 1.332 em funcionamento e as 927 que")
    print("   ofertam fundamental ou médio. Biblioteca fica em q3_biblioteca.csv, com")
    print("   os três itens separados (biblioteca, sala de leitura, união).")
    print(tab.to_string(index=False))

    por_rede = i.groupby("rede").apply(
        lambda d: pd.Series(
            {
                "n": len(d),
                "sem_lab_info_pct": round(100 * (num(d["IN_LABORATORIO_INFORMATICA"]) == 0).sum() / num(d["IN_LABORATORIO_INFORMATICA"]).notna().sum(), 1),
                "sem_internet_pct": round(100 * (num(d["IN_INTERNET"]) == 0).sum() / num(d["IN_INTERNET"]).notna().sum(), 1),
                "sem_quadra_pct": round(100 * (num(d["IN_QUADRA_ESPORTES"]) == 0).sum() / num(d["IN_QUADRA_ESPORTES"]).notna().sum(), 1),
            }
        ),
        include_groups=False,
    )
    por_rede.to_csv(INTERIM / "q3_infra_por_rede.csv")
    print("\npor rede (mesmo universo):")
    print(por_rede.to_string())

    por_ra = i.groupby("ra").apply(
        lambda d: pd.Series(
            {
                "escolas": len(d),
                "sem_lab_info_pct": round(100 * (num(d["IN_LABORATORIO_INFORMATICA"]) == 0).sum() / max(1, num(d["IN_LABORATORIO_INFORMATICA"]).notna().sum()), 1),
                "sem_quadra_pct": round(100 * (num(d["IN_QUADRA_ESPORTES"]) == 0).sum() / max(1, num(d["IN_QUADRA_ESPORTES"]).notna().sum()), 1),
                "sem_internet_pct": round(100 * (num(d["IN_INTERNET"]) == 0).sum() / max(1, num(d["IN_INTERNET"]).notna().sum()), 1),
            }
        ),
        include_groups=False,
    ).sort_values("sem_lab_info_pct", ascending=False)
    por_ra.to_csv(INTERIM / "q3_infra_por_ra.csv")
    print("\npor RA (pior → melhor em falta de laboratório de informática):")
    print(por_ra.head(8).to_string())

    biblioteca(i)


def biblioteca(i: pd.DataFrame) -> None:
    """Biblioteca, sala de leitura e bibliotecário — três coisas distintas.

    O Censo tem três itens separados (dicionário da infraestrutura, campos 123,
    124 e 144): `IN_BIBLIOTECA` é a biblioteca; `IN_SALA_LEITURA` é a sala de
    leitura; `IN_BIBLIOTECA_SALA_LEITURA` é "biblioteca e/ou sala de leitura" e
    é exatamente o OR dos outros dois. Sala de leitura não é biblioteca, então
    as duas nunca entram na mesma frase como se fossem a mesma coisa.

    O universo é o das escolas que ofertam fundamental ou médio: biblioteca não
    é exigência para creche, e usar todas as 1.332 unidades mistura públicos
    que a norma trata de forma diferente.
    """
    oferta = escolas_com_ef_em("2025")
    i = i.copy()
    i["efem"] = i["CO_ENTIDADE"].astype(str).map(oferta).fillna(False)
    for col in ["IN_BIBLIOTECA", "IN_SALA_LEITURA", "IN_BIBLIOTECA_SALA_LEITURA", "QT_PROF_BIBLIOTECARIO"]:
        i[col] = num(i[col])
    i["tem_biblioteca"] = i["IN_BIBLIOTECA"] == 1
    i["tem_espaco"] = i["IN_BIBLIOTECA_SALA_LEITURA"] == 1
    i["tem_bibliotecario"] = i["QT_PROF_BIBLIOTECARIO"].fillna(0) >= 1

    def medidas(d: pd.DataFrame) -> pd.Series:
        com_bib = d[d["tem_biblioteca"]]
        return pd.Series(
            {
                "n": len(d),
                "sem_biblioteca_pct": round(100 * (d["IN_BIBLIOTECA"] == 0).sum() / d["IN_BIBLIOTECA"].notna().sum(), 1) if d["IN_BIBLIOTECA"].notna().any() else None,
                "sem_biblioteca_nem_sala_leitura_pct": round(100 * (~d["tem_espaco"]).sum() / len(d), 1) if len(d) else None,
                "com_bibliotecario_pct": round(100 * d["tem_bibliotecario"].sum() / len(d), 1) if len(d) else None,
                "biblioteca_sem_bibliotecario_pct": round(100 * (~com_bib["tem_bibliotecario"]).sum() / len(com_bib), 1) if len(com_bib) else None,
            }
        )

    efem = i[i["efem"]].copy()
    por_rede = efem.groupby("rede").apply(medidas, include_groups=False)
    por_rede.loc["todas (EF/EM)"] = medidas(efem)
    # linha do universo completo (inclui quem só oferta educação infantil): é dela
    # que sai o 66,3% histórico, e ela existe para que o número antigo continue
    # rastreável ao lado do correto — não para ser citada como "escolas sem
    # biblioteca" sem dizer o universo
    por_rede.loc["todas as escolas em funcionamento (inclui EI)"] = medidas(i)
    por_rede.to_csv(INTERIM / "q3_biblioteca.csv")
    print("\n== Q3 biblioteca — universo: escolas em funcionamento que ofertam fundamental ou médio")
    print("   três medidas nomeadas; 'sem biblioteca nem sala de leitura' não é 'sem biblioteca'")
    print(por_rede.to_string())

    por_ra = efem.groupby("ra").apply(medidas, include_groups=False).sort_values("sem_biblioteca_pct", ascending=False)
    por_ra.to_csv(INTERIM / "q3_biblioteca_por_ra.csv")
    print("\npor RA (pior → melhor em falta de biblioteca; n pequeno = ordenação instável):")
    print(por_ra.head(8).to_string())

    # série 2014–2025 no mesmo universo (EF/EM do cadastro de cada ano)
    serie = []
    for ano in [str(a) for a in range(2014, 2026)]:
        arquivos = sorted(S.glob(f"infraestrutura__relatorio_infraestrutura_{ano}.parquet"))
        if not arquivos:
            continue
        d = pd.read_parquet(arquivos[0])
        if "TP_SITUACAO_FUNCIONAMENTO" in d:
            d = d[d["TP_SITUACAO_FUNCIONAMENTO"] == "1"]
        oferta_ano = escolas_com_ef_em(ano)
        d = d.copy()
        d["efem"] = d["CO_ENTIDADE"].astype(str).map(oferta_ano).fillna(False)
        d = d[d["efem"]]
        b = num(d["IN_BIBLIOTECA"])
        u = num(d["IN_BIBLIOTECA_SALA_LEITURA"])
        serie.append(
            {
                "ano": ano,
                "escolas_efem": len(d),
                "sem_biblioteca_pct": round(100 * (b == 0).sum() / b.notna().sum(), 1) if b.notna().any() else None,
                "sem_biblioteca_nem_sala_leitura_pct": round(100 * (u == 0).sum() / u.notna().sum(), 1) if u.notna().any() else None,
            }
        )
    serie_df = pd.DataFrame(serie)
    serie_df.to_csv(INTERIM / "q3_biblioteca_serie.csv", index=False)
    print("\nsérie 2014–2025, universo EF/EM de cada ano (2016 é cópia de 2017 — ver SCHEMA):")
    print(serie_df.to_string(index=False))


# ---------------------------------------------------------------- Q4
def q4() -> None:
    e = pd.read_parquet(S / "escolas__relatorio_escolas_2025.parquet")
    mapa_ra = {str(k): norm_ra(v) for k, v in zip(e["CO_ENTIDADE"], e["Nome RA"])}
    mapa_rede = {str(k): NOME_REDE.get(v, v) for k, v in zip(e["CO_ENTIDADE"], e["Nome Rede"])}

    ideb = pd.read_parquet(S / "ideb_serie__ideb_ef_ai_2005_2025_ckan1.parquet")
    ideb = ideb[ideb["indicador"] == "IDEB"].copy()
    ideb["valor"] = num(ideb["valor"])
    ideb["ra"] = ideb["cod_inep"].astype(str).map(mapa_ra)
    ideb["rede"] = ideb["cod_inep"].astype(str).map(mapa_rede)

    linhas, resumo = [], []
    for ano in ("2023", "2025"):
        sub = ideb[(ideb["ano"] == ano) & ideb["valor"].notna()]
        sub = sub.dropna(subset=["ra"])
        if sub.empty:
            continue
        g = sub.groupby("ra")["valor"].agg(["count", "median", "mean", "min", "max"])
        g["ano"] = ano
        linhas.append(g.reset_index())
        # decomposição da variância: quanto da variação é entre RAs
        media = sub["valor"].mean()
        n = len(sub)
        k = sub["ra"].nunique()
        sst = ((sub["valor"] - media) ** 2).sum()
        ssb = sum(len(d) * (d["valor"].mean() - media) ** 2 for _, d in sub.groupby("ra"))
        eta2 = ssb / sst
        # razao de quadrados medios (um F), nao um coeficiente de correlacao
        # intraclasse: o nome antigo (icc) foi corrigido em 2026-11-06 (L-41).
        f_entre_ra = (ssb / (k - 1)) / ((sst - ssb) / (n - k))
        resumo.append(
            {
                "ano": ano,
                "escolas_com_ideb": n,
                "ras": k,
                "media": round(media, 2),
                "desvio": round(sub["valor"].std(), 2),
                "p10": round(sub["valor"].quantile(0.10), 2),
                "mediana": round(sub["valor"].median(), 2),
                "p90": round(sub["valor"].quantile(0.90), 2),
                "min": round(sub["valor"].min(), 2),
                "max": round(sub["valor"].max(), 2),
                "eta2_entre_ra": round(eta2, 3),
                "f_entre_ra": round(f_entre_ra, 3),
            }
        )
    por_ra = pd.concat(linhas)
    por_ra.to_csv(INTERIM / "q4_ideb_por_ra.csv", index=False)
    res = pd.DataFrame(resumo)
    res.to_csv(INTERIM / "q4_ideb_resumo.csv", index=False)
    print("\n== Q4 IDEB por escola (anos iniciais, ideb_ef_ai_2005_2025.csv)")
    print(res.to_string(index=False))
    for ano in res["ano"].unique():
        print(f"\n   RA em {ano} (mediana do IDEB):")
        print(
            por_ra[por_ra["ano"] == ano]
            .sort_values("median", ascending=False)
            .assign(median=lambda d: d["median"].round(2))
            .to_string(index=False)
        )

    # 2023 também nos anos finais e no EM, para checar se a hierarquia se repete
    for arq, etapa in [
        ("ideb_serie__ideb_ef_af_2005_2025.parquet", "anos finais"),
        ("ideb_serie__ideb_em_2017_2025.parquet", "ensino médio"),
    ]:
        d = pd.read_parquet(S / arq)
        col_ind = "indicador" if "indicador" in d else "Indicador"
        col_ano = "ano" if "ano" in d else "Ano"
        col_cod = "cod_inep" if "cod_inep" in d else "Cód_Inep"
        d = d[d[col_ind] == "IDEB"].copy()
        d["valor"] = num(d["valor"] if "valor" in d else d["Valor"])
        d["ra"] = d[col_cod].astype(str).map(mapa_ra)
        sub = d[(d[col_ano] == "2023") & d["valor"].notna()].dropna(subset=["ra"])
        if sub.empty:
            continue
        media = sub["valor"].mean()
        ssb = sum(len(x) * (x["valor"].mean() - media) ** 2 for _, x in sub.groupby("ra"))
        sst = ((sub["valor"] - media) ** 2).sum()
        print(
            f"   {etapa} 2023: n={len(sub)} escolas, mediana={sub['valor'].median():.2f}, "
            f"p10={sub['valor'].quantile(.1):.2f}, p90={sub['valor'].quantile(.9):.2f}, "
            f"variação entre RAs={100*ssb/sst:.1f}%"
        )


# ---------------------------------------------------------------- Q5
def q5() -> None:
    m = pd.read_parquet(S / "matriculas__relatorio_matriculas_2024.parquet").copy()
    m["ra"] = m["NO_RA"].map(norm_ra)
    m["mat_creche"] = num(m["MAT_CRECHE"]).fillna(0)
    m["idade"] = num(m["IDADE"])
    oferta = m.groupby("ra")["mat_creche"].sum().rename("matriculas_creche_2024")

    # a matrícula em creche vem por idade simples: dá para separar 0–3 de 4 e mais
    em_creche = m[m["mat_creche"] > 0]
    mat03 = (
        em_creche[em_creche["idade"] <= 3].groupby("ra")["mat_creche"].sum()
        .rename("matriculas_creche_0_3")
    )
    mat4 = (
        em_creche[em_creche["idade"] >= 4].groupby("ra")["mat_creche"].sum()
        .rename("matriculas_creche_4_mais")
    )

    e = pd.read_parquet(S / "escolas__relatorio_escolas_2025.parquet").copy()
    e["ra"] = e["Nome RA"].map(norm_ra)
    unidades = e[num(e["INF_CRE"]) == 1].groupby("ra").size().rename("unidades_com_creche_2025")

    pop = pd.read_csv(INTERIM / "pdad_populacao.csv")
    pop["ra"] = pop["ra"].map(norm_ra)
    pop = pop[pop["ra"].isin(set(m["ra"]) | set(e["ra"]))].copy()
    pop = pop.dropna(subset=["pop_0_4"])
    pop = pop.groupby("ra")["pop_0_4"].sum().rename("pop_0_4_2024")

    # denominador em 0–3: vem dos microdados da PDAD-A (10_ingest_pdad.py), que
    # permitem idade simples; a faixa "até 4 anos" dos PDFs não permitia.
    freq_pdad = INTERIM / "pdad" / "pdad_frequencia.parquet"
    if freq_pdad.exists():
        f = pd.read_parquet(freq_pdad)
        c = f[(f["faixa"] == "0-3") & (f["ra"] != "DF")]
        pop03 = c.set_index("ra")["pop_est"].rename("pop_0_3_2024")
        freq03 = c.set_index("ra")["freq_pct"].rename("freq_pdad_0_3_pct")
    else:
        print("   (sem data/interim/pdad/pdad_frequencia.parquet: rode 10_ingest_pdad.py)")
        pop03 = pd.Series(dtype=float, name="pop_0_3_2024")
        freq03 = pd.Series(dtype=float, name="freq_pdad_0_3_pct")

    # Contagem que falta é zero; população e frequência que faltam são ausência.
    # O fillna(0) na tabela inteira transformava AREA RURAL (sem par no cadastro,
    # L-20) em "taxa 0,0% e 3.558 faltantes" — número que não existe. A taxa e o
    # faltante só são calculados onde o denominador existe; onde não existe, a
    # célula fica vazia.
    tab = pd.concat([oferta, mat03, mat4, unidades, pop, pop03, freq03], axis=1)
    contagens = ["matriculas_creche_2024", "matriculas_creche_0_3",
                 "matriculas_creche_4_mais", "unidades_com_creche_2025"]
    tab[contagens] = tab[contagens].fillna(0)
    # RA que não existe na série de matrículas não tem contagem zero: não tem
    # série. AREA RURAL é o caso (L-20) — marcar 0 ali inventa uma taxa de 0,0%
    # com denominador real (7.115 crianças de 0–3 na PDAD).
    ras_na_serie = set(m["ra"].dropna())
    tab.loc[~tab.index.isin(ras_na_serie), contagens] = float("nan")
    denom = tab["pop_0_4_2024"].where(tab["pop_0_4_2024"] > 0)
    tab["taxa_atendimento_pct"] = (100 * tab["matriculas_creche_2024"] / denom).round(1)
    # a taxa em 0–3 usa numerador e denominador na mesma faixa (com a ressalva de
    # que a matrícula usa idade no Censo e a PDAD usa idade na entrevista)
    denom03 = tab["pop_0_3_2024"].where(tab["pop_0_3_2024"] > 0)
    tab["taxa_atendimento_0_3_pct"] = (100 * tab["matriculas_creche_0_3"] / denom03).round(1)
    # estimativa: meta de 50% das crianças (referência usual de cobertura de creche)
    tab["faltam_para_50pct"] = (0.5 * tab["pop_0_4_2024"] - tab["matriculas_creche_2024"]).round(0)
    tab["faltam_para_50pct_0_3"] = (0.5 * tab["pop_0_3_2024"] - tab["matriculas_creche_0_3"]).round(0)
    tab = tab.sort_values("taxa_atendimento_0_3_pct")
    tab.index.name = "ra"
    tab.to_csv(INTERIM / "q5_creche.csv")
    print("\n== Q5 creche: matrículas 2024 × população (PDAD-A 2024)")
    print("   taxa_atendimento_pct usa 0–4 nos dois lados (limite inferior do atendimento);")
    print("   taxa_atendimento_0_3_pct usa 0–3 nos dois lados; freq_pdad_0_3_pct é a")
    print("   frequência autodeclarada da PDAD, que não é a mesma coisa que matrícula no Censo.")
    print(tab.to_string())
    print(
        f"\ntotal DF: {tab['matriculas_creche_2024'].sum():.0f} matrículas em creche; "
        f"{tab['pop_0_4_2024'].sum():.0f} crianças de 0–4 (PDF) e {tab['pop_0_3_2024'].sum():.0f} de 0–3 (microdado); "
        f"taxa 0–4 {100*tab['matriculas_creche_2024'].sum()/tab['pop_0_4_2024'].sum():.1f}%, "
        f"taxa 0–3 {100*tab['matriculas_creche_0_3'].sum()/tab['pop_0_3_2024'].sum():.1f}%"
    )
    print(
        f"dessas matrículas, {tab['matriculas_creche_0_3'].sum():.0f} são de crianças de 0–3 anos e "
        f"{tab['matriculas_creche_4_mais'].sum():.0f} de 4 anos ou mais no ano do Censo"
    )
    print(
        "atenção: IDADE é idade no ano do Censo e o corte de matrícula é 31/03; criança de "
        "'4 anos' pode estar em idade de creche. Ver a correção em REPORT.md §2.5 — o valor "
        "de 4 anos ou mais NÃO mede distorção idade-etapa."
    )


# ---------------------------------------------------------------- Q6
def q6() -> None:
    perfis = pd.read_csv(INTERIM / "profile_files.csv")
    print("\n== Q6 qualidade")
    print("\nano declarado no nome × ano dentro do dado:")
    sem_dic = perfis[(perfis.familia != "dicionario") & perfis["ano_no_dado"].notna()]
    trocas = sem_dic[sem_dic["ano_no_nome"].astype(str) != sem_dic["ano_no_dado"].astype(str)]
    print(
        trocas.assign(ano_no_dado=lambda d: d["ano_no_dado"].str.slice(0, 30))[
            ["arquivo", "familia", "ano_no_nome", "ano_no_dado", "linhas"]
        ].to_string(index=False)
    )
    a16 = pd.read_parquet(S / "infraestrutura__relatorio_infraestrutura_2016.parquet")
    a17 = pd.read_parquet(S / "infraestrutura__relatorio_infraestrutura_2017.parquet")
    print(f"   infraestrutura '2016' idêntica à '2017': {a16.equals(a17)}")

    print("\ncolunas por ano, por família (mudança de esquema):")
    print(
        perfis.pivot_table(index="ano_no_nome", columns="familia", values="colunas", aggfunc="max")
        .to_string()
    )

    # escolas que aparecem e desaparecem
    e = carrega("escolas")
    e["codigo"] = e["CO_ENTIDADE"].astype(str).str.strip()
    e["ano_d"] = e["NU_ANO_CENSO"] if "NU_ANO_CENSO" in e else e["Ano do Censo"]
    anos = sorted(e["ano_d"].unique())
    primeira = e.groupby("codigo")["ano_d"].min()
    ultima = e.groupby("codigo")["ano_d"].max()
    print(f"\nunidades distintas em toda a série: {e['codigo'].nunique()}")
    print(f"aparecem só em 2025 (novas ou recém-cadastradas): {int((primeira == '2025').sum())}")
    print(f"desaparecem antes de 2025 (fechadas ou não cadastradas): {int((ultima < '2025').sum())}")
    saida = pd.DataFrame({"primeiro_ano": primeira, "ultimo_ano": ultima, "nome": e.groupby("codigo")["Nome da escola"].last()})
    saida.to_csv(INTERIM / "q6_unidades_churn.csv")

    # nomes repetidos com códigos diferentes
    nomes = e[e["ano_d"] == "2025"].groupby("Nome da escola")["codigo"].nunique()
    print(f"nomes de escola repetidos com códigos diferentes em 2025: {int((nomes > 1).sum())}")
    if (nomes > 1).any():
        print(nomes[nomes > 1].head(10).to_string())

    # anos parciais
    print("\nlinhas por ano nas famílias com série:")
    for fam in ("matriculas", "situacao", "infraestrutura", "escolas"):
        sub = perfis[perfis.familia == fam][["ano_no_nome", "linhas", "entidades_distintas"]]
        print(f"  {fam}: " + "; ".join(f"{r.ano_no_nome}={r.linhas}" for r in sub.itertuples()))


def q7() -> None:
    """Posição do DF entre as UFs no Ideb, por etapa e por rede."""
    arq = INTERIM / "inep" / "ideb_uf_tidy.parquet"
    if not arq.exists():
        raise Pulado("falta data/interim/inep/ideb_uf_tidy.parquet (rode 08)")
    t = pd.read_parquet(arq)
    t = t[(t["indicador"] == "ideb_observado") & t["valor"].notna()]
    ufs = set(t["local"]) - {"Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"}
    linhas = []
    for etapa in ["AI", "AF", "EM"]:
        for ano in ["2023", "2025"]:
            for rede in ["Total", "Pública", "Estadual", "Privada"]:
                sub = t[(t.etapa == etapa) & (t.ano == ano) & (t["local"].isin(ufs)) & (t.rede_base == rede)]
                if sub.empty:
                    continue
                df_v = sub.loc[sub["local"] == "Distrito Federal", "valor"]
                if df_v.empty:
                    continue
                df_v = df_v.iloc[0]
                linhas.append(
                    {
                        "etapa": etapa,
                        "ano": ano,
                        "rede": rede,
                        "df": df_v,
                        "posicao": int((sub["valor"] > df_v).sum()) + 1,
                        "n_ufs": len(sub),
                        "mediana_ufs": round(sub["valor"].median(), 2),
                        "melhor": sub.loc[sub["valor"].idxmax(), "local"],
                        "melhor_valor": sub["valor"].max(),
                    }
                )
    tab = pd.DataFrame(linhas)
    tab.to_csv(INTERIM / "q7_ideb_uf.csv", index=False)
    print("\n== Q7 Ideb do DF entre as UFs (divulgacao_regioes_ufs_ideb_2025.zip)")
    print(tab.to_string(index=False))
    co = t[(t.etapa.isin(["AI", "AF", "EM"])) & (t["local"] == "Centro-Oeste") & (t.ano == "2025")]
    print("\nCentro-Oeste 2025:", co[["etapa", "rede", "valor"]].to_string(index=False))

    # Composição: por que a linha "Total" do DF não representa a rede pública.
    # Fonte: relatorio_matriculas_2024.csv (Censo 2024), colunas MAT_EF_TOTAL e
    # MAT_EM_TOTAL somadas por NO_REDE. Célula anulada não entra como zero.
    mat = pd.read_parquet(S / "matriculas__relatorio_matriculas_2024.parquet")
    comp = []
    for etapa, coluna in [("AI+AF", "MAT_EF_TOTAL"), ("EM", "MAT_EM_TOTAL")]:
        v = pd.to_numeric(mat[coluna], errors="coerce")
        g = v.groupby(mat["NO_REDE"]).sum(min_count=1)
        total = g.sum()
        for rede, valor in g.items():
            comp.append(
                {
                    "etapa": etapa,
                    "rede": NOME_REDE.get(rede, rede),
                    "matriculas": int(valor),
                    "percentual": round(valor / total * 100, 1),
                }
            )
    comp_df = pd.DataFrame(comp)
    comp_df.to_csv(INTERIM / "q7_matriculas_por_rede.csv", index=False)
    print("\nMatrículas de 2024 por rede (relatorio_matriculas_2024.csv):")
    print(comp_df.to_string(index=False))


# ---------------------------------------------------------------- Q8
REDE_INEP = {
    "pública federal": "Federal",
    "pública estadual (SEEDF)": "Estadual",
    "pública estadual (não vinculada)": "Estadual",
    "privada conveniada": "Privada",
    "privada não conveniada": "Privada",
}
LOCAIS_AGREGADOS = {"Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"}


def _distribuicao(serie: pd.Series) -> dict:
    """Mediana, p10, p90, mínimo e máximo — sobre os valores existentes.

    Série vazia devolve `None`, não zero: escola sem Ideb não entra em nenhuma
    estatística, e um grupo inteiro sem Ideb não vira "média 0".
    """
    v = serie.dropna()
    if v.empty:
        return {"com_ideb": 0, "mediana": None, "p10": None, "p90": None,
                "minimo": None, "maximo": None}
    return {
        "com_ideb": int(v.size),
        "mediana": round(float(v.median()), 2),
        "p10": round(float(v.quantile(0.10)), 2),
        "p90": round(float(v.quantile(0.90)), 2),
        "minimo": round(float(v.min()), 2),
        "maximo": round(float(v.max()), 2),
    }


def _ideb_uf_tabela() -> pd.DataFrame:
    """Monta a tabela DF × Brasil × UFs, por etapa, ano e rede (2023 e 2025).

    Entrada: `data/interim/inep/{ideb_uf_tidy, brasil_ideb_tidy}.parquet`
    (gravados por `08_profile_inep.py`).
    Saída: o DataFrame de `q8_df_brasil_uf.csv` e do parquet publicado
    `ideb_uf.parquet`; falha com `ExportError` se o insumo da INEP faltar, para
    que uma tabela não desapareça em silêncio.
    Idempotente: sim — só lê.
    """
    arquivos = {
        "uf": INTERIM / "inep" / "ideb_uf_tidy.parquet",
        "brasil": INTERIM / "inep" / "brasil_ideb_tidy.parquet",
    }
    faltando = [n for n, p in arquivos.items() if not p.exists()]
    if faltando:
        raise ExportError(
            f"falta {faltando} em data/interim/inep para a tabela de Ideb por UF "
            "(rode 08_profile_inep.py)"
        )
    uf = pd.read_parquet(arquivos["uf"])
    br = pd.read_parquet(arquivos["brasil"])
    uf = uf[(uf["indicador"] == "ideb_observado") & uf["valor"].notna()]
    br = br[(br["indicador"] == "ideb_observado") & br["valor"].notna()]

    locais_uf = set(uf["local"]) - LOCAIS_AGREGADOS
    linhas = []
    for etapa in ("AI", "AF", "EM"):
        for ano in ("2023", "2025"):
            for rede in ("Total", "Pública", "Estadual", "Privada"):
                s_uf = uf[
                    (uf.etapa == etapa) & (uf.ano == ano)
                    & uf["local"].isin(locais_uf) & (uf.rede_base == rede)
                ]
                s_br = br[(br.etapa == etapa) & (br.ano == ano) & (br.rede_base == rede)]
                if s_uf.empty and s_br.empty:
                    continue
                df_v = s_uf.loc[s_uf["local"] == "Distrito Federal", "valor"]
                df_v = float(df_v.iloc[0]) if not df_v.empty else None
                br_v = float(s_br["valor"].iloc[0]) if not s_br.empty else None
                linhas.append(
                    {
                        "etapa": etapa,
                        "ano": ano,
                        "rede": rede,
                        "df": round(df_v, 2) if df_v is not None else None,
                        "brasil": round(br_v, 2) if br_v is not None else None,
                        "df_menos_brasil": (
                            round(df_v - br_v, 2)
                            if df_v is not None and br_v is not None else None
                        ),
                        "posicao": (
                            int((s_uf["valor"] > df_v).sum()) + 1
                            if df_v is not None else None
                        ),
                        "n_ufs": int(len(s_uf)) if df_v is not None else None,
                        "mediana_ufs": (
                            round(float(s_uf["valor"].median()), 2)
                            if df_v is not None else None
                        ),
                    }
                )
    tab = pd.DataFrame(linhas)
    for c in ("posicao", "n_ufs"):
        tab[c] = tab[c].astype("Int64")
    return tab


def q8() -> None:
    """Ideb do DF contra o Brasil e evidência por escola, por rede (2023 e 2025).

    Entradas: `data/interim/inep/{ideb_uf_tidy, brasil_ideb_tidy,
    ideb_escolas_df}.parquet` (gravados por `08_profile_inep.py`) e o cadastro
    de 2025 em `data/interim/seedf/`.
    Saídas: `q8_df_brasil_uf.csv`, `q8_escolas_rede.csv`,
    `q8_cobertura_escolas_2025.csv`, `q8_conferencia_seedf.csv`.
    Idempotente: sim — leitura e reescrita das saídas.
    """
    arquivos = {
        "uf": INTERIM / "inep" / "ideb_uf_tidy.parquet",
        "brasil": INTERIM / "inep" / "brasil_ideb_tidy.parquet",
        "escolas": INTERIM / "inep" / "ideb_escolas_df.parquet",
    }
    faltando = [n for n, p in arquivos.items() if not p.exists()]
    if faltando:
        print(f"\n== Q8 não executado: falta {faltando} em data/interim/inep (rode 08)")
        return

    esc = pd.read_parquet(arquivos["escolas"])
    esc = esc[esc["indicador"] == "ideb_observado"]

    # 1. DF × Brasil × mediana das UFs, por etapa, rede e ano.
    tab = _ideb_uf_tabela()
    tab.to_csv(INTERIM / "q8_df_brasil_uf.csv", index=False)
    print("\n== Q8 Ideb do DF contra o Brasil e as UFs (2023 e 2025)")
    print(tab.to_string(index=False))
    print(
        "   ensino médio: a planilha de UF não publica a linha 'Pública' (só Total, "
        "Privada e Estadual); a do Brasil publica. Por isso EM/Pública tem Brasil "
        "e não tem posição."
    )

    # 2. Ideb por escola no DF, por etapa e rede — quantas escolas e como se distribui.
    linhas = []
    for etapa in ("AI", "AF", "EM"):
        for ano in ("2023", "2025"):
            for rede in sorted(esc.loc[esc.etapa == etapa, "REDE"].unique()):
                sub = esc[(esc.etapa == etapa) & (esc.ano == ano) & (esc.REDE == rede)]
                if sub.empty:
                    continue
                st = _distribuicao(sub["valor"])
                linhas.append(
                    {
                        "etapa": etapa,
                        "ano": ano,
                        "rede": rede,
                        "escolas_listadas": int(sub["ID_ESCOLA"].nunique()),
                        "sem_ideb": int(sub["valor"].isna().sum()),
                        "pct_sem_ideb": round(100 * sub["valor"].isna().mean(), 1),
                        **st,
                    }
                )
    tab = pd.DataFrame(linhas)
    tab.to_csv(INTERIM / "q8_escolas_rede.csv", index=False)
    print("\n== Q8 Ideb 2025 por escola no DF (ideb_escolas_df.parquet)")
    print(tab[tab.ano == "2025"].to_string(index=False))
    priv = esc[(esc.etapa == "EM") & (esc.REDE == "Privada")]
    print(
        f"   privada no ensino médio do DF: {priv['ID_ESCOLA'].nunique()} escolas listadas, "
        f"{int(priv.loc[priv.ano == '2017', 'valor'].notna().sum())} com Ideb em 2017, "
        f"{int(priv.loc[priv.ano == '2025', 'valor'].notna().sum())} com Ideb em 2025"
    )

    # 3. Cobertura contra o cadastro de 2025: quantas escolas da oferta atual têm Ideb.
    cad = pd.read_parquet(S / "escolas__relatorio_escolas_2025.parquet").copy()
    cad["codigo"] = cad["CO_ENTIDADE"].astype(str).str.strip()
    cad["rede_inep"] = cad["Nome Rede"].map(NOME_REDE).map(REDE_INEP)
    linhas = []
    for etapa, flag in (("AI", "FUND_AI"), ("AF", "FUND_AF"), ("EM", "MED")):
        base = cad[num(cad[flag]) == 1]
        oferta = esc[(esc.etapa == etapa) & (esc.ano == "2025")]
        for rede in ("Estadual", "Federal", "Privada"):
            n_cad = int((base["rede_inep"] == rede).sum())
            no_inep = oferta[oferta.REDE == rede]
            codigos_cad = set(base.loc[base["rede_inep"] == rede, "codigo"])
            com = no_inep[no_inep["valor"].notna()]
            com_no_cad = int(com["ID_ESCOLA"].isin(codigos_cad).sum())
            linhas.append(
                {
                    "etapa": etapa,
                    "rede": rede,
                    "escolas_cadastro_2025": n_cad,
                    "linhas_inep": int(len(no_inep)),
                    "linhas_inep_na_oferta_2025": int(
                        no_inep["ID_ESCOLA"].isin(codigos_cad).sum()
                    ),
                    "com_ideb_2025": int(com["valor"].notna().sum()),
                    "com_ideb_2025_na_oferta_2025": com_no_cad,
                    "cobertura_pct": round(100 * com_no_cad / n_cad, 1) if n_cad else None,
                }
            )
    tab = pd.DataFrame(linhas)
    tab.to_csv(INTERIM / "q8_cobertura_escolas_2025.csv", index=False)
    print("\n== Q8 cobertura: cadastro 2025 × Ideb por escola (relatorio_escolas_2025.csv)")
    print(tab.to_string(index=False))

    # 4. Conferência: a republicação da SEEDF bate valor a valor com a INEP?
    fontes = {
        "AI": "ideb_serie__ideb_ef_ai_2005_2025_ckan1.parquet",
        "AF": "ideb_serie__ideb_ef_af_2005_2025.parquet",
        "EM": "ideb_serie__ideb_em_2017_2025.parquet",
    }
    linhas = []
    for etapa, arq in fontes.items():
        d = pd.read_parquet(S / arq)
        c_ind = "indicador" if "indicador" in d else "Indicador"
        c_cod = "cod_inep" if "cod_inep" in d else "Cód_Inep"
        c_ano = "ano" if "ano" in d else "Ano"
        c_val = "valor" if "valor" in d else "Valor"
        d = d[d[c_ind] == "IDEB"].copy()
        d["valor_seedf"] = num(d[c_val])
        d["codigo"] = d[c_cod].astype(str).str.strip()
        d["ano"] = d[c_ano].astype(str)
        x = d.loc[d["valor_seedf"].notna(), ["codigo", "ano", "valor_seedf"]]
        y = esc.loc[
            (esc.etapa == etapa) & esc["valor"].notna(), ["ID_ESCOLA", "ano", "valor"]
        ].rename(columns={"ID_ESCOLA": "codigo", "valor": "valor_inep"})
        j = x.merge(y, on=["codigo", "ano"], how="outer", indicator=True)
        ambos = j[j["_merge"] == "both"]
        iguais = int(((ambos["valor_seedf"] - ambos["valor_inep"]).abs() < 1e-9).sum())
        linhas.append(
            {
                "etapa": etapa,
                "valores_seedf": int(len(x)),
                "valores_inep": int(len(y)),
                "ambos": int(len(ambos)),
                "iguais": iguais,
                "diferentes": int(len(ambos)) - iguais,
                "so_seedf": int((j["_merge"] == "left_only").sum()),
                "so_inep": int((j["_merge"] == "right_only").sum()),
            }
        )
    tab = pd.DataFrame(linhas)
    tab.to_csv(INTERIM / "q8_conferencia_seedf.csv", index=False)
    print("\n== Q8 conferência valor a valor: série da SEEDF × Ideb por escola da INEP")
    print(tab.to_string(index=False))
    print(
        "   leitura: a série da SEEDF é a republicação fiel da INEP para o DF — "
        "mesmas escolas, mesma ausência, mesmos valores."
    )


def q9() -> None:
    """Testa o último lugar do DF no ensino médio com o integrado à EPT.

    Entrada: `data/interim/inep/ideb_uf_em_integrado_tidy.parquet` (gravado por
    `08_profile_inep.py`) e `data/interim/q8_df_brasil_uf.csv` para a linha do
    médio regular.
    Saída: `data/interim/q9_em_integrado.csv`.
    Idempotente: sim — leitura e reescrita.

    A planilha do integrado inclui, no Saeb, os estudantes do médio propedêutico
    e da educação profissional técnica integrada ao médio; a divulgação regular
    exclui os do integrado para preservar a comparabilidade histórica. São dois
    recortes do mesmo indicador, e o DF pode mudar de posição entre eles.
    """
    arq = INTERIM / "inep" / "ideb_uf_em_integrado_tidy.parquet"
    q8 = INTERIM / "q8_df_brasil_uf.csv"
    if not arq.exists() or not q8.exists():
        print("\n== Q9 não executado: falta parquet do EM integrado (rode 08) ou q8")
        return
    t = pd.read_parquet(arq)
    t = t[(t["indicador"] == "ideb_observado") & t["valor"].notna()]
    regular = pd.read_csv(q8)
    regular["ano"] = regular["ano"].astype(str)
    linhas = []
    for ano in ("2023", "2025"):
        sub = t[t.ano == ano]
        df_v = sub.loc[sub["local"] == "Distrito Federal", "valor"]
        if df_v.empty:
            continue
        df_v = float(df_v.iloc[0])
        acima = sub.loc[sub["valor"] > df_v, "valor"]
        reg = regular[(regular.etapa == "EM") & (regular.rede == "Estadual")
                      & (regular.ano == ano)]
        reg = reg.iloc[0] if not reg.empty else None
        linhas.append(
            {
                "ano": ano,
                "df_integrado": round(df_v, 2),
                "posicao_integrado": int(len(acima)) + 1,
                "n_ufs_integrado": int(len(sub)),
                "mediana_ufs_integrado": round(float(sub["valor"].median()), 2),
                "proximo_valor": round(float(acima.min()), 2) if len(acima) else None,
                "ufs_empatadas": int((sub["valor"] == df_v).sum()),
                "df_regular": round(float(reg["df"]), 2) if reg is not None else None,
                "posicao_regular": int(reg["posicao"]) if reg is not None else None,
                "n_ufs_regular": int(reg["n_ufs"]) if reg is not None else None,
                "mediana_ufs_regular": (
                    round(float(reg["mediana_ufs"]), 2) if reg is not None else None
                ),
                "diferenca_integrado_regular": (
                    round(df_v - float(reg["df"]), 2) if reg is not None else None
                ),
            }
        )
    tab = pd.DataFrame(linhas)
    tab.to_csv(INTERIM / "q9_em_integrado.csv", index=False)
    print("\n== Q9 ensino médio com o integrado à EPT × médio regular (rede estadual)")
    print(tab.to_string(index=False))
    print("\n   ranking 2025 (integrado), do pior para o melhor:")
    ordem = t[t.ano == "2025"].sort_values("valor")[["local", "valor"]]
    print(ordem.to_string(index=False))


def q10() -> None:
    """Fluxo escolar (aprovação, reprovação, abandono) por rede no DF em 2025.

    Entrada: `data/interim/inep/tx_rend_escolas_df.parquet` (gravado por
    `08_profile_inep.py`).
    Saída: `data/interim/q10_fluxo_df.csv`.
    Idempotente: sim — leitura e reescrita.

    As taxas são por escola, não ponderadas por matrícula: a mediana descreve a
    escola típica da rede, não o aluno típico. `'--'` (não aplicável) e zero são
    estados distintos e contam separado.
    """
    arq = INTERIM / "inep" / "tx_rend_escolas_df.parquet"
    if not arq.exists():
        print("\n== Q10 não executado: falta tx_rend_escolas_df.parquet (rode 08)")
        return
    t = pd.read_parquet(arq)
    t = t[t["NU_ANO_CENSO"] == "2025"]
    linhas = []
    for recorte, etapa in (("FUN_AI", "anos iniciais"), ("FUN_AF", "anos finais"), ("MED", "ensino médio")):
        for rede in ("Estadual", "Federal", "Privada"):
            sub = t[(t.recorte == recorte) & (t.NO_DEPENDENCIA == rede)]
            if sub.empty:
                continue
            n_escolas = sub["CO_ENTIDADE"].nunique()
            for categoria in ("aprovacao", "reprovacao", "abandono"):
                s = sub[sub.categoria == categoria]
                st = _distribuicao(s["valor"])
                linhas.append(
                    {
                        "etapa": etapa,
                        "rede": rede,
                        "categoria": categoria,
                        "escolas_da_rede": int(n_escolas),
                        "com_valor": st["com_ideb"],
                        "pct_da_rede_com_valor": round(100 * st["com_ideb"] / n_escolas, 1) if n_escolas else None,
                        "mediana": st["mediana"],
                        "p10": st["p10"],
                        "p90": st["p90"],
                        "zeros": int((s["valor"] == 0).sum()),
                        "pct_zeros": round(100 * (s["valor"] == 0).sum() / n_escolas, 1) if n_escolas else None,
                    }
                )
    tab = pd.DataFrame(linhas)
    tab.to_csv(INTERIM / "q10_fluxo_df.csv", index=False)
    print("\n== Q10 fluxo escolar 2025 por rede (tx_rend_escolas_2025.zip)")
    print(
        tab.pivot_table(index=["etapa", "rede"], columns="categoria", values="mediana")
        .round(1)
        .to_string()
    )
    print("\n   escolas com valor (da rede no arquivo):")
    print(
        tab[tab.categoria == "aprovacao"][["etapa", "rede", "escolas_da_rede", "com_valor", "pct_da_rede_com_valor"]]
        .to_string(index=False)
    )

    # conferência: aprovação + reprovação + abandono = 100 por escola × recorte
    p = t[t["valor"].notna()].pivot_table(
        index=["CO_ENTIDADE", "recorte"], columns="categoria", values="valor"
    )
    soma = (p["aprovacao"] + p["reprovacao"] + p["abandono"]).dropna()
    print(
        f"\n   conferência: {len(soma)} pares escola × recorte com as três taxas; "
        f"desvio máximo de 100 = {float((soma - 100).abs().max()):.2e}"
    )


def q11() -> None:
    """Distorção idade-série por rede e etapa no DF em 2025 (INEP/TDI).

    Entrada: `data/interim/inep/tdi_escolas_df.parquet` (gravado por
    `08_profile_inep.py`).
    Saída: `data/interim/q11_distorcao_df.csv`.
    Idempotente: sim — leitura e reescrita.

    A TDI é taxa por escola: a mediana descreve a escola típica da rede, não o
    aluno típico — a taxa não é ponderada por matrícula. `'--'` (sem matrícula
    naquele recorte) não entra em estatística nenhuma; `0` é zero medido e entra.
    Nenhuma escola é listada: só distribuição por rede e etapa.
    """
    arq = INTERIM / "inep" / "tdi_escolas_df.parquet"
    if not arq.exists():
        print("\n== Q11 não executado: falta tdi_escolas_df.parquet (rode 08)")
        return
    t = pd.read_parquet(arq)
    t = t[t["NU_ANO_CENSO"] == "2025"]
    linhas = []
    for recorte, etapa in (("FUN_AI", "anos iniciais"), ("FUN_AF", "anos finais"),
                           ("MED", "ensino médio")):
        for rede in ("Estadual", "Privada", "Federal"):
            sub = t[(t.recorte == recorte) & (t.NO_DEPENDENCIA == rede)]
            if sub.empty:
                continue
            st = _distribuicao(sub["valor"])
            linhas.append(
                {
                    "etapa": etapa,
                    "rede": rede,
                    "escolas_no_arquivo": int(sub["CO_ENTIDADE"].nunique()),
                    "com_valor": st["com_ideb"],
                    "nao_aplicavel": int((sub["estado"] == "nao_aplicavel").sum()),
                    "zeros": int((sub["valor"] == 0).sum()),
                    "mediana": st["mediana"],
                    "p10": st["p10"],
                    "p90": st["p90"],
                    "minimo": st["minimo"],
                    "maximo": st["maximo"],
                }
            )
    tab = pd.DataFrame(linhas)
    tab.to_csv(INTERIM / "q11_distorcao_df.csv", index=False)
    print("\n== Q11 distorção idade-série 2025 por rede (tdi_escolas_df.parquet)")
    print(
        tab.pivot_table(index="rede", columns="etapa", values="mediana")
        .reindex(columns=["anos iniciais", "anos finais", "ensino médio"])
        .to_string()
    )
    print("\n   distribuição completa (mediana; p10–p90):")
    for r in tab.itertuples():
        faixa = (
            f"{r.p10:.1f}–{r.p90:.1f}" if pd.notna(r.mediana) else "sem valor"
        )
        print(
            f"     {r.etapa:<14} {r.rede:<8} n={r.com_valor:>3} com taxa "
            f"({r.escolas_no_arquivo:>3} no arquivo); "
            f"mediana {r.mediana if pd.notna(r.mediana) else '—'}; {faixa}; "
            f"'--'={r.nao_aplicavel}; zeros={r.zeros}"
        )


def q12() -> None:
    """A taxa de não-resposta (TNR) explica o Ideb ausente em 2025?

    Entrada: `data/interim/inep/tnr_escolas_df.parquet` e
             `data/interim/inep/ideb_escolas_df.parquet` (08) e o cadastro de
             2025 em `data/interim/seedf/`.
    Saída:   `data/interim/q12_tnr_ideb_ausente.csv` e
             `data/interim/q12_tnr_nao_aplicavel.csv`.
    Idempotente: sim — leitura e reescrita.

    A hipótese do catálogo era que a TNR diria, por escola, se o Ideb ausente é
    não participação no Saeb ou resultado suprimido. Ela é testada aqui, não
    assumida: a TNR mede o percentual de alunos **sem informação de
    rendimento/movimento** no Censo Escolar e não tem campo de participação no
    Saeb. O teste empírico compara a distribuição da TNR entre as escolas com e
    sem Ideb; se as duas distribuições se sobrepõem, a TNR não separa os grupos.
    """
    tnr_arq = INTERIM / "inep" / "tnr_escolas_df.parquet"
    ideb_arq = INTERIM / "inep" / "ideb_escolas_df.parquet"
    cad_arq = S / "escolas__relatorio_escolas_2025.parquet"
    if not tnr_arq.exists() or not ideb_arq.exists() or not cad_arq.exists():
        print("\n== Q12 não executado: falta tnr, ideb por escola (rode 08) ou cadastro (rode 03)")
        return
    t = pd.read_parquet(tnr_arq)
    t = t[t["NU_ANO_CENSO"] == "2025"]
    esc = pd.read_parquet(ideb_arq)
    esc = esc[(esc["indicador"] == "ideb_observado") & (esc["ano"] == "2025")]
    cad = pd.read_parquet(cad_arq).copy()
    cad["codigo"] = cad["CO_ENTIDADE"].astype(str).str.strip()
    flags = {"AI": "FUND_AI", "AF": "FUND_AF", "EM": "MED"}

    linhas, nao_aplicavel = [], []
    for etapa, recorte in (("AI", "FUN_AI"), ("AF", "FUN_AF"), ("EM", "MED")):
        for rede in ("Estadual", "Federal", "Privada"):
            e = esc[(esc.etapa == etapa) & (esc.REDE == rede)]
            if e.empty:
                continue
            sub = t[(t.recorte == recorte) & (t.NO_DEPENDENCIA == rede)]
            sem = set(e.loc[e.valor.isna(), "ID_ESCOLA"])
            com = set(e.loc[e.valor.notna(), "ID_ESCOLA"])
            t_sem = sub[sub["CO_ENTIDADE"].isin(sem)]
            t_com = sub[sub["CO_ENTIDADE"].isin(com)]
            st_com = _distribuicao(t_com["valor"])
            st_sem = _distribuicao(t_sem["valor"])
            linhas.append(
                {
                    "etapa": etapa,
                    "rede": rede,
                    "ideb_listadas": int(e["ID_ESCOLA"].nunique()),
                    "ideb_com_valor": len(com),
                    "ideb_sem_valor": len(sem),
                    "tnr_escolas_sem_ideb": int(t_sem["CO_ENTIDADE"].nunique()),
                    "tnr_com_taxa_na_rede": int(sub["valor"].notna().sum()),
                    "tnr_nao_aplicavel_sem_ideb": int((t_sem["estado"] == "nao_aplicavel").sum()),
                    "tnr_com_taxa_sem_ideb": st_sem["com_ideb"],
                    "tnr_zero_sem_ideb": int((t_sem["valor"] == 0).sum()),
                    "tnr_mediana_com_ideb": st_com["mediana"],
                    "tnr_p10_com_ideb": st_com["p10"],
                    "tnr_p90_com_ideb": st_com["p90"],
                    "tnr_mediana_sem_ideb": st_sem["mediana"],
                    "tnr_p10_sem_ideb": st_sem["p10"],
                    "tnr_p90_sem_ideb": st_sem["p90"],
                }
            )
            if t_sem["estado"].eq("nao_aplicavel").any():
                na = t_sem[t_sem["estado"] == "nao_aplicavel"]
                oferta = pd.to_numeric(
                    cad.set_index("codigo").reindex(na["CO_ENTIDADE"])[flags[etapa]],
                    errors="coerce",
                )
                nao_aplicavel.append(
                    {
                        "etapa": etapa,
                        "rede": rede,
                        "escolas_sem_ideb": len(sem),
                        "tnr_nao_aplicavel": len(na),
                        "oferta_ausente_no_cadastro_2025": int((oferta == 0).sum()),
                        "oferta_presente_no_cadastro_2025": int((oferta == 1).sum()),
                        "fora_do_cadastro_2025": int(oferta.isna().sum()),
                    }
                )

    tab = pd.DataFrame(linhas)
    tab.to_csv(INTERIM / "q12_tnr_ideb_ausente.csv", index=False)
    ids_ideb = set(esc["ID_ESCOLA"])
    ids_tnr = set(t["CO_ENTIDADE"])
    cad_cod = set(cad["codigo"])
    print("\n== Q12 taxa de não-resposta 2025 × Ideb ausente (tnr_escolas_2025.zip)")
    print(
        f"   junção medida antes de qualquer comparação: {len(ids_ideb & ids_tnr)} de "
        f"{len(ids_ideb)} IDs de escola do Ideb 2025 estão na TNR "
        f"({100 * len(ids_ideb & ids_tnr) / len(ids_ideb):.1f}%); {len(ids_ideb & cad_cod)} de "
        f"{len(ids_ideb)} estão no cadastro de 2025 ({100 * len(ids_ideb & cad_cod) / len(ids_ideb):.1f}%)"
    )
    print(
        "   campos de origem da TNR: identificação "
        + ", ".join(("NU_ANO_CENSO", "NO_REGIAO", "SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO",
                     "CO_ENTIDADE", "NO_ENTIDADE", "NO_CATEGORIA", "NO_DEPENDENCIA"))
        + f"; {t['campo'].nunique()} taxas no padrão 4_CAT_<recorte>"
    )
    print("   recortes da TNR: " + ", ".join(sorted(t["recorte"].unique())))
    print(
        "   a TNR não tem campo de participação no Saeb nem de resultado suprimido: "
        "mede alunos sem informação de rendimento/movimento no Censo Escolar."
    )
    print(
        "\n"
        + tab[
            ["etapa", "rede", "ideb_listadas", "ideb_com_valor", "ideb_sem_valor",
             "tnr_com_taxa_na_rede", "tnr_mediana_com_ideb", "tnr_mediana_sem_ideb",
             "tnr_nao_aplicavel_sem_ideb"]
        ].to_string(index=False)
    )
    print("\n   distribuições completas (p10–p90):")
    for r in tab.itertuples():
        if r.ideb_sem_valor == 0:
            continue
        faixa_com = (
            f"{r.tnr_p10_com_ideb:.1f}–{r.tnr_p90_com_ideb:.1f}"
            if pd.notna(r.tnr_mediana_com_ideb) else "sem valor"
        )
        faixa_sem = (
            f"{r.tnr_p10_sem_ideb:.1f}–{r.tnr_p90_sem_ideb:.1f}"
            if pd.notna(r.tnr_mediana_sem_ideb) else "sem valor"
        )
        print(
            f"     {r.etapa} {r.rede:<8} com Ideb {r.tnr_mediana_com_ideb} ({faixa_com}); "
            f"sem Ideb {r.tnr_mediana_sem_ideb} ({faixa_sem}); "
            f"TNR no arquivo para {r.tnr_escolas_sem_ideb} de {r.ideb_sem_valor} sem Ideb"
        )
    priv = tab[(tab.etapa == "EM") & (tab.rede == "Privada")]
    if not priv.empty:
        r = priv.iloc[0]
        print(
            f"\n   privada no ensino médio: {r.ideb_listadas} escolas listadas no arquivo de "
            f"Ideb, {r.tnr_com_taxa_na_rede} com taxa na TNR — a TNR cobre a rede privada, "
            f"e o Ideb privado ausente não é não-resposta: é não publicação."
        )
    if nao_aplicavel:
        na_tab = pd.DataFrame(nao_aplicavel)
        na_tab.to_csv(INTERIM / "q12_tnr_nao_aplicavel.csv", index=False)
        print("\n   onde a TNR é '--' entre as escolas sem Ideb (não aplicável):")
        print(na_tab.to_string(index=False))
        print(
            "     leitura: '--' é a etapa sem matrícula na escola, e o cadastro de 2025 "
            "confirma oferta ausente em quase todos os casos — não é não participação."
        )


# ---------------------------------------------------------------- Censo
# Peso de cada etapa: a matrícula que o Censo 2025 declara por escola. É o
# denominador que faltava para transformar taxa por escola em taxa por aluno.
PESO_ETAPA = {
    "anos iniciais": "QT_MAT_FUND_AI",
    "anos finais": "QT_MAT_FUND_AF",
    "ensino médio": "QT_MAT_MED",
}
RECORTE_ETAPA = {"FUN_AI": "anos iniciais", "FUN_AF": "anos finais", "MED": "ensino médio"}
CODIGO_ETAPA = {"anos iniciais": "AI", "anos finais": "AF", "ensino médio": "EM"}


def _censo() -> pd.DataFrame:
    """Recorte do DF dos microdados do Censo (11_ingest_censo.py)."""
    arq = INTERIM / "inep" / "censo_escola_df.parquet"
    if not arq.exists():
        raise Pulado("falta data/interim/inep/censo_escola_df.parquet (rode 11)")
    c = pd.read_parquet(arq)
    c["CO_ENTIDADE"] = c["CO_ENTIDADE"].astype(str).str.strip()
    return c


def q13() -> None:
    """A leitura por escola contra a leitura por matrícula, no DF de 2025.

    Entrada: `data/interim/inep/{censo_escola_df, tdi_escolas_df,
             tx_rend_escolas_df, ideb_escolas_df}.parquet` e
             `data/interim/q8_df_brasil_uf.csv` (para a referência oficial).
    Saída:   `data/interim/q13_ponderacao_df.csv`.
    Idempotente: sim — leitura e reescrita.

    As medianas de q8, q10, q11 e q12 descrevem a **escola típica** da rede. Com
    a matrícula por escola × etapa do Censo 2025, a média ponderada descreve o
    **aluno típico** — que é outra coisa, e a diferença entre as duas é medida
    aqui, não suposta. Peso 0 é escola sem matrícula naquela etapa: ela não
    pesa, e o universo com peso > 0 é o que serve de denominador da cobertura.
    """
    censo = _censo()
    tdi_arq = INTERIM / "inep" / "tdi_escolas_df.parquet"
    tx_arq = INTERIM / "inep" / "tx_rend_escolas_df.parquet"
    ideb_arq = INTERIM / "inep" / "ideb_escolas_df.parquet"
    if not tdi_arq.exists() or not tx_arq.exists() or not ideb_arq.exists():
        raise Pulado("faltam os indicadores por escola (rode 08)")

    c25 = censo[censo["ano"] == 2025].copy()
    taxas = []

    t = pd.read_parquet(tdi_arq)
    t = t[(t["NU_ANO_CENSO"] == "2025") & t["valor"].notna()]
    for r in t.itertuples():
        if r.recorte not in RECORTE_ETAPA:
            continue
        taxas.append(
            {
                "indicador": "distorcao_idade_serie",
                "etapa": RECORTE_ETAPA[r.recorte],
                "rede": r.NO_DEPENDENCIA,
                "CO_ENTIDADE": str(r.CO_ENTIDADE).strip(),
                "valor": r.valor,
            }
        )

    t = pd.read_parquet(tx_arq)
    t = t[(t["NU_ANO_CENSO"] == "2025") & t["valor"].notna()]
    for r in t.itertuples():
        if r.recorte not in RECORTE_ETAPA:
            continue
        taxas.append(
            {
                "indicador": r.categoria,
                "etapa": RECORTE_ETAPA[r.recorte],
                "rede": r.NO_DEPENDENCIA,
                "CO_ENTIDADE": str(r.CO_ENTIDADE).strip(),
                "valor": r.valor,
            }
        )

    t = pd.read_parquet(ideb_arq)
    t = t[(t["ano"] == "2025") & (t["indicador"] == "ideb_observado") & t["valor"].notna()]
    for r in t.itertuples():
        taxas.append(
            {
                "indicador": "ideb_observado",
                "etapa": {v: k for k, v in CODIGO_ETAPA.items()}.get(r.etapa, r.etapa),
                "rede": r.REDE,
                "CO_ENTIDADE": str(r.ID_ESCOLA).strip(),
                "valor": r.valor,
            }
        )
    taxas = pd.DataFrame(taxas)

    oficial = pd.read_csv(INTERIM / "q8_df_brasil_uf.csv")
    oficial = oficial[oficial["ano"].astype(str) == "2025"]

    linhas = []
    for (indicador, etapa, rede), sub in taxas.groupby(["indicador", "etapa", "rede"]):
        peso_col = PESO_ETAPA[etapa]
        universo = c25[c25["rede"] == rede]
        # peso 0 = escola sem matrícula naquela etapa; nulo aqui é ausência de
        # matrícula declarada, e a escola não pesa (não é "nota zero")
        w_universo = universo[peso_col].fillna(0)
        s = sub.merge(
            c25[["CO_ENTIDADE", peso_col]],
            on="CO_ENTIDADE",
            how="left",
        )
        s["peso"] = s[peso_col].fillna(0)
        soma_peso = float(s["peso"].sum())
        ponderada = float((s["valor"] * s["peso"]).sum() / soma_peso) if soma_peso else None
        st = _distribuicao(s["valor"])
        base = {"indicador": indicador, "etapa": etapa, "rede": rede}
        # a referência oficial (Ideb da UF por rede) só existe para o Ideb; nas
        # taxas por escola não há valor oficial por rede para comparar
        ref = oficial[
            (oficial["etapa"] == CODIGO_ETAPA[etapa]) & (oficial["rede"] == rede)
        ] if indicador == "ideb_observado" else oficial.iloc[0:0]
        linhas.append(
            {
                **base,
                "escolas_da_rede_com_a_etapa": int((w_universo > 0).sum()),
                "escolas_com_valor": st["com_ideb"],
                "matricula_da_etapa": int(w_universo.sum()),
                "matricula_com_valor": int(soma_peso),
                "cobertura_matricula_pct": round(100 * soma_peso / w_universo.sum(), 1)
                if w_universo.sum()
                else None,
                "mediana": st["mediana"],
                "p10": st["p10"],
                "p90": st["p90"],
                "ponderada": round(ponderada, 2) if ponderada is not None else None,
                "diferenca_pp": round(ponderada - st["mediana"], 2)
                if ponderada is not None and st["mediana"] is not None
                else None,
                "referencia_oficial": float(ref["df"].iloc[0]) if len(ref) else None,
                "diferenca_vs_oficial": round(ponderada - float(ref["df"].iloc[0]), 2)
                if len(ref) and ponderada is not None
                else None,
            }
        )
    tab = pd.DataFrame(linhas)
    ordem_i = ["ideb_observado", "distorcao_idade_serie", "aprovacao", "reprovacao", "abandono"]
    ordem_e = {"anos iniciais": 0, "anos finais": 1, "ensino médio": 2}
    tab["_i"] = tab["indicador"].map({k: i for i, k in enumerate(ordem_i)})
    tab["_e"] = tab["etapa"].map(ordem_e)
    tab = tab.sort_values(["_i", "_e", "rede"]).drop(columns=["_i", "_e"])
    tab.to_csv(INTERIM / "q13_ponderacao_df.csv", index=False)

    print("\n== Q13 ponderação (Censo 2025 × indicadores por escola)")
    print(
        "   mediana = escola típica (o que q8/q10/q11 publicam); ponderada = aluno "
        "típico (peso = matrícula da etapa no Censo 2025)"
    )
    for indicador in ordem_i:
        sub = tab[tab.indicador == indicador]
        if sub.empty:
            continue
        print(f"\n   {indicador}:")
        print(
            sub[["etapa", "rede", "escolas_com_valor", "cobertura_matricula_pct",
                 "mediana", "ponderada", "diferenca_pp", "referencia_oficial"]]
            .to_string(index=False)
        )
    print(
        "\n   cobertura: entre as escolas que têm a etapa, a fração da matrícula "
        "coberta pelo indicador"
    )


def q14() -> None:
    """Creche: o lado da oferta no Censo, a idade exata e o fecho com a PDAD.

    Entrada: `data/interim/inep/censo_escola_df.parquet` (11),
             `data/interim/seedf/matriculas__relatorio_matriculas_2024.parquet`,
             `matriculas__2025_educa_dados_matricula_alt.parquet` (03) e
             `data/interim/pdad/pdad_frequencia.parquet` (10).
    Saída:   `data/interim/q14_creche_oferta.csv`, `q14_creche_idade.csv` e
             `q14_creche_fecho.csv`.
    Idempotente: sim — leitura e reescrita.

    Três contagens de "criança pequena na escola" que já circularam como se
    fossem a mesma: creche × idade no ano (26.076, série da SEEDF), faixa 0–3 do
    Censo (37.595) e 0–3 frequentando (37.654, PDAD). Aqui as três aparecem lado
    a lado com o cálculo de cada uma e com o teste que identifica a data de
    referência da faixa etária.
    """
    censo = _censo()

    # (1) oferta: unidades com creche e matrícula, por rede e ano
    oferta = []
    for ano in sorted(censo["ano"].unique()):
        c = censo[censo["ano"] == ano]
        for rede in ("Estadual", "Privada", "Federal", "Municipal"):
            sub = c[c["rede"] == rede]
            if sub.empty:
                continue
            com_creche = sub[sub["QT_MAT_INF_CRE"].fillna(0) > 0]
            oferta.append(
                {
                    "ano": ano,
                    "rede": rede,
                    "unidades_na_rede": len(sub),
                    "unidades_com_creche": len(com_creche),
                    "matriculas_creche": int(sub["QT_MAT_INF_CRE"].fillna(0).sum()),
                    "faixa_0_3_censo": int(sub["QT_MAT_BAS_0_3"].fillna(0).sum()),
                    "faixa_0_3_31_03": int(sub["QT_MAT_BAS_0_3_REF_31_03"].fillna(0).sum())
                    if sub["QT_MAT_BAS_0_3_REF_31_03"].notna().any()
                    else None,
                }
            )
        oferta.append(
            {
                "ano": ano,
                "rede": "total",
                "unidades_na_rede": len(c),
                "unidades_com_creche": int((c["QT_MAT_INF_CRE"].fillna(0) > 0).sum()),
                "matriculas_creche": int(c["QT_MAT_INF_CRE"].fillna(0).sum()),
                "faixa_0_3_censo": int(c["QT_MAT_BAS_0_3"].fillna(0).sum()),
                "faixa_0_3_31_03": int(c["QT_MAT_BAS_0_3_REF_31_03"].fillna(0).sum())
                if c["QT_MAT_BAS_0_3_REF_31_03"].notna().any()
                else None,
            }
        )
    oferta = pd.DataFrame(oferta)
    oferta["faixa_0_3_31_03"] = oferta["faixa_0_3_31_03"].astype("Int64")
    oferta.to_csv(INTERIM / "q14_creche_oferta.csv", index=False)

    # (2) matrícula por idade exata: só a série da SEEDF tem idade simples, já
    # que o Censo publica faixa etária e não idade (ver SCHEMA.md)
    idades = []
    m24 = pd.read_parquet(S / "matriculas__relatorio_matriculas_2024.parquet")
    for c in ("MAT_CRECHE", "MAT_PRE"):
        m24[c] = num(m24[c]).fillna(0)
    m24["idade"] = num(m24["IDADE"])
    g24 = m24.groupby("idade")[["MAT_CRECHE", "MAT_PRE"]].sum()
    m25 = pd.read_parquet(S / "matriculas__2025_educa_dados_matricula_alt.parquet")
    cre = "Educação infantil - Creche"
    pre = "Educação infantil - Pré-escola"
    for c in (cre, pre):
        m25[c] = num(m25[c]).fillna(0)
    m25["idade"] = num(m25["Idade"])
    g25 = m25.groupby("idade")[[cre, pre]].sum()
    for idade in range(0, 8):
        for ano, g, cc, cp in ((2024, g24, "MAT_CRECHE", "MAT_PRE"), (2025, g25, cre, pre)):
            if idade not in g.index:
                continue
            idades.append(
                {
                    "ano": ano,
                    "idade_no_ano": idade,
                    "matriculas_creche": int(g.loc[idade, cc]),
                    "matriculas_pre_escola": int(g.loc[idade, cp]),
                }
            )
    idades = pd.DataFrame(idades)
    idades.to_csv(INTERIM / "q14_creche_idade.csv", index=False)

    # (3) o fecho: três contagens e o teste da data de referência
    c24 = censo[censo["ano"] == 2024]
    c25 = censo[censo["ano"] == 2025]
    freq = pd.read_parquet(INTERIM / "pdad" / "pdad_frequencia.parquet")
    f03 = freq[(freq["ra"] == "DF") & (freq["faixa"] == "0-3")].iloc[0]

    cre24 = int(c24["QT_MAT_INF_CRE"].fillna(0).sum())
    cre25 = int(c25["QT_MAT_INF_CRE"].fillna(0).sum())
    faixa24 = int(c24["QT_MAT_BAS_0_3"].fillna(0).sum())
    faixa25 = int(c25["QT_MAT_BAS_0_3"].fillna(0).sum())
    faixa25_3103 = int(c25["QT_MAT_BAS_0_3_REF_31_03"].fillna(0).sum())

    fecho = pd.DataFrame(
        [
            {
                "contagem": "creche × idade no ano ≤ 3",
                "valor": int(m24.loc[m24["idade"] <= 3, "MAT_CRECHE"].sum()),
                "fonte": "relatorio_matriculas_2024.csv (SEEDF)",
                "calculo": "soma de MAT_CRECHE nas linhas com IDADE ≤ 3",
            },
            {
                "contagem": "0–3 na educação básica, faixa do Censo 2024",
                "valor": faixa24,
                "fonte": "microdados_censo_escolar_2024.zip (INEP)",
                "calculo": "soma de QT_MAT_BAS_0_3 no DF; data de referência não "
                "declarada no dicionário de 2024",
            },
            {
                "contagem": "0–3 frequentando escola (PDAD-A 2024)",
                "valor": int(f03["freq_est"]),
                "fonte": "pdad_frequencia.parquet (IPEDF)",
                "calculo": "peso_mor × H02=1 para idade na entrevista 0–3",
            },
            {
                "contagem": "creche total 2024",
                "valor": cre24,
                "fonte": "microdados_censo_escolar_2024.zip (INEP)",
                "calculo": "soma de QT_MAT_INF_CRE no DF",
            },
            {
                "contagem": "creche total 2025",
                "valor": cre25,
                "fonte": "microdados_censo_escolar_2025_.zip (INEP)",
                "calculo": "soma de QT_MAT_INF_CRE no DF",
            },
        ]
    )
    referencia = pd.DataFrame(
        [
            {
                "ano": 2024,
                "data_de_referencia": "não declarada no dicionário",
                "subconjunto": "todas as escolas",
                "faixa_0_3": faixa24,
                "creche": cre24,
                "razao_pct": round(100 * faixa24 / cre24, 1),
            },
            {
                "ano": 2025,
                "data_de_referencia": "última quarta-feira de maio",
                "subconjunto": "todas as escolas",
                "faixa_0_3": faixa25,
                "creche": cre25,
                "razao_pct": round(100 * faixa25 / cre25, 1),
            },
            {
                "ano": 2025,
                "data_de_referencia": "31/03 (Resolução CNE/CEB nº 05/2009)",
                "subconjunto": "todas as escolas",
                "faixa_0_3": faixa25_3103,
                "creche": cre25,
                "razao_pct": round(100 * faixa25_3103 / cre25, 1),
            },
        ]
    )
    # O teste que isola a data de referência: nas escolas que só têm creche,
    # toda a matrícula é de criança pequena, então a razão faixa/creche mede
    # exatamente a proporção de alunos com ≤ 3 anos na data da faixa. Se a
    # faixa fosse em 31/03, essa razão seria ~100% (creche não tem criança de 4
    # anos em 31/03); se for na data do Censo (maio), fica abaixo disso.
    so_creche = lambda c: c[
        (c["QT_MAT_INF_CRE"].fillna(0) > 0)
        & (c["QT_MAT_INF_PRE"].fillna(0) == 0)
        & (c["QT_MAT_FUND"].fillna(0) == 0)
        & (c["QT_MAT_MED"].fillna(0) == 0)
        & (c["QT_MAT_EJA"].fillna(0) == 0)
    ]
    for c, ano, colunas in (
        (c24, 2024, [("não declarada no dicionário", "QT_MAT_BAS_0_3")]),
        (
            c25,
            2025,
            [
                ("última quarta-feira de maio", "QT_MAT_BAS_0_3"),
                ("31/03 (Resolução CNE/CEB nº 05/2009)", "QT_MAT_BAS_0_3_REF_31_03"),
            ],
        ),
    ):
        s = so_creche(c)
        for rotulo, coluna in colunas:
            referencia.loc[len(referencia)] = {
                "ano": ano,
                "data_de_referencia": rotulo,
                "subconjunto": f"escolas só de creche ({len(s)} escolas)",
                "faixa_0_3": int(s[coluna].fillna(0).sum()),
                "creche": int(s["QT_MAT_INF_CRE"].fillna(0).sum()),
                "razao_pct": round(
                    100 * s[coluna].fillna(0).sum() / s["QT_MAT_INF_CRE"].fillna(0).sum(), 1
                ),
            }
    referencia.to_csv(INTERIM / "q14_creche_referencia.csv", index=False)
    # o conjunto de unidades com creche em 2025 contra o cadastro da SEEDF
    cad = pd.read_parquet(S / "escolas__relatorio_escolas_2025.parquet")
    cad_creche = set(cad.loc[num(cad["INF_CRE"]) == 1, "CO_ENTIDADE"].astype(str).str.strip())
    censo_creche = set(c25.loc[c25["QT_MAT_INF_CRE"].fillna(0) > 0, "CO_ENTIDADE"])
    fecho.loc[len(fecho)] = {
        "contagem": "unidades com creche: Censo 2025 ∩ cadastro 2025",
        "valor": len(cad_creche & censo_creche),
        "fonte": "microdados_censo_escolar_2025_.zip + relatorio_escolas_2025.csv",
        "calculo": (
            f"interseção de CO_ENTIDADE; só no cadastro {len(cad_creche - censo_creche)}, "
            f"só no Censo {len(censo_creche - cad_creche)}, "
            f"cadastro {len(cad_creche)}, Censo {len(censo_creche)}"
        ),
    }
    fecho.to_csv(INTERIM / "q14_creche_fecho.csv", index=False)

    print("\n== Q14 creche: oferta no Censo")
    print(oferta.to_string(index=False))
    print(
        f"\n   unidades com creche em 2025: {len(censo_creche)} no Censo, {len(cad_creche)} no "
        f"cadastro, {len(cad_creche & censo_creche)} em comum "
        f"(só no cadastro {len(cad_creche - censo_creche)}, só no Censo {len(censo_creche - cad_creche)})"
    )
    print("\n   matrícula em creche por idade no ano (série da SEEDF, a única com idade simples):")
    print(idades.pivot(index="idade_no_ano", columns="ano", values="matriculas_creche").to_string())
    print("\n   teste da data de referência da faixa etária:")
    print(referencia.to_string(index=False))
    print(
        f"\n   creche × idade ≤ 3 = {int(m24.loc[m24['idade'] <= 3, 'MAT_CRECHE'].sum()):,}; "
        f"faixa 0–3 do Censo 2024 = {faixa24:,}; diferença = "
        f"{faixa24 - int(m24.loc[m24['idade'] <= 3, 'MAT_CRECHE'].sum()):,}"
    )
    print(
        f"   0–3 frequentando (PDAD) = {int(f03['freq_est']):,} contra faixa 0–3 do Censo "
        f"{faixa24:,}: diferença {int(f03['freq_est']) - faixa24:,} "
        f"({100 * (int(f03['freq_est']) - faixa24) / faixa24:+.2f}%), dentro do IC de "
        f"±{f03['freq_ic95_pp']} p.p. da PDAD"
    )


def q15() -> None:
    """Conferência valor a valor: a série de matrículas da SEEDF contra o Censo.

    Entrada: `data/interim/seedf/matriculas__relatorio_matriculas_2024.parquet`
             e `data/interim/inep/censo_escola_df.parquet`.
    Saída:   `data/interim/q15_conferencia_censo.csv`.
    Idempotente: sim — leitura e reescrita.

    Mesmo exercício do Ideb (q8): o mapeamento entre as colunas das duas fontes
    é medido, não suposto. Só entram escolas presentes nos dois arquivos; as que
    o Censo lista com a célula de matrícula vazia não são zero e ficam de fora,
    contadas à parte.
    """
    censo = _censo()
    arq = S / "matriculas__relatorio_matriculas_2024.parquet"
    if not arq.exists():
        raise Pulado("falta a serie de matriculas da SEEDF (rode 03)")
    c = censo[censo["ano"] == 2024].copy()
    c["QT_MAT_MED_PROP_NM"] = c["QT_MAT_MED_PROP"].fillna(0) + c["QT_MAT_MED_NM"].fillna(0)
    # a série da SEEDF é escola × idade × sexo × cor/raça: soma por escola
    m = pd.read_parquet(arq).copy()
    campos = [
        "MAT_CRECHE",
        "MAT_PRE",
        "MAT_EI_TOTAL",
        "MAT_EF_INI",
        "MAT_EF_FIN",
        "MAT_EF_TOTAL",
        "MAT_EM_TOTAL",
        "MAT_EMI",
        "MAT_EJA_TOTAL",
        "MAT_EE_TOTAL",
        "MAT_EP_TEC_CONC",
        "MAT_EP_TEC_SUBS",
        "MAT_FIC",
    ]
    for campo in campos:
        m[campo] = num(m[campo]).fillna(0)
    g = m.groupby("CO_ENTIDADE")[campos].sum().reset_index()
    g["CO_ENTIDADE"] = g["CO_ENTIDADE"].astype(str).str.strip()

    pares = [
        ("creche", "MAT_CRECHE", "QT_MAT_INF_CRE", "MAT_CRECHE ↔ QT_MAT_INF_CRE"),
        ("pré-escola", "MAT_PRE", "QT_MAT_INF_PRE", "MAT_PRE ↔ QT_MAT_INF_PRE"),
        ("educação infantil", "MAT_EI_TOTAL", "QT_MAT_INF", "MAT_EI_TOTAL ↔ QT_MAT_INF"),
        ("EF anos iniciais", "MAT_EF_INI", "QT_MAT_FUND_AI", "MAT_EF_INI ↔ QT_MAT_FUND_AI"),
        ("EF anos finais", "MAT_EF_FIN", "QT_MAT_FUND_AF", "MAT_EF_FIN ↔ QT_MAT_FUND_AF"),
        ("EF total", "MAT_EF_TOTAL", "QT_MAT_FUND", "MAT_EF_TOTAL ↔ QT_MAT_FUND"),
        (
            "EM propedêutico + normal",
            "MAT_EM_TOTAL",
            "QT_MAT_MED_PROP_NM",
            "MAT_EM_TOTAL ↔ QT_MAT_MED_PROP + QT_MAT_MED_NM",
        ),
        ("EM integrado", "MAT_EMI", "QT_MAT_MED_CT", "MAT_EMI ↔ QT_MAT_MED_CT"),
        ("EJA", "MAT_EJA_TOTAL", "QT_MAT_EJA", "MAT_EJA_TOTAL ↔ QT_MAT_EJA"),
        ("educação especial", "MAT_EE_TOTAL", "QT_MAT_ESP", "MAT_EE_TOTAL ↔ QT_MAT_ESP"),
        (
            "técnico concomitante",
            "MAT_EP_TEC_CONC",
            "QT_MAT_PROF_TEC_CONC",
            "MAT_EP_TEC_CONC ↔ QT_MAT_PROF_TEC_CONC",
        ),
        (
            "técnico subsequente",
            "MAT_EP_TEC_SUBS",
            "QT_MAT_PROF_TEC_SUBS",
            "MAT_EP_TEC_SUBS ↔ QT_MAT_PROF_TEC_SUBS",
        ),
        ("FIC concomitante", "MAT_FIC", "QT_MAT_PROF_FIC_CONC", "MAT_FIC ↔ QT_MAT_PROF_FIC_CONC"),
    ]
    j = g.merge(c, on="CO_ENTIDADE", how="inner")
    linhas = []
    for etapa, campo_seedf, campo_censo, calculo in pares:
        d = j[campo_seedf] - j[campo_censo]
        por_rede = (
            j.assign(d=d).query("d != 0")["rede"].value_counts().to_dict()
        )
        linhas.append(
            {
                "etapa": etapa,
                "campo_seedf": campo_seedf,
                "campo_censo": campo_censo,
                "calculo": calculo,
                "escolas_comparadas": len(j),
                "iguais": int((d == 0).sum()),
                "divergentes": int((d != 0).sum()),
                "soma_seedf": int(j[campo_seedf].sum()),
                "soma_censo": int(j[campo_censo].sum()),
                "delta": int(d.sum()),
                "delta_pct": round(100 * d.sum() / j[campo_censo].sum(), 3)
                if j[campo_censo].sum()
                else None,
                "max_abs": int(d.abs().max()),
                "redes_das_divergencias": "; ".join(f"{k} {v}" for k, v in por_rede.items()),
            }
        )

    # total da educação básica: soma reconstruída dos componentes que a série
    # da SEEDF tem, contra QT_MAT_BAS (ver dicionário da INEP para a definição)
    comp_seedf = (
        j["MAT_EI_TOTAL"]
        + j["MAT_EF_TOTAL"]
        + j["MAT_EM_TOTAL"]
        + j["MAT_EMI"]
        + j["MAT_EJA_TOTAL"]
        + j["MAT_EP_TEC_CONC"]
        + j["MAT_EP_TEC_SUBS"]
        + j["MAT_FIC"]
    )
    linhas.append(
        {
            "etapa": "total da educação básica",
            "campo_seedf": "EI + EF + EM + EMI + EJA + TEC_CONC + TEC_SUBS + FIC",
            "campo_censo": "QT_MAT_BAS",
            "calculo": "soma dos componentes acima, que é a definição de QT_MAT_BAS no "
            "dicionário da INEP (a educação especial não entra: ela atravessa as etapas "
            "e já está contada dentro delas)",
            "escolas_comparadas": len(j),
            "iguais": int((comp_seedf == j["QT_MAT_BAS"]).sum()),
            "divergentes": int((comp_seedf != j["QT_MAT_BAS"]).sum()),
            "soma_seedf": int(comp_seedf.sum()),
            "soma_censo": int(j["QT_MAT_BAS"].sum()),
            "delta": int((comp_seedf - j["QT_MAT_BAS"]).sum()),
            "delta_pct": round(
                100 * (comp_seedf - j["QT_MAT_BAS"]).sum() / j["QT_MAT_BAS"].sum(), 3
            ),
            "max_abs": int((comp_seedf - j["QT_MAT_BAS"]).abs().max()),
            "redes_das_divergencias": "; ".join(
                f"{k} {v}"
                for k, v in j.assign(d=comp_seedf - j["QT_MAT_BAS"])
                .query("d != 0")["rede"]
                .value_counts()
                .items()
            ),
        }
    )
    tab = pd.DataFrame(linhas)
    tab.to_csv(INTERIM / "q15_conferencia_censo.csv", index=False)

    sem_matricula = int((censo[censo["ano"] == 2024]["QT_MAT_BAS"].isna()).sum())
    print("\n== Q15 conferência SEEDF × Censo 2024, valor a valor por escola")
    print(tab.drop(columns="calculo").to_string(index=False))
    print(
        f"\n   {len(j):,} escolas comparadas; o Censo 2024 lista ainda {sem_matricula} escolas "
        "do DF com a célula de matrícula vazia (ausente, não zero) — essas ficam fora"
    )
    eja = tab[tab.etapa == "EJA"].iloc[0]
    etapas = tab[tab.etapa != "total da educação básica"].copy()
    etapas["_abs"] = etapas["delta_pct"].abs()
    piores = etapas.sort_values("_abs", ascending=False).head(3)
    print("   maiores divergências em %:")
    for r in piores.itertuples():
        print(f"     {r.etapa}: {r.delta:+,} ({r.delta_pct:+.2f}%) em {r.divergentes} escolas")
    print(
        f"   EJA: {eja.delta:+,} ({eja.delta_pct:+.2f}%), em {eja.divergentes} escolas. A causa "
        "não é determinável nas tabelas por escola — a base por aluno que explicaria não é "
        "mais publicada desde 2024"
    )


# ---------------------------------------------------------------- Q16
ETAPAS_Q16 = {
    "FUN_AI": ("FUND_AI", "QT_MAT_FUND_AI", "AI", "anos iniciais"),
    "FUN_AF": ("FUND_AF", "QT_MAT_FUND_AF", "AF", "anos finais"),
    "MED": ("MED", "QT_MAT_MED", "EM", "ensino médio"),
}
FAIXAS_N = [0, 10, 20, 30, 50, 100, float("inf")]
ROTULO_FAIXA = ["1-9", "10-19", "20-29", "30-49", "50-99", "100+"]


def wilson_pp(n: float, p: float = 0.10, z: float = 1.96) -> float:
    """Meia-largura do intervalo de Wilson de 95% para uma proporção, em p.p."""
    if not n:
        return float("nan")
    meio = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / (1 + z * z / n)
    return round(100 * meio, 1)


def q16() -> None:
    """Matriz de presença escola × etapa e o tamanho de cada denominador.

    Entrada: `data/interim/seedf/escolas__relatorio_escolas_2025.parquet` (vetor
             de oferta `INF_CRE`…`PROF`), `data/interim/inep/censo_escola_df.parquet`
             (matrícula por etapa em 2025), `ideb_escolas_df.parquet` (2025),
             `tdi_escolas_df.parquet`, `tnr_escolas_df.parquet` e
             `tx_rend_escolas_df.parquet` (as três de 2025).
    Saída:   `data/interim/q16_presenca_escola_etapa.csv` (uma linha por escola ×
             etapa), `data/interim/q16_faixas_n.csv` (distribuição de n por etapa
             e valor extremo por faixa, evidência do limiar de n pequeno) e o
             resumo impresso.
    Idempotente: sim — leitura e reescrita.

    O denominador de n é a matrícula da etapa no Censo 2025 (`QT_MAT_FUND_AI`,
    `QT_MAT_FUND_AF`, `QT_MAT_MED`), a mesma proxy do q13 (L-21). A etapa entra
    quando o vetor de oferta da SEEDF diz 1 **ou** quando o Censo declara
    matrícula maior que zero: a divergência entre os dois fica visível na coluna
    `oferta_seedf`, não resolvida por escolha de um dos lados.

    Estado ausente de indicador numa etapa ofertada é `ausente`, não zero
    (L-30); estado vindo da fonte é copiado como está, inclusive
    `nao_aplicavel` (L-59).
    """
    e = pd.read_parquet(S / "escolas__relatorio_escolas_2025.parquet").copy()
    e["co"] = e["CO_ENTIDADE"].astype(str)
    e["rede"] = e["Nome Rede"].map(NOME_REDE).fillna(e["Nome Rede"])
    for col in ("INF_CRE", "INF_PRE", "FUND_AI", "FUND_AF", "MED", "EJA", "ESP", "PROF"):
        e[col] = num(e[col]).fillna(0).astype(int)

    censo = _censo()
    c25 = censo[censo["ano"] == 2025].set_index("CO_ENTIDADE")
    ideb = pd.read_parquet(INTERIM / "inep" / "ideb_escolas_df.parquet")
    # só linha com valor entra no mapa: a linha com estado ausente não é Ideb
    ideb = ideb[(ideb["ano"] == "2025") & (ideb["indicador"] == "ideb_observado")
                & (ideb["estado"] == "valor")]
    tdi = pd.read_parquet(INTERIM / "inep" / "tdi_escolas_df.parquet")
    tnr = pd.read_parquet(INTERIM / "inep" / "tnr_escolas_df.parquet")
    tx = pd.read_parquet(INTERIM / "inep" / "tx_rend_escolas_df.parquet")
    tdi = tdi[tdi["NU_ANO_CENSO"] == "2025"]
    tnr = tnr[tnr["NU_ANO_CENSO"] == "2025"]
    ap = tx[(tx["NU_ANO_CENSO"] == "2025") & (tx["categoria"] == "aprovacao")]

    def mapa(df: pd.DataFrame, recorte: str, coluna: str = "valor") -> dict:
        d = df[df["recorte"] == recorte]
        return d.set_index("CO_ENTIDADE")[coluna].to_dict()

    linhas = []
    for etapa, (oferta_col, mat_col, codigo, nome) in ETAPAS_Q16.items():
        tdi_v, tdi_e = mapa(tdi, etapa), mapa(tdi, etapa, "estado")
        tnr_v, tnr_e = mapa(tnr, etapa), mapa(tnr, etapa, "estado")
        ap_v, ap_e = mapa(ap, etapa), mapa(ap, etapa, "estado")
        ideb_etapa = ideb[ideb["etapa"] == codigo].set_index("ID_ESCOLA")
        ideb_v = ideb_etapa["valor"].to_dict()
        ideb_e = ideb_etapa["estado"].to_dict()
        mat = c25[mat_col].to_dict()
        for r in e.itertuples():
            n = mat.get(r.co)
            n = int(n) if pd.notna(n) else None
            if not getattr(r, oferta_col) and not n:
                continue
            linhas.append(
                {
                    "co_entidade": r.co,
                    "rede": r.rede,
                    "etapa": nome,
                    "oferta_seedf": int(getattr(r, oferta_col)),
                    "matriculas_censo_2025": n,
                    "ideb_2025": ideb_v.get(r.co),
                    "ideb_estado": ideb_e.get(r.co, "ausente"),
                    "tdi_2025": tdi_v.get(r.co),
                    "tdi_estado": tdi_e.get(r.co, "ausente"),
                    "tnr_2025": tnr_v.get(r.co),
                    "tnr_estado": tnr_e.get(r.co, "ausente"),
                    "aprovacao_2025": ap_v.get(r.co),
                    "aprovacao_estado": ap_e.get(r.co, "ausente"),
                }
            )
    m = pd.DataFrame(linhas).sort_values(["etapa", "co_entidade"])
    m.to_csv(INTERIM / "q16_presenca_escola_etapa.csv", index=False)

    # universos medidos, na mesma definição do REPORT §2.4
    efem = e[(e["FUND_AI"] + e["FUND_AF"] + e["MED"]) > 0]
    com_taxa = set(tdi["CO_ENTIDADE"]) if len(tdi) else set()
    com_ideb = set(ideb["ID_ESCOLA"])
    com_efem = set(efem["co"])
    sem_indicador = com_efem - com_taxa - com_ideb
    tdi_sem_ideb = (com_taxa & com_efem) - com_ideb
    print("\n== Q16 presença escola × etapa (Censo 2025 como denominador)")
    print(f"   cadastro 2025: {len(e):,} unidades; com EF/EM no vetor de oferta: {len(efem):,}; "
          f"sem EF/EM: {len(e) - len(efem):,}")
    print(f"   com TDI e fluxo 2025: {len(com_taxa):,} (fora do cadastro: "
          f"{len(com_taxa - set(e['co'])):,}); com Ideb 2025: {len(com_ideb):,}")
    print(f"   TDI sem Ideb: {len(tdi_sem_ideb):,}; sem indicador nenhum: {len(sem_indicador):,}"
          f"{' (' + ', '.join(sorted(sem_indicador)) + ')' if sem_indicador else ''}")
    print(f"   linhas escola × etapa: {len(m):,}")

    u = m[m["tdi_estado"].isin(["valor", "zero"]) & m["matriculas_censo_2025"].notna()].copy()
    u["faixa"] = pd.cut(u["matriculas_censo_2025"], FAIXAS_N, right=False, labels=ROTULO_FAIXA)
    resumo = []
    for etapa in ["anos iniciais", "anos finais", "ensino médio", "todas"]:
        sub = u if etapa == "todas" else u[u["etapa"] == etapa]
        for faixa, g in sub.groupby("faixa", observed=True):
            n = g["matriculas_censo_2025"]
            ap100 = ((g["aprovacao_2025"] == 100) & (g["aprovacao_estado"] == "valor")).mean()
            resumo.append(
                {
                    "etapa": etapa,
                    "faixa": str(faixa),
                    "unidades": len(g),
                    "n_min": int(n.min()),
                    "n_mediana": float(n.median()),
                    "n_max": int(n.max()),
                    "tdi_zero_pct": round(100 * (g["tdi_2025"] == 0).mean(), 1),
                    "aprovacao_100_pct": round(100 * ap100, 1),
                    "wilson_hw_p10_pp": wilson_pp(float(n.median())),
                }
            )
    faixas = pd.DataFrame(resumo)
    faixas.to_csv(INTERIM / "q16_faixas_n.csv", index=False)
    print("\n   n por faixa e valor extremo (unidades com TDI valor ou zero):")
    print(faixas.to_string(index=False))
    print(f"   unidades com n < 30: {(u['matriculas_censo_2025'] < 30).sum():,} em "
          f"{u[u['matriculas_censo_2025'] < 30]['co_entidade'].nunique():,} escolas; "
          f"n < 50: {(u['matriculas_censo_2025'] < 50).sum():,} em "
          f"{u[u['matriculas_censo_2025'] < 50]['co_entidade'].nunique():,} escolas")


# ---------------------------------------------------------------- insumo público
# O recorte que o build do site lê. O grão e as colunas são o contrato de
# `docs/FASE-1.md` §5.1; nada aqui é microdado e nenhuma linha identifica aluno.

REDE_SITE = {
    "REDE PÚBLICA FEDERAL": "federal",
    "REDE PÚBLICA ESTADUAL VINCULADA À SEEDF": "estadual",
    "REDE PÚBLICA ESTADUAL NÃO VINCULADA À SE": "estadual",
    "REDE PARTICULAR CONVENIADA": "privada conveniada",
    "REDE PARTICULAR NÃO CONVENIADA": "privada não conveniada",
}

ETAPAS_PUBLICAS = [
    ("AI", "anos iniciais", "FUND_AI", "QT_MAT_FUND_AI", "oferta_fund_ai", "mat_fund_ai"),
    ("AF", "anos finais", "FUND_AF", "QT_MAT_FUND_AF", "oferta_fund_af", "mat_fund_af"),
    ("EM", "ensino médio", "MED", "QT_MAT_MED", "oferta_med", "mat_med"),
]

INFRA_ITENS = [
    "IN_BIBLIOTECA",
    "IN_SALA_LEITURA",
    "IN_QUADRA_ESPORTES",
    "IN_LABORATORIO_INFORMATICA",
    "IN_LABORATORIO_CIENCIAS",
    "IN_INTERNET_ALUNOS",
    "IN_REFEITORIO",
    "IN_BANHEIRO_PNE",
]

ANOS_IDEB = [str(ano) for ano in range(2005, 2026, 2)]

# Licença por família: a SEEDF vem do inventário do CKAN (o valor declarado no
# conjunto, nunca inferido); a INEP não declara licença no portal. O export falha
# antes de gravar quando uma família SEEDF resolve para ODbL (L-62).
LICENCA_INEP = "público, sem licença declarada no portal"

DATASET_SEEDF_POR_FAMILIA = {
    "identificacao": "relacao-de-unidades-escolares-abrangendo-todas-as-redes-de-ensino-do-distrito-federal",
    "oferta": "relacao-de-unidades-escolares-abrangendo-todas-as-redes-de-ensino-do-distrito-federal",
    "infraestrutura": "dados-de-infraestrutura-abrangendo-todas-as-redes-de-ensino-df",
    "home_contagem": "relacao-de-unidades-escolares-abrangendo-todas-as-redes-de-ensino-do-distrito-federal",
}

FAMILIAS_INEP = {
    "matricula", "ideb", "fluxo", "tdi", "tnr", "creche",
    "ideb_uf", "home_creche", "home_ideb_cobertura", "home_tdi_rede",
}

# Texto de cálculo das linhas `tdi-*` do agregado da home; entra no
# `procedencia.json` e no JSON de procedência da página, palavra por palavra.
CALCULO_TDI_REDE = (
    "Percentil (interpolação linear) da distorção idade-série de 2025 entre as unidades "
    "escola × etapa da rede, com taxa publicada (estados valor e zero). Inclui unidades de "
    "turma pequena, cuja taxa a página da escola não publica (D4). Rede privada = conveniada "
    "+ não conveniada. Rede federal fora."
)

REGISTROS_PUBLICOS = [
    {
        "familia": "identificacao",
        "bloco": 1,
        "fonte": "SEEDF — Cadastro de Unidades Escolares 2025",
        "arquivo": "data/public/escolas.parquet",
        "anos": ["2025"],
        "calculo": "cópia dos campos Nome da escola, Nome RA e Nome Rede do cadastro",
        "limites": ["L-36", "L-37"],
    },
    {
        "familia": "oferta",
        "bloco": 2,
        "fonte": "SEEDF — Cadastro de Unidades Escolares 2025",
        "arquivo": "data/public/escolas.parquet",
        "anos": ["2025"],
        "calculo": "sinalizador 1 = oferta da etapa; 0 = não oferta; não traduzir 'é EI'",
        "limites": ["L-57", "L-36"],
    },
    {
        "familia": "matricula",
        "bloco": 3,
        "fonte": "INEP — Censo Escolar 2024–2025",
        "arquivo": "data/public/escolas.parquet",
        "anos": ["2024", "2025"],
        "calculo": "matrícula da etapa por escola, como está no campo do Censo",
        "limites": ["L-28", "L-43", "L-48", "L-62", "L-63"],
    },
    {
        "familia": "ideb",
        "bloco": 4,
        "fonte": "INEP — Ideb por Escola 2005–2025",
        "arquivo": "data/public/indicadores.parquet",
        "anos": ANOS_IDEB,
        "calculo": "valor observado da etapa, como publicado; a meta projetada não entra",
        "limites": ["L-08", "L-12", "L-30", "L-33", "L-56"],
    },
    {
        "familia": "fluxo",
        "bloco": 5,
        "fonte": "INEP — Taxas de Rendimento por Escola 2025",
        "arquivo": "data/public/indicadores.parquet",
        "anos": ["2025"],
        "calculo": "percentual da etapa, como publicado",
        "limites": ["L-11", "L-59", "L-21", "D4"],
    },
    {
        "familia": "tdi",
        "bloco": 6,
        "fonte": "INEP — Distorção Idade-Série por Escola 2025",
        "arquivo": "data/public/indicadores.parquet",
        "anos": ["2025"],
        "calculo": "percentual da etapa, como publicado",
        "limites": ["L-11", "L-59", "L-40", "D4"],
    },
    {
        "familia": "tnr",
        "bloco": 7,
        "fonte": "INEP — Taxa de Não-Resposta por Escola 2025",
        "arquivo": "data/public/indicadores.parquet",
        "anos": ["2025"],
        "calculo": "percentual da etapa, como publicado",
        "limites": ["L-09", "L-11", "L-59"],
    },
    {
        "familia": "infraestrutura",
        "bloco": 8,
        "fonte": "SEEDF — Infraestrutura Escolar 2025",
        "arquivo": "data/public/infraestrutura.parquet",
        "anos": ["2025"],
        "calculo": "presença do item declarada pela escola",
        "limites": ["L-25", "L-29", "L-38", "L-51"],
    },
    {
        "familia": "creche",
        "bloco": 9,
        "fonte": "INEP — Censo Escolar 2024–2025",
        "arquivo": "data/public/escolas.parquet",
        "anos": ["2024", "2025"],
        "calculo": "matrícula em creche da escola, como está no campo do Censo",
        "limites": ["L-27", "L-28", "L-62", "L-63"],
    },
    {
        "familia": "ideb_uf",
        "bloco": 10,
        "fonte": "INEP — Ideb divulgação por UF e Brasil 2023–2025",
        "arquivo": "data/public/ideb_uf.parquet",
        "anos": ["2023", "2025"],
        "calculo": (
            "valor observado do Ideb da UF e do Brasil, como publicado; posição = "
            "1 + número de UFs com valor maior; denominador = UFs com valor no ano"
        ),
        "limites": ["L-10", "L-32", "L-66"],
    },
    {
        "familia": "home_contagem",
        "bloco": 11,
        "fonte": "SEEDF — Cadastro de Unidades Escolares 2025",
        "arquivo": "data/public/agregados.parquet",
        "anos": ["2025"],
        "calculo": "contagem de escolas e de Regiões Administrativas distintas no cadastro",
        "limites": ["L-36", "L-37", "L-64"],
    },
    {
        "familia": "home_creche",
        "bloco": 12,
        "fonte": "INEP — Censo Escolar 2024–2025",
        "arquivo": "data/public/agregados.parquet",
        "anos": ["2025"],
        "calculo": (
            "contagem das unidades que ofertam creche e soma da matrícula em creche de "
            "2025 por rede; a rede vem do cadastro da SEEDF"
        ),
        "limites": ["L-27", "L-28", "L-36", "L-62", "L-63"],
    },
    {
        "familia": "home_ideb_cobertura",
        "bloco": 13,
        "fonte": "INEP — Ideb por Escola 2025 + Censo Escolar 2025",
        "arquivo": "data/public/agregados.parquet",
        "anos": ["2025"],
        "calculo": (
            "escolas com oferta de anos iniciais, finais ou médio, decompostas por ter "
            "Ideb em 2025, ter linha de 2025 sem valor e não ter linha; pública = "
            "estadual + federal"
        ),
        "limites": ["L-08", "L-09", "L-30", "L-31"],
    },
    {
        "familia": "home_tdi_rede",
        "bloco": 14,
        "fonte": "INEP — Distorção Idade-Série por Escola 2025",
        "arquivo": "data/public/agregados.parquet",
        "anos": ["2025"],
        "calculo": CALCULO_TDI_REDE,
        "limites": ["L-11", "L-32", "L-36", "L-37", "L-59", "L-65", "L-67"],
    },
]


class ExportError(Exception):
    """O insumo público não pode ser gravado sem intervenção explícita."""


def _licencas_seedf() -> dict[str, tuple[str, str | None]]:
    """Resolve a licença das famílias SEEDF no inventário do CKAN.

    Devolve `{familia: (licenca, licenca_url)}` com o `license_title` e o
    `license_url` do conjunto, como declarados. Falha se o inventário faltar,
    se o conjunto não estiver nele, se a licença estiver vazia ou se o conjunto
    for ODbL (L-62).
    """
    caminho = INTERIM / "seedf_datasets.csv"
    if not caminho.is_file():
        raise ExportError(
            f"falta o inventário da SEEDF em {caminho}; rode 01_inventory_seedf.py "
            "antes de exportar o insumo público"
        )
    inventario = pd.read_csv(caminho, dtype=str, keep_default_na=False)
    if "dataset" not in inventario or "licenca_titulo" not in inventario:
        raise ExportError(f"{caminho} sem as colunas dataset/licenca_titulo")

    resolvidas: dict[str, tuple[str, str | None]] = {}
    for familia, dataset in DATASET_SEEDF_POR_FAMILIA.items():
        linha = inventario[inventario["dataset"] == dataset]
        if len(linha) != 1:
            raise ExportError(
                f"família {familia!r}: conjunto {dataset!r} não encontrado (ou duplicado) "
                f"em {caminho}"
            )
        licenca_id = str(linha.iloc[0]["licenca_id"]).strip().lower()
        titulo = str(linha.iloc[0]["licenca_titulo"]).strip()
        url = str(linha.iloc[0]["licenca_url"]).strip() or None
        if licenca_id == "odc-odbl" or "odbl" in titulo.lower() or "open data commons" in titulo.lower():
            raise ExportError(
                f"família {familia!r} resolve para o conjunto ODbL {dataset!r} "
                f"({titulo or licenca_id}); a página não publica derivado ODbL (L-62)"
            )
        if not titulo:
            raise ExportError(
                f"família {familia!r}: conjunto {dataset!r} sem licença declarada em {caminho}"
            )
        rotulo = {"cc-by": "CC BY", "cc-by-sa": "CC BY-SA"}.get(licenca_id)
        licenca = f"{rotulo} ({titulo})" if rotulo else titulo
        resolvidas[familia] = (licenca, url)
    return resolvidas


def _registros_publicos() -> list[dict]:
    """Copia `REGISTROS_PUBLICOS` e injeta a licença resolvida por família.

    Duas famílias da mesma fonte precisam declarar a mesma licença e a mesma
    URL; divergência é erro de inventário, não escolha silenciosa.
    """
    licencas = _licencas_seedf()
    registros = []
    por_fonte: dict[str, tuple[str, str | None]] = {}
    for base in REGISTROS_PUBLICOS:
        registro = dict(base)
        familia = registro["familia"]
        if familia in licencas:
            registro["licenca"], registro["licenca_url"] = licencas[familia]
        elif familia in FAMILIAS_INEP:
            registro["licenca"], registro["licenca_url"] = LICENCA_INEP, None
        else:
            raise ExportError(
                f"família {familia!r} sem origem de licença declarada no export"
            )
        chave = (registro["licenca"], registro["licenca_url"])
        anterior = por_fonte.setdefault(registro["fonte"], chave)
        if anterior != chave:
            raise ExportError(
                f"famílias da fonte {registro['fonte']!r} divergem em licença: "
                f"{anterior!r} × {chave!r}"
            )
        registros.append(registro)
    return registros


def _escolas_publicas() -> pd.DataFrame:
    """Monta o grão escola do insumo público, na ordem de `CO_ENTIDADE`."""
    e = pd.read_parquet(S / "escolas__relatorio_escolas_2025.parquet").copy()
    e["co_entidade"] = e["CO_ENTIDADE"].astype(str).str.strip()
    e["nome"] = e["Nome da escola"].astype(str).str.strip()
    e["rede_cadastro"] = e["Nome Rede"].astype(str).str.strip()
    e["rede"] = e["rede_cadastro"].map(REDE_SITE)
    if e["rede"].isna().any():
        faltantes = sorted(e.loc[e["rede"].isna(), "rede_cadastro"].unique())
        raise ExportError(f"rede sem mapa para o site: {faltantes}")
    e["ra"] = e["Nome RA"].map(lambda valor: norm_ra(valor) if pd.notna(valor) else "")

    for _, _, oferta_col, _, oferta_site, _ in ETAPAS_PUBLICAS:
        e[oferta_site] = pd.to_numeric(e[oferta_col], errors="coerce").fillna(0).astype("Int64")
    for coluna, destino in [
        ("INF_CRE", "oferta_inf_cre"),
        ("INF_PRE", "oferta_inf_pre"),
        ("EJA", "oferta_eja"),
        ("ESP", "oferta_esp"),
        ("PROF", "oferta_prof"),
    ]:
        e[destino] = pd.to_numeric(e[coluna], errors="coerce").fillna(0).astype("Int64")

    censo = pd.read_parquet(INTERIM / "inep" / "censo_escola_df.parquet")
    censo["CO_ENTIDADE"] = censo["CO_ENTIDADE"].astype(str).str.strip()
    censo_2024 = censo[censo["ano"] == 2024]
    if censo_2024["CO_ENTIDADE"].duplicated().any():
        raise ExportError("Censo 2024 tem CO_ENTIDADE duplicado")
    e["censo_2024_presente"] = e["co_entidade"].isin(censo_2024["CO_ENTIDADE"]).astype(bool)

    for ano, coluna_censo, destino in [
        (2024, "QT_MAT_INF_CRE", "mat_inf_cre_2024"),
        (2024, "QT_MAT_FUND_AI", "mat_fund_ai_2024"),
        (2024, "QT_MAT_FUND_AF", "mat_fund_af_2024"),
        (2024, "QT_MAT_MED", "mat_med_2024"),
        (2025, "QT_MAT_INF_CRE", "mat_inf_cre_2025"),
        (2025, "QT_MAT_FUND_AI", "mat_fund_ai_2025"),
        (2025, "QT_MAT_FUND_AF", "mat_fund_af_2025"),
        (2025, "QT_MAT_MED", "mat_med_2025"),
    ]:
        recorte = censo[censo["ano"] == ano].set_index("CO_ENTIDADE")
        if recorte.index.duplicated().any():
            raise ExportError(f"Censo {ano} tem CO_ENTIDADE duplicado")
        e[destino] = pd.array(
            recorte[coluna_censo].reindex(e["co_entidade"]).to_numpy(), dtype="Int64"
        )

    colunas_2024 = [
        "mat_inf_cre_2024",
        "mat_fund_ai_2024",
        "mat_fund_af_2024",
        "mat_med_2024",
    ]
    inconsistentes = e.loc[
        (~e["censo_2024_presente"]) & e[colunas_2024].notna().any(axis=1), "co_entidade"
    ]
    if len(inconsistentes):
        raise ExportError(
            "escola sem linha no Censo 2024 com matrícula de 2024: "
            + ", ".join(sorted(inconsistentes.astype(str)))
        )

    colunas = [
        "co_entidade", "nome", "ra", "rede", "rede_cadastro", "censo_2024_presente",
        "oferta_inf_cre", "oferta_inf_pre", "oferta_fund_ai", "oferta_fund_af",
        "oferta_med", "oferta_eja", "oferta_esp", "oferta_prof",
        "mat_inf_cre_2024", "mat_fund_ai_2024", "mat_fund_af_2024", "mat_med_2024",
        "mat_inf_cre_2025", "mat_fund_ai_2025", "mat_fund_af_2025", "mat_med_2025",
    ]
    return e[colunas].sort_values("co_entidade", kind="mergesort").reset_index(drop=True)


def _indicadores_publicos(escolas: pd.DataFrame) -> pd.DataFrame:
    """Monta o grão escola × etapa × indicador × ano do insumo público."""
    codigos = set(escolas["co_entidade"])
    linhas: list[dict] = []

    ideb = pd.read_parquet(INTERIM / "inep" / "ideb_escolas_df.parquet")
    ideb = ideb[
        (ideb["indicador"] == "ideb_observado")
        & (ideb["etapa"].isin(["AI", "AF", "EM"]))
        & (ideb["ID_ESCOLA"].astype(str).str.strip().isin(codigos))
    ]
    for r in ideb.itertuples():
        linhas.append(
            {
                "co_entidade": str(r.ID_ESCOLA).strip(),
                "etapa": r.etapa,
                "indicador": "ideb_observado",
                "ano": str(r.ano),
                "valor": r.valor,
                "estado": r.estado,
            }
        )

    for familia, arquivo in [
        ("tdi", "tdi_escolas_df.parquet"),
        ("tnr", "tnr_escolas_df.parquet"),
    ]:
        d = pd.read_parquet(INTERIM / "inep" / arquivo)
        d = d[(d["NU_ANO_CENSO"] == "2025") & (d["recorte"].isin(["FUN_AI", "FUN_AF", "MED"]))]
        d["CO_ENTIDADE"] = d["CO_ENTIDADE"].astype(str).str.strip()
        d = d[d["CO_ENTIDADE"].isin(codigos)]
        for r in d.itertuples():
            linhas.append(
                {
                    "co_entidade": r.CO_ENTIDADE,
                    "etapa": {"FUN_AI": "AI", "FUN_AF": "AF", "MED": "EM"}[r.recorte],
                    "indicador": familia,
                    "ano": "2025",
                    "valor": r.valor,
                    "estado": r.estado,
                }
            )

    tx = pd.read_parquet(INTERIM / "inep" / "tx_rend_escolas_df.parquet")
    tx = tx[(tx["NU_ANO_CENSO"] == "2025") & (tx["recorte"].isin(["FUN_AI", "FUN_AF", "MED"]))]
    tx["CO_ENTIDADE"] = tx["CO_ENTIDADE"].astype(str).str.strip()
    tx = tx[tx["CO_ENTIDADE"].isin(codigos)]
    for r in tx.itertuples():
        linhas.append(
            {
                "co_entidade": r.CO_ENTIDADE,
                "etapa": {"FUN_AI": "AI", "FUN_AF": "AF", "MED": "EM"}[r.recorte],
                "indicador": r.categoria,
                "ano": "2025",
                "valor": r.valor,
                "estado": r.estado,
            }
        )

    etapa_ordem = {"AI": 0, "AF": 1, "EM": 2}
    indicador_ordem = {
        "ideb_observado": 0,
        "tdi": 1,
        "tnr": 2,
        "aprovacao": 3,
        "reprovacao": 4,
        "abandono": 5,
    }
    linhas.sort(
        key=lambda r: (
            r["co_entidade"],
            indicador_ordem[r["indicador"]],
            etapa_ordem[r["etapa"]],
            r["ano"],
        )
    )
    return pd.DataFrame(
        linhas,
        columns=["co_entidade", "etapa", "indicador", "ano", "valor", "estado"],
    )


def _infraestrutura_publica(escolas: pd.DataFrame) -> pd.DataFrame:
    """Monta o grão escola × item (8 itens publicados) do insumo público.

    O universo é o das escolas que oferecem ensino fundamental ou médio (927 em
    2025), o mesmo da tabela de `docs/FASE-1.md` §2. Para as demais, o bloco é
    `nao_aplicavel`: laboratório, quadra e biblioteca não são exigência da
    educação infantil (L-25).
    """
    inf = pd.read_parquet(S / "infraestrutura__relatorio_infraestrutura_2025.parquet")
    inf["CO_ENTIDADE"] = inf["CO_ENTIDADE"].astype(str).str.strip()
    mapa = inf.set_index("CO_ENTIDADE")
    universo = escolas[
        (escolas["oferta_fund_ai"] == 1)
        | (escolas["oferta_fund_af"] == 1)
        | (escolas["oferta_med"] == 1)
    ]
    linhas = []
    for co in universo["co_entidade"]:
        for item in INFRA_ITENS:
            bruto = mapa.at[co, item] if co in mapa.index else None
            if bruto is None or pd.isna(bruto):
                linhas.append(
                    {"co_entidade": co, "item": item, "ano": "2025", "valor": None, "estado": "ausente"}
                )
            else:
                linhas.append(
                    {
                        "co_entidade": co,
                        "item": item,
                        "ano": "2025",
                        "valor": int(bruto),
                        "estado": "valor",
                    }
                )
    return pd.DataFrame(linhas, columns=["co_entidade", "item", "ano", "valor", "estado"])


def _ideb_uf_publica() -> pd.DataFrame:
    """Recorte publicado da tabela de Ideb por UF (grão etapa × ano × rede).

    Entrada: `_ideb_uf_tabela()`.
    Saída: 24 linhas com `df`, `brasil`, o `estado` de cada um e a posição; sem
    `df_menos_brasil` nem `mediana_ufs`, que são derivados e o site não usa.
    Idempotente: sim — derivação pura.
    """
    tabela = _ideb_uf_tabela().copy()
    tabela["df_estado"] = tabela["df"].map(lambda v: "valor" if pd.notna(v) else "ausente")
    tabela["brasil_estado"] = tabela["brasil"].map(
        lambda v: "valor" if pd.notna(v) else "ausente"
    )
    return tabela[
        [
            "etapa", "ano", "rede", "df", "df_estado",
            "brasil", "brasil_estado", "posicao", "n_ufs",
        ]
    ].reset_index(drop=True)


def _agregados_publicos(escolas: pd.DataFrame, indicadores: pd.DataFrame) -> pd.DataFrame:
    """Monta os números da home em formato longo (grão: id do número).

    Entrada: os DataFrames exportados `escolas` e `indicadores` — nunca
    `data/interim/`, para que o agregado nasça do mesmo recorte que o site lê.
    Saída: `id`, `bloco`, `grupo`, `etapa`, `ano`, `metrica`, `valor`, `n`,
    `estado`; `valor` quantizado a 4 decimais e `n` inteiro ou nulo.
    Idempotente: sim — derivação pura, em ordem fixa.
    """
    linhas: list[dict] = []

    def linha(id, bloco, grupo, etapa, metrica, valor, n=None) -> None:
        linhas.append(
            {
                "id": id,
                "bloco": bloco,
                "grupo": grupo,
                "etapa": etapa,
                "ano": "2025",
                "metrica": metrica,
                "valor": None if valor is None else round(float(valor), 4),
                "n": n,
                "estado": "valor",
            }
        )

    # Contagem do cadastro: 1.291 escolas em 35 RAs (não é o universo do Ideb).
    linha("escolas-total", "contagem", "todas", "", "escolas", len(escolas))
    linha("ras-total", "contagem", "todas", "", "ras", int(escolas["ra"].nunique()), len(escolas))

    # Creche: unidades que ofertam creche e a matrícula delas em 2025.
    creche = escolas[escolas["oferta_inf_cre"] == 1]
    if creche["mat_inf_cre_2025"].isna().any():
        raise ExportError(
            "agregado da home: unidade que oferta creche sem matrícula de 2025; "
            "nulo não entra como zero"
        )
    mat_creche = creche["mat_inf_cre_2025"]
    unidades = int(len(creche))
    unidades_estadual = int((creche["rede"] == "estadual").sum())
    mat_total = int(mat_creche.sum())
    mat_estadual = int(mat_creche[creche["rede"] == "estadual"].sum())
    linha("creche-unidades-total", "creche", "todas", "", "unidades", unidades)
    linha("creche-unidades-estadual", "creche", "estadual", "", "unidades",
          unidades_estadual, unidades)
    linha("creche-mat-total", "creche", "todas", "", "matriculas", mat_total, unidades)
    linha("creche-mat-estadual", "creche", "estadual", "", "matriculas",
          mat_estadual, unidades_estadual)
    linha("creche-mat-estadual-pct", "creche", "estadual", "", "percentual",
          100 * mat_estadual / mat_total if mat_total else None, mat_total)

    # Cobertura do Ideb no universo de escolas com AI, AF ou EM em 2025.
    universo = escolas[
        (escolas["oferta_fund_ai"] == 1)
        | (escolas["oferta_fund_af"] == 1)
        | (escolas["oferta_med"] == 1)
    ]
    ideb = indicadores[
        (indicadores["indicador"] == "ideb_observado") & (indicadores["ano"] == "2025")
    ]
    com_valor = set(
        zip(
            ideb.loc[ideb["estado"] == "valor", "co_entidade"],
            ideb.loc[ideb["estado"] == "valor", "etapa"],
        )
    )
    com_linha = set(zip(ideb["co_entidade"], ideb["etapa"]))
    ofertas = (("AI", "oferta_fund_ai"), ("AF", "oferta_fund_af"), ("EM", "oferta_med"))
    contagem = {
        "publica": {"com_valor": 0, "linha_sem_valor": 0, "sem_linha": 0},
        "privada": {"com_valor": 0, "linha_sem_valor": 0, "sem_linha": 0},
    }
    for r in universo.itertuples():
        etapas = [etapa for etapa, coluna in ofertas if getattr(r, coluna) == 1]
        grupo = "publica" if r.rede in ("estadual", "federal") else "privada"
        if any((r.co_entidade, etapa) in com_valor for etapa in etapas):
            contagem[grupo]["com_valor"] += 1
        elif any((r.co_entidade, etapa) in com_linha for etapa in etapas):
            contagem[grupo]["linha_sem_valor"] += 1
        else:
            contagem[grupo]["sem_linha"] += 1
    total_universo = int(len(universo))
    total_com_valor = sum(c["com_valor"] for c in contagem.values())
    total_sem_valor = total_universo - total_com_valor
    linha("ideb-universo", "ausencia", "todas", "", "escolas", total_universo)
    linha("ideb-com-valor", "ausencia", "todas", "", "escolas", total_com_valor)
    linha("ideb-sem-valor", "ausencia", "todas", "", "escolas", total_sem_valor)
    for grupo in ("publica", "privada"):
        c = contagem[grupo]
        linha(f"ideb-{grupo}-com-valor", "ausencia", grupo, "", "escolas", c["com_valor"])
        linha(
            f"ideb-{grupo}-linha-sem-valor", "ausencia", grupo, "", "escolas",
            c["linha_sem_valor"],
        )
        linha(f"ideb-{grupo}-sem-linha", "ausencia", grupo, "", "escolas", c["sem_linha"])

    # Distribuição da distorção idade-série por rede: todos os valores publicados
    # (estados valor e zero), sem limiar de n — a página da escola suprime a taxa
    # de turma pequena (D4), aqui ela entra e a diferença é declarada (L-67).
    tdi = indicadores[
        (indicadores["indicador"] == "tdi")
        & (indicadores["ano"] == "2025")
        & (indicadores["estado"].isin(["valor", "zero"]))
    ]
    tdi = tdi.merge(escolas[["co_entidade", "rede"]], on="co_entidade", how="left")
    grupos = {
        "estadual": {"estadual"},
        "privada": {"privada conveniada", "privada não conveniada"},
    }
    for etapa, rotulo in (("AI", "anos iniciais"), ("AF", "anos finais"), ("EM", "ensino médio")):
        for grupo, redes in grupos.items():
            serie = tdi.loc[(tdi["etapa"] == etapa) & tdi["rede"].isin(redes), "valor"]
            if serie.empty:
                raise ExportError(
                    f"agregado da home: sem unidade de distorção em {etapa}/{grupo}"
                )
            prefixo = f"tdi-{etapa.lower()}-{grupo}"
            linha(f"{prefixo}-p10", "tdi", grupo, rotulo, "p10",
                  float(serie.quantile(0.10)), int(serie.size))
            linha(f"{prefixo}-mediana", "tdi", grupo, rotulo, "mediana",
                  float(serie.median()), int(serie.size))
            linha(f"{prefixo}-p90", "tdi", grupo, rotulo, "p90",
                  float(serie.quantile(0.90)), int(serie.size))
            linha(f"{prefixo}-n", "tdi", grupo, rotulo, "unidades", int(serie.size))

    agregados = pd.DataFrame(
        linhas,
        columns=["id", "bloco", "grupo", "etapa", "ano", "metrica", "valor", "n", "estado"],
    )
    agregados["n"] = pd.array(agregados["n"], dtype="Int64")
    if agregados["id"].duplicated().any():
        raise ExportError("agregado da home com id duplicado")
    return agregados


def _grava_parquets(
    destino: Path,
    escolas: pd.DataFrame,
    indicadores: pd.DataFrame,
    infra: pd.DataFrame,
    ideb_uf: pd.DataFrame,
    agregados: pd.DataFrame,
) -> dict[str, str]:
    """Grava os cinco parquets e devolve o sha256 de cada um."""
    escolas.to_parquet(destino / "escolas.parquet", index=False)
    indicadores.to_parquet(destino / "indicadores.parquet", index=False)
    infra.to_parquet(destino / "infraestrutura.parquet", index=False)
    ideb_uf.to_parquet(destino / "ideb_uf.parquet", index=False)
    agregados.to_parquet(destino / "agregados.parquet", index=False)
    return {
        nome: sha256(destino / nome)
        for nome in (
            "escolas.parquet",
            "indicadores.parquet",
            "infraestrutura.parquet",
            "ideb_uf.parquet",
            "agregados.parquet",
        )
    }


def export_public(
    dest: Path,
    force: bool = False,
    etapas_puladas: list[str] | None = None,
) -> dict[str, int]:
    """Exporta `data/public/` a partir de `data/interim/`.

    Entrada: parquets de `data/interim/seedf/` e `data/interim/inep/`.
    Saída:   `dest/escolas.parquet`, `dest/indicadores.parquet`,
             `dest/infraestrutura.parquet`, `dest/ideb_uf.parquet`,
             `dest/agregados.parquet` e `dest/procedencia.json`.
    Idempotente: sim — o mesmo insumo produz os mesmos bytes. Se `dest` já tem
    um arquivo com sha256 diferente do que seria gravado, a exportação falha e
    só sobrescreve com `force=True`, para que mudança no insumo apareça no diff.

    `etapas_puladas` só é preenchido quando o `06` roda com `--parcial`; a lista
    fica registrada em `procedencia.json` e o build avisa sobre ela.
    """
    import tempfile

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    escolas = _escolas_publicas()
    indicadores = _indicadores_publicos(escolas)
    infra = _infraestrutura_publica(escolas)
    ideb_uf = _ideb_uf_publica()
    agregados = _agregados_publicos(escolas, indicadores)

    with tempfile.TemporaryDirectory(prefix=".public-", dir=dest.parent) as tmp:
        tmp = Path(tmp)
        hashes = _grava_parquets(tmp, escolas, indicadores, infra, ideb_uf, agregados)
        procedencia = {
            "sha256": hashes,
            "registros": _registros_publicos(),
            "execucao": {"etapas_puladas": [str(etapa) for etapa in (etapas_puladas or [])]},
        }
        (tmp / "procedencia.json").write_text(
            json.dumps(procedencia, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

        novos = {
            nome: sha256(tmp / nome)
            for nome in (
                "escolas.parquet",
                "indicadores.parquet",
                "infraestrutura.parquet",
                "ideb_uf.parquet",
                "agregados.parquet",
                "procedencia.json",
            )
        }
        diferentes = [
            nome
            for nome, digest in novos.items()
            if (dest / nome).exists() and sha256(dest / nome) != digest
        ]
        if diferentes and not force:
            raise ExportError(
                f"{dest} já existe com conteúdo diferente em "
                + ", ".join(diferentes)
                + "; rode com --force para sobrescrever (a mudança aparece no diff)"
            )

        dest.mkdir(parents=True, exist_ok=True)
        for nome in novos:
            (tmp / nome).replace(dest / nome)

        return {
            "escolas": len(escolas),
            "indicadores": len(indicadores),
            "infraestrutura": len(infra),
            "ideb_uf": len(ideb_uf),
            "agregados": len(agregados),
        }


ETAPAS = [
    ("q1", q1), ("q2", q2), ("q3", q3), ("q4", q4), ("q5", q5), ("q6", q6),
    ("q7", q7), ("q8", q8), ("q9", q9), ("q10", q10), ("q11", q11), ("q12", q12),
    ("q13", q13), ("q14", q14), ("q15", q15), ("q16", q16),
]


def main(argv: list[str] | None = None) -> int:
    """Executa as etapas e registra o que rodou, o que pulou e por quê.

    Saída: `data/interim/q0_execucao.csv`, uma linha por etapa, com
    `status = executado|pulado` e o motivo. Código de saída 1 se alguma etapa
    pulou (a menos de `--parcial`), 0 caso contrário.
    """
    import argparse
    import time

    ap = argparse.ArgumentParser(description="Respostas da fase 0, com registro de execução.")
    ap.add_argument(
        "--parcial",
        action="store_true",
        help="aceita etapa pulada e sai com zero; sem a flag, etapa pulada faz sair com 1",
    )
    ap.add_argument(
        "--public",
        type=Path,
        metavar="DIR",
        help="exporta o recorte versionado que o build do site lê (ex.: data/public)",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="sobrescreve --public mesmo quando o sha256 do destino difere",
    )
    args = ap.parse_args(argv)
    if args.force and not args.public:
        ap.error("--force só faz sentido com --public")

    execucao = []
    for nome, funcao in ETAPAS:
        inicio = time.time()
        try:
            funcao()
            status, motivo = "executado", ""
        except Pulado as exc:
            status, motivo = "pulado", str(exc)
            print(f"\n== {nome.upper()} PULADO: {motivo}")
        execucao.append(
            {
                "etapa": nome,
                "status": status,
                "motivo": motivo,
                "segundos": round(time.time() - inicio, 1),
            }
        )

    registro = pd.DataFrame(execucao)
    registro.to_csv(INTERIM / "q0_execucao.csv", index=False)
    print("\n== execução: " + "; ".join(f"{r.etapa}={r.status}" for r in registro.itertuples()))

    puladas = registro[registro["status"] == "pulado"]
    if len(puladas):
        print(
            f"\n{len(puladas)} etapa(s) pulada(s): "
            + ", ".join(puladas["etapa"])
            + ". Veja o motivo em data/interim/q0_execucao.csv."
        )
        if not args.parcial:
            print("Use --parcial para aceitar o resultado incompleto.")
            return 1
        print("--parcial: exportando o insumo com o resultado incompleto.")

    if args.public:
        try:
            resumo = export_public(
                args.public,
                force=args.force,
                etapas_puladas=puladas["etapa"].tolist(),
            )
        except ExportError as exc:
            print(f"\n== EXPORTAÇÃO PÚBLICA FALHOU: {exc}")
            return 1
        print(
            "\n== insumo público: "
            f"{resumo['escolas']:,} escolas, {resumo['indicadores']:,} linhas de indicador, "
            f"{resumo['infraestrutura']:,} linhas de infraestrutura, "
            f"{resumo['ideb_uf']:,} linhas de Ideb por UF e "
            f"{resumo['agregados']:,} agregados da home em {args.public}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
