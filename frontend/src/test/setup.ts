import { expect, beforeAll, afterEach, afterAll, vi } from "vitest";
import * as matchers from "@testing-library/jest-dom/matchers";
import { toHaveNoViolations } from "jest-axe";
import { cleanup } from "@testing-library/react";
import { server } from "../mocks/server";

function createMemoryStorage(): Storage {
  const storageState = new Map<string, string>();
  const storageShim = {
    clear(): void {
      storageState.clear();
    },
    getItem(key: string): string | null {
      return storageState.get(key) ?? null;
    },
    key(index: number): string | null {
      return Array.from(storageState.keys())[index] ?? null;
    },
    removeItem(key: string): void {
      storageState.delete(key);
    },
    setItem(key: string, value: string): void {
      storageState.set(key, String(value));
    },
  } as Storage;

  Object.defineProperty(storageShim, "length", {
    get: () => storageState.size,
  });

  return storageShim;
}


function ensureStorageApi(name: "localStorage" | "sessionStorage"): void {
  const existingStorage = window[name];
  if (
    existingStorage &&
    typeof existingStorage.clear === "function" &&
    typeof existingStorage.getItem === "function" &&
    typeof existingStorage.key === "function" &&
    typeof existingStorage.removeItem === "function" &&
    typeof existingStorage.setItem === "function"
  ) {
    return;
  }

  const storageShim = createMemoryStorage();
  // RU: Стандартизируем test storage API, если среда отдаёт неполный объект.
  // EN: Stabilize the storage API when the test runtime provides an incomplete object.
  Object.defineProperty(window, name, {
    configurable: true,
    value: storageShim,
    writable: true,
  });
  Object.defineProperty(globalThis, name, {
    configurable: true,
    value: storageShim,
    writable: true,
  });
}


ensureStorageApi("localStorage");
ensureStorageApi("sessionStorage");

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
