# Catálogo de componentes — apps/web

Referência rápida. Design tokens: [`DESIGN_SYSTEM.md`](./DESIGN_SYSTEM.md).  
Stories interactivas: `npm run storybook`.

---

## Shell e feedback

### AppShell

- **Propósito:** Layout raiz HUD (header, core, chat, overlays).
- **Props:** nenhuma (lê store).
- **Variants:** sidebar mobile; painéis lazy quando abertos.
- **Exemplo:** montado em `main.tsx` dentro de `ErrorBoundary`.
- **Deps:** store, quase todos os painéis (lazy).
- **A11y:** landmarks via secções; botões de header com texto.

### ErrorBoundary

- **Propósito:** Captura erros de render; fallback HUD + reset.
- **Props:** `children`, `fallback?`, `onError?`
- **Variants:** fallback default vs render prop.
- **Exemplo:** `<ErrorBoundary><AppShell /></ErrorBoundary>`
- **Deps:** `reportApiError`
- **A11y:** `role="alert"` no fallback.

### ErrorNotice

- **Propósito:** Mostra `store.error` global.
- **Props:** nenhuma.
- **Variants:** oculto se `error === null`.
- **Exemplo:** renderizado no AppShell.
- **Deps:** store.
- **A11y:** `role="alert"`.

### DemoBanner

- **Propósito:** Aviso de modo demonstração.
- **Props:** nenhuma.
- **Variants:** só quando demo activo.
- **Deps:** store / fixtures.
- **A11y:** `data-testid="demo-banner"`.

### AlertsBanner

- **Propósito:** Lista alertas dismissíveis do store.
- **Props:** nenhuma.
- **Variants:** por `severity` do alerta.
- **Deps:** store (`alerts`, `dismissAlert`).
- **A11y:** mensagens legíveis; botões dismiss.

### ConfirmationDialog

- **Propósito:** Confirmar acção pendente (HA, skills, etc.).
- **Props:** nenhuma (store `pending`).
- **Variants:** com/sem preview.
- **Deps:** store `resolveConfirm`.
- **A11y:** `role="dialog"`, `aria-describedby`.

### ConnectionStatus

- **Propósito:** Dots API / LM (+ badge DEMO).
- **Props:** nenhuma.
- **Variants:** ok (cyan) / fail (danger); demo força ok visual.
- **Deps:** store.
- **A11y:** `role="status"`, `sr-only` labels.

### CountryContextChip

- **Propósito:** Mostra país da sessão.
- **Props:** `country: string | null`
- **Variants:** vazio vs código país.
- **Deps:** nenhuma (apresentação).
- **A11y:** texto visível.

---

## Chat (`features/chat`)

### ConversationPanel

- **Propósito:** Lista de mensagens + empty + typing.
- **Props:** `compact?: boolean`
- **Variants:** empty / com mensagens / busy (typing).
- **Exemplo:** `<ConversationPanel compact />`
- **Deps:** store, `useAutoScroll`.
- **A11y:** `aria-label="Conversa"`, `role="log"`.

### MessageBubble

- **Propósito:** Uma mensagem user/assistant/system.
- **Props:** `message: Message`
- **Variants:** user | assistant | system | demo; feedback + regenerar no último assistant.
- **Deps:** store (`rateMessage`, etc.).
- **A11y:** `data-role`, botões com `aria-label`.

### ConversationEmpty

- **Propósito:** Empty state “Aguardando instruções…”.
- **Props:** nenhuma.
- **Deps:** nenhuma.

### TypingIndicator

- **Propósito:** Bolha busy com label de estado.
- **Props:** `label: string`
- **Deps:** nenhuma.
- **A11y:** `aria-label={label}`.

### VoiceControls

- **Propósito:** Input texto + mic + envio.
- **Props:** nenhuma.
- **Variants:** mic live (`.hud-btn-mic-live`).
- **Deps:** store (`sendText`, `toggleMic`).
- **A11y:** labels nos controlos.

### QuickActions

- **Propósito:** Atalhos de prompts.
- **Props:** `orbit?: boolean`
- **Variants:** orbit vs lista.
- **Deps:** store `sendText`.

---

## Domínio (painéis)

### SettingsPanel

- **Propósito:** Prefs (tema, TTS, perfil, Google…).
- **Props:** `onClose: () => void`
- **Variants:** Google ligado/desligado.
- **Deps:** store + `api.fetchGoogleStatus`.
- **A11y:** formulário com labels.

### CasaPanel

- **Propósito:** Entidades Home Assistant.
- **Props:** `onClose`
- **Variants:** loading / erro / listas luzes-switches.
- **Deps:** store Casa + API HA.

### SaudePanel

- **Propósito:** Resumo saúde / sync.
- **Props:** `onClose`
- **Deps:** API health.

### FinancasPanel

- **Propósito:** Ledger pessoal (salário, recurring, txs, investments).
- **Props:** `onClose`
- **Deps:** API finance.
- **Nota:** candidato a `features/finance/sections/` (LOC alto).

### AgendaPanel

- **Propósito:** Eventos Google Calendar (próximos dias).
- **Props:** `onClose`
- **Deps:** API agenda.

### MailPanel

- **Propósito:** Mensagens Gmail recentes.
- **Props:** `onClose`
- **Deps:** API mail.

---

## HUD widgets e dados

### FridayCore

- **Propósito:** Reactor SVG central; reflecte `state`.
- **Props:** nenhuma.
- **Variants:** tint por `FridayState`; reduced motion.
- **Deps:** store.
- **A11y:** `role="img"` + `aria-label` com `stateLabel`.

### HudDateGauge / HudRingMeter (`HudWidgets`)

- **Propósito:** Data/hora e meters API/LM/CORE.
- **Props:** `locale` / `label`, `value`, `ok`
- **Deps:** nenhuma (dados vindos do shell).

### ActivityTimeline

- **Propósito:** Passos de actividade do último pedido.
- **Deps:** store `activity`.

### SessionList

- **Propósito:** Sessões recentes + restore.
- **Deps:** store / API sessions.

### SourceCard

- **Propósito:** Fonte (web/doc/memory/news).
- **Props:** `source`, `demo?`
- **Variants:** por `kind` (borda/cor).

### ToolStatusCard

- **Propósito:** Estado de ferramenta/monitor.
- **Props:** conforme ficheiro (label/status).

### StageWires (interno AppShell)

- **Propósito:** Decoração SVG de ligações; `aria-hidden`.

---

## Exemplo rápido (chat)

```tsx
import { ConversationPanel, MessageBubble } from '@/features/chat'
import { makeMessage } from '@/test/fixtures'

// Painel completo (store)
<ConversationPanel />

// Bolha isolada (story / teste)
<MessageBubble message={makeMessage({ role: 'assistant', text: 'Olá', demo: true })} />
```
