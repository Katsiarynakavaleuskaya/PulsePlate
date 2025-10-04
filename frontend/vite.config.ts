import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["src/setupTests.ts"],
    globals: true,
    testTimeout: 15000,
    hookTimeout: 10000,
    teardownTimeout: 5000,
  },
});
