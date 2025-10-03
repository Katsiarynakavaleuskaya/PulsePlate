import js from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  {
    ignores: [
      'node_modules/**',
      'dist/**',
      'public/**',
      '**/*.d.ts',
      '**/mockServiceWorker.js'
    ]
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
        HTMLElement: 'readonly',
        Element: 'readonly',
        Node: 'readonly',
        MutationObserver: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        location: 'readonly',
        navigator: 'readonly',
        fetch: 'readonly',
        FormData: 'readonly',
        Blob: 'readonly',
        File: 'readonly',
        DOMException: 'readonly',
        reportError: 'readonly',
        __REACT_DEVTOOLS_GLOBAL_HOOK__: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
        crypto: 'readonly',
        IntersectionObserver: 'readonly',
        ResizeObserver: 'readonly'
      }
    },
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
      'no-console': process.env.NODE_ENV === 'production' ? ['error', { allow: ['warn', 'error'] }] : 'off', // Allow console.log for development
      'no-empty': 'warn',
      'no-constant-condition': 'warn',
      'no-cond-assign': 'warn',
      'no-func-assign': 'warn',
      'no-prototype-builtins': 'warn',
      '@typescript-eslint/no-this-alias': 'warn'
    },
  },
  {
    files: ['src/**/*.test.{ts,tsx}', 'src/**/__tests__/**/*.{ts,tsx}'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off', // Allow any in tests
      '@typescript-eslint/no-unused-vars': 'off' // Allow unused vars in tests
    },
  }
);
