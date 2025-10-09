// RU: Расширяем expect матчерами jest-dom для RTL.
// EN: Extend expect with jest-dom matchers for RTL.
import "@testing-library/jest-dom";

// Note: window.location is non-configurable in jsdom.
// If you need to test location changes, use:
// - window.location.href = "..." for simple URL changes
// - history.pushState/replaceState for navigation
// - vi.spyOn(window.location, 'assign') for mocking navigation

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
