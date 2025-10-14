import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{js,ts,jsx,tsx}', 'src/**/__tests__/*.{js,ts,jsx,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov', 'json'],
      reportsDirectory: 'coverage',
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80
      },
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['**/*.test.{ts,tsx}', '**/*.spec.{ts,tsx}', '**/types/**']
    }
  }
})
