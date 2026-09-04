# Frigate NVR — Fase 3 (stub até câmaras)

## Política

- Vídeo **100% local** — zero egress para cloud  
- Câmaras na rede IoT/Guest sem internet  
- **Não** sobe no `docker compose up` normal  

## Profile

```powershell
# Só quando houver RTSP + GPU/Coral configurados
docker compose --profile frigate up -d
```

Config stub: `deploy/frigate/config.yml` (sem câmeras).  
Gravações: volume `frigate_media` (mapear para SSD dedicado quando P1 existir).

## Variáveis reservadas

```env
FRIGATE_ENABLED=false
FRIGATE_URL=http://127.0.0.1:5000
```

## Skills

Nenhuma skill de snapshot nesta passagem 3.0. Fase 3.1: `frigate_get_events` / snapshot com ConfirmationGate.

## GPU

LLM + Whisper + Frigate competem por VRAM — preferir Coral USB para detecção (hardware P2) ou horários separados.
