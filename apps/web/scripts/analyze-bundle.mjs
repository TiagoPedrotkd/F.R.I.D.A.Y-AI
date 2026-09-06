#!/usr/bin/env node
/**
 * Analyze Vite dist/ assets: raw + gzip sizes vs performance-budget.json.
 * Usage: node scripts/analyze-bundle.mjs
 *        (expects dist/ from `vite build`)
 */
import { gzip as gzipCb } from 'node:zlib'
import { promisify } from 'node:util'
import { readdir, readFile, mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const gzipAsync = promisify(gzipCb)
const root = path.dirname(fileURLToPath(import.meta.url))
const webRoot = path.resolve(root, '..')
const distAssets = path.join(webRoot, 'dist', 'assets')
const budgetPath = path.join(webRoot, 'docs', 'performance-budget.json')
const outDir = path.join(webRoot, 'docs', 'benchmarks')
const outJson = path.join(outDir, 'bundle-latest.json')

function kb(bytes) {
  return Math.round((bytes / 1024) * 10) / 10
}

async function gzipSize(buf) {
  const gz = await gzipAsync(buf)
  return gz.length
}

function isEntryJs(name) {
  // Vite entry after manualChunks: typically index-*.js (not vendor-*)
  return /^index-.*\.js$/.test(name)
}

function isVendorReact(name) {
  return /vendor-react.*\.js$/.test(name) || /^react-.*\.js$/.test(name)
}

function isLazyPanel(name) {
  return /Financas|Settings|Casa|Saude|Agenda|Mail/i.test(name)
}

async function main() {
  let budget
  try {
    budget = JSON.parse(await readFile(budgetPath, 'utf8'))
  } catch {
    console.error('Missing docs/performance-budget.json')
    process.exit(1)
  }

  let files
  try {
    files = await readdir(distAssets)
  } catch {
    console.error('No dist/assets — run `npm run build` or `npm run build:analyze` first.')
    process.exit(1)
  }

  const assets = []
  for (const name of files) {
    if (!/\.(js|css)$/.test(name)) continue
    const full = path.join(distAssets, name)
    const buf = await readFile(full)
    const raw = buf.length
    const gzip = await gzipSize(buf)
    assets.push({ name, type: name.endsWith('.css') ? 'css' : 'js', raw, gzip, rawKb: kb(raw), gzipKb: kb(gzip) })
  }
  assets.sort((a, b) => b.gzip - a.gzip)

  console.log('\nBundle analysis (dist/assets)\n')
  console.log('File'.padEnd(48), 'raw KB'.padStart(8), 'gzip KB'.padStart(10))
  console.log('-'.repeat(68))
  for (const a of assets) {
    console.log(a.name.padEnd(48), String(a.rawKb).padStart(8), String(a.gzipKb).padStart(10))
  }

  const entry = assets.filter((a) => a.type === 'js' && isEntryJs(a.name))
  const vendorReact = assets.filter((a) => a.type === 'js' && isVendorReact(a.name))
  const css = assets.filter((a) => a.type === 'css')
  const lazyPanels = assets.filter((a) => a.type === 'js' && isLazyPanel(a.name))

  // Initial = entry + vendor-react + css (all JS that loads on first paint without lazy)
  // Also include other non-lazy JS chunks that are imported by entry (e.g. vendor shared)
  const lazyNames = new Set(lazyPanels.map((a) => a.name))
  const initialJs = assets.filter((a) => a.type === 'js' && !lazyNames.has(a.name))
  const entryGzip = entry.reduce((s, a) => s + a.gzip, 0)
  const vendorGzip = vendorReact.reduce((s, a) => s + a.gzip, 0)
  const cssGzip = css.reduce((s, a) => s + a.gzip, 0)
  const initialGzip = initialJs.reduce((s, a) => s + a.gzip, 0) + cssGzip

  const limits = budget.gzip
  const report = {
    generatedAt: new Date().toISOString(),
    assets,
    summary: {
      entryJsGzipKb: kb(entryGzip),
      vendorReactGzipKb: kb(vendorGzip),
      cssTotalGzipKb: kb(cssGzip),
      initialJsCssGzipKb: kb(initialGzip),
      lazyPanelChunks: lazyPanels.map((a) => ({ name: a.name, gzipKb: a.gzipKb })),
    },
    budget: limits,
    violations: [],
  }

  if (kb(entryGzip) > limits.entryJsMaxKb) {
    report.violations.push(`entry JS gzip ${kb(entryGzip)}KB > ${limits.entryJsMaxKb}KB`)
  }
  if (vendorReact.length && kb(vendorGzip) > limits.vendorReactMaxKb) {
    report.violations.push(`vendor-react gzip ${kb(vendorGzip)}KB > ${limits.vendorReactMaxKb}KB`)
  }
  if (kb(cssGzip) > limits.cssTotalMaxKb) {
    report.violations.push(`CSS gzip ${kb(cssGzip)}KB > ${limits.cssTotalMaxKb}KB`)
  }
  if (kb(initialGzip) > limits.initialJsCssMaxKb) {
    report.violations.push(`initial JS+CSS gzip ${kb(initialGzip)}KB > ${limits.initialJsCssMaxKb}KB`)
  }
  for (const p of lazyPanels) {
    if (p.gzipKb > limits.lazyPanelChunkMaxKb) {
      report.violations.push(`lazy ${p.name} gzip ${p.gzipKb}KB > ${limits.lazyPanelChunkMaxKb}KB`)
    }
  }

  console.log('\nSummary')
  console.log(`  Entry JS (index-*.js) gzip: ${report.summary.entryJsGzipKb} KB (max ${limits.entryJsMaxKb})`)
  console.log(`  vendor-react gzip:          ${report.summary.vendorReactGzipKb} KB (max ${limits.vendorReactMaxKb})`)
  console.log(`  CSS total gzip:             ${report.summary.cssTotalGzipKb} KB (max ${limits.cssTotalMaxKb})`)
  console.log(`  Initial JS+CSS gzip:        ${report.summary.initialJsCssGzipKb} KB (max ${limits.initialJsCssMaxKb})`)

  await mkdir(outDir, { recursive: true })
  await writeFile(outJson, JSON.stringify(report, null, 2))
  console.log(`\nWrote ${path.relative(webRoot, outJson)}`)

  if (report.violations.length) {
    console.error('\nBudget violations:')
    for (const v of report.violations) console.error('  -', v)
    process.exit(1)
  }
  console.log('\nBudget OK.\n')
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
