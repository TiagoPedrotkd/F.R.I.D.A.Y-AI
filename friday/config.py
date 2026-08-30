"""Application settings loaded from environment / .env file."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM (Bionic / LM Studio on host)
    lm_studio_base_url_host: str = Field(
        default="http://localhost:1234/v1",
        alias="LM_STUDIO_BASE_URL_HOST",
    )
    lm_studio_model: str = Field(default="microsoft/phi-4", alias="LM_STUDIO_MODEL")
    lm_studio_api_key: str = Field(default="lm-studio", alias="LM_STUDIO_API_KEY")
    llm_timeout_seconds: float = Field(default=15.0, alias="LLM_TIMEOUT_SECONDS")
    llm_max_tool_rounds: int = Field(default=3, alias="LLM_MAX_TOOL_ROUNDS")

    # Wake word
    wake_keyword: str = Field(default="hey_jarvis", alias="WAKE_KEYWORD")
    wake_threshold: float = Field(default=0.65, alias="WAKE_THRESHOLD")
    wake_model_path: str = Field(default="", alias="WAKE_MODEL_PATH")
    wake_inference_framework: str = Field(default="onnx", alias="WAKE_INFERENCE_FRAMEWORK")
    record_post_wake_ms: int = Field(default=500, alias="RECORD_POST_WAKE_MS")
    voice_trigger: str = Field(default="enter", alias="VOICE_TRIGGER")
    voice_push_to_talk: bool = Field(default=False, alias="VOICE_PUSH_TO_TALK")

    # STT
    whisper_model: str = Field(default="small", alias="WHISPER_MODEL")
    whisper_device: str = Field(default="cuda", alias="WHISPER_DEVICE")
    whisper_vad_filter: bool = Field(default=False, alias="WHISPER_VAD_FILTER")

    # Persona
    friday_user_address: str = Field(default="Senhor", alias="FRIDAY_USER_ADDRESS")

    # TTS
    piper_voice: str = Field(
        default="models/piper/en_GB-cori-high.onnx",
        alias="PIPER_VOICE",
    )
    piper_executable: str = Field(default="", alias="PIPER_EXECUTABLE")
    piper_length_scale: float = Field(default=1.0, alias="PIPER_LENGTH_SCALE")

    # Audio capture / playback
    sample_rate: int = Field(default=16000, alias="SAMPLE_RATE")
    audio_input_device: str = Field(default="", alias="AUDIO_INPUT_DEVICE")
    audio_output_device: str = Field(default="", alias="AUDIO_OUTPUT_DEVICE")
    max_record_seconds: float = Field(default=10.0, alias="MAX_RECORD_SECONDS")
    min_audio_db: float = Field(default=-60.0, alias="MIN_AUDIO_DB")
    vad_silence_db: float = Field(default=-45.0, alias="VAD_SILENCE_DB")
    speech_start_db: float = Field(default=-55.0, alias="SPEECH_START_DB")
    record_silence_ms: int = Field(default=1200, alias="RECORD_SILENCE_MS")

    # WebRTC VAD + preprocess (Enter hybrid capture)
    webrtc_vad_mode: int = Field(default=3, alias="WEBRTC_VAD_MODE")
    webrtc_silence_ms: int = Field(default=2000, alias="WEBRTC_SILENCE_MS")
    preproc_highpass_hz: float = Field(default=100.0, alias="PREPROC_HIGHPASS_HZ")

    # Memory
    max_context_messages: int = Field(default=20, alias="MAX_CONTEXT_MESSAGES")

    # News / monitors / web
    world_monitor_url: str = Field(default="", alias="WORLD_MONITOR_URL")
    finance_monitor_url: str = Field(default="", alias="FINANCE_MONITOR_URL")
    news_world_feeds: str = Field(default="", alias="NEWS_WORLD_FEEDS")
    news_finance_feeds: str = Field(default="", alias="NEWS_FINANCE_FEEDS")
    web_search_max_results: int = Field(default=5, alias="WEB_SEARCH_MAX_RESULTS")
    auto_open_monitors: bool = Field(default=False, alias="AUTO_OPEN_MONITORS")

    # Document RAG (separate from personal memory in data/chroma/)
    rag_enabled: bool = Field(default=True, alias="RAG_ENABLED")
    rag_backend: str = Field(default="embedding", alias="RAG_BACKEND")
    rag_embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        alias="RAG_EMBEDDING_MODEL",
    )
    rag_corpus_path: Path = Field(
        default=_REPO_ROOT / "friday-llm" / "data" / "rag" / "chunks.jsonl",
        alias="RAG_CORPUS_PATH",
    )
    rag_index_dir: Path = Field(
        default=_REPO_ROOT / "data" / "rag_chroma",
        alias="RAG_INDEX_DIR",
    )
    rag_top_k: int = Field(default=3, alias="RAG_TOP_K")

    # User-facing error messages (Portuguese)
    error_network_pt: str = Field(
        default="Nao consegui ligar ao modelo. Tenta outra vez.",
        alias="ERROR_NETWORK_PT",
    )
    error_no_audio_pt: str = Field(
        default="Nao percebi. Podes repetir?",
        alias="ERROR_NO_AUDIO_PT",
    )
    error_generic_pt: str = Field(
        default="Ocorreu um erro. Tenta outra vez.",
        alias="ERROR_GENERIC_PT",
    )
    error_timeout_pt: str = Field(
        default="Demorei demasiado a pensar.",
        alias="ERROR_TIMEOUT_PT",
    )
    error_model_pt: str = Field(
        default="O modelo de linguagem nao esta carregado. Abre o LM Studio e carrega um modelo.",
        alias="ERROR_MODEL_PT",
    )

    models_dir: Path = Field(default=_REPO_ROOT / "models")

    @property
    def record_timeout(self) -> float:
        return self.max_record_seconds


def get_settings() -> Settings:
    return Settings()
