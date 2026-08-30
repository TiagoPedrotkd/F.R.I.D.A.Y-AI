# Voz e personalidade F.R.I.D.A.Y.

## Personalidade (LLM)

Definida em `friday/llm/prompts.py` e injectada pelo `ToolRunner`.

| Traço | Comportamento |
|-------|----------------|
| Tom | Formal, profissional, humor seco ocasional |
| Tratamento PT | `FRIDAY_USER_ADDRESS` (default **Senhor**) |
| Tratamento EN | **Sir** |
| Idioma | Português europeu por defeito; inglês britânico formal se o utilizador falar inglês |

```env
FRIDAY_USER_ADDRESS=Senhor
```

Não hardcodes "Stark". Muda só o tratamento formal via env.

## TTS (Piper local)

Motor: `friday/tts/piper_engine.py`. Sem Azure/Google/ElevenLabs nesta fase.

| Variável | Função |
|----------|--------|
| `PIPER_VOICE` | Caminho ONNX (default `models/piper/en_GB-cori-high.onnx` — feminina britânica) |
| `PIPER_EXECUTABLE` | Binário Piper opcional |
| `PIPER_LENGTH_SCALE` | Velocidade base (1.0 = normal; ~0.95–1.05 ≈ 150–170 wpm) |

Voz PT-EU anterior (fallback): `models/piper/pt_PT-tugao-medium.onnx`.

A UI envia `rate` e `language` em `POST /v1/tts`. `rate > 1` fala mais depressa (length_scale = 1/rate).

### Trocar para voz britânica (inglês)

1. Descarrega um modelo Piper `en_GB` (ex. `en_GB-cori-high`) para `models/piper/`.
2. No `.env`:

```env
PIPER_VOICE=models/piper/en_GB-cori-high.onnx
PIPER_LENGTH_SCALE=1.0
```

3. Reinicia o agent-api / `friday-voice`.

Nota: a voz PT actual (`tugao`) não é RP britânica; o registo britânico no texto vem do system prompt. Para inglês falado com sotaque GB, usa um modelo `en_GB-*`.

## Preferências UI

Definições → Volume TTS e **Velocidade TTS** (`prefs.rate`). Persistidas em localStorage.
