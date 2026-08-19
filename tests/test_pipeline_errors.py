"""Tests for pipeline error hierarchy."""

import pytest

from friday.pipeline.errors import (
    APITimeoutError,
    EmptyAudioError,
    NetworkError,
    RecordingTimeoutError,
    UnknownSkillError,
    VoicePipelineError,
)


def test_exception_hierarchy():
    assert issubclass(NetworkError, VoicePipelineError)
    assert issubclass(APITimeoutError, VoicePipelineError)
    assert issubclass(EmptyAudioError, VoicePipelineError)
    assert issubclass(RecordingTimeoutError, VoicePipelineError)
    assert issubclass(UnknownSkillError, VoicePipelineError)


def test_raise_and_catch():
    with pytest.raises(EmptyAudioError):
        raise EmptyAudioError("silent")
