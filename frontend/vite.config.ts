import { defineConfig } from "vitest/config";
import { codecovVitePlugin } from "@codecov/vite-plugin";
import react from "@vitejs/plugin-react";

const enableCodecovBundleAnalysis =
  process.env.CODECOV_BUNDLE_ANALYSIS === "true";

export default defineConfig({
  plugins: [
    react(),
    codecovVitePlugin({
      bundleName: "pulseplate-frontend",
      enableBundleAnalysis: enableCodecovBundleAnalysis,
      gitService: "github",
      telemetry: false,
    }),
  ],
  test: {
    environment: "jsdom",
    setupFiles: ["src/setupTests.ts"],
    globals: true,
    testTimeout: 30000,
    hookTimeout: 10000,
    teardownTimeout: 5000,
    reporters: ["default", ["junit", { outputFile: "test-results/junit.xml" }]],
  },
});
