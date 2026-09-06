# Testing strategy — apps/web

Vitest + React Testing Library. Sem snapshots. AAA obrigatório. Suite alvo **&lt;10s**. Coverage alvo **≥60% lines** (`npm run test:coverage`).

## Princípios

1. **Priorizar risco** — core UI (FridayCore, chat), state machine, fluxo `sendText`.
2. **Fixtures estáveis** — [`src/test/fixtures.ts`](../src/test/fixtures.ts); IDs fixos.
3. **Mocks consistentes** — [`src/test/mockApi.ts`](../src/test/mockApi.ts) (`resetAppStore`, `mockFetchJson`) ou `vi.mock('../api/client')` no teste de store.
4. **Sem snapshots** — queries por `role` / `label` / texto.
5. **Integração leve** — componente + Zustand + API mockada (não Playwright nesta fase).

## Roadmap 4 semanas

### Semana 1 (esta entrega)

- [x] `setup.ts` global (cleanup, restore mocks, AbortSignal.timeout polyfill)
- [x] `fixtures.ts` + `mockApi.ts`
- [x] `machine.test.ts` table-driven em todas as arestas `ALLOWED`
- [x] `FridayCore.test.tsx`
- [x] Script `test:coverage` + thresholds Vitest

### Semana 2

- [x] `ConversationPanel.test.tsx` (empty / messages / typing)
- [x] `MessageBubble.test.tsx` — feedback +1/−1, Regenerar só no último assistant
- [x] Cobrir `ConversationEmpty` / `TypingIndicator` via painel (já parcial)

### Semana 3

- [ ] `SettingsPanel.test.tsx` — toggle prefs + mock `api.updatePrefs`
- [ ] `ErrorNotice.test.tsx` — mostra `store.error`, desaparece quando null
- [ ] Google connect block: `fetchGoogleStatus` mockado

### Semana 4

- [x] `FinancasPanel` — load `fetchFinanceSummary` com fixture `financeSummaryOk` (`features/financas/`)
- [ ] Fechar gaps até **≥60%** em todo `src/` (exceto `demo/`)
- [x] CI: `npm run test:coverage` no pipeline web (`.github/workflows/web-ci.yml`)

## Scripts

```bash
npm test                 # vitest run
npm run test:watch       # watch
npm run test:coverage    # relatório text + html + lcov; falha se < thresholds
```

Thresholds em `vite.config.ts`: lines/statements **60**, functions/branches **50**.

**CI:** o job `lint-test-build` em `.github/workflows/web-ci.yml` corre `npm run test:coverage` (não só `npm test`).

**Scope do gate:** superfície crítica (`machine`, slices ui/prefs, `features/chat`, FridayCore, ErrorBoundary, `api/http-client`+endpoints+errors, hooks, chips/dialogs, `components/ui`). Stories (`**/*.stories.tsx`) estão **excluídas** do coverage.  
**Depois:** alargar `coverage.include` a todo `src/` (exceto `demo/`) e manter ≥60%.

Relatório HTML: `apps/web/coverage/index.html`.

## Exemplos de integração (entregues)

| Teste | Camadas |
|-------|---------|
| `FridayCore.test.tsx` | store.state → aria-label |
| `ConversationPanel.test.tsx` | store.messages + busy → UI |
| `store.chat.integration.test.ts` | `sendText` → mock `chatStream` → messages + idle/error |

## Critérios de aceitação por componente

### FridayCore

- Label `role="img"` reflecte `stateLabel` em `idle`, `thinking`, `listening`, `error`
- Não usa snapshot de SVG
- Respeita `prefs.language` (PT por defeito nos testes)

### ConversationPanel

- Empty (“Aguardando instruções”) só com `messages.length === 0` e estado não-busy
- Mensagens do store aparecem no `role="log"`
- Busy (`thinking`, etc.) mostra typing com label do estado
- Contador de mensagens com padding `01`, `02`, …

### MessageBubble (semana 2)

- Demo badge quando `message.demo`
- +1/−1 chama `rateMessage`
- Regenerar/Continuar só no último assistant

### SettingsPanel (semana 3)

- Alterar um toggle atualiza `prefs` no store
- Persistência / API mockada sem network real
- Bloco Google não rebenta se `fetchGoogleStatus` falhar

### FinancasPanel (semana 4)

- Loading → summary com `financeSummaryOk`
- Erro de API mostrado ao utilizador
- Sem chamadas reais a `:8090`

### Store chat

- Com `sessionId` + mock `chatStream`: user + assistant messages; estado final `idle` (TTS off)
- Falha de stream → `state === 'error'` + mensagem de fallback

### State machine

- Todas as arestas `ALLOWED[from]` passam `canTransition` / `transition`
- Transição ilegal mantém `from` e faz `console.warn`
- `stateLabel` PT/EN para estados críticos

## Padrão AAA (exemplo)

```ts
it('shows typing while busy', () => {
  // Arrange
  resetAppStore({ state: 'thinking', messages: [makeMessage({ role: 'user', text: 'Oi' })] })
  // Act
  render(<ConversationPanel />)
  // Assert
  expect(screen.getByLabelText(/pensar/i)).toBeInTheDocument()
})
```
