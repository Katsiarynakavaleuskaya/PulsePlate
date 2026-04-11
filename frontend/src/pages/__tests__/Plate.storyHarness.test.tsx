import { afterEach, describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import '../../i18n';
import { setApiClientDependencies } from '../../api/client';
import Plate from '../Plate';

const STORYBOOK_API_BASE = 'https://storybook.pulseplate.local';

describe('Plate story harness parity', () => {
  const originalFetch = global.fetch.bind(global);

  afterEach(() => {
    global.fetch = originalFetch;
    setApiClientDependencies(null);
  });

  it('renders unlocked premium controls when the parity-pack session stub is active', async () => {
    setApiClientDependencies({
      getStoredApiKey: () => null,
      clearStoredApiKey: () => undefined,
      apiBase: STORYBOOK_API_BASE,
    });

    global.fetch = (async (input: RequestInfo | URL): Promise<Response> => {
      const requestUrl = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
      if (requestUrl.endsWith('/api/v1/pro/session')) {
        return new Response(
          JSON.stringify({
            status: 'ok',
            authenticated: true,
            auth_source: 'cookie',
            tier: 'PRO',
          }),
          {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }
        );
      }

      return originalFetch(input);
    }) as typeof global.fetch;

    render(
      <MemoryRouter initialEntries={['/plate']}>
        <Plate />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Premium Nutrition Controls')).toBeInTheDocument();
    });

    expect(screen.getByRole('link', { name: 'Configure Setup' })).toHaveAttribute('href', '/setup');
    expect(screen.getByRole('link', { name: 'View Progress' })).toHaveAttribute('href', '/progress');
  });
});
