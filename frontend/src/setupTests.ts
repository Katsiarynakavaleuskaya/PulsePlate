import '@testing-library/jest-dom';
import { toHaveNoViolations } from 'jest-axe';
import { configure } from '@testing-library/react';
import { server } from './mocks/server';
import { vi } from 'vitest';

// Extend Jest matchers with axe accessibility matchers
expect.extend(toHaveNoViolations);

// Configure Testing Library
configure({ testIdAttribute: 'data-testid' });

// Setup window.location for React Router tests
delete (window as any).location;
(window as any).location = {
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
};

// Поднимаем MSW до тестов
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
