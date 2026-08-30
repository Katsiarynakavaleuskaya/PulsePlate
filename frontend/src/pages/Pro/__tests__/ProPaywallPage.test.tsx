/** @vitest-environment jsdom */
import '../../../test/setup';
import '../../../i18n';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import ProPaywallPage from '../ProPaywallPage';

function renderAtProRoute(state?: Record<string, unknown>): ReturnType<typeof render> {
  return render(
    <MemoryRouter initialEntries={[{ pathname: '/pro', state }]}>
      <Routes>
        <Route path="/pro" element={<ProPaywallPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ProPaywallPage compatibility route', () => {
  it('renders information only with the two safe destinations', () => {
    renderAtProRoute();

    expect(
      screen.getByRole('heading', { level: 1, name: 'PulsePlate for Apple devices' })
    ).toBeInTheDocument();
    expect(screen.getByText('This website is free to use.')).toBeInTheDocument();
    expect(screen.getByText('Purchases are not offered on this website.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Try the free BMI calculator' })).toHaveAttribute(
      'href',
      '/bmi'
    );
    expect(
      screen.getByRole('link', { name: 'Learn about PulsePlate for Apple devices' })
    ).toHaveAttribute('href', '/marketing');
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /buy|subscribe|upgrade|trial|restore/i })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/auto-renew|payment error|available now|download/i);
  });

  it('ignores legacy route state instead of restoring an acquisition flow', () => {
    renderAtProRoute({
      exposureId: 'legacy-exposure',
      source: 'bmi_soft_paywall',
      triggerReason: 'post_bmi',
      via: 'pro_page',
      actionType: 'upgrade_for_export',
      recommendedSurface: 'pro_targets',
      recommendedTier: 'PRO',
      whyNow: 'legacy-upgrade-context',
    });

    expect(screen.getByTestId('apple-product-info-card')).toBeInTheDocument();
    expect(screen.queryByText(/legacy|upgrade_for_export|pro_targets/i)).not.toBeInTheDocument();
    expect(screen.queryByTestId('paywall-purchase-error')).not.toBeInTheDocument();
  });

  it('has no targeted accessibility violations', async () => {
    const { container } = renderAtProRoute();

    expect(await axe(container)).toHaveNoViolations();
  });
});
