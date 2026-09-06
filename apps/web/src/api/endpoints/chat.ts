import { ChatResponseSchema, type ChatResponse } from '../schemas'
import { defineParamEndpoint } from './types'

export type { ChatResponse }

export type ChatParams = {
  sessionId: string
  text: string
}

export const chat = defineParamEndpoint<ChatParams, ChatResponse>({
  method: 'POST',
  path: () => '/v1/chat',
  body: ({ sessionId, text }) => ({ session_id: sessionId, text }),
  schema: ChatResponseSchema,
  timeoutMs: 120_000,
  retries: 2,
})
