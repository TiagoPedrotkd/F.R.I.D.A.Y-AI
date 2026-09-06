import { reportApiError } from './report'

export type RequestContext = {
  path: string
  method: string
  headers: Record<string, string>
  body?: unknown
  /** Absolute URL after resolve */
  url: string
}

export type ResponseContext = {
  request: RequestContext
  status: number
  headers: Headers
  /** Parsed JSON body (or null) before Zod */
  data: unknown
}

export type RequestInterceptor = (ctx: RequestContext) => RequestContext | Promise<RequestContext>

export type ResponseInterceptor = (
  ctx: ResponseContext,
) => ResponseContext | Promise<ResponseContext>

export type ErrorInterceptor = (err: unknown, ctx: RequestContext) => unknown | Promise<unknown>

/** DEV console + optional store surface when notify path uses reportApiError. */
export const loggingErrorInterceptor: ErrorInterceptor = async (err, ctx) => {
  if (import.meta.env.DEV) {
    console.warn('[friday/http]', { path: ctx.path, method: ctx.method, err })
  }
  return err
}

/** Surfaces final failures via reportApiError (ErrorNotice). Call only when notify=true. */
export function notifyErrorInterceptor(err: unknown, ctx: RequestContext): unknown {
  reportApiError(err, { path: ctx.path, method: ctx.method })
  return err
}
