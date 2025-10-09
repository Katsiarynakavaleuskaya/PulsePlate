import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    env: {
      VITE_API_BASE: 'http://localhost:3000',
      VITE_APP_TITLE: 'PulsePlate',
    },
    coverage: {
      provider: 'v8',
      reportsDirectory: './coverage',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['**/*.stories.*', '**/*.mdx', 'src/**/__tests__/**/utils.*'],
      lines: 70,
      functions: 70,
      branches: 60,
      statements: 70,
    },
  },
});
