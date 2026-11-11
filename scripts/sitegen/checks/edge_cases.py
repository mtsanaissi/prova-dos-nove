"""Casos de limite: 2024 sem linha, 2025 ausente, creche, 493 e limiar 0.

Entrada: insumo público e carimbo do build.
Saída: o texto do `[ok]` ou `BuildError`.
Idempotente: sim — altera só uma cópia temporária do insumo."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path

import pandas as pd

from ..errors import BuildError
from ..contract import PHRASE_CENSUS_2024_NO_ROW, PHRASE_ENROLLMENT_2024, PHRASE_ENROLLMENT_2025, STUDENT_COUNT_FAMILIES
from ..loader import load_data, sha256
from ..school_page import SchoolPage


def check_edge_cases(public: Path, data_build: str) -> str:
    """Reproduz os casos de borda em uma cópia do insumo, sem build completo.

    Copia `data/public/` para um diretório temporário, altera as escolas dos
    casos, recalcula o sha256 e passa pelo `load_data` (portanto pela coluna
    nova e pelo guard de sha256). Renderiza só as escolas afetadas.
    """
    public = Path(public)
    temp_base = Path("/tmp/opencode") if Path("/tmp/opencode").is_dir() else None
    columns_2024 = ["mat_inf_cre_2024", "mat_fund_ai_2024", "mat_fund_af_2024", "mat_med_2024"]
    with tempfile.TemporaryDirectory(prefix="prova-dos-nove-casos-", dir=temp_base) as tmp:
        tmp = Path(tmp)
        for name in (
            "escolas.parquet", "indicadores.parquet", "infraestrutura.parquet",
            "ideb_uf.parquet", "agregados.parquet", "procedencia.json",
        ):
            shutil.copy2(public / name, tmp / name)

        schools = pd.read_parquet(tmp / "escolas.parquet")

        def alter(code: str, column: str, value) -> None:
            mask = schools["co_entidade"].astype(str) == code
            if not mask.any():
                raise BuildError(f"caso de limite: escola {code} não está no insumo")
            schools.loc[mask, column] = value

        # 2025 sem matrícula em anos iniciais; creche 2025 sem matrícula.
        alter("53000854", "mat_fund_ai_2025", pd.NA)
        alter("53000781", "mat_inf_cre_2025", pd.NA)
        # Os dois casos de 2024: sem linha e com linha e células vazias.
        alter("53020529", "censo_2024_presente", False)
        for column in columns_2024:
            alter("53020529", column, pd.NA)
        alter("53013662", "censo_2024_presente", True)
        for column in columns_2024:
            alter("53013662", column, pd.NA)
        # Oferta de 2025 não descreve a matrícula de 2024.
        alter("53014618", "oferta_fund_ai", 0)
        alter("53014618", "mat_fund_ai_2024", 493)
        # n = 0 precisa ser gravado como 0 quando o limiar é 0.
        alter("53000986", "mat_med_2025", 0)
        # Creche com célula vazia em 2024 (o 53000781 tem 2024 com valor).
        alter("53001419", "mat_inf_cre_2024", pd.NA)

        for column in (
            "mat_inf_cre_2024", "mat_fund_ai_2024", "mat_fund_af_2024", "mat_med_2024",
            "mat_inf_cre_2025", "mat_fund_ai_2025", "mat_fund_af_2025", "mat_med_2025",
        ):
            schools[column] = schools[column].astype("Int64")
        schools["censo_2024_presente"] = schools["censo_2024_presente"].astype(bool)
        schools.to_parquet(tmp / "escolas.parquet", index=False)

        provenance = json.loads((tmp / "procedencia.json").read_text(encoding="utf-8"))
        provenance["sha256"]["escolas.parquet"] = sha256(tmp / "escolas.parquet")
        (tmp / "procedencia.json").write_text(
            json.dumps(provenance, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

        data = load_data(tmp)

        def page(code: str, threshold: int) -> tuple[SchoolPage, str, str]:
            school = data["por_co"][code]
            p = SchoolPage(data, school, data_build, threshold)
            markup = p.render()
            return p, markup, re.sub(r"<[^>]+>", "", markup)

        def number(p: SchoolPage, identifier: str) -> dict:
            for item in p.numbers:
                if item["id"] == identifier:
                    return item
            raise BuildError(f"caso de limite: falta o número {identifier}")

        # 1. 2024 sem linha: frase de L-63, nunca a de célula vazia.
        p, markup, text = page("53020529", 30)
        if PHRASE_CENSUS_2024_NO_ROW not in text:
            raise BuildError("53020529: falta 'a escola não consta do Censo de 2024'")
        if PHRASE_ENROLLMENT_2024 in text:
            raise BuildError("53020529: usa a frase de célula vazia sem ter linha em 2024")
        if number(p, "matricula-ai-2024")["estado"] != "ausente":
            raise BuildError("53020529: matrícula de 2024 não está ausente")

        # 2. 2024 com linha e célula vazia: frase de L-28.
        p, markup, text = page("53013662", 30)
        if PHRASE_ENROLLMENT_2024 not in text:
            raise BuildError("53013662: falta 'matrícula não declarada no Censo de 2024'")
        if PHRASE_CENSUS_2024_NO_ROW in text:
            raise BuildError("53013662: usa a frase de escola ausente tendo linha em 2024")
        if number(p, "matricula-ai-2024")["estado"] != "ausente":
            raise BuildError("53013662: matrícula de 2024 não está ausente")

        # 3. 2025 sem matrícula: sem taxa, n = -, Ideb com n null. n_referencia
        #    só aparece nas linhas históricas com n presente (teste 3b).
        p, markup, text = page("53000854", 30)
        if PHRASE_ENROLLMENT_2025 not in text:
            raise BuildError("53000854: falta 'matrícula não declarada no Censo de 2025'")
        if "n = -" not in text:
            raise BuildError("53000854: a linha do n não mostra '-'")
        if number(p, "matricula-ai-2025")["estado"] != "ausente":
            raise BuildError("53000854: matrícula de AI em 2025 não está ausente")
        for item in p.numbers:
            if item["bloco"] in ("fluxo", "tdi", "tnr") and item["etapa"] == "anos iniciais":
                raise BuildError(f"53000854: publica taxa de AI sem denominador ({item['id']})")
            if item["bloco"] in STUDENT_COUNT_FAMILIES and item["n"] == 1:
                raise BuildError(f"53000854: n virou 1 em {item['id']}")
            if item["bloco"] == "ideb" and item["etapa"] == "anos iniciais":
                if item["ano"] == "2025":
                    if item["n"] is not None:
                        raise BuildError("53000854: Ideb de 2025 deveria ter n null")
                    if "n_referencia" in item:
                        raise BuildError("53000854: Ideb de 2025 não leva n_referencia")
                else:
                    if item["n"] is not None:
                        raise BuildError("53000854: Ideb histórico deveria ter n null")
                    if "n_referencia" in item:
                        raise BuildError(
                            "53000854: Ideb histórico com n null não leva n_referencia"
                        )

        # 3b. Ideb histórico com n presente continua carimbando o ano do n.
        for item in p.numbers:
            if (
                item["bloco"] == "ideb"
                and item["etapa"] == "anos finais"
                and item["ano"] != "2025"
            ):
                if item["n"] != 138:
                    raise BuildError("53000854: Ideb histórico de AF deveria ter n = 138")
                if item.get("n_referencia") != "2025":
                    raise BuildError(
                        "53000854: Ideb histórico de AF sem n_referencia 2025"
                    )

        # 4. Creche 2025 ausente usa a frase de 2025; 2024 presente não a usa.
        p, markup, text = page("53000781", 30)
        if PHRASE_ENROLLMENT_2025 not in text:
            raise BuildError("53000781: falta a frase de 2025 no bloco da creche")
        if PHRASE_ENROLLMENT_2024 in text or PHRASE_CENSUS_2024_NO_ROW in text:
            raise BuildError("53000781: bloco da creche com frase de 2024 sem célula vazia")
        if number(p, "creche-2025")["estado"] != "ausente":
            raise BuildError("53000781: creche 2025 não está ausente")
        if number(p, "creche-2024")["estado"] != "valor":
            raise BuildError("53000781: creche 2024 deveria continuar com valor")

        # 4b. Creche com célula vazia em 2024 usa a frase de L-28.
        p, markup, text = page("53001419", 30)
        if PHRASE_ENROLLMENT_2024 not in text:
            raise BuildError("53001419: falta a frase de célula vazia de 2024 na creche")
        if number(p, "creche-2024")["estado"] != "ausente":
            raise BuildError("53001419: creche 2024 não está ausente")

        # 5. 36 school-years: oferta de 2025 não apaga matrícula positiva de 2024.
        p, markup, text = page("53014618", 30)
        item = number(p, "matricula-ai-2024")
        if item["estado"] != "valor" or item["valor"] != 493:
            raise BuildError("53014618: 493 alunos em AI/2024 não aparecem como valor")

        # 6. Limiar 0: n = 0 é gravado como 0, não como 1.
        p, markup, text = page("53000986", 0)
        rates = [
            item for item in p.numbers
            if item["bloco"] in ("fluxo", "tdi", "tnr") and item["etapa"] == "ensino médio"
        ]
        if not rates:
            raise BuildError("53000986: nenhuma taxa do médio renderizada a limiar 0")
        if any(item["n"] != 0 for item in rates):
            raise BuildError("53000986: n=0 não foi gravado como 0 a limiar 0")

    return (
        "53 sem linha/3 com célula vazia em 2024, 2025 e creche ausentes, "
        "493 em 2024 preservado e n=0 a limiar 0 conferidos"
    )
