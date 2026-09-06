/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'

export default defineConfig(({ mode }) => {
  const analyze = mode === 'analyze' || process.env.ANALYZE === '1'

  return {
    plugins: [
      react(),
      analyze
        ? visualizer({
            filename: 'dist/stats.html',
            gzipSize: true,
            brotliSize: true,
            open: false,
          })
        : null,
    ].filter(Boolean),
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules/react-dom') || id.includes('node_modules/react/')) {
              return 'vendor-react'
            }
          },
        },
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/v1': 'http://127.0.0.1:8090',
        '/monitors': 'http://127.0.0.1:8090',
        '/health': 'http://127.0.0.1:8090',
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
      globals: true,
      coverage: {
        provider: 'v8',
        reporter: ['text', 'html', 'lcov'],
        include: [
          'src/state/machine.ts',
          'src/state/middleware.ts',
          'src/state/validators.ts',
          'src/state/selectors.ts',
          'src/state/slices/uiSlice.ts',
          'src/state/slices/prefsSlice.ts',
          'src/features/chat/**',
          'src/features/financas/FinancasSummary.tsx',
          'src/features/financas/Metric.tsx',
          'src/features/financas/format.ts',
          'src/components/FridayCore.tsx',
          'src/components/ErrorBoundary.tsx',
          'src/components/DemoBanner.tsx',
          'src/components/CountryContextChip.tsx',
          'src/components/ConfirmationDialog.tsx',
          'src/components/ConnectionStatus.tsx',
          'src/components/ui/**',
          'src/api/errors.ts',
          'src/api/http.ts',
          'src/api/http-client.ts',
          'src/api/interceptors.ts',
          'src/api/endpoints/**',
          'src/api/schemas.ts',
          'src/api/report.ts',
          'src/hooks/**',
        ],
        exclude: [
          'src/demo/**',
          'src/test/**',
          '**/*.test.ts',
          '**/*.test.tsx',
          '**/*.stories.tsx',
          '**/vite-env.d.ts',
        ],
        thresholds: {
          lines: 60,
          statements: 60,
          functions: 50,
          branches: 50,
        },
      },
    },
  }
})
