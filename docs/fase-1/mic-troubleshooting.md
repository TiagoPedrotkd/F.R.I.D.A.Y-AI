# Microfone — troubleshooting (Windows / Realtek)

O loop de voz usa **Enter + WebRTC VAD**: pressiona Enter, fala, e a gravação
para sozinha após ~2 s de silêncio. Se ouvires sempre “Não percebi”, o
problema costuma ser **ruído contínuo** no microfone, não o Whisper.

## Sem microfone (so colunas)

O loop de voz **precisa** de um microfone fisico para STT. Se so tens
altifalantes / monitor:

```env
VOICE_TRIGGER=text
AUDIO_OUTPUT_DEVICE=Realtek
```

Escreves a pergunta no terminal; a FRIDAY responde por voz nas colunas.
Quando tiveres um USB mic / headset, muda para `VOICE_TRIGGER=enter`.

## Diagnóstico rápido

```powershell
.\scripts\mic-benchmark.ps1
# ou um device concreto:
.\scripts\mic-benchmark.ps1 --device 1
```

Interpretação (em silêncio, sem falar):

| Métrica | Esperado | Problema |
|---------|----------|----------|
| RMS dB | &lt; -30 dB | &gt; -20 dB = ruído alto / Mistura estéreo |
| `webrtc_speech` % | ~0% | &gt; 20% = VAD trata ruído como fala |
| crest | &gt; 4 (fala) | &lt; 4 + alto = zumbido/loopback |

Lista de devices:

```powershell
.\scripts\list-audio-devices.ps1
# ou
python -m friday.audio.devices
```

## Correções no Windows

1. **Definições → Sistema → Som → Entrada** → escolhe **Microfone (Realtek)**, não Mistura estéreo.
2. **Painel de controlo → Som → Gravação** → desactiva **Mistura estéreo**.
3. Propriedades do microfone → **Níveis** → volume ~50–70%.
4. Desactiva **escuta / monitorização** se estiver activa.

No `.env`, devices MME estáveis neste projecto:

```env
AUDIO_INPUT_DEVICE=1
AUDIO_OUTPUT_DEVICE=4
VOICE_TRIGGER=enter
WEBRTC_VAD_MODE=3
WEBRTC_SILENCE_MS=2000
PREPROC_HIGHPASS_HZ=100
```

## USB mic (opcional)

Se o Realtek continuar &gt; -20 dB em silêncio depois das correções, um microfone
USB dedicado (ex. Samson Q2U) costuma baixar o floor 15–20 dB e melhorar o
WebRTC/Whisper sem mudanças de código. Define `AUDIO_INPUT_DEVICE` com o nome
parcial ou o índice do USB.

## Pipeline actual

1. Enter abre a janela de gravação.
2. High-pass 100 Hz + noise gate adaptativo.
3. WebRTC VAD (modo 3) decide início/fim de fala.
4. Whisper recebe só os frames de fala (16 kHz).
5. Piper → resample para a taxa nativa dos altifalantes.
