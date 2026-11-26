import { isAbsolute, relative, resolve } from "node:path";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { normalizePath, type Plugin } from "vite";

const tailwindSourceHmr: Plugin = {
  name: "pulseplate:tailwind-source-hmr",
  apply: "serve",
  applyToEnvironment: (environment) => environment.name === "client",
  hotUpdate({ type, file, modules, server }) {
    if (type !== "create") return;

    // Match the TypeScript @source in src/index.css. Vite expands PostCSS
    // directory dependencies to existing files, so a new file has no CSS edge yet.
    const sourceRoot = resolve(server.config.root, "src");
    const source = normalizePath(relative(sourceRoot, file));
    const isTypeScript = source.endsWith(".ts") || source.endsWith(".tsx");
    if (!isTypeScript || source.startsWith("../") || isAbsolute(source)) return;

    const stylesheet = normalizePath(resolve(sourceRoot, "index.css"));
    const styles = this.environment.moduleGraph.getModulesByFile(stylesheet);
    if (!styles?.size) return;

    const affectedModules = modules.concat(Array.from(styles));
    return Array.from(new Set(affectedModules));
  },
};

export default defineConfig({
  plugins: [react(), tailwindSourceHmr],
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
