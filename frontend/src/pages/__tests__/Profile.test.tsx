import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Profile from '../Profile';

vi.mock('../../lib/auth', () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from '../../lib/auth';

describe('Profile', () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReturnValue({
      apiKey: null,
      isAuthenticated: false,
      isLoading: false,
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });
  });

  it('renders profile page content', () => {
    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>
    );

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'Profile' })).toBeInTheDocument();
    expect(screen.getByText('Configuration Status')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Configure API Key' })).toHaveAttribute('href', '/enter-key');
    expect(screen.getByRole('link', { name: 'Configure Nutrition Profile' })).toHaveAttribute('href', '/setup');
  });

  it('shows connected status for authenticated cookie session', () => {
    vi.mocked(useAuth).mockReturnValue({
      apiKey: null,
      isAuthenticated: true,
      isLoading: false,
      setApiKey: vi.fn(),
      clearApiKey: vi.fn(),
      showAuthPrompt: false,
      setShowAuthPrompt: vi.fn(),
    });

    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>
    );

    expect(screen.getByText('Connected')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Update API Key' })).toHaveAttribute('href', '/enter-key');
  });

  it('has correct CSS classes', () => {
    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>
    );

    const main = screen.getByRole('main');
    expect(main).toHaveClass('flex');
    expect(main).toHaveClass('min-h-screen');
    expect(main).toHaveClass('flex-col');
  });

});
