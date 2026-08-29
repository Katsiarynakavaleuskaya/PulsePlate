import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import PulsePlateMarketingPage from '../../../pages/Marketing/PulsePlateMarketingPage';

const renderMarketingPage = (): ReturnType<typeof render> =>
  render(
    <MemoryRouter>
      <PulsePlateMarketingPage />
    </MemoryRouter>,
  );

describe('PulsePlateMarketingPage', () => {
  it('renders the polished wellness-safe launch hero and existing CTAs', () => {
    renderMarketingPage();

    expect(screen.getByTestId('marketing-page')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'Plan meals and progress with calmer structure',
      }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/without medical claims/i)).toHaveLength(2);
    expect(screen.getByRole('link', { name: /open the app/i })).toHaveAttribute('href', '/app');
    screen
      .getAllByRole('link', { name: /join early access/i })
      .forEach((link) => expect(link).toHaveAttribute('href', '/enter-key'));
    expect(screen.getByLabelText('PulsePlate product preview')).toBeInTheDocument();
  });

  it('keeps the Web tier area free and information-only', () => {
    const { container } = renderMarketingPage();
    const tiers = container.querySelector('#tiers');

    if (!(tiers instanceof HTMLElement)) {
      throw new Error('Marketing tiers section not found');
    }

    expect(screen.getByRole('heading', { name: 'Start here for free' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Free web tools' })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'What we’re designing for FitChef' })
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'App Store link' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Try the free BMI calculator' })).toHaveAttribute(
      'href',
      '/bmi'
    );
    expect(tiers.querySelectorAll('a')).toHaveLength(1);
    expect(tiers).not.toHaveTextContent(/available now|explore pro|upgrade when ready/i);
    expect(tiers.querySelector('a[href="/pro"]')).toBeNull();
    expect(container).not.toHaveTextContent(/Product Hunt|#1|doctor[-\s]?recommended|guaranteed|diagnose/i);
    expect(container).not.toHaveTextContent(/\$\d/);
  });
});
