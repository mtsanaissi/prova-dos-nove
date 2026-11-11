"""Documento HTML comum a todas as páginas.

Entrada: título, corpo, carimbo do build, limiar de n e markup extra de `<head>`.
Saída: o HTML completo com cabeçalho e rodapé.
Idempotente: sim — função pura."""

from __future__ import annotations

import html


def document(title: str, body: str, data_build: str, threshold: int, head_extra: str = "") -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="estilo.css">{head_extra}
</head>
<body>
<header class="topo">
  <a class="marca" href="index.html">Prova dos Nove</a>
  <nav class="menu" aria-label="Páginas do site">
    <a href="escolas.html">Escolas</a>
    <a href="metodologia.html">Metodologia</a>
  </nav>
  <p class="carimbo">build {html.escape(data_build)} · limiar de n pequeno = {threshold}</p>
</header>
{body}
<footer class="rodape">
  <p>Prova dos Nove · dados públicos de educação, com fonte, ano e cálculo.
  <a href="escolas.html">Escolas</a> ·
  <a href="metodologia.html">Metodologia</a> ·
  <a href="como-ler.html">Como ler os números</a> ·
  <a href="creditos.html">Créditos e licenças</a>.</p>
</footer>
</body>
</html>
"""
