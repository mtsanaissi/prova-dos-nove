"""Respostas às seis perguntas da fase 0, ao Ideb nacional (q7–q10) e ao Ideb
ausente (q11–q12).

Entrada: parquets de `data/interim/seedf/`, `data/interim/pdad_populacao.csv`,
         `data/interim/pdad/` (agregados da PDAD-A) e `data/interim/inep/`.
Saída:   `data/interim/q1_unidades.csv` ... `q8_conferencia_seedf.csv`,
         `q9_em_integrado.csv`, `q10_fluxo_df.csv`, `q11_distorcao_df.csv`,
         `q12_*.csv`, os três `q3_biblioteca*.csv` e um log com os números que
         vão para o REPORT.md.
Idempotente: sim — leitura e reescrita das saídas.

Regra de leitura: nulo é ausente, `0` é zero. Nunca se soma nulo como zero.
"""

from __future__ import annotations

import pandas as pd

from _common import INTERIM, norm_ra

S = INTERIM / "seedf"
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
        icc = (ssb / (k - 1)) / ((sst - ssb) / (n - k))  # F
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
                "icc": round(icc, 3),
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

    tab = pd.concat([oferta, mat03, mat4, unidades, pop, pop03, freq03], axis=1).fillna(0)
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
        print("\n== Q7 não executado: falta data/interim/inep/ideb_uf_tidy.parquet (rode 08)")
        return
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

    uf = pd.read_parquet(arquivos["uf"])
    br = pd.read_parquet(arquivos["brasil"])
    esc = pd.read_parquet(arquivos["escolas"])
    uf = uf[(uf["indicador"] == "ideb_observado") & uf["valor"].notna()]
    br = br[(br["indicador"] == "ideb_observado") & br["valor"].notna()]
    esc = esc[esc["indicador"] == "ideb_observado"]

    # 1. DF × Brasil × mediana das UFs, por etapa, rede e ano.
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


if __name__ == "__main__":
    q1()
    q2()
    q3()
    q4()
    q5()
    q6()
    q7()
    q8()
    q9()
    q10()
    q11()
    q12()
