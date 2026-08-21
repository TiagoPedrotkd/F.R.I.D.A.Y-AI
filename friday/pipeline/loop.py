"""Main voice pipeline loop."""

from __future__ import annotations

import asyncio
import logging
import sys

import sounddevice as sd

from friday.audio.capture import AudioBuffer, capture_until_silence
from friday.audio.devices import resolve_input_device, resolve_output_device
from friday.audio.mic_health import check_input_health, measure_input_level
from friday.audio.ptt import read_text_line, wait_for_enter
from friday.audio.utterance_capture import record_utterance
from friday.config import Settings, get_settings
from friday.llm.tool_runner import ToolRunner
from friday.memory.short_term import ShortTermMemory
from friday.pipeline.errors import (
    APITimeoutError,
    EmptyAudioError,
    ModelUnavailableError,
    NetworkError,
    RecordingTimeoutError,
    VoicePipelineError,
)
from friday.pipeline.metrics import LatencyMetrics
from friday.skills.registry import SkillRegistry, default_registry
from friday.stt.whisper_engine import WhisperEngine
from friday.tts.piper_engine import PiperEngine
from friday.wake.detector import WakeDetector

logger = logging.getLogger(__name__)


async def _safe_speak(tts: PiperEngine, text: str) -> None:
    try:
        await tts.speak(text)
    except Exception:
        logger.exception("TTS playback failed — message was: %s", text)


def _maybe_save_debug_wav(audio: AudioBuffer) -> None:
    import os
    import wave
    from pathlib import Path

    if os.environ.get("DEBUG_SAVE_AUDIO", "").lower() not in ("1", "true", "yes"):
        return
    path = Path("debug_last_utterance.wav")
    samples = (audio.samples * 32767).astype("int16")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(audio.sample_rate)
        wf.writeframes(samples.tobytes())
    logger.info("Debug audio guardado em %s", path.resolve())


def _device_label(index: int | None) -> str:
    if index is None:
        return "default"
    dev = sd.query_devices(index)
    return f"[{index}] {dev['name']}"


def _assert_audible(audio: AudioBuffer, min_db: float) -> None:
    if audio.is_empty:
        raise EmptyAudioError()
    if audio.speech_level_db < min_db:
        logger.warning(
            "Audio too quiet: %.1f dB (min %.1f dB)",
            audio.speech_level_db,
            min_db,
        )
        raise EmptyAudioError()


async def _transcribe_audio(
    *,
    stt: WhisperEngine,
    audio: AudioBuffer,
    loop: asyncio.AbstractEventLoop,
) -> str:
    text = await loop.run_in_executor(None, stt.transcribe, audio)
    logger.info("STT: %s", text or "(vazio)")
    if not text.strip():
        _maybe_save_debug_wav(audio)
        raise EmptyAudioError()
    return text


async def _capture_user_text(
    *,
    settings: Settings,
    stt: WhisperEngine,
    input_device: int | None,
    loop: asyncio.AbstractEventLoop,
    trigger: str,
    post_wake_ms: int,
    noise_floor_db: float | None,
) -> str:
    if trigger == "text":
        text = await read_text_line()
        if not text.strip():
            raise EmptyAudioError()
        logger.info("STT (texto): %s", text)
        return text

    if trigger == "enter":
        await wait_for_enter()
        audio = await record_utterance(
            input_device=input_device,
            max_seconds=settings.record_timeout,
            silence_ms=settings.webrtc_silence_ms,
            vad_mode=settings.webrtc_vad_mode,
            highpass_hz=settings.preproc_highpass_hz,
            noise_floor_db=noise_floor_db,
        )
    else:
        if post_wake_ms > 0:
            await asyncio.sleep(post_wake_ms / 1000.0)
        logger.info("A escutar... fala a tua pergunta")
        audio = await capture_until_silence(
            sample_rate=settings.sample_rate,
            timeout=settings.record_timeout,
            silence_ms=settings.record_silence_ms,
            silence_threshold_db=settings.vad_silence_db,
            input_device=input_device,
            speech_start_db=settings.speech_start_db,
            wait_timeout=15.0,
        )

    _assert_audible(audio, settings.min_audio_db)
    return await _transcribe_audio(stt=stt, audio=audio, loop=loop)


async def _finish_error(tts: PiperEngine, metrics: LatencyMetrics, message: str) -> None:
    await _safe_speak(tts, message)
    metrics.mark("tts_end")
    metrics.log()


async def _process_turn(
    *,
    settings: Settings,
    stt: WhisperEngine,
    llm: ToolRunner,
    tts: PiperEngine,
    memory: ShortTermMemory,
    input_device: int | None,
    loop: asyncio.AbstractEventLoop,
    trigger: str,
    post_wake_ms: int = 0,
    noise_floor_db: float | None = None,
) -> None:
    metrics = LatencyMetrics.start()
    metrics.mark("started")

    try:
        text = await _capture_user_text(
            settings=settings,
            stt=stt,
            input_device=input_device,
            loop=loop,
            trigger=trigger,
            post_wake_ms=post_wake_ms,
            noise_floor_db=noise_floor_db,
        )
        # capture + stt complete inside helper
        metrics.mark("capture_end")
        metrics.mark("stt_end")

        reply = await llm.chat_with_tools(text, memory.messages)
        metrics.mark("llm_end")
        logger.info("LLM reply (%d tool rounds): %s", reply.tool_rounds, reply.text)

        memory.add_user(text)
        memory.add_assistant(reply.text)

        await _safe_speak(tts, reply.text)
        metrics.mark("tts_end")
        metrics.log()

    except NetworkError:
        logger.warning("Network error during turn")
        await _finish_error(tts, metrics, settings.error_network_pt)
    except ModelUnavailableError as exc:
        logger.warning("LLM model unavailable: %s", exc)
        await _finish_error(tts, metrics, settings.error_model_pt)
    except APITimeoutError:
        logger.warning("LLM timeout during turn")
        await _finish_error(tts, metrics, settings.error_timeout_pt)
    except (EmptyAudioError, RecordingTimeoutError):
        logger.info("Empty, inaudible, or timed-out audio")
        await _finish_error(tts, metrics, settings.error_no_audio_pt)
    except VoicePipelineError as exc:
        logger.warning("Pipeline error", exc_info=exc)
        await _finish_error(tts, metrics, settings.error_generic_pt)
    except Exception:
        logger.exception("Unexpected pipeline error")
        try:
            await _safe_speak(tts, settings.error_generic_pt)
        except Exception:
            pass
        metrics.mark("tts_end")
        metrics.log()


