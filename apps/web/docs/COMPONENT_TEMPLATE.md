# Template — novo componente HUD

Checklist antes de abrir PR:

- [ ] Usa tokens CSS / Tailwind (`text-cyan`, `var(--text-muted)`), sem hex soltos
- [ ] Variants documentadas (classes ou props)
- [ ] Estados disabled / loading / error se aplicável
- [ ] A11y: `role`, labels, foco teclado
- [ ] Entrada em [`COMPONENTS.md`](./COMPONENTS.md)
- [ ] Story CSF3 se for primitivo ou padrão reutilizável
- [ ] Teste RTL mínimo se lógica não trivial
- [ ] LOC ≤ 120 ideal; partir se > 200 ([FOLDER_STRUCTURE](./FOLDER_STRUCTURE.md))

## Esqueleto TSX

```tsx
// src/components/ExampleWidget.tsx
type ExampleWidgetProps = {
  label: string
  variant?: 'default' | 'alert'
  disabled?: boolean
}

export function ExampleWidget({ label, variant = 'default', disabled }: ExampleWidgetProps) {
  return (
    <div
      className={`holo holo-frame p-3 ${variant === 'alert' ? 'border-amber/40' : ''}`}
      aria-disabled={disabled || undefined}
    >
      <p className="holo-label">{label}</p>
      <button type="button" className="hud-btn mt-2" disabled={disabled}>
        Acção
      </button>
    </div>
  )
}
```

## Story CSF3

```tsx
// src/components/ExampleWidget.stories.tsx
import type { Meta, StoryObj } from '@storybook/react'
import { ExampleWidget } from './ExampleWidget'

const meta: Meta<typeof ExampleWidget> = {
  title: 'HUD/ExampleWidget',
  component: ExampleWidget,
}
export default meta

type Story = StoryObj<typeof ExampleWidget>

export const Default: Story = { args: { label: 'Exemplo' } }
export const Alert: Story = { args: { label: 'Alerta', variant: 'alert' } }
```

## Secção para COMPONENTS.md

```markdown
### ExampleWidget

- **Propósito:** …
- **Props:** `label`, `variant?`, `disabled?`
- **Variants:** default | alert
- **Exemplo:** `<ExampleWidget label="…" />`
- **Deps:** nenhuma / store / api
- **A11y:** …
```
