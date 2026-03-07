import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Profile from '../Profile';

vi.mock('../../lib/auth', () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from '../../lib/auth';

function mockAuthState({
  isAuthenticated = false,
  isLoading = false,
}: {
  isAuthenticated?: boolean;
  isLoading?: boolean;
} = {}) {
  vi.mocked(useAuth).mockReturnValue({
    apiKey: null,
    isAuthenticated,
    isLoading,
    setApiKey: vi.fn(),
    clearApiKey: vi.fn(),
    showAuthPrompt: false,
    setShowAuthPrompt: vi.fn(),
  });
}

describe('Profile', () => {
  beforeEach(() => {
    mockAuthState();
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
    mockAuthState({ isAuthenticated: true });

    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>
    );

    expect(screen.getByText('Connected')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Update API Key' })).toHaveAttribute('href', '/enter-key');
  });

  it('shows neutral loading state during session bootstrap', () => {
    mockAuthState({ isLoading: true });

    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>
    );

    expect(screen.getByText('Checking')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Checking Session' })).toHaveAttribute('href', '/enter-key');
    expect(screen.queryByRole('link', { name: 'Configure API Key' })).not.toBeInTheDocument();
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
