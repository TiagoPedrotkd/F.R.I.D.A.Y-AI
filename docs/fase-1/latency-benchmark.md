# Latency benchmark — Fase 1

Target (voz): **p50 wake-to-TTS < 3–4s**, p95 < 5s on NVIDIA GPU with whisper-small + phi-4 + Piper.

Complemento (web/API): `.\scripts\fase1_chat_latency.ps1` — soft target p50 < 8s no caminho `/v1/chat`.

## Metrics format

Each completed voice turn logs a JSON line:

```json
{"event":"turn_complete","wake_to_tts_ms":3200,"capture_ms":2100,"stt_ms":450,"llm_ms":380,"tts_ms":270}
```

## Running the voice benchmark

1. Start Bionic/LM Studio on `http://localhost:1234`
2. Start the voice loop: `.\scripts\run-voice-loop.ps1`
3. Run several prompts; tee logs if useful
4. Aggregate: `.\scripts\benchmark-latency.ps1 -LogFile logs\voice.log`

The benchmark script parses `turn_complete` lines from stdout/log and reports p50/p95.

## Chat API latency (Fase 1 web path)

```powershell
.\scripts\run-agent-api.ps1   # LM Studio ON
.\scripts\fase1_chat_latency.ps1 -N 5
```

Report: `docs/fase-1/chat-latency-last.json`

## Manual test prompts

1. "Que horas sao?"
2. "Conta uma piada"
3. "Como te chamas?"
4. "O que podes fazer?"
5. "Qual e a capital de Portugal?"
6. Repeat time + joke prompts for consistency

## Tuning if over target

| Symptom | Action |
|---------|--------|
| High STT | Switch `WHISPER_MODEL=base`, use int8 |
| High LLM | Reduce `max_tokens`, use smaller model / free VRAM |
| High TTS | Use faster Piper voice |
| High capture | Reduce `RECORD_SILENCE_MS` (e.g. 600) |

## Acceptable ranges (NVIDIA GPU)

| Stage | Typical |
|-------|---------|
| Capture (VAD) | 800–2500 ms |
| STT | 300–800 ms |
| LLM | 500–2000 ms |
| TTS | 200–500 ms |
