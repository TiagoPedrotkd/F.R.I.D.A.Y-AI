import type { Meta, StoryObj } from '@storybook/react'
import { ConnectionStatus } from './ConnectionStatus'
import { resetAppStore } from '@/test/mockApi'

const meta: Meta<typeof ConnectionStatus> = {
  title: 'Feedback/ConnectionStatus',
  component: ConnectionStatus,
}
export default meta

type Story = StoryObj<typeof ConnectionStatus>

export const Online: Story = {
  decorators: [
    (Story) => {
      resetAppStore({ backendOk: true, llmOk: true, demoForced: false })
      return <Story />
    },
  ],
}

export const Offline: Story = {
  decorators: [
    (Story) => {
      resetAppStore({ backendOk: false, llmOk: false, demoForced: false })
      return <Story />
    },
  ],
}

export const DemoMode: Story = {
  decorators: [
    (Story) => {
      resetAppStore({ backendOk: false, llmOk: false, demoForced: true })
      return <Story />
    },
  ],
}
