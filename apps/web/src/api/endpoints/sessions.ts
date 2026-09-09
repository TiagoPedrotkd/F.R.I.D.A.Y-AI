import {
  CreateSessionResponseSchema,
  GetSessionResponseSchema,
  ListSessionsResponseSchema,
  type CreateSessionResponse,
  type GetSessionResponse,
  type ListSessionsResponse,
} from '../schemas'
import { defineEndpoint, defineParamEndpoint } from './types'

export type { CreateSessionResponse, GetSessionResponse, ListSessionsResponse }

export const createSession = defineEndpoint<CreateSessionResponse>({
  method: 'POST',
  path: '/v1/sessions',
  schema: CreateSessionResponseSchema,
  timeoutMs: 8_000,
  retries: 2,
})

export const listSessions = defineEndpoint<ListSessionsResponse>({
  method: 'GET',
  path: '/v1/sessions',
  schema: ListSessionsResponseSchema,
  timeoutMs: 8_000,
  retries: 2,
})

export type GetSessionParams = { sessionId: string }

export const getSession = defineParamEndpoint<GetSessionParams, GetSessionResponse>({
  method: 'GET',
  path: ({ sessionId }) => `/v1/sessions/${encodeURIComponent(sessionId)}`,
  schema: GetSessionResponseSchema,
  timeoutMs: 8_000,
  retries: 2,
})
