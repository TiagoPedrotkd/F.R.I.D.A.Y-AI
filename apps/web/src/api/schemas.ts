import { z } from 'zod'

/** Shared fragments used by chat + finance schemas. */

export const ActivityStepSchema = z
  .object({
    label: z.string(),
    status: z.string(),
    tool: z.string().optional(),
    monitor: z.string().optional(),
  })
  .passthrough()

export type ActivityStep = z.infer<typeof ActivityStepSchema>

export const SourceItemSchema = z
  .object({
    title: z.string(),
    url: z.string(),
    snippet: z.string().optional(),
    source: z.string().optional(),
    date: z.string().nullable().optional(),
    kind: z.string().nullable().optional(),
  })
  .passthrough()

export type SourceItem = z.infer<typeof SourceItemSchema>

export const PendingConfirmationSchema = z
  .object({
    action: z.string(),
    target: z.string(),
    summary: z.string(),
    consequences: z.string().optional(),
    preview: z.record(z.string(), z.unknown()).optional(),
  })
  .passthrough()

export const StatusResponseSchema = z
  .object({
    status: z.string(),
    backend: z.boolean(),
    demo: z.boolean(),
    llm: z
      .object({
        ok: z.boolean(),
        model: z.string().optional(),
        error: z.string().nullable().optional(),
      })
      .passthrough(),
    ha: z
      .object({
        enabled: z.boolean(),
        ok: z.boolean().nullable().optional(),
        url: z.string().nullable().optional(),
      })
      .passthrough()
      .optional(),
    google: z
      .object({
        enabled: z.boolean(),
        configured: z.boolean().optional(),
      })
      .passthrough()
      .optional(),
    finance: z
      .object({
        enabled: z.boolean(),
        configured: z.boolean(),
      })
      .passthrough()
      .optional(),
    auto_open_monitors: z.boolean().optional(),
  })
  .passthrough()

export type StatusResponse = z.infer<typeof StatusResponseSchema>

export const ChatResponseSchema = z
  .object({
    reply: z.string(),
    metadata: z.record(z.string(), z.unknown()).default({}),
    activity: z.array(ActivityStepSchema).default([]),
    ui: z
      .object({
        sources: z.array(SourceItemSchema).optional(),
        headlines_only: z.boolean().optional(),
        not_realtime_prices: z.boolean().optional(),
        country: z.string().optional(),
        kind: z.string().optional(),
        opened: z.boolean().optional(),
        monitor_kind: z.string().nullable().optional(),
        offer_monitor: z.boolean().optional(),
        monitor_path: z.string().nullable().optional(),
        grounding_score: z.number().nullable().optional(),
        grounded: z.boolean().optional(),
        confidence_score: z.number().nullable().optional(),
        confidence_level: z.string().nullable().optional(),
        hallucination_risk: z.string().nullable().optional(),
      })
      .passthrough()
      .default({}),
    session: z
      .object({
        last_country: z.string().nullable().optional(),
        last_news_context: z.string().nullable().optional(),
        last_language: z.string().optional(),
      })
      .passthrough()
      .optional(),
    pending_confirmation: PendingConfirmationSchema.nullable().optional(),
    grounding: z
      .object({
        score: z.number().optional(),
        grounded: z.boolean().optional(),
      })
      .passthrough()
      .optional(),
    confidence: z
      .object({
        score: z.number().optional(),
        level: z.string().optional(),
        hallucination_risk: z.string().optional(),
      })
      .passthrough()
      .optional(),
    error: z.string().optional(),
  })
  .passthrough()

export type ChatResponse = z.infer<typeof ChatResponseSchema>

export const FinanceLedgerTxSchema = z
  .object({
    id: z.string(),
    date: z.string().optional(),
    amount: z.number().optional(),
    category: z.string().optional(),
    note: z.string().optional(),
    invoice_id: z.string().nullable().optional(),
    source: z.string().optional(),
  })
  .passthrough()

export type FinanceLedgerTx = z.infer<typeof FinanceLedgerTxSchema>

