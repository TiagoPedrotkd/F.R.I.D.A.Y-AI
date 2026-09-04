"""Tests for domain router MoE pillars and quality heuristics."""

from friday.llm.domain_router import (
    clear_catalog_cache,
    format_routing_block,
    load_pillars,
    primary_pillar,
    route_domains,
)
from friday.llm.prompts import PROMPT_VERSION
from friday.llm.quality import needs_low_confidence_hedge, score_response


def setup_function():
    clear_catalog_cache()


def test_prompt_v8():
    assert PROMPT_VERSION.startswith("v8")


def test_six_pillars_in_catalog():
    pillars = load_pillars()
    for key in (
        "stem",
        "life_health",
        "humanities",
        "language",
        "business",
        "practical",
    ):
        assert key in pillars
        assert pillars[key].get("title")


def test_route_taekwondo_pillar():
    ranked = route_domains("Como melhorar o poomsae de taekwondo?")
    assert ranked
    assert ranked[0]["domain"] == "taekwondo"
    assert ranked[0]["weight"] > 0.3
    assert ranked[0].get("pillar") == "practical"
    assert ranked[0].get("subarea") == "games_entertainment"
    assert primary_pillar(ranked) == "practical"


def test_route_tech_stem():
    ranked = route_domains("debug deste codigo python na api")
    assert ranked
    assert ranked[0]["domain"] == "tech"
    assert ranked[0].get("pillar") == "stem"


def test_route_finance_business():
    ranked = route_domains("preciso de ajuda com o orcamento e investimentos")
    assert ranked
    assert ranked[0]["domain"] == "finance"
    assert ranked[0].get("pillar") == "business"


def test_route_productivity_boost():
    ranked = route_domains(
        "marca uma reuniao",
        domains_of_interest=["productivity"],
    )
    assert any(r["domain"] == "productivity" for r in ranked)


def test_format_routing_includes_pillar():
    block = format_routing_block(
        [
            {
                "domain": "tech",
                "weight": 0.9,
                "pillar": "stem",
                "subarea": "software_devops",
            }
        ]
    )
    assert "ROUTING" in block
    assert "tech" in block
    assert "Pillar: stem" in block
    assert "stem/software_devops" in block


def test_quality_hedge():
    scores = score_response("Garanto 100% sem risco.", used_tools=False)
    assert needs_low_confidence_hedge(scores)
