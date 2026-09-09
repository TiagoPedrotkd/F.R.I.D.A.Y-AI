import {
  AlertsResponseSchema,
  ConfirmResponseSchema,
  FeedbackResponseSchema,
  type AlertsResponse,
  type ConfirmResponse,
  type FeedbackResponse,
} from '../schemas'
import { defineEndpoint, defineParamEndpoint } from './types'

export type { AlertsResponse, ConfirmResponse, FeedbackResponse }

export type ConfirmParams = {
  sessionId: string
  decision: 'confirm' | 'cancel'
}

export const confirm = defineParamEndpoint<ConfirmParams, ConfirmResponse>({
  method: 'POST',
  path: () => '/v1/confirm',
  body: ({ sessionId, decision }) => ({ session_id: sessionId, decision }),
  schema: ConfirmResponseSchema,
  timeoutMs: 15_000,
  retries: 2,
})

export type FeedbackParams = {
  session_id: string
  message_id?: string
  rating: 'up' | 'down'
  reply_text?: string
  user_text?: string
  comment?: string
  grounding_score?: number | null
}

export const sendFeedback = defineParamEndpoint<FeedbackParams, FeedbackResponse>({
  method: 'POST',
  path: () => '/v1/feedback',
  body: (payload) => payload,
  schema: FeedbackResponseSchema,
  timeoutMs: 10_000,
  retries: 2,
})

export const fetchAlerts = defineEndpoint<AlertsResponse>({
  method: 'GET',
  path: '/v1/alerts',
  schema: AlertsResponseSchema,
  timeoutMs: 20_000,
  retries: 2,
})
