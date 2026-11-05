import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command, mode, isPreview }) => ({
  plugins: [react()],
  ...(command === "serve" && mode === "remote" && !isPreview
    ? {
        server: {
          proxy: {
            "^/api/v1(?:[/?]|$)": {
              target: "http://127.0.0.1:8001",
            },
          },
        },
      }
    : {}),
  test: {
    environment: "jsdom",
    setupFiles: ["src/setupTests.ts"],
    globals: true,
    testTimeout: 30000,
    hookTimeout: 10000,
    teardownTimeout: 5000,
    reporters: ["default", ["junit", { outputFile: "test-results/junit.xml" }]],
  },
}));
