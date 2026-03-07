import { expect, beforeAll, afterEach, afterAll, vi } from "vitest";
import * as matchers from "@testing-library/jest-dom/matchers";
import { toHaveNoViolations } from "jest-axe";
import { cleanup } from "@testing-library/react";
import { server } from "../mocks/server";

// Mock window.location.replace globally to prevent jsdom errors
Object.defineProperty(window, 'location', {
  value: {
    ...window.location,
    replace: vi.fn(),
    assign: vi.fn(),
    reload: vi.fn(),
  },
  writable: true,
});

// Extend Vitest expect with jest-dom matchers
expect.extend(matchers);

// Extend Vitest expect with jest-axe matchers
expect.extend(toHaveNoViolations);

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
  cleanup(); // Global cleanup after each test
});

// Clean up after all tests
afterAll(() => {
  if (server?.close) {
    server.close();
  }
});
