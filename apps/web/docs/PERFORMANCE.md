# Performance — apps/web

Metas: **entry JS gzip &lt; 120 KB**, Lighthouse Performance **&gt; 80**, LCP **&lt; 2.5 s**, INP **&lt; 200 ms** (FID deprecado). Chunks lazy **não** entram no budget de entry.

## Scripts

```bash
npm run build:analyze   # vite build + scripts/analyze-bundle.mjs
npm run analyze         # só analisa dist/ existente
npm run build:stats     # vite build --mode analyze → dist/stats.html (treemap)
npm run lighthouse      # LHCI (preview :4173) — requer build prévio
```

Budget: [`performance-budget.json`](./performance-budget.json)  
Relatórios: [`benchmarks/bundle-baseline.json`](./benchmarks/bundle-baseline.json), [`benchmarks/bundle-latest.json`](./benchmarks/bundle-latest.json)  
LHCI: [`../lighthouserc.json`](../lighthouserc.json)

## Code-splitting com React.lazy

Painéis secundários só carregam no primeiro open:

```tsx
const FinancasPanel = lazy(() =>
  import('./FinancasPanel').then((m) => ({ default: m.FinancasPanel })),
)

function LazyPanel({ open, children }: { open: boolean; children: ReactNode }) {
  if (!open) return null
  return <Suspense fallback={<PanelFallback />}>{children}</Suspense>
}

// …
<LazyPanel open={financasOpen}>
  <FinancasPanel onClose={() => setFinancasOpen(false)} />
</LazyPanel>
```

**Eager (LCP):** `FridayCore`, `ConversationPanel`, `VoiceControls`, banners, `ConfirmationDialog`.  
**Lazy:** Settings, Casa, Saúde, Finanças, Agenda, Mail.

`manualChunks` em `vite.config.ts`: `vendor-react` = `react` + `react-dom`.

## Checklist SVG (FridayCore)

- [x] 72 `<line>` → 2 `<path>` pré-computados (`TICK_PATHS`)
- [x] `feGaussianBlur` desligado com `reducedMotion`; blur menor em idle
- [x] Spins CSS; `will-change: transform` só em estados intensos
- [x] `memo(FridayCore)`
- [x] FridayCore **não** é lazy (herói visual / LCP)

## Performance budget (gzip)

| Asset | Max |
|-------|-----|
| Entry JS (`index-*.js`) | 120 KB |
| `vendor-react-*.js` | 70 KB |
| CSS total | 40 KB |
| Lazy panel (cada) | 40 KB |
| Initial JS+CSS | 150 KB |

`analyze-bundle.mjs` falha (exit 1) se violar.

## Benchmark before / after

Medido com `npm run build:analyze` (manualChunks já activos no baseline; after = + lazy panels + SVG).

| Métrica | Baseline | After | Δ |
|---------|----------|-------|---|
| App `index-*.js` (maior) gzip | 49.5 KB | 45.1 KB | −4.4 KB |
| Entry JS total (`index-*`) gzip | 50.8 KB | 46.4 KB | −4.4 KB |
| vendor-react gzip | 44.7 KB | 44.7 KB | 0 |
| CSS gzip | 6.2 KB | 6.2 KB | 0 |
| Initial JS+CSS gzip | 101.6 KB | 97.2 KB | −4.4 KB |
| Lazy panels | — | 6 chunks (~10 KB gzip total) | off critical path |

**Interpretação:** o budget de 120 KB já era cumprido; o ganho principal é **menos parse/compile no boot** e painéis fora do critical path (Finanças ~2.4 KB gzip só no open).

### Lighthouse (CI)

```bash
npm run build
npm run lighthouse
```

Assertions: Performance ≥ 0.8, LCP ≤ 2500 ms. Relatórios em `lhci-reports/`.

Checklist manual: Performance score, LCP, TBT/INP, CLS.
