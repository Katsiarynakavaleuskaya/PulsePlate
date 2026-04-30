import { describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { createElement, useEffect } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '../../i18n';
import {
  ProPaywallStorySurface,
  StorybookApiStub,
} from '../storybookParitySupport';

const frontendRoot = resolve(__dirname, '../../..');

function readFrontend(path: string): string {
  return readFileSync(resolve(frontendRoot, path), 'utf8');
}

describe('PR-8 Storybook parity surfaces', () => {
  it('keeps the Storybook addon split free of the uuid carrier addons', () => {
    const storybookMain = readFrontend('.storybook/main.ts');

    expect(storybookMain).not.toContain('@storybook/addon-actions');
    expect(storybookMain).not.toContain('@storybook/addon-interactions');
    expect(storybookMain).not.toContain('@storybook/addon-essentials');
  });

  it('registers review-only parity stories for implemented product surfaces', () => {
    const productStories = [
      'src/pages/Home.stories.tsx',
      'src/pages/NutritionSetup.stories.tsx',
      'src/pages/Pro/ProPaywallPage.stories.tsx',
      'src/pages/Plate.stories.tsx',
      'src/pages/Progress.stories.tsx',
    ];

    for (const storyPath of productStories) {
      expect(readFrontend(storyPath)).toContain('PulsePlate/Parity Pack/');
    }
  });

  it('documents governed primitive state coverage in Storybook', () => {
    const primitiveStories = [
      'src/components/ui/Button.stories.tsx',
      'src/components/ui/Skeleton.stories.tsx',
      'src/components/ui/EmptyState.stories.tsx',
    ];

    for (const storyPath of primitiveStories) {
      expect(readFrontend(storyPath)).toMatch(/Loading|State|Status|Disabled|Error|Decorative/);
    }
  });

  it('uses local Storybook fixtures instead of live backend URLs', () => {
    const support = readFrontend('src/stories/storybookParitySupport.tsx');

    expect(support).toContain('https://storybook.pulseplate.local');
    expect(support).toContain('setApiClientDependencies');
    expect(support).toContain('Unhandled Storybook API fixture');
    expect(support).not.toContain('localhost');
  });

  it('fails closed for unhandled Storybook API requests without touching live fetch', async () => {
    const originalFetch = window.fetch;
    const liveFetch = vi.fn(async () => new Response('live backend should not be called'));
    window.fetch = liveFetch as unknown as typeof window.fetch;

    function UnhandledApiProbe() {
      useEffect(() => {
        void fetch('/api/v1/storybook/unhandled').then(async (response) => {
          document.body.dataset.storybookUnhandledStatus = String(response.status);
          document.body.dataset.storybookUnhandledPayload = await response.text();
        });
      }, []);

      return createElement('div', null, 'Unhandled API probe');
    }

    try {
      render(
        createElement(StorybookApiStub, null, createElement(UnhandledApiProbe))
      );

      await waitFor(() => {
        expect(document.body.dataset.storybookUnhandledStatus).toBe('500');
      });
      expect(document.body.dataset.storybookUnhandledPayload).toContain(
        'Unhandled Storybook API fixture'
      );
      expect(liveFetch).not.toHaveBeenCalled();
    } finally {
      delete document.body.dataset.storybookUnhandledStatus;
      delete document.body.dataset.storybookUnhandledPayload;
      window.fetch = originalFetch;
    }
  });

  it('does not treat Storybook hostname prefixes as the fixture origin', async () => {
    const originalFetch = window.fetch;
    const liveFetch = vi.fn(async () => new Response('external host'));
    window.fetch = liveFetch as unknown as typeof window.fetch;

    function SpoofedOriginProbe() {
      useEffect(() => {
        void fetch('https://storybook.pulseplate.local.evil.test/api/v1/pro/session');
      }, []);

      return createElement('div', null, 'Spoofed origin probe');
    }

    try {
      render(
        createElement(StorybookApiStub, null, createElement(SpoofedOriginProbe))
      );

      await waitFor(() => {
        expect(liveFetch).toHaveBeenCalledTimes(1);
      });
    } finally {
      window.fetch = originalFetch;
    }
  });

  it('renders the Pro paywall review surface behind the local API stub', async () => {
    const originalFetch = window.fetch;
    const liveFetch = vi.fn(async () => new Response('live backend should not be called'));
    window.fetch = liveFetch as unknown as typeof window.fetch;

    try {
      render(createElement(ProPaywallStorySurface));

      expect(await screen.findByTestId('paywall-cta')).toBeInTheDocument();
      await waitFor(() => {
        expect(liveFetch).not.toHaveBeenCalled();
      });
    } finally {
      window.fetch = originalFetch;
    }
  });
});