async def _run_trigger_loop(
    *,
    settings: Settings,
    stt: WhisperEngine,
    llm: ToolRunner,
    tts: PiperEngine,
    memory: ShortTermMemory,
    input_device: int | None,
    loop: asyncio.AbstractEventLoop,
    trigger: str,
    noise_floor_db: float | None,
    pause_s: float,
) -> None:
    while True:
        await _process_turn(
            settings=settings,
            stt=stt,
            llm=llm,
            tts=tts,
            memory=memory,
            input_device=input_device,
            loop=loop,
            trigger=trigger,
            noise_floor_db=noise_floor_db,
        )
        await asyncio.sleep(pause_s)


async def run_forever(
    settings: Settings | None = None,
    registry: SkillRegistry | None = None,
) -> None:
    settings = settings or get_settings()
    registry = registry or default_registry(settings)

    input_device = resolve_input_device(settings.audio_input_device or None)
    output_device = resolve_output_device(settings.audio_output_device or None)

    stt = WhisperEngine(
        settings.whisper_model,
        device=settings.whisper_device,
        vad_filter=settings.whisper_vad_filter,
    )
    llm = ToolRunner(settings, registry)
    tts = PiperEngine(settings, output_device=output_device)
    memory = ShortTermMemory(max_messages=settings.max_context_messages)

    logger.info("FRIDAY voice loop started")

    loop = asyncio.get_running_loop()
    logger.info("Preloading Whisper model '%s'...", settings.whisper_model)
    await loop.run_in_executor(None, stt._ensure_model)
    logger.info("Whisper ready")
    try:
        await loop.run_in_executor(None, llm._client.ensure_model_ready)
    except ModelUnavailableError:
        logger.exception("LLM model unavailable at startup")
        logger.error(
            "Corrige o LM Studio e volta a correr. "
            "URL=%s MODEL=%s",
            settings.lm_studio_base_url_host,
            settings.lm_studio_model,
        )
        raise
    logger.info("Audio input: %s", _device_label(input_device))
    logger.info("Audio output: %s", _device_label(output_device))

    trigger = settings.voice_trigger.lower()
    turn_kwargs = dict(
        settings=settings,
        stt=stt,
        llm=llm,
        tts=tts,
        memory=memory,
        input_device=input_device,
        loop=loop,
    )

    if trigger == "text":
        logger.info(
            "Modo TEXT — sem microfone: escreve a pergunta e ENTER "
            "(resposta por voz nas colunas)"
        )
        await _run_trigger_loop(
            **turn_kwargs, trigger=trigger, noise_floor_db=None, pause_s=0.3
        )
        return

    noise_floor_db = measure_input_level(input_device)
    check_input_health(input_device)

    if trigger == "enter":
        logger.info(
            "Modo ENTER — pressiona Enter, fala em portugues "
            "(para sozinho apos ~%dms de silencio)",
            settings.webrtc_silence_ms,
        )
        await _run_trigger_loop(
            **turn_kwargs, trigger=trigger, noise_floor_db=noise_floor_db, pause_s=0.5
        )
        return

    if trigger == "speech":
        logger.info("Modo SPEECH — fala em portugues quando quiseres")
        await _run_trigger_loop(
            **turn_kwargs, trigger=trigger, noise_floor_db=noise_floor_db, pause_s=1.5
        )
        return

    wake = WakeDetector(
        keyword=settings.wake_keyword,
        threshold=settings.wake_threshold,
        sample_rate=settings.sample_rate,
        push_to_talk=settings.voice_push_to_talk,
        models_dir=settings.models_dir,
        model_path=settings.wake_model_path,
        inference_framework=settings.wake_inference_framework,
        input_device=input_device,
        trigger_mode=trigger,
        speech_threshold_db=settings.speech_start_db,
    )

    if trigger == "push" or settings.voice_push_to_talk:
        logger.info("Modo PUSH-TO-TALK")
    else:
        logger.info("Modo WAKE — diz 'Hey Jarvis' e depois a pergunta")

    async for _wake_event in wake.listen():
        wake.pause()
        try:
            await _process_turn(
                **turn_kwargs,
                trigger=trigger,
                post_wake_ms=settings.record_post_wake_ms,
            )
        finally:
            if trigger != "push" and not settings.voice_push_to_talk:
                wake.resume()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    try:
        asyncio.run(run_forever())
    except ModelUnavailableError:
        logger.exception("LLM model unavailable")
    except NetworkError:
        logger.exception(
            "LM Studio inacessivel — abre o LM Studio, carrega o modelo "
            "e inicia o Local Server (porta 1234)"
        )
    except KeyboardInterrupt:
        logger.info("Voice loop stopped")


if __name__ == "__main__":
    main()
