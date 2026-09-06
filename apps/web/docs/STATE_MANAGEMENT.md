# State management (Zustand)

A single composed store (`useAppStore`) holds app-wide UI, session, prefs, and Casa data. Slices keep the code organised; components keep importing from `@/state/store`.

## Layout

| Module | Role |
| --- | --- |
| `store.ts` | `create` + `devtools` + `persist` (prefs only) + `logger` |
| `slices/uiSlice.ts` | Panels, draft, error |
| `slices/sessionSlice.ts` | State machine, chat, mic/TTS, bootstrap |
| `slices/prefsSlice.ts` | Preferences + DOM theme hooks |
| `slices/casaSlice.ts` | Home Assistant entities / actions |
| `machine.ts` | Allowed `FridayState` transitions |
| `validators.ts` | Zod for prefs patches, ratings, states |
| `middleware.ts` | DEV transition logger + `withRollback` |
| `selectors.ts` | Derived reads (`selectBusy`, `selectDemo`, …) |

## Global vs local

| Prefer **global** (`useAppStore`) | Prefer **local** (`useState` / form state) |
| --- | --- |
| Panel open flags (`settingsOpen`, `casaOpen`, …) | Transient form fields until submit (except chat `draft`) |
| Session / messages / connection flags | One-off modal / dropdown open state inside a panel |
| Prefs that must survive reload | Ephemeral filters, search boxes, pagination cursors |
| Chat `draft` (shared with voice / quick actions) | Component-private animation / focus flags |

Rule of thumb: if two distant components must stay in sync, or the value must survive navigation within the shell, put it in the store. Otherwise keep it local.

## Selectors

```ts
import { useAppStore } from '@/state/store'
import { selectBusy, selectDemo } from '@/state/selectors'

const busy = useAppStore(selectBusy)
const demo = useAppStore(selectDemo)
```

Prefer selectors for derived booleans so UI does not re-render on unrelated fields.

## Persist

Only **`prefs`** are persisted (`partialize`). Messages, `sessionId`, mic recorders, and `AbortController`s are never written to storage. The adapter uses the `friday.prefs.*` prefix and mirrors the legacy `friday.prefs.prefs` key.

## DevTools & time-travel

1. Install the [Redux DevTools](https://chromewebstore.google.com/detail/redux-devtools) browser extension.
2. Open the app in DEV; the store appears as **FridayApp**.
3. Trigger an action (e.g. send a message → `sendText`).
4. Inspect `state` / `messages` in the tree.
5. Use **Jump** / scrub the action list to time-travel. Prefer jumping on serialisable snapshots; avoid relying on time-travel while mic/TTS controllers are live.

The DEV `logger` prints `{ from, to }` on `FridayState` changes to the console.

## Rollback

`withRollback(get, set, mutate)` snapshots top-level fields, runs `mutate`, and on throw restores the snapshot and sets `error`. Used for risky async paths (e.g. Casa service requests). Prefs validate **before** `set` via `safeParsePrefsPatch` — invalid patches never mutate prefs.

## Coverage exclusions

Line-level coverage gates target `middleware.ts`, `validators.ts`, UI/prefs slices, and critical transitions. Full I/O paths in `sessionSlice` (mic, TTS WAV playback, SSE bootstrap) and Casa HA fetch fan-out are exercised selectively with mocks; 100% line coverage of those branches is out of scope for this layer.

## Compatibility

Keep exporting `useAppStore` and `Message` from `@/state/store` so AppShell, chat, Storybook, and tests do not need import churn.
