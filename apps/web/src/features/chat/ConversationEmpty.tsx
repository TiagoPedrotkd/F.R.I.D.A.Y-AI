export function ConversationEmpty() {
  return (
    <div className="flex h-full min-h-[88px] flex-col items-center justify-center gap-1.5 text-center">
      <p className="font-display text-sm tracking-[0.2em] text-cyan/85">Aguardando instruções…</p>
      <p className="max-w-xs text-xs leading-relaxed text-[var(--text-muted)]">
        Fala ou escreve. Hora, notícias, pesquisa e mais.
      </p>
      <p className="mt-1 font-display text-[10px] tracking-[0.18em] text-cyan/40">
        Enter envia · Shift+Enter nova linha
      </p>
    </div>
  )
}
