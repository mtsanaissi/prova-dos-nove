"""Perfil e recorte do DF dos arquivos da INEP ingeridos em `data/raw/inep/`.

Entrada: `data/raw/inep/*.zip` (ingeridos por 07_ingest_inep.py).
Saída:   `data/interim/inep_perfil.csv` e, em `data/interim/inep/`,
         `ideb_uf_tidy.parquet`, `brasil_ideb_tidy.parquet`,
         `ideb_uf_em_integrado_tidy.parquet`, `ideb_escolas_df.parquet`,
         `tx_rend_escolas_df.parquet`, `tdi_escolas_df.parquet` e
         `tnr_escolas_df.parquet` (os quatro últimos só com o DF).
Idempotente: sim — reescreve as saídas a partir dos brutos.

O script não presume o formato interno dos arquivos da INEP (não há dois
produtos com o mesmo desenho). Ele lista o conteúdo, lê o cabeçalho de cada
tabela, mostra as colunas e só recorta quando reconhece uma coluna de UF. Se
não reconhecer, diz isso em vez de adivinhar.

Para os três zips de Ideb por escola, o recorte do DF é feito em **streaming**
(`openpyxl` em modo `read_only`): a planilha tem dezenas de milhares de linhas e
o recorte é uma fração pequena delas. Carregar a planilha inteira em `pandas`
para depois filtrar custaria memória sem ganho.
"""

from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from _common import INTERIM, RAW

INEP = RAW / "inep"
OUT = INTERIM / "inep"
TABULAR = {".xlsx", ".xls", ".csv"}
UF_COLS = {"SG_UF", "UF", "UF_SIGLA", "SG_UF_ESCOLA", "CO_UF"}
UF_SIGLAS = {
    "RO", "AC", "AM", "RR", "PA", "AP", "TO", "MA", "PI", "CE", "RN", "PB",
    "PE", "AL", "SE", "BA", "MG", "ES", "RJ", "SP", "PR", "SC", "RS", "MS",
    "MT", "GO", "DF",
}
ESCOLAS_ZIP = re.compile(r"divulgacao_(anos_iniciais|anos_finais|ensino_medio)_escolas")
# Indicadores de uma taxa por escola (TDI e TNR). Apesar do mesmo desenho — uma
# aba `ESCOLAS`, 8 linhas de título, códigos na linha 9 — os códigos **não** são
# escritos no mesmo padrão: a TDI usa `<recorte>_CAT_0` (`FUN_AI_CAT_0`) e a TNR
# usa `4_CAT_<recorte>` (`4_CAT_FUN_AI`), porque na TNR a categoria (não-resposta)
# vem antes do recorte. Um leitor que assumisse um dos dois padrões leria zero
# colunas no outro.
INDICADORES_ESCOLA = [
    {
        "marca": "TDI_2025_ESCOLAS",
        "xlsx": "TDI_ESCOLAS_2025.xlsx",
        "indicador": "distorcao_idade_serie",
        "padrao": re.compile(r"^(?P<recorte>.+)_CAT_0$"),
        "saida": "tdi_escolas_df.parquet",
    },
    {
        "marca": "tnr_escolas_2025",
        "xlsx": "tnr_escolas_2025.xlsx",
        "indicador": "taxa_nao_resposta",
        "padrao": re.compile(r"^4_CAT_(?P<recorte>.+)$"),
        "saida": "tnr_escolas_df.parquet",
    },
]
# A planilha do médio com o integrado escreve três UFs por extenso; a do médio
# regular usa abreviação ("R. G. do Norte"). O mapa deixa as duas na mesma chave.
UFS_POR_EXTENSO = {
    "R. G. do Norte": "Rio Grande do Norte",
    "R. G. do Sul": "Rio Grande do Sul",
    "M. G. do Sul": "Mato Grosso do Sul",
}


def membros_do_zip(zip_path: Path) -> list[str]:
    """Lista o conteúdo do zip sem extrair."""
    with zipfile.ZipFile(zip_path) as z:
        return z.namelist()


def ler_cabecalho(caminho: Path) -> tuple[pd.DataFrame | None, list[str], str]:
    """Lê as primeiras linhas e devolve (amostra, abas, erro)."""
    try:
        if caminho.suffix.lower() == ".csv":
            amostra = pd.read_csv(caminho, dtype=str, nrows=20, sep=None, engine="python")
            return amostra, ["(csv único)"], ""
        abas = pd.ExcelFile(caminho).sheet_names
        amostra = pd.read_excel(caminho, sheet_name=abas[0], dtype=str, nrows=20)
        return amostra, abas, ""
    except Exception as exc:  # noqa: BLE001
        return None, [], f"{type(exc).__name__}: {exc}"


def achar_coluna_uf(colunas: list[str]) -> str | None:
    for c in colunas:
        if str(c).strip().upper() in UF_COLS:
            return c
    return None


def filtrar_df(df: pd.DataFrame, col_uf: str) -> pd.DataFrame:
    """Recorta o DF pela coluna de UF, aceitando sigla ou código."""
    v = df[col_uf].astype(str).str.strip().str.upper()
    if col_uf.upper() == "CO_UF":
        return df[v.isin({"53", "53.0"})]
    return df[v == "DF"]


