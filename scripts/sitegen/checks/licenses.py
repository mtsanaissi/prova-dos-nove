"""Critério 6: licenças declaradas e fontes citadas nos créditos.

Entrada: HTML de créditos e JSON de procedência do site.
Saída: o texto do `[ok]` ou `BuildError`.
Idempotente: sim — só lê."""

from __future__ import annotations

from pathlib import Path

import html
import json

from ..errors import BuildError


def check_licenses(site: Path, data: dict) -> str:
    records = data["registros"]
    license_by_source: dict[str, tuple[str, str | None]] = {}
    for family, record in records.items():
        license_name = record.get("licenca")
        if not license_name:
            raise BuildError(f"registro {family!r} sem licença em procedencia.json")
        lowercase = str(license_name).lower()
        if any(term in lowercase for term in ("odbl", "odc", "open data commons")):
            raise BuildError(f"registro {family!r} publicado sob licença ODbL: {license_name!r}")
        license_by_source[record["fonte"]] = (license_name, record.get("licenca_url"))

    sources = set()
    for path in sorted((site / "dados").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        for number in record["numeros"]:
            source = number["fonte"]
            sources.add(source)
            lowercase = source.lower()
            for term in ("odbl", "odc", "open data commons", "matriculas__relatorio_matriculas"):
                if term in lowercase:
                    raise BuildError(f"{path.name}: fonte ODbL/matrículas proibida: {source}")
            if source not in license_by_source:
                raise BuildError(f"{path.name}: fonte {source!r} sem licença no insumo")

    credits_html = (site / "creditos.html").read_text(encoding="utf-8")
    for source in sources:
        if source not in credits_html:
            raise BuildError(f"creditos.html não lista a fonte {source!r}")
        license_name, url = license_by_source[source]
        if html.escape(license_name) not in credits_html:
            raise BuildError(f"creditos.html não mostra a licença de {source!r}")
        if url and html.escape(url, quote=True) not in credits_html:
            raise BuildError(f"creditos.html não mostra a licenca_url de {source!r}")
    for required in ("MIT", "CC BY 4.0", "Marcelo Anaissi"):
        if required not in credits_html:
            raise BuildError(f"creditos.html sem {required!r}")
    return f"{len(sources)} fontes com licença declarada nos créditos"
