// RU: Расширяем expect матчерами jest-dom для RTL.
// EN: Extend expect with jest-dom matchers for RTL.
import "@testing-library/jest-dom";
import { afterEach, vi } from "vitest";

// RU: Удаляем существующее неконфигурируемое свойство window.location
// EN: Delete the existing non-configurable window.location property
delete (window as unknown as { location?: unknown }).location;

// RU: Определяем новое конфигурируемое свойство window.location с моковыми значениями
// EN: Define a new configurable window.location property with mock values
Object.defineProperty(window, "location", {
  configurable: true,
  writable: true,
  value: {
    href: "http://localhost:3000/",
    origin: "http://localhost:3000",
    protocol: "http:",
    host: "localhost:3000",
    hostname: "localhost",
    port: "3000",
    pathname: "/",
    search: "",
    hash: "",
    assign: vi.fn(),
    replace: vi.fn(),
    reload: vi.fn(),
    toString: () => "http://localhost:3000/",
  },
});

// RU: Восстанавливаем оригинальный window.location после каждого теста
// EN: Restore original window.location after each test
afterEach(() => {
  // Reset mock functions
  const assign = window.location.assign as unknown as { mockClear?: () => void };
  const replace = window.location.replace as unknown as { mockClear?: () => void };
  const reload = window.location.reload as unknown as { mockClear?: () => void };
  assign.mockClear?.();
  replace.mockClear?.();
  reload.mockClear?.();

  // Reset href to default
  window.location.href = "http://localhost:3000/";
  window.location.pathname = "/";
  window.location.search = "";
  window.location.hash = "";
});

// RU: Полностью восстанавливаем оригинальный window.location в конце всех тестов
// EN: Fully restore original window.location at the end of all tests
// Note: This is commented out because jsdom doesn't allow restoring after delete
// If needed, tests should handle location mocking individually
/*
afterAll(() => {
  delete (window as any).location;
  window.location = originalLocation;
});
*/

// MSW temporarily disabled due to version conflicts
// TODO(#136): Fix MSW setup for jsdom environment
// MSW 2.x has compatibility issues with jsdom 22.x in Vitest
// Target: Q2 2025 or earlier
/*
import { server } from "./mocks/server";

beforeAll(() => {
  server.listen({
    onUnhandledRequest: "bypass",
  });
});

afterEach(() => {
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});
*/
