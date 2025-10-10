// For more info, see https://github.com/storybookjs/eslint-plugin-storybook#configuration-flat-config-format
import storybook from "eslint-plugin-storybook";

import js from "@eslint/js";
import tseslint from "typescript-eslint";

const storybookConfigs = (storybook.configs["flat/recommended"] ?? [])
  .map((config) => ({
    ...config,
    files: (config.files ?? []).map((pattern) =>
      pattern.replace("**/", "src/**/"),
    ),
    plugins: {
      ...(config.plugins ?? {}),
      storybook,
    },
    rules: {
      ...(config.rules ?? {}),
      "storybook/no-renderer-packages": "off",
    },
  }))
  .filter((config) => !config.files || config.files.length > 0); // Filter out configs with empty files array

export default tseslint.config(
  {
    ignores: [
      "node_modules/**",
      "dist/**",
      "public/**",
      "coverage/**",
      "storybook-static/**",
      "**/*.d.ts",
      "**/mockServiceWorker.js",
    ],
  },
  {
    files: ["**/*.js"],
    languageOptions: {
      globals: {
        module: "readonly",
        require: "readonly",
        __dirname: "readonly",
        __filename: "readonly",
        process: "readonly",
        console: "readonly",
      },
    },
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        window: "readonly",
        document: "readonly",
        console: "readonly",
        process: "readonly",
        URL: "readonly",
        URLSearchParams: "readonly",
        HTMLElement: "readonly",
        Element: "readonly",
        Node: "readonly",
        MutationObserver: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        location: "readonly",
        navigator: "readonly",
        fetch: "readonly",
        FormData: "readonly",
        Blob: "readonly",
        File: "readonly",
        DOMException: "readonly",
        reportError: "readonly",
        __REACT_DEVTOOLS_GLOBAL_HOOK__: "readonly",
        localStorage: "readonly",
        sessionStorage: "readonly",
        crypto: "readonly",
        IntersectionObserver: "readonly",
        ResizeObserver: "readonly",
      },
    },
    rules: {
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "@typescript-eslint/no-explicit-any": "warn",
      "no-console": "off", // Allow console.log for development - process.env check not reliable in ESLint
      "no-empty": "warn",
      "no-constant-condition": "warn",
      "no-cond-assign": "warn",
      "no-func-assign": "warn",
      "no-prototype-builtins": "warn",
      "@typescript-eslint/no-this-alias": "warn",
    },
  },
  {
    files: ["src/**/*.test.{ts,tsx}", "src/**/__tests__/**/*.{ts,tsx}"],
    languageOptions: {
      globals: {
        describe: "readonly",
        it: "readonly",
        test: "readonly",
        expect: "readonly",
        beforeEach: "readonly",
        afterEach: "readonly",
        beforeAll: "readonly",
        afterAll: "readonly",
        jest: "readonly",
        vi: "readonly",
      },
    },
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unused-vars": "off",
    },
  },
  ...storybookConfigs,
);