export const FinancePositionSchema = z
  .object({
    id: z.string().optional(),
    symbol: z.string(),
    qty: z.number(),
    avg_cost: z.number().nullable().optional(),
    currency: z.string().optional(),
  })
  .passthrough()

export type FinancePosition = z.infer<typeof FinancePositionSchema>

export const FinanceSummarySchema = z
  .object({
    ok: z.boolean(),
    year: z.number(),
    month: z.number(),
    currency: z.string(),
    salary_monthly: z.number().nullable().optional(),
    income_extra: z.number(),
    expenses: z.number(),
    recurring_imputed: z.number(),
    remaining: z.number(),
    transactions_count: z.number(),
    transactions: z.array(FinanceLedgerTxSchema).default([]),
    recurring_breakdown: z
      .array(
        z
          .object({
            name: z.string().optional(),
            monthly_imputed: z.number().optional(),
            cadence: z.string().optional(),
          })
          .passthrough(),
      )
      .optional(),
    investments: z
      .object({
        brokers: z
          .record(
            z.string(),
            z
              .object({
                positions_count: z.number().optional(),
                cost_basis_approx: z.number().optional(),
                positions: z.array(FinancePositionSchema).optional(),
              })
              .passthrough(),
          )
          .optional(),
      })
      .passthrough()
      .optional(),
  })
  .passthrough()

export type FinanceSummary = z.infer<typeof FinanceSummarySchema>

/** Session bootstrap + list. */
export const CreateSessionResponseSchema = z
  .object({
    id: z.string(),
  })
  .passthrough()

export type CreateSessionResponse = z.infer<typeof CreateSessionResponseSchema>

export const SessionListItemSchema = z
  .object({
    id: z.string(),
    updated_at: z.number().optional(),
    message_count: z.number().optional(),
    preview: z.string().optional(),
    last_country: z.string().nullable().optional(),
    last_language: z.string().optional(),
  })
  .passthrough()

export const ListSessionsResponseSchema = z
  .object({
    sessions: z.array(SessionListItemSchema),
  })
  .passthrough()

export type ListSessionsResponse = z.infer<typeof ListSessionsResponseSchema>

export const GetSessionResponseSchema = z
  .object({
    id: z.string(),
    messages: z.array(
      z
        .object({
          role: z.string(),
          content: z.string(),
        })
        .passthrough(),
    ),
    session_summary: z.string().optional(),
    last_country: z.string().nullable().optional(),
    last_language: z.string().optional(),
  })
  .passthrough()

export type GetSessionResponse = z.infer<typeof GetSessionResponseSchema>

export const PrefsResponseSchema = z
  .object({
    prefs: z.record(z.string(), z.unknown()),
    prompt_version: z.string().optional(),
  })
  .passthrough()

export type PrefsResponse = z.infer<typeof PrefsResponseSchema>

export const SavePrefsResponseSchema = z
  .object({
    prefs: z.record(z.string(), z.unknown()),
  })
  .passthrough()

export type SavePrefsResponse = z.infer<typeof SavePrefsResponseSchema>

export const ConfirmResponseSchema = z
  .object({
    reply: z.string(),
    decision: z.string(),
  })
  .passthrough()

export type ConfirmResponse = z.infer<typeof ConfirmResponseSchema>

export const FeedbackResponseSchema = z
  .object({
    ok: z.boolean(),
  })
  .passthrough()

export type FeedbackResponse = z.infer<typeof FeedbackResponseSchema>

export const FridayAlertSchema = z
  .object({
    severity: z.string(),
    kind: z.string(),
    message: z.string(),
    cta: z.string().optional(),
  })
  .passthrough()

export type FridayAlertDto = z.infer<typeof FridayAlertSchema>

export const AlertsResponseSchema = z
  .object({
    alerts: z.array(FridayAlertSchema),
    context_time: z.string().optional(),
  })
  .passthrough()

export type AlertsResponse = z.infer<typeof AlertsResponseSchema>
