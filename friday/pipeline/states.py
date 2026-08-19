"""Pipeline state enumeration."""

from enum import Enum, auto


class PipelineState(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()
    THINKING = auto()
    SPEAKING = auto()
