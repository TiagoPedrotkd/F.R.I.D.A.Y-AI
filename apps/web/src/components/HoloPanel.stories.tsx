import type { Meta, StoryObj } from '@storybook/react'
import { HoloPanel } from '@/components/ui'

const meta: Meta<typeof HoloPanel> = {
  title: 'HUD/HoloPanel',
  component: HoloPanel,
  args: {
    label: 'Comms',
    children: 'Conteúdo do painel holográfico.',
    className: 'max-w-md',
  },
}
export default meta

type Story = StoryObj<typeof HoloPanel>

export const Default: Story = {}
export const Contexto: Story = {
  args: { label: 'Contexto', children: 'Sem país em sessão.' },
}
