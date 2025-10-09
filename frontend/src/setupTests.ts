// RU: Расширяем expect матчерами jest-dom для RTL.
// EN: Extend expect with jest-dom matchers for RTL.
import "@testing-library/jest-dom";

// Setup window.location for React Router tests
// Temporarily disabled due to jsdom issues
/*
Object.defineProperty(window, 'location', {
  writable: true,
  value: {
  href: 'http://localhost:3000/',
  origin: 'http://localhost:3000',
  protocol: 'http:',
  host: 'localhost',
  port: '3000',
  pathname: '/',
  search: '',
  hash: '',
  replace: vi.fn(),
  assign: vi.fn(),
  reload: vi.fn(),
  toString: function() { return this.href; }
  }
});
*/

// MSW temporarily disabled due to version conflicts
// TODO(#<issue-number>): Fix MSW setup for jsdom environment
// MSW 2.x has compatibility issues with jsdom 22.x in Vitest
// Target: Sprint X or Q2 2025
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
