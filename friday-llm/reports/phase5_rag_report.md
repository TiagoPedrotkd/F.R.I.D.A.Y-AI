# Fase 5 — RAG e integração

**Run:** `friday-fase5-rag`  
**Gerado:** 2026-09-04T23:00:14.427211+00:00

## Corpus

- Documentos repo: **45** | seeds: **3**
- Chunks: **82** → `D:\Repositories\F.R.I.D.A.Y-AI\friday-llm\data\rag\chunks.jsonl`

## Índice vetorial

- Modelo: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Chunks indexados: **82**
- Pasta: `D:\Repositories\F.R.I.D.A.Y-AI\data\rag_chroma`

## Smoke (keyword/embedding)

- Backend: `embedding`

```json
{
  "O que diz o manual sobre VLAN IoT?": [
    {
      "text": "A F.R.I.D.A.Y. liga-se ao LM Studio via API OpenAI-compatible em localhost:1234/v1. O modelo default de producao e microsoft/phi-4, configuravel por LM_STUDIO_MODEL.",
      "title": "LM Studio setup",
      "source": "docs/fase-0/lm-studio-setup.md",
      "url_or_document_id": "docs/fase-0/lm-studio-setup.md",
      "captured_at_or_version": "repo",
      "language": "pt",
      "score": 0.4135
    },
    {
      "text": "USB dedicado (ex. Samson Q2U) costuma baixar o floor 15–20 dB e melhorar o\nWebRTC/Whisper sem mudanças de código. Define `AUDIO_INPUT_DEVICE` com o nome\nparcial ou o índice do USB.\n\n## Pipeline actual\n\n1. Enter abre a janela de gravação.\n2. High-pass 100 Hz + noise gate adaptativo.\n3. WebRTC VAD (modo 3) decide início/fim de fala.\n4. Whisper recebe só os frames de fala (16 kHz).\n5. Piper → resample para a taxa nativa dos altifalantes.",
      "title": "mic troubleshooting",
      "source": "repo_docs",
      "url_or_document_id": "docs/fase-1/mic-troubleshooting.md",
      "captured_at_or_version": "git",
      "language": "pt",
      "score": 0.3717
    },
    {
      "text": "# VLANs no WR11000 (OpenWrt/LuCI)\n\nGuia especifico para o router detectado em `192.168.10.1` (OpenWrt + LuCI, modelo **WR11000**).\n\n## Estado actual da tua rede\n\n| Item | Valor |\n|---|---|\n| Gateway / router | `192.168.10.1` |\n| PC hub (FRIDAY) | `192.168.10.131` |\n| Subnet actual | `192.168.10.0/24` |\n| DNS suffix | `lan` |\n\nA rede **Main (VLAN 10)** ja corresponde ao teu LAN actual. Vais **adicionar** VLAN 30 (IoT) e VLAN 99 (Mgmt) sem alterar o IP do PC.\n\n---\n\n## IMPORTANTE — antes de comecar\n\n1. **Faz backup** da configuracao: LuCI → System → Backup / Flash Operations → Generate archive\n2. Garante acesso **fisico** ao router (cabo Ethernet) — se algo correr mal, podes reset\n3. Aplica num momento em que podes reiniciar a rede se necessario\n4. **Nao tenho acesso ao teu router** — segues ",
      "title": "rede vlan openwrt wr11000",
      "source": "repo_docs",
      "url_or_document_id": "docs/arquitectura/rede-vlan-openwrt-wr11000.md",
      "captured_at_or_version": "git",
      "language": "pt",
      "score": 0.359
    }
  ],
  "Como ligar ao LM Studio?": [
    {
      "text": "A F.R.I.D.A.Y. liga-se ao LM Studio via API OpenAI-compatible em localhost:1234/v1. O modelo default de producao e microsoft/phi-4, configuravel por LM_STUDIO_MODEL.",
      "title": "LM Studio setup",
      "source": "docs/fase-0/lm-studio-setup.md",
      "url_or_document_id": "docs/fase-0/lm-studio-setup.md",
      "captured_at_or_version": "repo",
      "language": "pt",
      "score": 0.6708
    },
    {
      "text": "# Cutover modelo próprio\n\n1. Treinar / seleccionar melhor adapter (`friday-llm/checkpoints/...`).\n2. Export GGUF (`python -m friday_llm.export.cli ...`) se aplicável.\n3. Carregar no LM Studio.\n4. Definir `LM_STUDIO_MODEL` no `.env` para o novo id.\n5. Smoke: `scripts/training/cutover_smoke.ps1`.\n6. Rollback: repor `LM_STUDIO_MODEL=microsoft/phi-4` ([friday-llm/export/rollback.md](../../friday-llm/export/rollback.md)).\n\n**Nunca** cutover automático sem gate de eval.",
      "title": "cutover",
      "source": "repo_docs",
      "url_or_document_id": "docs/fase-llm/cutover.md",
      "captured_at_or_version": "git",
      "language": "pt",
      "score": 0.3707
    },
    {
      "text": "# Documentação F.R.I.D.A.Y-AI\n\n| Área | Índice |\n|------|--------|\n| Layout do monorepo | [REPO_LAYOUT.md](REPO_LAYOUT.md) |\n| Arquitectura / rede | [arquitectura/README.md](arquitectura/README.md) |\n| Fase 0 — Docker + LM Studio | [fase-0/README.md](fase-0/README.md) |\n| Fase 1 — Voz / UI / skills | [fase-1/README.md](fase-1/README.md) |\n| Fase 2 — CalDAV / Email / desktop | [fase-2/README.md](fase-2/README.md) |\n| Fase LLM — prompts, treino, especialistas | [fase-llm/README.md](fase-llm/README.md) |\n\nRuntime do assistente: `friday/` + `services/agent-api` + `apps/web`.  \nTreino de modelo: `friday-llm/` (não misturar com `data/` de produção).",
      "title": "README",
      "source": "repo_docs",
      "url_or_document_id": "docs/README.md",
      "captured_at_or_version": "git",
      "language": "pt",
      "score": 0.3521
    }
  ],
  "Tres camadas de conhecimento": [
    {
      "text": "Camada A: conhecimento nos pesos via CPT. Camada B: comportamento via SFT. Camada C: RAG e tools para factos exactos e actualizaveis. Nao confundir as tres.",
      "title": "Tres camadas de conhecimento",
      "source": "friday-llm/reports/phase0_audit.md",
      "url_or_document_id": "friday-llm/reports/phase0_audit.md",
      "captured_at_or_version": "2026-08-29",
      "language": "pt",
      "score": 0.6161
    },
    {
      "text": "# Documentação F.R.I.D.A.Y-AI\n\n| Área | Índice |\n|------|--------|\n| Layout do monorepo | [REPO_LAYOUT.md](REPO_LAYOUT.md) |\n| Arquitectura / rede | [arquitectura/README.md](arquitectura/README.md) |\n| Fase 0 — Docker + LM Studio | [fase-0/README.md](fase-0/README.md) |\n| Fase 1 — Voz / UI / skills | [fase-1/README.md](fase-1/README.md) |\n| Fase 2 — CalDAV / Email / desktop | [fase-2/README.md](fase-2/README.md) |\n| Fase LLM — prompts, treino, especialistas | [fase-llm/README.md](fase-llm/README.md) |\n\nRuntime do assistente: `friday/` + `services/agent-api` + `apps/web`.  \nTreino de modelo: `friday-llm/` (não misturar com `data/` de produção).",
      "title": "README",
      "source": "repo_docs",
      "url_or_document_id": "docs/README.md",
      "captured_at_or_version": "git",
      "language": "pt",
      "score": 0.3425
    },
    {
      "text": "iras pessoais (fases posteriores)\n- Geopolítica tipo “World Monitor” comercial completo (podes ligar URL externa)\n- Tradução automática de todos os artigos (só títulos + summary curto)\n\n---\n\n## Resumo\n\nO utilizador escolhe um **país**; a FRIDAY usa um **perfil** (feeds + TZ + mercados + mapa),\ncorre as skills de **notícias** e/ou **finanças**, fala um briefing honesto e\npode abrir um **monitor** desse país. Mundo (`WW`) continua a ser o default\nquando não há país na frase.",
      "title": "noticias financas worldwide",
      "source": "repo_docs",
      "url_or_document_id": "docs/fase-1/noticias-financas-worldwide.md",
      "captured_at_or_version": "git",
      "language": "pt",
      "score": 0.3383
    }
  ]
}
```

## Integração agente

- Skill `search_docs` no ToolRunner (CLI + agent-api)
- Router: documento/manual → RAG; notícias/hora → tools
- Phi-4 em produção inalterado (`LM_STUDIO_MODEL`)
