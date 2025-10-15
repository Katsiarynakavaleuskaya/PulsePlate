import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{js,ts,jsx,tsx}', 'src/**/__tests__/*.{js,ts,jsx,tsx}'],
    globals: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov', 'json'],
      reportsDirectory: 'coverage',
      all: true,
      thresholds: {
        lines: 97,
        functions: 97,
        branches: 97,
        statements: 97
      },
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'node_modules/',
        'dist/',
        '**/*.config.{js,ts}',
        '**/*.test.{js,ts,jsx,tsx}',
        '**/*.spec.{js,ts,jsx,tsx}',
        '**/__tests__/**',
        '**/types/**'
      ]
    }
  }
})
