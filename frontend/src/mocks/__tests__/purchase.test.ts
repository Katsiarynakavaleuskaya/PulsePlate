import { expect, test } from "vitest";
import { handlers } from "../handlers";

test("shared MSW surface does not expose legacy purchase or restore release paths", () => {
  const legacyPaths = new Set(["/api/purchase", "/api/restore"]);
  const runtimePaths = handlers.map((handler) => (handler as { info?: { path?: string } }).info?.path);

  expect(runtimePaths).not.toContain("/api/purchase");
  expect(runtimePaths).not.toContain("/api/restore");
  expect(runtimePaths.some((path) => path !== undefined && legacyPaths.has(path))).toBe(false);
});
