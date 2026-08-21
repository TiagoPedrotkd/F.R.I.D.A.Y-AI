"""Tests for deterministic intent routing."""

from friday.llm.intent_router import match_skill


def test_match_time_portuguese():
    assert match_skill("Que horas são?") == "get_current_datetime"
    assert match_skill("diz-me as horas") == "get_current_datetime"
    assert match_skill("Qual e a hora atual?") == "get_current_datetime"
    assert match_skill("que dia e hoje") == "get_current_datetime"


def test_match_joke():
    assert match_skill("Conta uma piada") == "tell_joke"
    assert match_skill("diz-me uma piada") == "tell_joke"
    assert match_skill("Conta uma historia") is None


def test_no_match():
    assert match_skill("Ola, tudo bem?") is None
    assert match_skill("Quem és tu?") is None
