"""Application settings loaded from environment / .env file."""

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # LLM (Bionic / LM Studio on host)
    lm_studio_base_url_host: str = Field(
        default="http://localhost:1234/v1",
        alias="LM_STUDIO_BASE_URL_HOST",
    )
    lm_studio_model: str = Field(default="microsoft/phi-4", alias="LM_STUDIO_MODEL")
    lm_studio_api_key: str = Field(default="lm-studio", alias="LM_STUDIO_API_KEY")
    # Vision / multimodal (LM Studio VLM). Empty = auto-detect from /v1/models.
    lm_studio_vision_model: str = Field(default="", alias="LM_STUDIO_VISION_MODEL")
    llm_vision_enabled: bool = Field(default=True, alias="LLM_VISION_ENABLED")
    llm_timeout_seconds: float = Field(default=15.0, alias="LLM_TIMEOUT_SECONDS")
    llm_max_tool_rounds: int = Field(default=3, alias="LLM_MAX_TOOL_ROUNDS")
    # Optional OpenAI-compatible fallback (Ollama / llama.cpp server)
    llm_fallback_base_url: str = Field(default="", alias="LLM_FALLBACK_BASE_URL")
    llm_fallback_model: str = Field(default="", alias="LLM_FALLBACK_MODEL")
    llm_fallback_api_key: str = Field(default="ollama", alias="LLM_FALLBACK_API_KEY")
    llm_fallback_vision_model: str = Field(
        default="", alias="LLM_FALLBACK_VISION_MODEL"
    )
    # Vision stability
    llm_vision_ping_ttl_seconds: float = Field(
        default=300.0, alias="LLM_VISION_PING_TTL_SECONDS"
    )
    # Planner: off | hint | aggressive
    llm_planner_mode: str = Field(default="aggressive", alias="LLM_PLANNER_MODE")
    llm_planner_max_per_minute: int = Field(
        default=12, alias="LLM_PLANNER_MAX_PER_MINUTE"
    )
    # Context budget + web grounding
    llm_context_token_budget: int = Field(
        default=6000, alias="LLM_CONTEXT_TOKEN_BUDGET"
    )
    web_source_required: bool = Field(default=True, alias="WEB_SOURCE_REQUIRED")
    # Persistence / feedback
    sessions_dir: Path = Field(
        default=_REPO_ROOT / "data" / "sessions",
        alias="SESSIONS_DIR",
    )
    feedback_path: Path = Field(
        default=_REPO_ROOT / "data" / "feedback" / "feedback.jsonl",
        alias="FEEDBACK_PATH",
    )
    prefs_dir: Path = Field(
        default=_REPO_ROOT / "data" / "prefs",
        alias="PREFS_DIR",
    )

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
    )  # short id "paraphrase-multilingual-MiniLM-L12-v2" also accepted
    rag_corpus_path: Path = Field(
        default=_REPO_ROOT / "friday-llm" / "data" / "rag" / "chunks.jsonl",
        alias="RAG_CORPUS_PATH",
    )
    rag_index_dir: Path = Field(
        default=_REPO_ROOT / "data" / "rag_chroma",
        alias="RAG_INDEX_DIR",
    )
    rag_top_k: int = Field(default=3, alias="RAG_TOP_K")

    # Fase 2 — CalDAV
    caldav_enabled: bool = Field(default=True, alias="CALDAV_ENABLED")
    caldav_url: str = Field(default="", alias="CALDAV_URL")
    caldav_user: str = Field(default="friday", alias="CALDAV_USER")
    caldav_password: str = Field(default="", alias="CALDAV_PASSWORD")

    # Fase 2 — Email
    email_enabled: bool = Field(default=False, alias="EMAIL_ENABLED")
    imap_host: str = Field(default="", alias="IMAP_HOST")
    imap_port: int = Field(default=993, alias="IMAP_PORT")
    imap_user: str = Field(default="", alias="IMAP_USER")
    imap_password: str = Field(default="", alias="IMAP_PASSWORD")
    imap_folder: str = Field(default="INBOX", alias="IMAP_FOLDER")
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="", alias="SMTP_FROM")
    email_use_ssl: bool = Field(default=True, alias="EMAIL_USE_SSL")

    # Fase 3 — Home Assistant / MQTT / Frigate
    ha_enabled: bool = Field(default=False, alias="HA_ENABLED")
    ha_url: str = Field(default="http://127.0.0.1:8123", alias="HA_URL")
    ha_token: str = Field(default="", alias="HA_TOKEN")
    mqtt_host: str = Field(default="127.0.0.1", alias="MQTT_HOST")
    mqtt_port: int = Field(default=1883, alias="MQTT_PORT")
    frigate_enabled: bool = Field(default=False, alias="FRIGATE_ENABLED")
    frigate_url: str = Field(default="http://127.0.0.1:5000", alias="FRIGATE_URL")

    # Fase 4 — Google (OAuth + Calendar / Gmail / Health)
    google_enabled: bool = Field(default=False, alias="GOOGLE_ENABLED")
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://127.0.0.1:8090/v1/google/callback",
        alias="GOOGLE_REDIRECT_URI",
    )
    google_token_path: Path = Field(
        default=_REPO_ROOT / "data" / "secrets" / "google_tokens.json",
        alias="GOOGLE_TOKEN_PATH",
    )
    # Fitbit Web API (legacy bridge até Google Health; opcional)
    fitbit_enabled: bool = Field(default=False, alias="FITBIT_ENABLED")
    fitbit_client_id: str = Field(default="", alias="FITBIT_CLIENT_ID")
    fitbit_client_secret: str = Field(default="", alias="FITBIT_CLIENT_SECRET")
    fitbit_token_path: Path = Field(
        default=_REPO_ROOT / "data" / "secrets" / "fitbit_tokens.json",
        alias="FITBIT_TOKEN_PATH",
    )

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

    @model_validator(mode="after")
    def _resolve_repo_relative_paths(self) -> "Settings":
        """Make relative .env paths stable regardless of process CWD."""
        path_fields = (
            "sessions_dir",
            "feedback_path",
            "prefs_dir",
            "rag_corpus_path",
            "rag_index_dir",
            "models_dir",
            "google_token_path",
            "fitbit_token_path",
        )
        for name in path_fields:
            value = getattr(self, name, None)
            if not isinstance(value, Path):
                continue
            if not value.is_absolute():
                object.__setattr__(self, name, (_REPO_ROOT / value).resolve())
        # Piper voice may be a relative path string inside models/
        voice = (self.piper_voice or "").strip()
        if voice and not Path(voice).is_absolute():
            object.__setattr__(self, "piper_voice", str((_REPO_ROOT / voice).resolve()))
        return self

    @property
    def record_timeout(self) -> float:
        return self.max_record_seconds


def get_settings() -> Settings:
    return Settings()
