# Checklist manual — web UI Fase 1

Automatizado (código): `.\scripts\fase1_acceptance.ps1`  
Fecho: [checklist-conclusao.md](checklist-conclusao.md)

## Antes de começar

1. LM Studio → modelo carregado → Local Server **ON** (`localhost:1234`)
2. `.\scripts\run-agent-api.ps1`
3. `.\scripts\run-web-ui.ps1` → http://127.0.0.1:5173

## Checklist

- [ ] Arranque: header mostra API/LM ligados (não demo forçado).
- [ ] Chat texto: pedido simples (hora / piada) → bolha + timeline de actividade.
- [ ] Mic: gravar → transcrição → chat → (se TTS on) áudio interruptível com Stop.
- [ ] Quick actions: notícias / finanças → country chip + source cards (ou demo etiquetado).
- [ ] Monitor: botão “Abrir monitor” abre `/monitors/...` após clique (com `AUTO_OPEN` false).
- [ ] Confirmação: “Confirmação demo” → modal; Escape cancela; Enter **não** confirma.
- [ ] Definições: persistência após refresh (localStorage); alto contraste / reduced motion.
- [ ] Demo: desligar LM → banner demo + respostas `[DEMO]`.
- [ ] Teclado: foco visível; Tab no modal de confirmação; Escape interrompe fala.
- [ ] Mobile / estreito: conversa + mic; drawer “Painel” para lateral.

## Atalhos de verificação

```powershell
.\scripts\fase1_acceptance.ps1 -RequireLive
.\scripts\fase1_chat_latency.ps1 -N 5
```
