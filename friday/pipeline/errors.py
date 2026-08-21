"""Voice pipeline exception hierarchy."""


class VoicePipelineError(Exception):
    """Base error for the voice pipeline."""


class NetworkError(VoicePipelineError):
    """LLM or external service unreachable."""


class ModelUnavailableError(VoicePipelineError):
    """LLM server reachable but no model loaded / wrong model id."""


class APITimeoutError(VoicePipelineError):
    """LLM request exceeded timeout."""


class EmptyAudioError(VoicePipelineError):
    """Recorded audio is silent or too quiet."""


class RecordingTimeoutError(VoicePipelineError):
    """Recording exceeded maximum duration without usable speech."""


class UnknownSkillError(VoicePipelineError):
    """LLM requested a skill that is not registered."""
