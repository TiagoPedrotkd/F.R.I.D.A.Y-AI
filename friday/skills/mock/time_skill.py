"""Deprecated path — use friday.skills.local.datetime_skill."""

from friday.skills.local.datetime_skill import DateTimeSkill as TimeSkill
from friday.skills.local.datetime_skill import LegacyTimeSkill

__all__ = ["TimeSkill", "LegacyTimeSkill"]
