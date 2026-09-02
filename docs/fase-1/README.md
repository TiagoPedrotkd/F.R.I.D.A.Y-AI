# Fase 1 — Núcleo conversacional (voz + web + skills)

**Estado:** engenharia fechada (2026-09-02). Aceitação live UI no PC do utilizador — ver [checklist-conclusao.md](checklist-conclusao.md).

## Documentos

| Doc | Conteúdo |
|-----|----------|
| [checklist-conclusao.md](checklist-conclusao.md) | Fecho Fase 1 + gates |
| [conversacao.md](conversacao.md) | Contrato conversacional |
| [skills-contract.md](skills-contract.md) | Interface de skills |
| [voz.md](voz.md) | Personalidade + Piper |
| [web-ui.md](web-ui.md) | Agent API + UI |
| [web-ui-checklist.md](web-ui-checklist.md) | Checklist manual UI |
| [mcp.md](mcp.md) | MCP Cursor |
| [noticias-financas-worldwide.md](noticias-financas-worldwide.md) | News / finance |
| [latency-benchmark.md](latency-benchmark.md) | Latência voz |
| [mic-troubleshooting.md](mic-troubleshooting.md) | Microfone |
| [desktop-tauri.md](desktop-tauri.md) | Plano Fase 2 (não implementar na F1) |

## Arranque rápido

```powershell
# LM Studio Local Server ON
.\scripts\run-agent-api.ps1
.\scripts\run-web-ui.ps1
.\scripts\fase1_acceptance.ps1
```

Voz CLI: `.\scripts\run-voice-loop.ps1` (`VOICE_TRIGGER=text` sem mic).

MCP: copiar/activar `.cursor/mcp.json` (já gerado localmente a partir do example).

## Validação

```powershell
.\scripts\fase1_acceptance.ps1          # gates código
.\scripts\fase1_acceptance.ps1 -RequireLive
.\scripts\fase1_chat_latency.ps1
.\scripts\benchmark-latency.ps1 -LogFile logs\voice.log
```
