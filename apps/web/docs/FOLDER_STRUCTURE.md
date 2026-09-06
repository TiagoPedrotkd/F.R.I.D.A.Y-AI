# Folder structure — apps/web (FRIDAY)

Documento de convenções para escalar o frontend React (~24 componentes hoje → 100+).  
Piloto implementado: `src/features/chat/`.

## 1. Princípios

1. **Feature-first** — ecrãs e domínio vivem em `features/<domain>/`, não num `components/` flat infinito.
2. **`ui/` sem domínio** — primitivos reutilizáveis **não** importam `@/state` nem `@/api`.
3. **Aliases `@/`** — proibir imports relativos profundos (`../../../`); usar `@/features/...`, `@/hooks/...`.
4. **Limites de LOC** — um ficheiro de UI idealmente ≤ 120 linhas; acima de 200 partir; acima de 350 bloquear PR.
5. **Migração incremental** — não big-bang; mover uma feature de cada vez (chat → finance → settings → shell).

## 2. Árvore alvo

```
apps/web/src/
├── app/                      # shell / bootstrap (AppShell migra aqui depois)
├── features/
│   ├── chat/                 # ✅ piloto
│   │   ├── ConversationPanel.tsx
│   │   ├── ConversationEmpty.tsx
│   │   ├── TypingIndicator.tsx
│   │   ├── MessageBubble.tsx
│   │   ├── useAutoScroll.ts
│   │   └── index.ts
│   ├── financas/             # ✅ Finanças (ex-FinancasPanel)
│   ├── home/                 # CasaPanel
│   ├── health/               # SaudePanel
│   ├── agenda/
│   ├── mail/
│   └── settings/
├── components/
│   ├── ui/                   # ✅ HudButton, HoloPanel (sem store)
│   └── …                     # legado flat — esvaziar progressivamente
├── hooks/                    # hooks cross-feature (useApi, …)
├── state/                    # zustand + machine
├── api/
├── lib/                      # formatMoney, cn, …
├── types/
├── constants/
├── platform/                 # audio, storage, config, links
├── styles/
│   └── tokens.css
├── demo/
└── test/
```

`components/` permanece temporariamente para painéis ainda não migrados. Preferir `components/ui/` para primitives HUD até existir `src/ui/` dedicado.

## 3. Naming conventions

| Tipo | Padrão | Exemplo |
|------|--------|---------|
| Componente React | `PascalCase.tsx` | `TypingIndicator.tsx` |
| Hook | `use` + `camelCase.ts` | `useAutoScroll.ts` |
| Util (`lib/`) | `camelCase.ts` | `formatMoney.ts` |
| Tipos | `PascalCase` em `types/` ou co-localizados | `types/message.ts` |
| Constantes | `SCREAMING_SNAKE` no módulo | `BUSY_STATES` |
| Feature folder | singular / domain | `features/finance/` |
| Teste | `*.test.ts(x)` ao lado | `MessageBubble.test.tsx` |
| Barrel | `index.ts` só API pública | `export { ConversationPanel } from './ConversationPanel'` |

### Regras de dependência

```
ui/        → (nada de state/api)
hooks/     → preferir args; se usar store, documentar (useApp*)
features/  → ui, hooks, state, api, lib, constants
app/       → features, ui, state
```

## 4. Limites de tamanho

| LOC | Acção |
|-----|--------|
| ≤ 120 | Ideal |
| 120–200 | Aceitável para um painel/form único; preferir `sections/` |
| > 200 | Obrigatório partir |
| > 350 | Bloqueio de PR |

Hooks: preferir ≤ 80 LOC. Store: planear slices quando um domínio ultrapassar ~400 LOC.

## 5. Path alias

```ts
// tsconfig.json — paths
"baseUrl": ".",
"paths": { "@/*": ["src/*"] }

// vite.config.ts
resolve: { alias: { '@': path.resolve(__dirname, 'src') } }
```

