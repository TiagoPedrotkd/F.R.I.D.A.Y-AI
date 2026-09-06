import type { Meta, StoryObj } from '@storybook/react'
import { applyTheme, hudButtonVariants } from '@/styles/system'

function ThemeMatrix() {
  const cells: { title: string; apply: () => void }[] = [
    { title: 'Dark', apply: () => applyTheme({ mode: 'dark' }) },
    { title: 'Light', apply: () => applyTheme({ mode: 'light' }) },
    { title: 'Dark + HC', apply: () => applyTheme({ mode: 'dark', highContrast: true }) },
    { title: 'Light + HC', apply: () => applyTheme({ mode: 'light', highContrast: true }) },
  ]

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {cells.map((cell) => (
        <div key={cell.title} className="holo holo-frame space-y-3 p-4">
          <p className="holo-label">{cell.title}</p>
          <button type="button" className={hudButtonVariants.default} onClick={cell.apply}>
            Aplicar {cell.title}
          </button>
          <button type="button" className={hudButtonVariants.primary}>
            Primary
          </button>
          <p className="text-sm text-[var(--text-muted)]">Texto muted · cyan sample</p>
          <p className="text-cyan">Accent cyan</p>
        </div>
      ))}
    </div>
  )
}

const meta: Meta<typeof ThemeMatrix> = {
  title: 'HUD/ThemeMatrix',
  component: ThemeMatrix,
  parameters: {
    docs: {
      description: {
        component:
          'Clica “Aplicar …” para mudar o tema do documento. Usa também a toolbar Theme / Contrast do Storybook.',
      },
    },
  },
}
export default meta

type Story = StoryObj<typeof ThemeMatrix>

export const Matrix: Story = {}
