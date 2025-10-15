import { expect, beforeAll, afterEach, afterAll } from "vitest";
import * as matchers from "@testing-library/jest-dom/matchers";
import { toHaveNoViolations } from "jest-axe";
import { server } from "../mocks/server";

// Extend Vitest expect with jest-dom matchers
expect.extend(matchers);

// Extend Vitest expect with jest-axe matchers
// Note: jest-axe types are not fully compatible with Vitest, using type assertion
expect.extend({ toHaveNoViolations } as any);

// Start MSW server before all tests
beforeAll(() => {
  if (server?.listen) {
    server.listen({ onUnhandledRequest: "bypass" });
  }
});

// Reset handlers after each test
afterEach(() => {
  if (server?.resetHandlers) {
    server.resetHandlers();
  }
});

// Clean up after all tests
afterAll(() => {
  if (server?.close) {
    server.close();
  }
});
