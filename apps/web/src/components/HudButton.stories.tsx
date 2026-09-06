import type { Meta, StoryObj } from '@storybook/react'
import { HudButton } from '@/components/ui'

const meta: Meta<typeof HudButton> = {
  title: 'HUD/HudButton',
  component: HudButton,
  args: { children: 'Acção', variant: 'default', disabled: false },
}
export default meta

type Story = StoryObj<typeof HudButton>

export const Default: Story = {}
export const Primary: Story = { args: { variant: 'primary', children: 'Confirmar' } }
export const Danger: Story = { args: { variant: 'danger', children: 'Apagar' } }
export const Disabled: Story = { args: { disabled: true, children: 'Indisponível' } }

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap gap-3">
      <HudButton variant="default">Default</HudButton>
      <HudButton variant="primary">Primary</HudButton>
      <HudButton variant="danger">Danger</HudButton>
      <HudButton disabled>Disabled</HudButton>
    </div>
  ),
}