UFS = {
    "Rondônia", "Acre", "Amazonas", "Roraima", "Pará", "Amapá", "Tocantins",
    "Maranhão", "Piauí", "Ceará", "R. G. do Norte", "Paraíba", "Pernambuco",
    "Alagoas", "Sergipe", "Bahia", "Minas Gerais", "Espírito Santo",
    "Rio de Janeiro", "São Paulo", "Paraná", "Santa Catarina", "R. G. do Sul",
    "M. G. do Sul", "Mato Grosso", "Goiás", "Distrito Federal",
}
REGIOES = {"Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"}


def _extrair(zip_path: Path) -> Path:
    """Extrai o zip para um diretório temporário e devolve a raiz."""
    destino = Path(tempfile.mkdtemp(prefix="inep_"))
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(destino)
    return destino


def processar_ideb_uf(zip_path: Path) -> None:
    """Lê a divulgação do Ideb por UF (planilha formatada) e grava formato longo.

    A planilha tem 5 linhas de título, cabeçalho em três faixas e os códigos das
    variáveis na linha 10 (`VL_OBSERVADO_2025`, `VL_PROJECAO_2019`...). Não é uma
    tabela legível por `read_excel` direto: os nomes de coluna reais estão na
    linha de códigos, e as demais linhas são rótulos humanos.

    Mantém **todas as UFs**, não só o DF: sem as outras 26 não existe comparação
    possível, e a tabela inteira tem menos de 200 linhas.
    """
    xlsx = next(p for p in _extrair(zip_path).rglob("*.xlsx") if "regioes_ufs" in p.name)
    partes = []
    for aba in pd.ExcelFile(xlsx).sheet_names:
        etapa = re.search(r"\((A[IF]|EM)\)", aba)
        if not etapa:
            continue
        bruto = pd.read_excel(xlsx, sheet_name=aba, header=None, dtype=str)
        linha_cod = next(
            i for i in range(len(bruto))
            if any(str(v).startswith("VL_OBSERVADO_") for v in bruto.iloc[i].tolist())
        )
        codigos = [str(c) for c in bruto.iloc[linha_cod].tolist()]
        corpo = bruto.iloc[linha_cod + 1:].copy()
        corpo = corpo[corpo[0].astype(str).str.strip().isin(UFS | REGIOES)]
        for indicador, prefixo in (("ideb_observado", "VL_OBSERVADO_"), ("ideb_projetado", "VL_PROJECAO_")):
            for col, codigo in enumerate(codigos):
                if not codigo.startswith(prefixo):
                    continue
                ano = codigo.rsplit("_", 1)[-1]
                partes.append(
                    pd.DataFrame(
                        {
                            "etapa": etapa.group(1),
                            "local": corpo[0].astype(str).str.strip(),
                            "rede": corpo[1].astype(str).str.strip(),
                            "ano": ano,
                            "indicador": indicador,
                            "valor": pd.to_numeric(corpo[col], errors="coerce"),
                        }
                    )
                )
    tidy = pd.concat(partes, ignore_index=True)
    shutil.rmtree(xlsx.parent.parent, ignore_errors=True)
    # o rótulo de rede carrega marcadores de nota de rodapé, ex. 'Total (3)(4)':
    # são ressalvas históricas (2009, 2011), não de todos os anos. Preserva-se o
    # rótulo original e separa-se a base sem marcador.
    tidy["rede_base"] = tidy["rede"].str.replace(r"\s*\([\d)(]+\)\s*$", "", regex=True).str.strip()
    tidy["marcadores_nota"] = tidy["rede"].str.extract(r"\(([\d)(]+)\)\s*$").fillna("")
    destino = OUT / "ideb_uf_tidy.parquet"
    tidy.to_parquet(destino, index=False)
    print(
        f"   Ideb por UF: {len(tidy)} linhas, {tidy.etapa.nunique()} etapas, "
        f"{tidy.local.nunique()} locais, {sorted(tidy.ano.unique())} → {destino.name}"
    )


