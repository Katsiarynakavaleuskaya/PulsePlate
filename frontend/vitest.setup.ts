import 'whatwg-fetch';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { setProjectAnnotations } from '@storybook/react'; // НЕ из react-vite
import * as projectAnnotations from './.storybook/preview';
import '@testing-library/jest-dom/vitest';

// Storybook annotations (глобальные декораторы/провайдеры) в тестах
setProjectAnnotations(projectAnnotations as any);

// MSW setup
import { server } from './src/test/msw/server';

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
