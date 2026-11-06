# data/public/

Exceção declarada à regra "`data/` nunca entra no git" (`AGENTS.md`,
Convenções). Aqui entra **apenas** o recorte mínimo que o build do site lê:
agregado por escola e por etapa, sem arquivo bruto, sem microdado e sem linha
que identifique uma pessoa. Tudo nesta pasta é gerado por script, versionado e
descrito em `SCHEMA.md`.

Nada foi publicado aqui ainda. O conteúdo nasce na fase 1, junto de
`scripts/12_build_site.py` (ver `docs/FASE-1.md`), e a regra de tamanho é a
mesma de qualquer artefato do projeto: o repositório carrega o que o build
precisa, não o que a fonte publicou.
