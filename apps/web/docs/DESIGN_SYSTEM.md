# Design system — F.R.I.D.A.Y. HUD

Documentação do visual system da app web (`apps/web`).  
**Fonte de verdade visual:** [`src/styles/tokens.css`](../src/styles/tokens.css)  
**Tokens tipados:** [`src/styles/system.ts`](../src/styles/system.ts)  
**Catálogo de componentes:** [`COMPONENTS.md`](./COMPONENTS.md)  
**Template novo componente:** [`COMPONENT_TEMPLATE.md`](./COMPONENT_TEMPLATE.md)

## 1. Princípios

1. **Uma composição** — o ecrã principal é um HUD, não um dashboard de cards.
2. **Vidro + ciano** — painéis `.holo` / `.holo-frame`; acento `--color-cyan` e bloom.
3. **Tipografia display** — Rajdhani para labels/títulos (`font-display`); corpo Source Sans 3.
4. **Cards só para interacção** — se remover borda/fundo não muda a compreensão, não é card.
5. **Motion com respeito** — animações CSS; honrar `prefers-reduced-motion` e `.reduce-motion`.
6. **Tokens via CSS vars** — nunca hardcode hex em componentes novos; usa `var(--…)` ou Tailwind (`text-cyan`, `bg-night-900`).

## 2. Tokens

### Cores (dark de referência)

| Token | CSS var | Hex dark |
|-------|---------|----------|
| Night 950 | `--color-night-950` | `#000208` |
| Night 900 | `--color-night-900` | `#040a14` |
| Cyan | `--color-cyan` | `#5cefff` |
| Electric | `--color-electric` | `#4aa3ff` |
| Amber | `--color-amber` | `#ffb020` |
| Danger | `--color-danger` | `#ff4d6a` |
| Text primary | `--text-primary` | `#e8fbff` |
| Text muted | `--text-muted` | `#6eb8c9` |

Light e high-contrast **remapeiam as mesmas vars** em `tokens.css` (`:root[data-theme='light']`, `.high-contrast`).

Em TypeScript:

```ts
import { colors, cssVar } from '@/styles/system'

style={{ color: cssVar(colors.cyan.css) }}
// ou Tailwind: className="text-cyan"
```

### Tipografia

| Uso | Família | Tracking tipico |
|-----|---------|-----------------|
| Labels HUD / botões | `font-display` (Rajdhani) | `0.14em`–`0.35em`, uppercase |
| Corpo | `font-body` / default | normal |
| `.holo-label` | display | tracking largo, cyan dim |

### Spacing

Escala Tailwind usual (`p-2` … `p-8`). Preferir `gap-2`/`gap-3` em stacks HUD. Ver `spacing` em `system.ts`.

### Motion & shadows

- `--motion`: `320ms` (ou `0ms` com reduced motion)
- `--bloom`: glow ciano nos hovers de botão
- Classes: `.hud-spin`, `.hud-breathe`, `.hud-pulse`, `.hud-typing`

## 3. Padrões UI

### Botões

```html
<button type="button" class="hud-btn">Default</button>
<button type="button" class="hud-btn hud-btn-primary">Primary</button>
<button type="button" class="hud-btn hud-btn-danger">Danger</button>
<button type="button" class="hud-btn" disabled>Disabled</button>
```

Variants tipadas: `hudButtonVariants` em `system.ts`.

### Painel holográfico

```html
<section class="holo holo-frame p-3">
  <p class="holo-label">Comms</p>
  <!-- conteúdo -->
</section>
```

### State chip

```html
<div class="hud-state-chip" data-busy="true" role="status">
  <span class="hud-state-dot hud-pulse" aria-hidden></span>
  A pensar…
</div>
```

Variants: `data-busy`, `data-alert`, `data-error`.

### Viewport

Raiz da app: `.hud-viewport` > `.hud-stage`. Grelha e vignette vêm de pseudo-elementos CSS.

## 4. Theming (dark / light / high-contrast)

| Modo | Como activar |
|------|----------------|
| **Dark** (default) | Sem `data-theme`, ou remover `dataset.theme` |
| **Light** | `document.documentElement.dataset.theme = 'light'` |
| **High contrast** | `classList.add('high-contrast')` no `<html>` |
| **Reduced motion** | `classList.add('reduce-motion')` + CSS `@media (prefers-reduced-motion)` |

Helper:

```ts
import { applyTheme } from '@/styles/system'

applyTheme({ mode: 'light', highContrast: true, reducedMotion: false })
```

Na app real, Settings / `applyPrefsDom` no store faz o mesmo via prefs (`theme`, `highContrast`, `reducedMotion`).

**Não** duplicates palettes em TS para light — o CSS já redefine as vars.

## 5. Storybook

```bash
cd apps/web
npm run storybook        # http://127.0.0.1:6006
npm run build-storybook  # static build
```

Toolbar: tema Dark / Light e High contrast.  
Stories cobrem padrões HUD + componentes representativos (ver `*.stories.tsx`).

## 6. Novo componente

Segue [`COMPONENT_TEMPLATE.md`](./COMPONENT_TEMPLATE.md), actualiza [`COMPONENTS.md`](./COMPONENTS.md), e se for primitivo partilhável considera `src/ui/` (ver [`FOLDER_STRUCTURE.md`](./FOLDER_STRUCTURE.md)).

## 7. Actualizar o design

1. Alterar vars em `tokens.css` (dark + light + HC).
2. Sincronizar hex de referência em `system.ts` se necessário.
3. Verificar Storybook ThemeMatrix.
4. Correr `npm test` + smoke visual.
