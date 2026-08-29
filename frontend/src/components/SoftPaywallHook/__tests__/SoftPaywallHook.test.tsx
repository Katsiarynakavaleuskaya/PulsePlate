/** @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest';
import '../../../i18n';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import type { components } from '../../../api/schema';
import SoftPaywallHook from '../SoftPaywallHook';

const backendHook: components['schemas']['SoftPaywallHook'] = {
  id: 'bmi.pro_interpretation_v1',
  kind: 'cta',
  position: 'post_result',
  priority: 50,
  target: 'pro_paywall',
  message: {
    lang: 'en',
    title_key: 'soft_paywall.title',
    body_key: 'soft_paywall.body',
    cta_key: 'soft_paywall.cta',
    default_title: 'Buy the browser plan now',
    default_body: 'Start a trial and subscribe.',
    default_cta: 'Upgrade',
  },
  availability: { pro_available: true },
};

const backendNextAction: components['schemas']['NextBestAction'] = {
  type: 'upgrade_for_export',
  recommended_surface: 'pro_targets',
  recommended_tier: 'PRO',
  trigger_reason: 'targets_ready',
  why_now: 'legacy_purchase_hint',
};

function renderHook(
  hook: components['schemas']['SoftPaywallHook'] | null | undefined,
  nextBestAction: components['schemas']['NextBestAction'] | null | undefined = undefined
): ReturnType<typeof render> {
  return render(
    <MemoryRouter>
      <SoftPaywallHook hook={hook} nextBestAction={nextBestAction} />
    </MemoryRouter>
  );
}

describe('SoftPaywallHook information boundary', () => {
  it('renders fixed localized copy and only the marketing destination', () => {
    renderHook(backendHook);

    expect(screen.getByRole('heading', { name: 'Keep exploring for free' })).toBeInTheDocument();
    expect(screen.getByText('This website is free to use.')).toBeInTheDocument();
    expect(
      screen.getByText(
        'We’re designing more advanced FitChef features for PulsePlate on Apple devices.'
      )
    ).toBeInTheDocument();
    expect(screen.getByText('Purchases are not offered on this website.')).toBeInTheDocument();
    expect(
      screen.getByText(
        'We’ll add a verified App Store link when public availability is confirmed.'
      )
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Learn about PulsePlate for Apple devices' })
    ).toHaveAttribute('href', '/marketing');
    expect(screen.queryByText(/buy the browser plan|start a trial|subscribe|upgrade/i)).not.toBeInTheDocument();
  });

  it.each([null, undefined])('renders nothing for %s hook', (hook) => {
    const { container } = renderHook(hook);

    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when backend availability is false', () => {
    const { container } = renderHook({
      ...backendHook,
      availability: { pro_available: false },
    });

    expect(container.firstChild).toBeNull();
  });

  it('does not let next_best_action choose copy, navigation, or effects', () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    renderHook(backendHook, backendNextAction);

    expect(document.body).not.toHaveTextContent(
      /upgrade_for_export|pro_targets|targets_ready|legacy_purchase_hint/i
    );
    expect(screen.getByTestId('soft-paywall-cta')).toHaveAttribute('href', '/marketing');
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