def _texto_codigo(v) -> str:
    """Converte célula em texto sem perder o código: 53000854.0 → '53000854'."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _classificar_celula(v) -> tuple[float | None, str, str]:
    """Devolve (valor, valor_bruto, estado) preservando ausência como ausência.

    Nas planilhas do Ideb a célula vazia é traço `'-'`, que significa **sem
    resultado divulgado** (não participou do Saeb ou participação insuficiente,
    conforme a Portaria nº 435/2025) — nunca desempenho zero. O texto original
    fica em `valor_bruto` para que nenhum token seja apagado na conversão.
    """
    if v is None:
        return None, "", "ausente"
    if isinstance(v, bool):  # openpyxl não devolve bool aqui, mas não custa
        return None, str(v), "ausente"
    if isinstance(v, (int, float)):
        x = float(v)
        return x, f"{x:g}", "zero" if x == 0 else "valor"
    s = str(v).strip()
    if s in {"", "-", "nan", "None"}:
        return None, s, "ausente"
    try:
        x = float(s)
    except ValueError:
        # token não numérico (ex. ND, ND*): mantido como ausente e registrado
        return None, s, "ausente"
    return x, s, "zero" if x == 0 else "valor"


def estado_da_taxa(v) -> tuple[float | None, str, str]:
    """Classifica célula de taxa: `'--'` = não aplicável; vazio = ausente.

    É o vocabulário das planilhas de indicadores por escola (taxas de rendimento,
    TDI e TNR): o traço duplo marca a etapa/série sem matrícula na escola — a
    taxa não se aplica e não vale zero. `0` é zero medido (abandono zero, TNR
    zero) e entra como `zero`.
    """
    if v is None:
        return None, "", "ausente"
    if isinstance(v, (int, float)):
        x = float(v)
        return x, f"{x:g}", "zero" if x == 0 else "valor"
    s = str(v).strip()
    if s == "--":
        return None, s, "nao_aplicavel"
    if s in {"", "nan", "None"}:
        return None, s, "ausente"
    try:
        x = float(s)
    except ValueError:
        return None, s, "ausente"
    return x, s, "zero" if x == 0 else "valor"


def _banda_ideb(bruto: pd.DataFrame, linha_cod: int) -> dict[int, str]:
    """Lê os anos da faixa de cabeçalho ('IDEB 2023 (N x P)') por coluna.

    Serve de reserva quando a célula de código está vazia. É o caso da aba
    `Brasil (Anos Finais)`: a coluna do Ideb de 2023 **tem valor** (5,0) mas o
    código `VL_OBSERVADO_2023` não foi preenchido na linha de códigos. Ler só os
    códigos perderia o Ideb de 2023 do Brasil nos anos finais.
    """
    melhor: dict[int, str] = {}
    for i in range(linha_cod):
        anos = {}
        for col, v in enumerate(bruto.iloc[i].tolist()):
            m = re.search(r"IDEB\s*(\d{4})", str(v), re.I)
            if m:
                anos[col] = m.group(1)
        if len(anos) > len(melhor):
            melhor = anos
    return melhor


def _completar_codigos(codigos: list[str], banda: dict[int, str]) -> list[str]:
    """Preenche código vazio com o ano da faixa de cabeçalho, e relata."""
    completos = list(codigos)
    for col, ano in banda.items():
        if col >= len(completos):
            continue
        if completos[col] in {"", "nan"}:
            completos[col] = f"VL_OBSERVADO_{ano}"
            print(
                f"   coluna {col + 1} sem código; ano {ano} lido da faixa de cabeçalho "
                f"→ {completos[col]}"
            )
    return completos


def processar_uf_em_integrado(xlsx: Path) -> None:
    """Lê o Ideb do ensino médio **com o integrado à EPT**, por UF e rede estadual.

    Planilha solta (não vem em zip), uma aba, 5 linhas de título, cabeçalho em
    três faixas e códigos na linha 10 — o mesmo desenho da divulgação por UF. A
    primeira coluna é o nome da UF por extenso, sem código; a rede é sempre
    `Estadual`; não há linha Brasil nem regiões.

    `etapa` recebe `EM_integrado` para não se confundir com `EM`, que é o médio
    regular: são recortes diferentes do mesmo indicador, e misturar os dois
    mudaria a série sem aviso. `valor_bruto` preserva `'-'` quando não há valor.
    """
    bruto = pd.read_excel(xlsx, sheet_name=0, header=None, dtype=str)
    linha_cod = next(
        i for i in range(len(bruto))
        if any(str(v).startswith("VL_OBSERVADO_") for v in bruto.iloc[i].tolist())
    )
    codigos = [str(c) for c in bruto.iloc[linha_cod].tolist()]
    corpo = bruto.iloc[linha_cod + 1:].copy()
    nomes_validos = {UFS_POR_EXTENSO.get(n, n) for n in UFS}
    corpo = corpo[corpo[0].astype(str).str.strip().isin(nomes_validos)]

    partes = []
    for col, codigo in enumerate(codigos):
        if not codigo.startswith("VL_OBSERVADO_"):
            continue
        ano = codigo.rsplit("_", 1)[-1]
        bruto_col = corpo[col].astype(str).str.strip()
        partes.append(
            pd.DataFrame(
                {
                    "etapa": "EM_integrado",
                    "local": corpo[0].astype(str).str.strip(),
                    "local_base": corpo[0].astype(str).str.strip().map(
                        lambda n: UFS_POR_EXTENSO.get(n, n)
                    ),
                    "rede": corpo[1].astype(str).str.strip(),
                    "ano": ano,
                    "indicador": "ideb_observado",
                    "valor": pd.to_numeric(corpo[col], errors="coerce"),
                    "valor_bruto": bruto_col.where(~bruto_col.isin({"nan", "None"}), ""),
                }
            )
        )
    tidy = pd.concat(partes, ignore_index=True)
    destino = OUT / "ideb_uf_em_integrado_tidy.parquet"
    tidy.to_parquet(destino, index=False)
    df_25 = tidy[(tidy.ano == "2025") & tidy.valor.notna()]
    print(
        f"   Ideb EM com integrado à EPT: {len(tidy)} linhas, {tidy.local.nunique()} UFs, "
        f"anos {sorted(tidy.ano.unique())}, redes {sorted(tidy.rede.unique())} → {destino.name}"
    )
    print(
        f"     2025: {len(df_25)} UFs com valor, DF "
        f"{tidy.loc[(tidy.local == 'Distrito Federal') & (tidy.ano == '2025'), 'valor'].tolist()}"
    )


def processar_tx_rend(zip_path: Path) -> pd.DataFrame:
    """Recorta o DF das taxas de rendimento por escola e devolve formato longo.

    A planilha tem uma aba (`ESCOLAS`), 5 linhas de título, cabeçalho em três
    faixas e os códigos na linha 9: `NU_ANO_CENSO`…`NO_DEPENDENCIA` e 54 colunas
    de taxa, no padrão `<categoria>_CAT_<recorte>` — `1_CAT_*` aprovação,
    `2_CAT_*` reprovação, `3_CAT_*` abandono; `FUN`/`FUN_AI`/`FUN_AF`/`FUN_01`…
    e `MED`/`MED_01`…/`MED_NS`.

    O token `'--'` é **não aplicável** (a escola não tem matrícula naquela etapa
    ou série), e não zero; célula vazia é ausente. Os três estados vão para
    `estado`, com o texto original em `valor_bruto`.
    """
    xlsx = next(p for p in _extrair(zip_path).rglob("*.xlsx") if "tx_rend" in p.name)
    wb = load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    it = ws.iter_rows(values_only=True)

    codigos: list[str] | None = None
    linha_cod = 0
    for i, row in enumerate(it):
        vals = ["" if v is None else str(v) for v in row]
        if vals and vals[0] == "NU_ANO_CENSO":
            codigos, linha_cod = vals, i
            break
    if codigos is None:
        raise RuntimeError(f"{zip_path.name}: linha de códigos NU_ANO_CENSO não encontrada")

    nomes = ("NU_ANO_CENSO", "SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO",
             "CO_ENTIDADE", "NO_ENTIDADE", "NO_CATEGORIA", "NO_DEPENDENCIA")
    col = {c: codigos.index(c) for c in nomes}
    taxas = [(k, c) for k, c in enumerate(codigos) if re.match(r"^[123]_CAT_", c)]

    def cel(row, k: int):
        return row[k] if k < len(row) else None

    linhas = []
    n_total = n_df = 0
    for row in it:
        n_total += 1
        if _texto_codigo(cel(row, col["SG_UF"])) != "DF":
            continue
        n_df += 1
        base = {
            "NU_ANO_CENSO": _texto_codigo(cel(row, col["NU_ANO_CENSO"])),
            "SG_UF": "DF",
            "CO_MUNICIPIO": _texto_codigo(cel(row, col["CO_MUNICIPIO"])),
            "NO_MUNICIPIO": str(cel(row, col["NO_MUNICIPIO"]) or "").strip(),
            "CO_ENTIDADE": _texto_codigo(cel(row, col["CO_ENTIDADE"])),
            "NO_ENTIDADE": str(cel(row, col["NO_ENTIDADE"]) or "").strip(),
            "NO_CATEGORIA": str(cel(row, col["NO_CATEGORIA"]) or "").strip(),
            "NO_DEPENDENCIA": str(cel(row, col["NO_DEPENDENCIA"]) or "").strip(),
        }
        for k, campo in taxas:
            valor, texto, estado = estado_da_taxa(cel(row, k))
            categoria, recorte = campo.split("_CAT_", 1)
            linhas.append(
                {
                    **base,
                    "campo": campo,
                    "categoria": {"1": "aprovacao", "2": "reprovacao", "3": "abandono"}[categoria],
                    "recorte": recorte,
                    "valor": valor,
                    "valor_bruto": texto,
                    "estado": estado,
                }
            )
    wb.close()
    shutil.rmtree(xlsx.parent.parent, ignore_errors=True)

    df = pd.DataFrame(linhas)
    if df.empty:
        print(f"   taxas de rendimento: nenhuma linha do DF")
        return df
    dup = int(df.duplicated(subset=["CO_ENTIDADE", "campo"]).sum())
    print(
        f"   Taxas de rendimento: cabeçalho na linha {linha_cod + 1}, "
        f"{n_total} linhas nacionais, {n_df} do DF, {len(taxas)} taxas por escola"
    )
    print(
        f"     DF por dependência: {dict(Counter(df['NO_DEPENDENCIA']))}; "
        f"estados: {dict(Counter(df['estado']))}; duplicatas: {dup}"
    )
    return df


def medir_juncao_cadastro(df: pd.DataFrame) -> None:
    """Mede a junção `CO_ENTIDADE` × cadastro da SEEDF de 2025 e imprime a taxa.

    Mesma regra de 04 e q8: taxa medida antes de qualquer junção. Código do
    arquivo da INEP que não está no cadastro de 2025 é escola que não consta como
    ativa naquele ano — não é falha de chave, é diferença de universo, e fica
    registrada como órfã.
    """
    cadastro = INTERIM / "seedf" / "escolas__relatorio_escolas_2025.parquet"
    if not cadastro.exists():
        print("     junção não medida: falta o cadastro de 2025 (rode 03_profile_seedf.py)")
        return
    codigos = set(
        pd.read_parquet(cadastro, columns=["CO_ENTIDADE"])["CO_ENTIDADE"].astype(str).str.strip()
    )
    do_arquivo = set(df["CO_ENTIDADE"].astype(str))
    casados = len(do_arquivo & codigos)
    print(
        f"     junção com o cadastro de 2025: {casados} de {len(do_arquivo)} escolas do DF "
        f"({100 * casados / len(do_arquivo):.1f}% casadas); "
        f"{len(do_arquivo - codigos)} códigos fora do cadastro"
    )


def processar_indicador_escola(zip_path: Path, meta: dict) -> pd.DataFrame:
    """Recorta o DF de um indicador de uma taxa por escola (TDI ou TNR).

    Desenho medido nas duas planilhas: uma aba `ESCOLAS`, 8 linhas de título,
    códigos na linha 9 (`NU_ANO_CENSO`…`NO_DEPENDENCIA` + as taxas), dados da 10
    em diante, ~126 mil linhas nacionais. O que **não** é comum às duas é o padrão
    do código da taxa — a TDI escreve `<recorte>_CAT_0` e a TNR escreve
    `4_CAT_<recorte>` —, e é o `padrao` de `INDICADORES_ESCOLA` que diz qual
    vale em cada arquivo.

    A leitura é em streaming: o recorte do DF é uma fração pequena das linhas.
    `'--'` é não aplicável, célula vazia é ausente, `0` é zero medido; os três
    estados vão para `estado`, com o texto original em `valor_bruto`.
    """
    raiz = _extrair(zip_path)
    xlsx = next(p for p in raiz.rglob("*.xlsx") if meta["xlsx"] in p.name)
    wb = load_workbook(xlsx, read_only=True, data_only=True)
    abas = wb.sheetnames
    ws = wb[abas[0]]
    it = ws.iter_rows(values_only=True)

    padrao: re.Pattern = meta["padrao"]
    codigos: list[str] | None = None
    linha_cod = 0
    for i, row in enumerate(it):
        vals = ["" if v is None else str(v) for v in row]
        if vals and vals[0] == "NU_ANO_CENSO":
            codigos, linha_cod = vals, i
            break
    if codigos is None:
        raise RuntimeError(f"{zip_path.name}: linha de códigos NU_ANO_CENSO não encontrada")

    nomes = ("NU_ANO_CENSO", "NO_REGIAO", "SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO",
             "CO_ENTIDADE", "NO_ENTIDADE", "NO_CATEGORIA", "NO_DEPENDENCIA")
    col = {c: codigos.index(c) for c in nomes}
    taxas = [(k, c, padrao.match(c).group("recorte")) for k, c in enumerate(codigos) if padrao.match(c)]
    if not taxas:
        raise RuntimeError(
            f"{zip_path.name}: o padrão {padrao.pattern} não casou coluna alguma; "
            f"códigos lidos: {[c for c in codigos if c][:30]}"
        )

    def cel(row, k: int):
        return row[k] if k < len(row) else None

    linhas = []
    n_total = n_df = 0
    for row in it:
        n_total += 1
        if _texto_codigo(cel(row, col["SG_UF"])) != "DF":
            continue
        n_df += 1
        base = {
            "indicador": meta["indicador"],
            "NU_ANO_CENSO": _texto_codigo(cel(row, col["NU_ANO_CENSO"])),
            "NO_REGIAO": str(cel(row, col["NO_REGIAO"]) or "").strip(),
            "SG_UF": "DF",
            "CO_MUNICIPIO": _texto_codigo(cel(row, col["CO_MUNICIPIO"])),
            "NO_MUNICIPIO": str(cel(row, col["NO_MUNICIPIO"]) or "").strip(),
            "CO_ENTIDADE": _texto_codigo(cel(row, col["CO_ENTIDADE"])),
            "NO_ENTIDADE": str(cel(row, col["NO_ENTIDADE"]) or "").strip(),
            "NO_CATEGORIA": str(cel(row, col["NO_CATEGORIA"]) or "").strip(),
            "NO_DEPENDENCIA": str(cel(row, col["NO_DEPENDENCIA"]) or "").strip(),
        }
        for k, campo, recorte in taxas:
            valor, texto, estado = estado_da_taxa(cel(row, k))
            linhas.append(
                {**base, "campo": campo, "recorte": recorte, "valor": valor,
                 "valor_bruto": texto, "estado": estado}
            )
    wb.close()
    shutil.rmtree(raiz, ignore_errors=True)

    df = pd.DataFrame(linhas)
    if df.empty:
        print(f"   {meta['indicador']}: nenhuma linha do DF")
        return df
    dup = int(df.duplicated(subset=["CO_ENTIDADE", "campo"]).sum())
    tokens = sorted(set(df.loc[df.estado.isin({"ausente", "nao_aplicavel"}), "valor_bruto"].unique()))
    print(
        f"   {meta['indicador']}: abas {abas}, cabeçalho na linha {linha_cod + 1}, "
        f"{len([c for c in codigos if c])} colunas com código, {len(taxas)} taxas por escola; "
        f"{n_total} linhas nacionais, {n_df} do DF"
    )
    print(
        f"     recortes: {[r for _, _, r in taxas]}; dependências no DF: "
        f"{dict(Counter(df['NO_DEPENDENCIA']))}; estados: {dict(Counter(df['estado']))}; "
        f"duplicatas (escola × campo): {dup}"
    )
    print(f"     identificação: {', '.join(nomes)}")
    print(f"     tokens não numéricos: {tokens}")
    return df


def _etapa_da_aba(nome: str) -> str | None:
    """Mapeia o nome da aba para a sigla usada no projeto: AI, AF ou EM.

    As abas de UF se chamam `UF e Regiões (AI)`; as do Brasil, `Brasil (Anos
    Iniciais)`. Não há um padrão único entre os dois arquivos, então a sigla é
    extraída do que existir no nome, e não da posição da aba.
    """
    for padrao, etapa in (
        (r"Anos Iniciais|\bAI\b", "AI"),
        (r"Anos Finais|\bAF\b", "AF"),
        (r"\bEM\b", "EM"),
    ):
        if re.search(padrao, nome, re.I):
            return etapa
    return None


def processar_brasil(zip_path: Path) -> None:
    """Lê o Ideb do Brasil (planilha formatada, mesmo desenho da de UF).

    A planilha de UF e regiões não tem a linha "Brasil"; esta tem, e só ela.
    Saída no mesmo formato longo de `ideb_uf_tidy.parquet`, para que as duas
    possam ser empilhadas sem tradução.
    """
    xlsx = next(p for p in _extrair(zip_path).rglob("*.xlsx") if "brasil_ideb" in p.name)
    partes = []
    for aba in pd.ExcelFile(xlsx).sheet_names:
        etapa = _etapa_da_aba(aba)
        if not etapa:
            continue
        bruto = pd.read_excel(xlsx, sheet_name=aba, header=None, dtype=str)
        linha_cod = next(
            i for i in range(len(bruto))
            if any(str(v).startswith("VL_OBSERVADO_") for v in bruto.iloc[i].tolist())
        )
        codigos = _completar_codigos(
            [str(c) for c in bruto.iloc[linha_cod].tolist()], _banda_ideb(bruto, linha_cod)
        )
        corpo = bruto.iloc[linha_cod + 1:].copy()
        corpo = corpo[corpo[0].astype(str).str.strip().str.lower() == "brasil"]
        for indicador, prefixo in (
            ("ideb_observado", "VL_OBSERVADO_"),
            ("ideb_projetado", "VL_PROJECAO_"),
        ):
            for col, codigo in enumerate(codigos):
                if not codigo.startswith(prefixo):
                    continue
                ano = codigo.rsplit("_", 1)[-1]
                partes.append(
                    pd.DataFrame(
                        {
                            "etapa": etapa,
                            "local": corpo[0].astype(str).str.strip(),
                            "rede": corpo[1].astype(str).str.strip(),
                            "ano": ano,
                            "indicador": indicador,
                            "valor": pd.to_numeric(corpo[col], errors="coerce"),
                        }
                    )
                )
    tidy = pd.concat(partes, ignore_index=True)
    shutil.rmtree(xlsx.parent.parent, ignore_errors=True)
    tidy["rede_base"] = tidy["rede"].str.replace(r"\s*\([\d)(]+\)\s*$", "", regex=True).str.strip()
    tidy["marcadores_nota"] = tidy["rede"].str.extract(r"\(([\d)(]+)\)\s*$").fillna("")
    destino = OUT / "brasil_ideb_tidy.parquet"
    tidy.to_parquet(destino, index=False)
    print(
        f"   Ideb do Brasil: {len(tidy)} linhas, {tidy.etapa.nunique()} etapas, "
        f"redes {sorted(tidy.rede_base.unique())}, anos {sorted(tidy.ano.unique())} "
        f"→ {destino.name}"
    )


def processar_ideb_escolas(zip_path: Path, etapa: str) -> pd.DataFrame:
    """Recorta o DF do Ideb por escola e devolve formato longo (uma linha por célula).

    Lê a planilha em streaming (`read_only`): são ~66 mil linhas nacionais em
    anos iniciais e só ~426 do DF. O recorte é por `SG_UF == 'DF'`; o script
    confere que todo `CO_MUNICIPIO` resultante é 5300108 (o DF tem um único
    município) e imprime a contagem nacional de linhas lidas, para que o filtro
    não pareça maior do que foi.

    Estados possíveis em `estado`: `valor` (número divulgado), `zero` (zero
    divulgado) e `ausente` (traço ou célula vazia). Não há `nao_aplicavel`:
    a planilha só publica a coluna do ano em que a etapa é avaliada.
    """
    xlsx = next(p for p in _extrair(zip_path).rglob("*.xlsx") if "escolas" in p.name)
    wb = load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    it = ws.iter_rows(values_only=True)

    codigos: list[str] | None = None
    linha_cod = 0
    for i, row in enumerate(it):
        vals = ["" if v is None else str(v) for v in row]
        if "SG_UF" in vals and any(v.startswith("VL_OBSERVADO_") for v in vals):
            codigos, linha_cod = vals, i
            break
    if codigos is None:
        raise RuntimeError(f"{zip_path.name}: cabeçalho com SG_UF e VL_OBSERVADO_ não encontrado")

    nomes = ("SG_UF", "CO_MUNICIPIO", "NO_MUNICIPIO", "ID_ESCOLA", "NO_ESCOLA", "REDE")
    col = {c: codigos.index(c) for c in nomes}
    alvos = []
    for k, c in enumerate(codigos):
        if c.startswith("VL_OBSERVADO_"):
            alvos.append((k, "ideb_observado", c.rsplit("_", 1)[-1]))
        elif c.startswith("VL_PROJECAO_"):
            alvos.append((k, "ideb_projetado", c.rsplit("_", 1)[-1]))

    def cel(row, k: int):
        """Célula por índice, tolerando linha mais curta que o cabeçalho."""
        return row[k] if k < len(row) else None

    linhas, redes_nac = [], Counter()
    n_total = n_df = 0
    municipios = set()
    for row in it:
        n_total += 1
        uf = _texto_codigo(cel(row, col["SG_UF"]))
        if uf not in UF_SIGLAS:
            continue  # rodapé da planilha (fonte, notas) não é linha de escola
        redes_nac[_texto_codigo(cel(row, col["REDE"]))] += 1
        if uf != "DF":
            continue
        n_df += 1
        municipios.add(_texto_codigo(cel(row, col["CO_MUNICIPIO"])))
        base = {
            "etapa": etapa,
            "SG_UF": uf,
            "CO_MUNICIPIO": _texto_codigo(cel(row, col["CO_MUNICIPIO"])),
            "NO_MUNICIPIO": str(cel(row, col["NO_MUNICIPIO"]) or "").strip(),
            "ID_ESCOLA": _texto_codigo(cel(row, col["ID_ESCOLA"])),
            "NO_ESCOLA": str(cel(row, col["NO_ESCOLA"]) or "").strip(),
            "REDE": _texto_codigo(cel(row, col["REDE"])),
        }
        for k, indicador, ano in alvos:
            valor, texto, estado = _classificar_celula(cel(row, k))
            linhas.append(
                {**base, "ano": ano, "indicador": indicador, "valor": valor,
                 "valor_bruto": texto, "estado": estado}
            )
    wb.close()
    shutil.rmtree(xlsx.parent.parent, ignore_errors=True)

    df = pd.DataFrame(linhas)
    if df.empty:
        print(f"   {etapa}: nenhuma linha do DF")
        return df
    dup = int(df.duplicated(subset=["ID_ESCOLA", "ano", "indicador"]).sum())
    tokens = sorted(set(df.loc[df.estado == "ausente", "valor_bruto"].unique()))
    print(
        f"   {etapa}: cabeçalho na linha {linha_cod + 1}, {len(codigos)} colunas; "
        f"{n_total} linhas nacionais, {n_df} do DF; redes DF "
        f"{dict(Counter(df.loc[df.ano == df.ano.max(), 'REDE']))}"
    )
    print(
        f"     nacional por rede: {dict(redes_nac)}; municípios do DF: {sorted(municipios)}; "
        f"duplicatas (escola × ano × indicador): {dup}"
    )
    if municipios != {"5300108"}:
        print(f"   ATENÇÃO: município inesperado em linha do DF: {sorted(municipios)}")
    print(f"     tokens de ausência encontrados: {tokens}")
    return df


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    zips = sorted(INEP.glob("*.zip"))
    pdfs = sorted(INEP.glob("*.pdf"))
    planilhas = sorted(INEP.glob("*.xlsx"))
    if not zips and not pdfs and not planilhas:
        print("nenhum arquivo da INEP em data/raw/inep — rode 07_ingest_inep.py --check")
        return

    perfil = []
    partes_escola = []
    for z in zips:
        membros = membros_do_zip(z)
        print(f"\n== {z.name}: {len(membros)} membros")
        for m in membros:
            print(f"   {m}")

        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(z) as zf:
                zf.extractall(tmp)
            for membro in membros:
                extraido = Path(tmp) / membro
                if not extraido.is_file():
                    continue
                if extraido.suffix.lower() not in TABULAR:
                    if extraido.suffix.lower() == ".ods":
                        perfil.append({"arquivo": z.name, "membro": membro, "formato": "ods", "situacao": "não lido (falta odfpy)"})
                    continue
                amostra, abas, erro = ler_cabecalho(extraido)
                if amostra is None:
                    perfil.append({"arquivo": z.name, "membro": membro, "formato": extraido.suffix, "situacao": f"erro: {erro}"})
                    print(f"   ERRO ao ler {membro}: {erro}")
                    continue
                col_uf = achar_coluna_uf(list(amostra.columns))
                print(
                    f"   {membro}: {len(abas)} aba(s) {abas[:4]}, {amostra.shape[1]} colunas, "
                    f"UF identificada: {col_uf or 'NÃO'}"
                )
                perfil.append(
                    {
                        "arquivo": z.name,
                        "membro": membro,
                        "formato": extraido.suffix,
                        "abas": ";".join(abas),
                        "colunas": amostra.shape[1],
                        "colunas_nomes": ";".join(map(str, amostra.columns))[:800],
                        "coluna_uf": col_uf or "",
                        "situacao": "perfilado",
                    }
                )
                if col_uf is None:
                    continue
                if ESCOLAS_ZIP.search(z.name):
                    print(
                        "     recorte do DF: feito pelo leitor específico em streaming "
                        "(a planilha inteira não entra em memória)"
                    )
                    perfil[-1]["situacao"] = "perfilado; recorte do DF em leitor específico"
                    continue
                # recorte do DF, mantendo tudo como texto para não colapsar
                # zero, ausente e não aplicável nesta etapa
                partes = []
                for aba in abas if extraido.suffix.lower() != ".csv" else [0]:
                    try:
                        df = (
                            pd.read_csv(extraido, dtype=str, sep=None, engine="python")
                            if extraido.suffix.lower() == ".csv"
                            else pd.read_excel(extraido, sheet_name=aba, dtype=str)
                        )
                    except Exception as exc:  # noqa: BLE001
                        print(f"     falhou {aba}: {exc}")
                        continue
                    sub = filtrar_df(df, col_uf)
                    if len(sub):
                        partes.append(sub)
                if not partes:
                    print("     nenhuma linha do DF encontrada")
                    continue
                df_df = pd.concat(partes, ignore_index=True)
                destino = OUT / f"{Path(membro).stem}.parquet"
                df_df.to_parquet(destino, index=False)
                print(f"     DF: {len(df_df)} linhas → {destino.name}")

        if "regioes_ufs_ideb" in z.name:
            processar_ideb_uf(z)
        if "brasil_ideb" in z.name:
            processar_brasil(z)
        for etapa, marca in (("AI", "anos_iniciais"), ("AF", "anos_finais"), ("EM", "ensino_medio")):
            if f"{marca}_escolas" in z.name:
                partes_escola.append(processar_ideb_escolas(z, etapa))
                perfil.append(
                    {
                        "arquivo": z.name,
                        "membro": "(xlsx lido em streaming)",
                        "formato": ".xlsx",
                        "coluna_uf": "SG_UF",
                        "situacao": (
                            f"leitor específico: {etapa}, {len(partes_escola[-1])} linhas "
                            f"longas do DF"
                        ),
                    }
                )

        if "tx_rend_escolas" in z.name:
            fluxo = processar_tx_rend(z)
            if not fluxo.empty:
                fluxo.to_parquet(OUT / "tx_rend_escolas_df.parquet", index=False)
                print(f"     DF: {len(fluxo)} linhas longas → tx_rend_escolas_df.parquet")
                perfil.append(
                    {
                        "arquivo": z.name,
                        "membro": "(xlsx lido em streaming)",
                        "formato": ".xlsx",
                        "coluna_uf": "SG_UF",
                        "situacao": (
                            f"leitor específico: taxas de rendimento, {len(fluxo)} linhas "
                            f"longas do DF"
                        ),
                    }
                )

        for meta in INDICADORES_ESCOLA:
            if meta["marca"] not in z.name:
                continue
            indicador = processar_indicador_escola(z, meta)
            if indicador.empty:
                continue
            indicador.to_parquet(OUT / meta["saida"], index=False)
            print(f"     DF: {len(indicador)} linhas longas → {meta['saida']}")
            medir_juncao_cadastro(indicador)
            perfil.append(
                {
                    "arquivo": z.name,
                    "membro": "(xlsx lido em streaming)",
                    "formato": ".xlsx",
                    "coluna_uf": "SG_UF",
                    "situacao": (
                        f"leitor específico: {meta['indicador']}, {len(indicador)} linhas "
                        f"longas do DF ({indicador['CO_ENTIDADE'].nunique()} escolas)"
                    ),
                }
            )

    # Ideb por escola: os três recortes do DF empilhados em formato longo.
    partes_escola = [p for p in partes_escola if not p.empty]
    if partes_escola:
        escolas = pd.concat(partes_escola, ignore_index=True)
        destino = OUT / "ideb_escolas_df.parquet"
        escolas.to_parquet(destino, index=False)
        print(
            f"\nIdeb por escola (DF): {len(escolas)} linhas longas, "
            f"{escolas['ID_ESCOLA'].nunique()} escolas distintas, "
            f"etapas {sorted(escolas['etapa'].unique())} → {destino.name}"
        )

    # Planilhas soltas (não vêm em zip): perfil genérico, sem recorte do DF —
    # são tabelas formatadas de UF, e o leitor específico entra quando o layout
    # for conhecido.
    for x in planilhas:
        if "Ensino_Medio_integrado" in x.name:
            print(f"\n== {x.name}: leitor específico (EM com integrado à EPT)")
            processar_uf_em_integrado(x)
            perfil.append(
                {
                    "arquivo": x.name,
                    "membro": "(xlsx solto)",
                    "formato": ".xlsx",
                    "coluna_uf": "Região/UF (nome por extenso)",
                    "situacao": "leitor específico: EM_integrado, 27 UFs × 5 anos",
                }
            )
            continue
        amostra, abas, erro = ler_cabecalho(x)
        if amostra is None:
            perfil.append({"arquivo": x.name, "membro": "", "formato": ".xlsx", "situacao": f"erro: {erro}"})
            print(f"\n== {x.name}: erro ao ler — {erro}")
            continue
        col_uf = achar_coluna_uf(list(amostra.columns))
        print(
            f"\n== {x.name}: {len(abas)} aba(s) {abas[:4]}, {amostra.shape[1]} colunas, "
            f"UF identificada: {col_uf or 'NÃO'}"
        )
        perfil.append(
            {
                "arquivo": x.name,
                "membro": "",
                "formato": ".xlsx",
                "abas": ";".join(abas),
                "colunas": amostra.shape[1],
                "colunas_nomes": ";".join(map(str, amostra.columns))[:800],
                "coluna_uf": col_uf or "",
                "situacao": "perfilado (planilha solta, sem leitor específico)",
            }
        )

    if perfil:
        pd.DataFrame(perfil).to_csv(INTERIM / "inep_perfil.csv", index=False)
        print(f"\nperfil gravado em data/interim/inep_perfil.csv ({len(perfil)} tabelas)")
    for p in pdfs:
        print(f"PDF ingerido (leitura manual, não convertido): {p.name}")


if __name__ == "__main__":
    main()
