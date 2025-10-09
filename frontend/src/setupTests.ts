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
  host: 'localhost:3000',
  hostname: 'localhost',
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

// MSW temporarily disabled due to import issues
// TODO: Fix MSW setup for jsdom environment
