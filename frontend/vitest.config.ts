import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    env: {
      VITE_API_BASE: 'http://localhost:8000/api/v1',
      VITE_API_KEY: 'test_key',
      VITE_DEV_MODE: 'true',
      VITE_ANALYTICS_ENABLED: 'false',
    },
    include: ['src/**/*.test.{js,ts,jsx,tsx}', 'src/**/__tests__/*.{js,ts,jsx,tsx}'],
    globals: true,
    coverage: {
      provider: 'v8',
      reporters: ['text', 'lcov', 'json'],
      reportsDirectory: 'coverage',
      all: true,
      thresholds: {
        lines: 52,
        functions: 71,
        branches: 76,
        statements: 52,
      },
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'node_modules/',
        'dist/',
        '**/*.config.{js,ts}',
        '**/*.test.{js,ts,jsx,tsx}',
        '**/*.spec.{js,ts,jsx,tsx}',
        '**/__tests__/**',
        '**/types/**',
      ],
    },
  },
});
