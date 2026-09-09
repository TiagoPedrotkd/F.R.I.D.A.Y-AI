import {
  PrefsResponseSchema,
  SavePrefsResponseSchema,
  type PrefsResponse,
  type SavePrefsResponse,
} from '../schemas'
import { defineEndpoint, defineParamEndpoint } from './types'

export type { PrefsResponse, SavePrefsResponse }

export const fetchPrefs = defineEndpoint<PrefsResponse>({
  method: 'GET',
  path: '/v1/prefs',
  schema: PrefsResponseSchema,
  timeoutMs: 8_000,
  retries: 2,
})

export type SavePrefsParams = { patch: Record<string, unknown> }

export const savePrefs = defineParamEndpoint<SavePrefsParams, SavePrefsResponse>({
  method: 'PUT',
  path: () => '/v1/prefs',
  body: ({ patch }) => patch,
  schema: SavePrefsResponseSchema,
  timeoutMs: 8_000,
  retries: 2,
})
