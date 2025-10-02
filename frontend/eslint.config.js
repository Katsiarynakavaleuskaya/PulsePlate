import js from "@eslint/js";
import tseslint from "typescript-eslint";

const baseConfig = {
  ignores: ["dist/**", "frontend/dist/**", "node_modules/**"],
};

const typedConfig = {
  files: ["src/**/*.{ts,tsx}", "vite.config.ts", "tailwind.config.ts"],
  languageOptions: {
    parserOptions: {
      ecmaVersion: 2023,
      sourceType: "module",
      project: ["./tsconfig.json", "./tsconfig.node.json"],
      tsconfigRootDir: import.meta.dirname,
      ecmaFeatures: {
        jsx: true,
      },
    },
  },
  settings: {
    react: {
      version: "detect",
    },
  },
  rules: {
    "react/react-in-jsx-scope": "off",
    "react/jsx-uses-react": "off",
  },
};

export default tseslint.config(baseConfig, js.configs.recommended, ...tseslint.configs.recommended, typedConfig);
