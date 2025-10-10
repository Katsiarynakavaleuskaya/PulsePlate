import { setProjectAnnotations } from '@storybook/react'; // NOT from react-vite
import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll, vi } from 'vitest';
import 'whatwg-fetch';
import { preview as projectAnnotations } from './.storybook/preview';

// Storybook annotations (global decorators/providers) in tests
setProjectAnnotations(projectAnnotations);

// Setup window.location for React Router tests
Object.defineProperty(window, 'location', {
  configurable: true,
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
    toString: () => 'http://localhost:3000/'
  }
});

// MSW setup
import { server } from './src/mocks/server';

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
