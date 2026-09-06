import type { Meta, StoryObj } from '@storybook/react'
import { ErrorNotice } from './ErrorNotice'
import { resetAppStore } from '@/test/mockApi'

const meta: Meta<typeof ErrorNotice> = {
  title: 'Feedback/ErrorNotice',
  component: ErrorNotice,
}
export default meta

type Story = StoryObj<typeof ErrorNotice>

export const Hidden: Story = {
  decorators: [
    (Story) => {
      resetAppStore({ error: null })
      return <Story />
    },
  ],
}

export const Visible: Story = {
  decorators: [
    (Story) => {
      resetAppStore({ error: 'API sem resposta (timeout).' })
      return <Story />
    },
  ],
}
