# MCP — Model Context Protocol (F.R.I.D.A.Y)

## O que e MCP? (passo a passo)

### 1. Problema que resolve

Assistentes (Cursor, Claude Desktop, etc.) precisam de **ferramentas externas**
de forma padronizada: ler ficheiros, chamar APIs, resumir texto, etc.
Sem MCP, cada app inventa o seu plugin. Com MCP, ha um **contrato unico**.

### 2. Tres pecas

| Peca | Papel |
|------|--------|
| **Host** | A aplicacao (ex.: Cursor) |
| **Client** | Dentro do Host, liga-se a servidores MCP |
| **Server** | O teu programa (ex.: `friday-mcp`) que expoe tools/prompts/resources |

```text
[Cursor Host] --stdio/HTTP--> [friday-mcp Server]
                                 |- tools (summarize, explain_code, ...)
                                 |- prompts (templates)
                                 |- resources (capabilities)
```

### 3. Tools vs Prompts vs Resources

- **Tool**: funcao que o modelo pode **executar** (ex.: `get_current_datetime`).
- **Prompt**: **template** que o Host usa para montar uma tarefa
  (ex.: `summarize`, `explain_code`) — o LLM do Host e que gera a resposta.
- **Resource**: dados de leitura (ex.: `friday://capabilities`).

### 4. Como a FRIDAY expoe MCP neste repo

Servidor: `python -m friday.mcp_server.server` (ou `.\scripts\run-mcp-server.ps1`).

Prompts MCP:

- `summarize` — template para resumir texto
- `explain_code` — template para explicar codigo passo a passo

Tools MCP (executaveis):

- `summarize`, `explain_code` (com LLM local se disponivel)
- `get_current_datetime`, `get_system_info`
- `remember`, `recall` (memoria Chroma / JSONL)

As mesmas capacidades existem tambem como **skills** no voice loop
(`VOICE_TRIGGER=text`), para falares com a FRIDAY sem Cursor.

### 5. Ligar no Cursor

Copia [`.cursor/mcp.json.example`](../../.cursor/mcp.json.example) para
`.cursor/mcp.json` (ou cola o mesmo bloco em Cursor Settings → MCP):

```json
{
  "mcpServers": {
    "friday": {
      "command": "${workspaceFolder}/.venv/Scripts/python.exe",
      "args": ["-m", "friday.mcp_server.server"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

Se `${workspaceFolder}` nao funcionar no teu Cursor, usa o caminho absoluto
para o `python.exe` do `.venv` (o ficheiro local `.cursor/mcp.json` ja usa
caminho absoluto neste repo).

### 6. Fluxo tipico

1. Abres o Cursor com o MCP `friday` activo.
2. Perguntas: "Usa o prompt summarize neste texto: ..."
3. O Host pede o prompt ao servidor MCP → recebe o template preenchido.
4. O modelo do Cursor gera o resumo **ou** chama a tool `summarize` se preferires execucao local.

### 7. Relacao com a conversa por voz

- **Sem MCP**: `.\scripts\run-voice-loop.ps1` → skills internas + Phi-4.
- **Com MCP**: Cursor (ou outro Host) usa o mesmo servidor para tools/prompts.
- Nao precisas de MCP para a FRIDAY falar contigo; MCP e a **ponte para outras apps**.

### 8. Dependencias

```powershell
pip install -r requirements-voice.txt
# inclui: mcp, chromadb
```

### 9. Teste rapido do servidor

```powershell
.\scripts\run-mcp-server.ps1
```

O processo fica a espera em **stdio** (normal para MCP). Para testar tools
sem Cursor, usa o voice loop: `Guarda isto: o projecto usa Phi-4` depois
`Lembras-te do projecto?`.
