"""Leitura e validação de `data/public/`.

Entrada: diretório público com os três parquets e `procedencia.json`.
Saída: o modelo em memória usado por todas as páginas e pelos checks.
Idempotente: sim — só lê e confere sha256."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from .errors import BuildError
from .contract import NETWORKS, STAGES, STAGE_LABEL, STATES, ENROLLMENT_COLUMNS, OFFERINGS


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _int_or_none(value) -> int | None:
    return None if value is None or pd.isna(value) else int(value)


def _records_by_family(provenance: dict) -> dict[str, dict]:
    records = provenance.get("registros")
    if not isinstance(records, list) or not records:
        raise BuildError("procedencia.json sem a lista 'registros'")
    mapping = {}
    licenses_by_source: dict[str, tuple[str, str | None]] = {}
    for record in records:
        family = record.get("familia")
        if not family or family in mapping:
            raise BuildError(f"procedencia.json com família ausente ou duplicada: {family!r}")
        for field in ("fonte", "arquivo", "calculo", "licenca"):
            if not record.get(field):
                raise BuildError(f"registro {family!r} sem {field}")
        if "licenca_url" not in record:
            raise BuildError(f"registro {family!r} sem licenca_url (pode ser null)")
        if not record.get("limites"):
            raise BuildError(f"registro {family!r} sem limites")
        key = (record["licenca"], record["licenca_url"])
        previous = licenses_by_source.setdefault(record["fonte"], key)
        if previous != key:
            raise BuildError(
                f"famílias da fonte {record['fonte']!r} divergem em licença: "
                f"{previous!r} × {key!r}"
            )
        mapping[family] = record
    return mapping


def load_data(public: Path) -> dict:
    """Lê e valida `data/public/`; devolve o modelo usado por todas as páginas."""
    public = Path(public)
    if not public.is_dir():
        raise BuildError(f"data/public não existe: {public} (rode 06_analysis.py --public)")
    for name in ("escolas.parquet", "indicadores.parquet", "infraestrutura.parquet", "procedencia.json"):
        if not (public / name).is_file():
            raise BuildError(f"falta {public / name} (rode 06_analysis.py --public)")

    provenance = json.loads((public / "procedencia.json").read_text(encoding="utf-8"))
    hashes = provenance.get("sha256")
    if not isinstance(hashes, dict):
        raise BuildError("procedencia.json sem o mapa 'sha256' dos parquets")
    for name in ("escolas.parquet", "indicadores.parquet", "infraestrutura.parquet"):
        if not hashes.get(name):
            raise BuildError(f"procedencia.json sem sha256 de {name}")
        actual = sha256(public / name)
        if actual != hashes[name]:
            raise BuildError(
                f"sha256 de {name} não confere: registrado {hashes[name]}, arquivo {actual}. "
                "Rode 06_analysis.py --public novamente."
            )

    schools_df = pd.read_parquet(public / "escolas.parquet")
    for column in (
        "co_entidade", "nome", "ra", "rede", "rede_cadastro",
        "censo_2024_presente",
        "oferta_inf_cre", "oferta_inf_pre", "oferta_fund_ai", "oferta_fund_af",
        "oferta_med", "oferta_eja", "oferta_esp", "oferta_prof",
        "mat_inf_cre_2024", "mat_fund_ai_2024", "mat_fund_af_2024", "mat_med_2024",
        "mat_inf_cre_2025", "mat_fund_ai_2025", "mat_fund_af_2025", "mat_med_2025",
    ):
        if column not in schools_df:
            raise BuildError(f"escolas.parquet sem a coluna {column}")

    schools = []
    for r in schools_df.to_dict("records"):
        code = str(r["co_entidade"]).strip()
        if not code:
            raise BuildError("escolas.parquet com co_entidade vazio")
        if len(code) < 8:
            code = code.zfill(8)
        if r["rede"] not in NETWORKS:
            raise BuildError(f"escola {code} com rede fora do contrato: {r['rede']!r}")
        if pd.isna(r["censo_2024_presente"]):
            raise BuildError(f"escola {code} sem censo_2024_presente")
        school = {
            "co": code,
            "nome": str(r["nome"]).strip(),
            "ra": str(r["ra"]).strip(),
            "rede": r["rede"],
            "rede_cadastro": str(r["rede_cadastro"]).strip(),
            "censo_2024_presente": bool(r["censo_2024_presente"]),
        }
        for column, _ in OFFERINGS:
            school[column] = int(r[column]) if not pd.isna(r[column]) else 0
        for (stage, year), column in ENROLLMENT_COLUMNS.items():
            school[f"mat_{stage}_{year}"] = _int_or_none(r[column])
        if not school["censo_2024_presente"]:
            filled = [
                stage for stage in ("CRE", "AI", "AF", "EM")
                if school.get(f"mat_{stage}_2024") is not None
            ]
            if filled:
                raise BuildError(
                    f"escola {code} sem linha no Censo 2024 com matrícula de 2024: "
                    + ", ".join(filled)
                )
        schools.append(school)
    schools.sort(key=lambda e: e["co"])

    by_code = {}
    for school in schools:
        if school["co"] in by_code:
            raise BuildError(f"escolas.parquet com CO_ENTIDADE duplicado: {school['co']}")
        by_code[school["co"]] = school

    indicators = {}
    indicators_df = pd.read_parquet(public / "indicadores.parquet")
    for r in indicators_df.to_dict("records"):
        code = str(r["co_entidade"]).strip()
        stage = str(r["etapa"])
        indicator = str(r["indicador"])
        year = str(r["ano"])
        state = str(r["estado"])
        if code not in by_code:
            raise BuildError(f"indicador de escola fora do cadastro: {code}")
        if stage not in STAGE_LABEL:
            raise BuildError(f"indicador com etapa fora do contrato: {stage!r}")
        if state not in STATES:
            raise BuildError(f"indicador com estado fora do contrato: {state!r}")
        value = None if pd.isna(r["valor"]) else float(r["valor"])
        if state in ("valor", "zero") and value is None:
            raise BuildError(f"indicador {code}/{stage}/{indicator}/{year} com estado {state} e valor nulo")
        if state in ("ausente", "nao_aplicavel") and value is not None:
            raise BuildError(f"indicador {code}/{stage}/{indicator}/{year} com estado {state} e valor")
        key = (code, stage, indicator, year)
        if key in indicators:
            raise BuildError(f"indicador duplicado: {key}")
        indicators[key] = {"valor": value, "estado": state}

    infra = {}
    infra_df = pd.read_parquet(public / "infraestrutura.parquet")
    for r in infra_df.to_dict("records"):
        code = str(r["co_entidade"]).strip()
        item = str(r["item"])
        state = str(r["estado"])
        if code not in by_code:
            raise BuildError(f"infraestrutura de escola fora do cadastro: {code}")
        if state not in STATES:
            raise BuildError(f"infraestrutura com estado fora do contrato: {state!r}")
        value = _int_or_none(r["valor"])
        if state == "valor" and value not in (0, 1):
            raise BuildError(f"infraestrutura {code}/{item} com valor fora de 0/1: {value!r}")
        infra[(code, item)] = {"valor": value, "estado": state, "ano": str(r["ano"])}

    execution = provenance.get("execucao") or {}
    skipped_steps = execution.get("etapas_puladas") if isinstance(execution, dict) else None
    if skipped_steps is None:
        skipped_steps = []
    if not isinstance(skipped_steps, list):
        raise BuildError("procedencia.json com execucao.etapas_puladas fora de lista")
    if skipped_steps:
        print(
            "AVISO: o insumo público foi exportado com --parcial e tem etapa(s) "
            "pulada(s): " + ", ".join(str(e) for e in skipped_steps)
        )

    return {
        "escolas": schools,
        "por_co": by_code,
        "indicadores": indicators,
        "infra": infra,
        "procedencia": provenance,
        "registros": _records_by_family(provenance),
        "hashes": hashes,
        "etapas_puladas": [str(e) for e in skipped_steps],
    }


def get_indicator(data: dict, code: str, stage: str, name: str, year: str = "2025") -> dict:
    """Devolve o registro do indicador ou `ausente` quando não existe linha."""
    return data["indicadores"].get((code, stage, name, str(year)), {"valor": None, "estado": "ausente"})


def has_published_ideb(data: dict, school: dict) -> bool:
    return any(
        school[offering]
        and get_indicator(data, school["co"], stage, "ideb_observado")["estado"] == "valor"
        for stage, _, offering in STAGES
    )


def has_rate_row(data: dict, school: dict) -> bool:
    for stage, _, offering in STAGES:
        if not school[offering]:
            continue
        for name in ("tdi", "tnr", "aprovacao", "reprovacao", "abandono"):
            if (school["co"], stage, name, "2025") in data["indicadores"]:
                return True
    return False
