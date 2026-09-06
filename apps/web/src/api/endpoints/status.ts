import { StatusResponseSchema, type StatusResponse } from '../schemas'
import { defineEndpoint } from './types'

export type { StatusResponse }

export const fetchStatus = defineEndpoint({
  method: 'GET',
  path: '/v1/status',
  schema: StatusResponseSchema,
  timeoutMs: 15_000,
  retries: 3,
})
