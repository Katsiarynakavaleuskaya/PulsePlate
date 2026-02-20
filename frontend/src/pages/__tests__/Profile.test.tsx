import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Profile from '../Profile';

describe('Profile', () => {

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
