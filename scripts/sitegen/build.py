"""Build do site: limpeza, escrita e limite de tamanho.

Entrada: `data/public/`, diretório de saída, carimbo e limiar.
Saída: o site completo em disco.
Idempotente: sim — reescreve sempre o mesmo conteúdo."""

from __future__ import annotations

import json
from pathlib import Path

from .errors import BuildError
from .contract import MAX_SITE_BYTES
from .loader import load_data
from .assets import CSS
from .layout import document
from .schools_page import render_schools_page
from .home_page import render_home_page
from .methodology_page import render_methodology_page
from .info_pages import render_how_to_read_page, render_credits_page
from .school_page import SchoolPage

HOME_TITLE = "Prova dos Nove — uma página por escola no Distrito Federal"


def _clean_output(site: Path) -> None:
    for name in (
        "index.html", "escolas.html", "metodologia.html", "creditos.html",
        "como-ler.html", "estilo.css", "indice.json",
    ):
        target = site / name
        if target.is_file():
            target.unlink()
    for target in site.glob("[0-9]" * 8 + ".html"):
        target.unlink()
    data_dir = site / "dados"
    if data_dir.is_dir():
        for target in data_dir.glob("*.json"):
            target.unlink()


def _total_size(site: Path) -> int:
    return sum(p.stat().st_size for p in site.rglob("*") if p.is_file())


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def build_site(public: Path, out: Path, data_build: str, threshold: int, quiet: bool = False) -> dict:
    """Gera o site inteiro; devolve contagens e tamanho."""
    data = load_data(public)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "dados").mkdir(parents=True, exist_ok=True)
    _clean_output(out)

    (out / "estilo.css").write_text(CSS, encoding="utf-8")

    index_entries = [
        {"co_entidade": e["co"], "nome": e["nome"], "ra": e["ra"], "rede": e["rede"]}
        for e in data["escolas"]
    ]
    index_entries.sort(key=lambda x: (x["nome"], x["co_entidade"]))
    (out / "indice.json").write_text(
        json.dumps(index_entries, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    home_body, home_numbers = render_home_page(data, data_build, threshold)
    (out / "index.html").write_text(
        document(HOME_TITLE, home_body, data_build, threshold), encoding="utf-8"
    )
    _write_json(
        out / "dados" / "home.json",
        {"pagina": "home", "gerado_em": data_build, "numeros": home_numbers},
    )
    (out / "escolas.html").write_text(render_schools_page(data, data_build, threshold), encoding="utf-8")
    (out / "metodologia.html").write_text(
        render_methodology_page(data_build, threshold), encoding="utf-8"
    )
    (out / "como-ler.html").write_text(render_how_to_read_page(data_build, threshold), encoding="utf-8")
    (out / "creditos.html").write_text(render_credits_page(data, data_build, threshold), encoding="utf-8")

    for school in data["escolas"]:
        page = SchoolPage(data, school, data_build, threshold)
        body = page.render()
        (out / f'{school["co"]}.html').write_text(
            document(f'{school["nome"]} — Prova dos Nove', body, data_build, threshold),
            encoding="utf-8",
        )
        _write_json(
            out / "dados" / f'{school["co"]}.json',
            {"escola": school["co"], "gerado_em": data_build, "numeros": page.numbers},
        )

    total = _total_size(out)
    if total > MAX_SITE_BYTES:
        raise BuildError(
            f"site com {total / (1024 * 1024):.1f} MB passa do limite de "
            f"{MAX_SITE_BYTES / (1024 * 1024):.0f} MB"
        )
    if not quiet:
        print(
            f"site: {len(data['escolas']):,} páginas de escola, "
            f"{total / (1024 * 1024):.1f} MB em {out}"
        )
    return {"escolas": len(data["escolas"]), "bytes": total, "dados": data}
