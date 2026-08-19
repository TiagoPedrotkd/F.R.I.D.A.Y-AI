# Scripts — F.R.I.D.A.Y-AI

## Arranque condicional

No login do Windows, o FRIDAY pergunta se queres iniciar os serviços. Serviços pesados (LM Studio, Docker) só sobem se confirmares.

### Instalação (uma vez)

PowerShell **como Administrador**:

```powershell
cd D:\Repositories\F.R.I.D.A.Y-AI
powershell -ExecutionPolicy Bypass -File scripts\register-startup-task.ps1
```

### Teste manual

```powershell
powershell -ExecutionPolicy Bypass -File scripts\friday-start.ps1
```

### Remover tarefa agendada

```powershell
Unregister-ScheduledTask -TaskName "FRIDAY-AI-Startup" -Confirm:$false
```

## Ficheiros

| Script | Descrição |
|---|---|
| [`friday-start.ps1`](friday-start.ps1) | Popup "Iniciar FRIDAY?" → LM Studio + `docker compose up -d` |
| [`register-startup-task.ps1`](register-startup-task.ps1) | Regista tarefa no Task Scheduler (requer Admin) |

## Configuração

Editar variáveis no topo de `friday-start.ps1` se o repo ou LM Studio estiver noutro caminho:

```powershell
$RepoPath = "D:\Repositories\F.R.I.D.A.Y-AI"
```

## Comportamento

1. Utilizador faz login no Windows
2. Task Scheduler executa `friday-start.ps1`
3. Popup: "Queres iniciar o F.R.I.D.A.Y-AI?"
4. **Sim** → inicia LM Studio + `docker compose up -d --build`
5. **Não** → nada acontece; PC fica sem carga FRIDAY