```ts
import { useAppStore } from '@/state/store'
import { ConversationPanel } from '@/features/chat'
```

## 6. Checklist de migração (por feature)

1. Criar `features/<name>/`.
2. Mover componente(s) e actualizar imports para `@/…`.
3. Extrair subcomponentes se > 120 LOC ou responsabilidades claras.
4. Exportar via `index.ts`.
5. Actualizar consumidores (`AppShell`, testes).
6. Remover ficheiros antigos em `components/`.
7. Correr `npm test` / vitest no pacote web.

### Ordem sugerida (próximos PRs)

1. ~~chat (piloto)~~
2. **finance** — partir `FinancasPanel` em `sections/`
3. **settings** — `SettingsPanel`
4. **home / health / agenda / mail**
5. Mover `AppShell` → `app/`
6. Extrair primitivos repetidos → `ui/`
7. Fatiar `state/store.ts` por domínio

## 7. Exemplo: ConversationPanel

### Antes (`components/ConversationPanel.tsx`, ~72 LOC)

Um ficheiro com header, empty state, lista de mensagens, typing indicator e auto-scroll.

### Depois

```
features/chat/
  ConversationPanel.tsx   # orquestra
  ConversationEmpty.tsx
  TypingIndicator.tsx
  MessageBubble.tsx
  useAutoScroll.ts
  index.ts
```

```tsx
// ConversationPanel.tsx (orquestração)
import { stateLabel } from '@/state/machine'
import { useAppStore } from '@/state/store'
import { ConversationEmpty } from './ConversationEmpty'
import { MessageBubble } from './MessageBubble'
import { TypingIndicator } from './TypingIndicator'
import { useAutoScroll } from './useAutoScroll'
import { BUSY_STATES } from './constants'

export function ConversationPanel({ compact }: { compact?: boolean }) {
  const messages = useAppStore((s) => s.messages)
  const state = useAppStore((s) => s.state)
  const lang = useAppStore((s) => s.prefs.language)
  const busy = BUSY_STATES.has(state)
  const endRef = useAutoScroll([messages, state])

  return (
    <section className={/* … */} aria-label="Conversa">
      {/* header */}
      <div className="hud-scroll …" role="log">
        {messages.length === 0 && !busy && <ConversationEmpty />}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {busy && <TypingIndicator label={stateLabel(state, lang)} />}
        <div ref={endRef} />
      </div>
    </section>
  )
}
```

```tsx
// AppShell.tsx
import { ConversationPanel } from '@/features/chat'
```

Nota: o ConversationPanel já era pequeno; o valor do piloto é o **padrão de pasta + extração**, não o LOC. O mesmo padrão aplica-se a `FinancasPanel` (~365 LOC).

## 8. Onboarding rápido

1. Ler este doc.
2. Feature nova → pasta em `features/`, não ficheiro solto em `components/`.
3. Coisa visual reutilizável sem domínio → `ui/`.
4. Lógica reutilizável → `hooks/` ou `lib/`.
5. Imports sempre com `@/`.

## 9. Estado vs review Set 2026

A avaliação externa (coverage &lt;5%, sem hooks/ESLint/Storybook/ErrorBoundary/API Zod) **está desactualizada**. Snapshot do delta:

| Item | Estado |
|------|--------|
| Strict TS, ESLint, Prettier, Husky, `@/` | DONE |
| Zustand slices + validators + persist + docs | DONE |
| HttpClient + endpoints tipados + Zod | DONE (stream/TTS ainda legado) |
| ErrorBoundary, lazy panels, Storybook, design docs | DONE |
| `features/chat` + `features/financas` | DONE |
| `components/ui` (HudButton, HoloPanel) | DONE |
| CI `test:coverage` | DONE |
| Playwright / PWA / i18n framework / analytics | **Deferred** (fora de fase) |
| Migrar Casa/Mail/Settings → `features/` | Próximo |
| Coverage gate em todo `src/` | Próximo |
