import type { Meta, StoryObj } from '@storybook/react'
import { MessageBubble } from '@/features/chat'
import { makeMessage } from '@/test/fixtures'
import { resetAppStore } from '@/test/mockApi'

const meta: Meta<typeof MessageBubble> = {
  title: 'Chat/MessageBubble',
  component: MessageBubble,
  decorators: [
    (Story) => {
      resetAppStore({
        messages: [
          makeMessage({ id: 'u1', role: 'user', text: 'Olá' }),
          makeMessage({ id: 'a1', role: 'assistant', text: 'Resposta' }),
        ],
      })
      return <Story />
    },
  ],
}
export default meta

type Story = StoryObj<typeof MessageBubble>

export const User: Story = {
  args: { message: makeMessage({ id: 'u1', role: 'user', text: 'Que horas são?' }) },
}

export const Assistant: Story = {
  args: {
    message: makeMessage({
      id: 'a1',
      role: 'assistant',
      text: 'São quinze horas.',
      groundingScore: 0.9,
      confidenceScore: 0.85,
      confidenceLevel: 'high',
    }),
  },
}

export const System: Story = {
  args: {
    message: makeMessage({ id: 's1', role: 'system', text: 'Sessão restaurada.' }),
  },
}

export const Demo: Story = {
  args: {
    message: makeMessage({
      id: 'd1',
      role: 'assistant',
      text: '[DEMO] Resposta simulada.',
      demo: true,
    }),
  },
}
