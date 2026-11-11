"""Leitura e validação de `data/public/`.

Entrada: diretório público com os cinco parquets e `procedencia.json`.
Saída: o modelo em memória usado por todas as páginas e pelos checks.
Idempotente: sim — só lê e confere sha256."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from .errors import BuildError
from .contract import NETWORKS, STAGES, STAGE_LABEL, STATES, ENROLLMENT_COLUMNS, OFFERINGS, IDEB_UF_NETWORKS


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
    files = (
        "escolas.parquet",
        "indicadores.parquet",
        "infraestrutura.parquet",
        "ideb_uf.parquet",
        "agregados.parquet",
        "procedencia.json",
    )
    for name in files:
        if not (public / name).is_file():
            raise BuildError(f"falta {public / name} (rode 06_analysis.py --public)")

    provenance = json.loads((public / "procedencia.json").read_text(encoding="utf-8"))
    hashes = provenance.get("sha256")
    if not isinstance(hashes, dict):
        raise BuildError("procedencia.json sem o mapa 'sha256' dos parquets")
    for name in files:
        if name == "procedencia.json":
            continue
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

    table = {}
    table_df = pd.read_parquet(public / "ideb_uf.parquet")
    for column in (
        "etapa", "ano", "rede", "df", "df_estado",
        "brasil", "brasil_estado", "posicao", "n_ufs",
    ):
        if column not in table_df:
            raise BuildError(f"ideb_uf.parquet sem a coluna {column}")
    for r in table_df.to_dict("records"):
        stage = str(r["etapa"])
        year = str(r["ano"])
        network = str(r["rede"])
        if stage not in STAGE_LABEL:
            raise BuildError(f"ideb_uf com etapa fora do contrato: {stage!r}")
        if year not in ("2023", "2025"):
            raise BuildError(f"ideb_uf com ano fora do contrato: {year!r}")
        if network not in IDEB_UF_NETWORKS:
            raise BuildError(f"ideb_uf com rede fora do contrato: {network!r}")
        entry = {"posicao": _int_or_none(r["posicao"]), "n_ufs": _int_or_none(r["n_ufs"])}
        for field, state_field in (("df", "df_estado"), ("brasil", "brasil_estado")):
            state = str(r[state_field])
            if state not in ("valor", "ausente"):
                raise BuildError(f"ideb_uf {stage}/{year}/{network}: {state_field} {state!r}")
            value = None if pd.isna(r[field]) else float(r[field])
            if (state == "valor") != (value is not None):
                raise BuildError(
                    f"ideb_uf {stage}/{year}/{network}: {field} não casa com {state_field}"
                )
            entry[field] = value
            entry[state_field] = state
        key = (stage, year, network)
        if key in table:
            raise BuildError(f"ideb_uf duplicado: {key}")
        table[key] = entry

    agregados = {}
    agregados_df = pd.read_parquet(public / "agregados.parquet")
    for column in ("id", "bloco", "grupo", "etapa", "ano", "metrica", "valor", "n", "estado"):
        if column not in agregados_df:
            raise BuildError(f"agregados.parquet sem a coluna {column}")
    for r in agregados_df.to_dict("records"):
        identifier = str(r["id"]).strip()
        if not identifier:
            raise BuildError("agregados.parquet com id vazio")
        if identifier in agregados:
            raise BuildError(f"agregados.parquet com id duplicado: {identifier}")
        state = str(r["estado"])
        if state not in ("valor", "ausente"):
            raise BuildError(f"agregado {identifier} com estado fora do contrato: {state!r}")
        value = None if pd.isna(r["valor"]) else float(r["valor"])
        if (state == "valor") != (value is not None):
            raise BuildError(f"agregado {identifier}: valor não casa com o estado {state}")
        agregados[identifier] = {
            "id": identifier,
            "bloco": str(r["bloco"]),
            "grupo": str(r["grupo"]),
            "etapa": str(r["etapa"]),
            "ano": str(r["ano"]),
            "metrica": str(r["metrica"]),
            "valor": value,
            "n": _int_or_none(r["n"]),
            "estado": state,
        }

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
        "ideb_uf": table,
        "agregados": agregados,
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
