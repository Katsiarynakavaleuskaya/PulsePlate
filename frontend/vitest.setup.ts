import 'whatwg-fetch';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { setProjectAnnotations } from '@storybook/react'; // НЕ из react-vite
import { preview as projectAnnotations } from './.storybook/preview';
import '@testing-library/jest-dom/vitest';

// Storybook annotations (global decorators/providers) in tests
setProjectAnnotations(projectAnnotations);

// MSW setup
import { server } from './src/test/msw/server';

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
