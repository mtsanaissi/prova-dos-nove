"""Constantes do contrato do site (etapas, frases, anos e limites).

Entrada: nenhuma (módulo importado).
Saída: listas e dicionários fixos usados pelo build.
Idempotente: sim — constantes apenas."""

from __future__ import annotations




DEFAULT_DATA_BUILD = "2026-11-06"


DEFAULT_N_THRESHOLD = 30


MAX_SITE_BYTES = 700 * 1024 * 1024


STAGES = [
    ("AI", "anos iniciais", "oferta_fund_ai"),
    ("AF", "anos finais", "oferta_fund_af"),
    ("EM", "ensino médio", "oferta_med"),
]


STAGE_LABEL = {stage_code: label for stage_code, label, _ in STAGES}


STAGE_SLUG = {"AI": "ai", "AF": "af", "EM": "em", "CRE": "creche"}


ENROLLMENT_COLUMNS = {
    ("CRE", "2024"): "mat_inf_cre_2024",
    ("CRE", "2025"): "mat_inf_cre_2025",
    ("AI", "2024"): "mat_fund_ai_2024",
    ("AI", "2025"): "mat_fund_ai_2025",
    ("AF", "2024"): "mat_fund_af_2024",
    ("AF", "2025"): "mat_fund_af_2025",
    ("EM", "2024"): "mat_med_2024",
    ("EM", "2025"): "mat_med_2025",
}


ENROLLMENT_LABEL = {"CRE": "creche", "AI": "anos iniciais", "AF": "anos finais", "EM": "ensino médio"}


OFFERINGS = [
    ("oferta_inf_cre", "Creche"),
    ("oferta_inf_pre", "Pré-escola"),
    ("oferta_fund_ai", "Anos iniciais do ensino fundamental"),
    ("oferta_fund_af", "Anos finais do ensino fundamental"),
    ("oferta_med", "Ensino médio"),
    ("oferta_eja", "Educação de jovens e adultos"),
    ("oferta_esp", "Educação especial"),
    ("oferta_prof", "Educação profissional"),
]


INFRA_ITEMS = [
    ("IN_BIBLIOTECA", "Biblioteca"),
    ("IN_SALA_LEITURA", "Sala de leitura"),
    ("IN_QUADRA_ESPORTES", "Quadra de esportes"),
    ("IN_LABORATORIO_INFORMATICA", "Laboratório de informática"),
    ("IN_LABORATORIO_CIENCIAS", "Laboratório de ciências"),
    ("IN_INTERNET_ALUNOS", "Internet para os alunos"),
    ("IN_REFEITORIO", "Refeitório"),
    ("IN_BANHEIRO_PNE", "Banheiro acessível (cadeirante)"),
]


IDEB_YEARS = [str(year) for year in range(2005, 2026, 2)]


IDEB_YEARS_BY_STAGE = {"AI": IDEB_YEARS, "AF": IDEB_YEARS, "EM": ["2017", "2019", "2021", "2023", "2025"]}


NETWORKS = {"federal", "estadual", "privada conveniada", "privada não conveniada"}


STATES = {"valor", "zero", "ausente", "nao_aplicavel"}


PHRASE_STAGE_NOT_OFFERED = "— esta etapa não é ofertada pela escola em 2025"


PHRASE_IDEB_PRIVATE = "sem Ideb: a INEP não publica resultado de escola privada depois de 2017"


PHRASE_IDEB_PUBLIC = (
    "sem Ideb em 2025: a INEP não publica quando há menos de 10 alunos na prova "
    "ou participação abaixo de 80%, e não informa qual foi o caso"
)


PHRASE_CENSUS_2024_NO_ROW = "a escola não consta do Censo de 2024"


PHRASE_ENROLLMENT_2024 = "matrícula não declarada no Censo de 2024"


PHRASE_ENROLLMENT_2025 = "matrícula não declarada no Censo de 2025"


PHRASE_NO_INDICATOR = "esta escola não tem Ideb nem taxas publicadas em 2025"


PHRASE_INFRA_NOT_APPLICABLE = (
    "a infraestrutura é publicada para as escolas que oferecem ensino fundamental ou médio"
)


PHRASE_SMALL_N = "nesta etapa — o indicador não é publicado quando a turma é pequena"


STUDENT_COUNT_FAMILIES = {"ideb", "fluxo", "tdi", "tnr"}


SLUG_BY_STAGE_LABEL = {
    label: STAGE_SLUG[stage_code] for stage_code, label, _ in STAGES
}
