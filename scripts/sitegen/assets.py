"""Assets estáticos lidos uma vez (CSS e JS de busca).

Entrada: `static/style.css` e `static/search.js`.
Saída: as constantes `CSS` e `JS_INDEX`.
Idempotente: sim — só lê.
"""

from __future__ import annotations

from pathlib import Path

STATIC = Path(__file__).with_name("static")

# O CSS publicado sempre começou com uma quebra de linha; o arquivo começa em `:root`.
CSS = "\n" + (STATIC / "style.css").read_text(encoding="utf-8")
JS_INDEX = (STATIC / "search.js").read_text(encoding="utf-8")
