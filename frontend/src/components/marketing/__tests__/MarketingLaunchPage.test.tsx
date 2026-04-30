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

  it('keeps tier copy bounded without unsupported pricing or proof claims', () => {
    const { container } = renderMarketingPage();

    expect(screen.getByText(/VIP preview language without pricing or billing claims/i)).toBeInTheDocument();
    expect(screen.getByText('Guided wellness prompts')).toBeInTheDocument();
    expect(container).not.toHaveTextContent(/Product Hunt|#1|doctor[-\s]?recommended|guaranteed|diagnose/i);
    expect(container).not.toHaveTextContent(/\$\d/);
  });
});
