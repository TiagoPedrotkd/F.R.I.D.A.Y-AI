"""Skill registry and OpenAI tool export."""

from __future__ import annotations

from typing import Any

from friday.config import Settings, get_settings
from friday.pipeline.errors import UnknownSkillError
from friday.skills.base import Skill, SkillResult


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}
        self._aliases: dict[str, str] = {}

    def register(self, skill: Skill, *, aliases: list[str] | None = None) -> None:
        if skill.name in self._skills:
            raise ValueError(f"Skill already registered: {skill.name}")
        self._skills[skill.name] = skill
        for alias in aliases or []:
            self._aliases[alias] = skill.name

    def get(self, name: str) -> Skill:
        resolved = self._aliases.get(name, name)
        skill = self._skills.get(resolved)
        if skill is None:
            raise UnknownSkillError(f"Unknown skill: {name}")
        return skill

    def names(self) -> list[str]:
        return list(self._skills.keys()) + list(self._aliases.keys())

    def to_openai_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        for skill in self._skills.values():
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": skill.name,
                        "description": skill.description,
                        "parameters": skill.parameters,
                    },
                }
            )
        return tools

    async def execute(self, name: str, arguments: dict[str, Any]) -> SkillResult:
        try:
            skill = self.get(name)
        except UnknownSkillError as exc:
            return SkillResult(success=False, content="", error=str(exc))
        return await skill.execute(arguments)


def default_registry(settings: Settings | None = None) -> SkillRegistry:
    settings = settings or get_settings()

    from friday.skills.local.calculate import CalculateSkill
    from friday.skills.local.calendar_skills import (
        CancelCalendarEventSkill,
        CreateCalendarEventSkill,
        FindFreeSlotsSkill,
        ListCalendarEventsSkill,
        ModifyCalendarEventSkill,
        StatusCheckSkill,
        SummarizeDaySkill,
    )
    from friday.skills.local.datetime_skill import DateTimeSkill
    from friday.skills.local.email_skills import (
        DraftEmailReplySkill,
        ListEmailsSkill,
        PrepareMeetingSkill,
        ReadEmailSkill,
        ResolveContactSkill,
        ScheduleLocalReminderSkill,
        SendEmailSkill,
        StartMeetingWorkflowSkill,
    )
    from friday.skills.local.format_json import FormatJsonSkill
    from friday.skills.local.llm_text_skills import ExplainCodeSkill, SummarizeSkill
    from friday.skills.local.memory_skills import RecallSkill, RememberSkill
    from friday.skills.local.system_info import SystemInfoSkill
    from friday.skills.local.word_count import WordCountSkill
    from friday.skills.local.integration_skills import (
        GetHealthSummarySkill,
        GetWeatherSkill,
        SearchPersonalNotesSkill,
    )
    from friday.skills.mock.joke_skill import JokeSkill
    from friday.skills.news import (
        CountryBriefingSkill,
        FinanceNewsSkill,
        ListSupportedCountriesSkill,
        OpenFinanceMonitorSkill,
        OpenWorldMonitorSkill,
        WorldNewsSkill,
    )
    from friday.skills.rag.search_docs import SearchDocsSkill
    from friday.skills.rag.search_knowledge_graph import SearchKnowledgeGraphSkill
    from friday.skills.web.fetch_url import FetchUrlSkill
    from friday.skills.web.research_web import ResearchWebSkill
    from friday.skills.web.search_web import SearchWebSkill

    registry = SkillRegistry()
    registry.register(DateTimeSkill(), aliases=["get_current_time"])
    registry.register(JokeSkill())
    registry.register(SystemInfoSkill())
    registry.register(WordCountSkill())
    registry.register(FormatJsonSkill())
    registry.register(CalculateSkill())
    registry.register(SummarizeSkill())
    registry.register(ExplainCodeSkill())
    registry.register(RememberSkill())
    registry.register(RecallSkill())
    registry.register(ListCalendarEventsSkill(settings=settings))
    registry.register(CreateCalendarEventSkill(settings=settings))
    registry.register(CancelCalendarEventSkill(settings=settings))
    registry.register(ModifyCalendarEventSkill(settings=settings))
    registry.register(FindFreeSlotsSkill(settings=settings))
    registry.register(SummarizeDaySkill(settings=settings))
    registry.register(StatusCheckSkill(settings=settings))
    registry.register(ListEmailsSkill(settings=settings))
    registry.register(ReadEmailSkill(settings=settings))
    registry.register(SendEmailSkill(settings=settings))
    registry.register(DraftEmailReplySkill(settings=settings))
    registry.register(ResolveContactSkill(settings=settings))
    registry.register(StartMeetingWorkflowSkill(settings=settings))
    registry.register(ScheduleLocalReminderSkill(settings=settings))
    registry.register(PrepareMeetingSkill(settings=settings))
    registry.register(GetWeatherSkill(settings=settings))
    registry.register(GetHealthSummarySkill(settings=settings))
    registry.register(SearchPersonalNotesSkill(settings=settings))
    if getattr(settings, "ha_enabled", False):
        from friday.skills.local.ha_skills import (
            HaGetStateSkill,
            HaGetStatusSkill,
            HaListEntitiesSkill,
        )

        registry.register(HaGetStatusSkill(settings=settings), aliases=["get_home_status"])
        registry.register(HaListEntitiesSkill(settings=settings))
        registry.register(HaGetStateSkill(settings=settings))
    registry.register(
        SearchWebSkill(max_results_default=settings.web_search_max_results)
    )
    registry.register(
        ResearchWebSkill(max_results_default=settings.web_search_max_results)
    )
    registry.register(SearchDocsSkill(settings=settings))
    registry.register(SearchKnowledgeGraphSkill(settings=settings))
    registry.register(FetchUrlSkill())
    registry.register(
        WorldNewsSkill(
            feeds_csv=settings.news_world_feeds,
            monitor_url=settings.world_monitor_url,
            auto_open_monitors=settings.auto_open_monitors,
        ),
        aliases=["get_news"],
    )
    registry.register(
        FinanceNewsSkill(
            feeds_csv=settings.news_finance_feeds,
            monitor_url=settings.finance_monitor_url,
            auto_open_monitors=settings.auto_open_monitors,
        ),
        aliases=["get_finance"],
    )
    registry.register(
        CountryBriefingSkill(
            world_feeds_csv=settings.news_world_feeds,
            finance_feeds_csv=settings.news_finance_feeds,
            world_monitor_url=settings.world_monitor_url,
            finance_monitor_url=settings.finance_monitor_url,
            auto_open_monitors=settings.auto_open_monitors,
        ),
        aliases=["country_update"],
    )
    registry.register(ListSupportedCountriesSkill())
    registry.register(OpenWorldMonitorSkill(monitor_url=settings.world_monitor_url))
    registry.register(
        OpenFinanceMonitorSkill(monitor_url=settings.finance_monitor_url)
    )
    return registry
