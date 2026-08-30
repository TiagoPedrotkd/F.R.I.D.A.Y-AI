"""Tests for deterministic intent routing."""

from friday.llm.intent_router import match_skill, match_skill_with_args


def test_match_time_portuguese():
    assert match_skill("Que horas são?") == "get_current_datetime"
    assert match_skill("diz-me as horas") == "get_current_datetime"
    assert match_skill("Qual e a hora atual?") == "get_current_datetime"
    assert match_skill("que dia e hoje") == "get_current_datetime"


def test_match_joke():
    assert match_skill("Conta uma piada") == "tell_joke"
    assert match_skill("diz-me uma piada") == "tell_joke"
    assert match_skill("Conta uma historia") is None


def test_match_rag_docs():
    assert match_skill("Na documentação do projeto, como ligo o LM Studio?") == "search_docs"
    assert match_skill("Segundo o manual interno, o que é VLAN?") == "search_docs"


def test_match_search_web():
    assert match_skill("Pesquisa na web a versão mais recente do Phi-4") == "search_web"
    assert match_skill("Procura na internet o preço do Bitcoin hoje") == "search_web"


def test_match_remember():
    name, args = match_skill_with_args("Lembra que prefiro português europeu")
    assert name == "remember"
    assert "português europeu" in args["text"]


def test_no_match():
    assert match_skill("Ola, tudo bem?") is None
    assert match_skill("Quem és tu?") is None
