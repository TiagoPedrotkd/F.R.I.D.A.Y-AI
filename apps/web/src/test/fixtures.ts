import { defaultPrefs, type Prefs } from '@/demo/fixtures'
import type { ChatResponse, FinanceSummary, StatusResponse } from '@/api/schemas'
import type { Message } from '@/state/store'

/** Stable message builder for UI / store tests (fixed ids). */
export function makeMessage(overrides: Partial<Message> & Pick<Message, 'role' | 'text'>): Message {
  return {
    id: overrides.id ?? 'msg-1',
    role: overrides.role,
    text: overrides.text,
    demo: overrides.demo,
    sources: overrides.sources,
    groundingScore: overrides.groundingScore,
    confidenceScore: overrides.confidenceScore,
    confidenceLevel: overrides.confidenceLevel,
    hallucinationRisk: overrides.hallucinationRisk,
    feedback: overrides.feedback ?? null,
  }
}

export const prefsPt: Prefs = {
  ...defaultPrefs,
  language: 'pt',
  ttsEnabled: false,
  autoplay: false,
  demoMode: false,
}

export const statusOk: StatusResponse = {
  status: 'ok',
  backend: true,
  demo: false,
  llm: { ok: true, model: 'test-model' },
  ha: { enabled: false, ok: null, url: null },
  google: { enabled: false, configured: false },
  finance: { enabled: true, configured: true },
  auto_open_monitors: false,
}

export const statusDemo: StatusResponse = {
  ...statusOk,
  demo: true,
  llm: { ok: false, model: undefined, error: 'offline' },
}

export function chatReplyOk(overrides?: Partial<ChatResponse>): ChatResponse {
  return {
    reply: overrides?.reply ?? 'Resposta de teste da F.R.I.D.A.Y.',
    metadata: overrides?.metadata ?? {},
    activity: overrides?.activity ?? [
      { label: 'A interpretar…', status: 'done' },
      { label: 'Concluído.', status: 'done' },
    ],
    ui: overrides?.ui ?? {},
    session: overrides?.session,
    pending_confirmation: overrides?.pending_confirmation,
    grounding: overrides?.grounding,
    confidence: overrides?.confidence,
    error: overrides?.error,
  }
}

export const financeSummaryOk: FinanceSummary = {
  ok: true,
  year: 2026,
  month: 9,
  currency: 'EUR',
  salary_monthly: 2000,
  income_extra: 0,
  expenses: 400,
  recurring_imputed: 600,
  remaining: 1000,
  transactions_count: 1,
  transactions: [{ id: 'tx-1', date: '2026-09-01', amount: -40, category: 'food', note: 'Café' }],
  recurring_breakdown: [{ name: 'Renda', monthly_imputed: 600, cadence: 'monthly' }],
}
