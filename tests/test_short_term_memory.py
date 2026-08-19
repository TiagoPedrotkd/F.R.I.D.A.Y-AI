"""Tests for short-term memory."""

from friday.memory.short_term import ShortTermMemory


def test_memory_keeps_last_n_messages():
    mem = ShortTermMemory(max_messages=4)
    mem.add_user("a")
    mem.add_assistant("b")
    mem.add_user("c")
    mem.add_assistant("d")
    mem.add_user("e")
    assert len(mem) == 4
    roles = [m["role"] for m in mem.messages]
    assert roles == ["assistant", "user", "assistant", "user"]
    assert mem.messages[-1]["content"] == "e"


def test_memory_clear():
    mem = ShortTermMemory()
    mem.add_user("hello")
    mem.clear()
    assert len(mem) == 0
