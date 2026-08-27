# Checklist manual — web UI Fase 1

- [ ] Arranque: `run-agent-api.ps1` + `run-web-ui.ps1`; header mostra API/LM.
- [ ] Chat texto: pedido simples (hora / piada) → bolha + timeline de actividade.
- [ ] Mic: gravar → transcrição → chat → (se TTS on) áudio interruptível com Stop.
- [ ] Quick actions: notícias / finanças → country chip + source cards (ou demo etiquetado).
- [ ] Monitor: botão “Abrir monitor” abre `/monitors/...` após clique (com `AUTO_OPEN` false).
- [ ] Confirmação: “Confirmação demo” → modal; Escape cancela; Enter **não** confirma.
- [ ] Definições: persistência após refresh (localStorage); alto contraste / reduced motion.
- [ ] Demo: desligar LM → banner demo + respostas `[DEMO]`.
- [ ] Teclado: foco visível; Tab no modal de confirmação.
- [ ] Mobile / estreito: conversa + mic; drawer “Painel” para lateral.
