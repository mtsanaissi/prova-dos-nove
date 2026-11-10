"""Erro de build.

Entrada: nenhuma (módulo importado).
Saída: a exceção `BuildError`, que interrompe o build com mensagem.
Idempotente: sim — não altera estado."""

from __future__ import annotations




class BuildError(Exception):
    """O build não pode continuar; a mensagem diz o que falta ou diverge."""
