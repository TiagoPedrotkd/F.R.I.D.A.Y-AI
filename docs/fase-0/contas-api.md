# Contas API — Preparatório Fase 1

A Fase 0 usa **LM Studio local** — não são necessárias contas cloud para o Hello World.

Este documento prepara a integração com APIs cloud nas fases seguintes.

## Providers previstos

| Provider | Uso típico | Dashboard |
|---|---|---|
| **Anthropic** | Raciocínio complexo, Claude | [console.anthropic.com](https://console.anthropic.com) |
| **OpenAI** | Ecossistema amplo, GPT | [platform.openai.com](https://platform.openai.com) |

## Quando criar contas

- **Fase 1** — quando o orquestrador precisar de LLM cloud como fallback ou complemento ao local
- Não bloqueia a conclusão da Fase 0

## Setup recomendado (quando activar)

1. Criar conta no provider escolhido
2. Gerar API key com permissões mínimas
3. Adicionar ao `.env` local (nunca commitar):

   ```env
   ANTHROPIC_API_KEY=sk-ant-...
   OPENAI_API_KEY=sk-...
   ```

4. Activar **billing alerts** no dashboard (limite mensal)
5. Documentar key ID e data de criação num gestor de passwords

## Política de uso

- Preferir LM Studio local para desenvolvimento e testes
- Usar cloud apenas quando necessário (modelos maiores, funcionalidades específicas)
- Nunca enviar dados sensíveis (finanças, saúde) a APIs cloud sem revisão de privacidade

## Rotação

Ver [gestao-secrets.md](gestao-secrets.md) para procedimento completo de rotação e resposta a leaks.
