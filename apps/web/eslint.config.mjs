import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import eslintConfigPrettier from 'eslint-config-prettier'

/**
 * FRIDAY web ESLint (flat config).
 * Each rule includes a short “why” so new contributors learn the quirk, not just the error.
 */
export default tseslint.config(
  {
    ignores: [
      'dist/**',
      'storybook-static/**',
      'coverage/**',
      'lhci-reports/**',
      'node_modules/**',
      '**/*.config.js',
      '**/*.config.ts',
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      globals: { ...globals.browser, ...globals.es2022 },
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      // Dead code hides bugs and confuses readers — prefix unused args with `_`.
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
      // Prefer real types; `any` is allowed temporarily but surfaces in review.
      '@typescript-eslint/no-explicit-any': 'warn',
      // Hooks must be called unconditionally at the top level (React rules of hooks).
      'react-hooks/rules-of-hooks': 'error',
      // Missing deps often cause stale closures; fix or justify with a comment.
      'react-hooks/exhaustive-deps': 'warn',
      // Fast Refresh only works if files export React components cleanly.
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      // Prefer structured logging; `console.error` is OK for reportApiError paths.
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      // Empty catch blocks hide failures — at least comment why.
      'no-empty': ['error', { allowEmptyCatch: false }],
    },
  },
  // Disable stylistic rules that fight Prettier (run Prettier separately / via lint-staged).
  eslintConfigPrettier,
)
